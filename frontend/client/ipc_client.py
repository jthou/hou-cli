"""IPC 客户端 (TCP Localhost)"""
import json
import httpx
from pathlib import Path
import platform
import time
from typing import Optional, AsyncIterator

class IPCClient:
    """跨平台 IPC 客户端"""
    
    def __init__(self, max_retries: int = 5, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.port = None
        self.base_url = None
        self.client = None
        self.async_client = None
        self._connect()
    
    def _get_port_file(self) -> Path:
        """获取端口文件路径（跨平台）"""
        if platform.system() == "Windows":
            base = Path.home() / "AppData" / "Local" / "hou-cli"
        elif platform.system() == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support" / "hou-cli"
        else:  # Linux
            base = Path.home() / ".local" / "share" / "hou-cli"
        
        base.mkdir(parents=True, exist_ok=True)
        return base / "port.txt"
    
    def _load_port(self) -> int:
        """加载端口号"""
        port_file = self._get_port_file()
        
        # 重试读取端口文件
        for _ in range(self.max_retries):
            if port_file.exists():
                try:
                    port = int(port_file.read_text().strip())
                    return port
                except (ValueError, FileNotFoundError):
                    pass
            time.sleep(self.retry_delay)
        
        raise ConnectionError("无法连接到后端服务：端口文件不存在")
    
    def _connect(self):
        """连接到后端服务"""
        self.port = self._load_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.client = httpx.Client(timeout=30.0)
        self.async_client = httpx.AsyncClient(timeout=30.0)
        
        # 验证连接
        if not self.health_check():
            raise ConnectionError(f"无法连接到后端服务：{self.base_url}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    def send(self, message: str, session_id: Optional[str] = None) -> str:
        """
        发送消息（非流式）
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选）
            
        Returns:
            LLM 生成的回复
        """
        try:
            payload = {"message": message}
            if session_id:
                payload["session_id"] = session_id
            
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result["status"] == "success":
                return result["response"]
            else:
                raise Exception(result.get("error", "未知错误"))
        
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    async def stream_send(self, message: str, session_id: Optional[str] = None) -> AsyncIterator[str]:
        """
        发送消息（流式 SSE）
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选）
            
        Yields:
            流式数据块
        """
        # 确保异步客户端存在
        if not self.async_client:
            self.async_client = httpx.AsyncClient(timeout=60.0)
        
        url = f"{self.base_url}/api/chat/stream"
        try:
            payload = {"message": message}
            if session_id:
                payload["session_id"] = session_id
            
            async with self.async_client.stream(
                "POST",
                url,
                json=payload,
                timeout=60.0
            ) as response:
                # 检查状态码
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"HTTP 错误 {response.status_code}: {error_text.decode('utf-8', errors='ignore')}")
                
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode('utf-8', errors='ignore')
                    
                    # 处理 SSE 格式：data: {json}\n\n
                    while "\n\n" in buffer:
                        line, buffer = buffer.split("\n\n", 1)
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # 跳过 "data: "
                                if data.get("status") == "streaming":
                                    yield data.get("content", "")
                                elif data.get("status") == "done":
                                    return
                                elif data.get("status") == "error":
                                    raise Exception(data.get("error", "未知错误"))
                            except json.JSONDecodeError:
                                continue
        
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            error_text = ""
            try:
                if hasattr(e.response, 'text'):
                    error_text = e.response.text
            except:
                pass
            raise Exception(f"HTTP 错误 {e.response.status_code}: {error_text}")
    
    def close(self):
        """关闭客户端"""
        if self.client:
            self.client.close()
        # async_client 会在使用完毕后自动关闭，或者通过 async with 管理
        # 这里不主动关闭，避免事件循环问题
    
    async def aclose(self):
        """异步关闭客户端"""
        if self.async_client:
            await self.async_client.aclose()

