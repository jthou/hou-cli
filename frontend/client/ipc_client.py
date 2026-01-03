"""IPC 客户端 (TCP Localhost)"""
import json
import httpx
import requests  # 用于健康检查和流式请求，httpx 在某些情况下可能有问题
from pathlib import Path
import platform
import time
from typing import Optional, AsyncIterator, List, Dict, Any
import asyncio

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
        
        # 先验证连接（使用临时客户端）
        if not self.health_check():
            raise ConnectionError(f"无法连接到后端服务：{self.base_url}\n提示: 请检查后端服务是否正常运行")
        
        # 连接验证成功后，创建持久客户端
        # 配置代理：跳过本地地址（127.0.0.1, localhost），避免代理问题
        # httpx 通过设置 trust_env=False 来忽略环境变量中的代理设置
        # 对于本地地址，httpx 会自动跳过代理，但为了确保，我们明确禁用代理
        self.client = httpx.Client(
            timeout=30.0, 
            follow_redirects=True,
            trust_env=False  # 不信任环境变量中的代理设置，避免代理问题
        )
        self.async_client = httpx.AsyncClient(
            timeout=30.0, 
            follow_redirects=True,
            trust_env=False  # 不信任环境变量中的代理设置，避免代理问题
        )
    
    def health_check(self) -> bool:
        """健康检查（带重试，使用 requests 库）"""
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # 使用 requests 库进行健康检查，因为 httpx 在某些情况下可能返回 502
                response = requests.get(
                    f"{self.base_url}/health", 
                    timeout=10.0,
                    proxies=self._get_no_proxy_config()
                )
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 502 and attempt < max_retries - 1:
                    # 502 可能是服务还在启动，等待后重试
                    time.sleep(retry_delay)
                    continue
                else:
                    return False
            except requests.exceptions.ConnectionError as e:
                # 连接错误：服务可能未启动或端口错误
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False
            except requests.exceptions.Timeout as e:
                # 超时：服务可能响应慢或不可用
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False
            except Exception as e:
                # 其他错误
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False
        
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
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            payload = {"message": message}
            if session_id:
                payload["session_id"] = session_id
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result["status"] == "success":
                return result["response"]
            else:
                raise Exception(result.get("error", "未知错误"))
        
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
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
        url = f"{self.base_url}/api/chat/stream"
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        # 使用 requests 库进行流式请求，因为 httpx 在某些情况下可能返回 502
        # 在异步函数中运行同步的 requests 请求
        loop = asyncio.get_event_loop()
        try:
            # 在 lambda 中无法直接使用 self，所以先获取代理配置
            no_proxy = self._get_no_proxy_config()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, stream=True, timeout=60.0, proxies=no_proxy)
            )
            
            # 检查状态码
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else f"状态码: {response.status_code}"
                response.close()
                raise Exception(f"HTTP 错误 {response.status_code}: {error_text}")
            
            try:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8', errors='ignore')
                        # 每行就是一个完整的 SSE 消息（data: {...}）
                        if line_str.startswith("data: "):
                            try:
                                # 解析JSON，会自动处理Unicode转义序列
                                data = json.loads(line_str[6:])  # 跳过 "data: "
                                if data.get("status") == "streaming":
                                    content = data.get("content", "")
                                    if content:  # 只yield非空内容
                                        yield content
                                elif data.get("status") == "done":
                                    return
                                elif data.get("status") == "error":
                                    raise Exception(data.get("error", "未知错误"))
                            except json.JSONDecodeError:
                                # 忽略解析错误，继续处理下一行
                                continue
            finally:
                response.close()
        
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except Exception as e:
            if "HTTP 错误" in str(e):
                raise
            raise Exception(f"请求失败：{str(e)}")
    
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
    
    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        列出最近的会话
        
        Args:
            limit: 返回数量限制
            
        Returns:
            会话列表（包含预览信息）
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.get(
                f"{self.base_url}/api/sessions/list",
                params={"limit": limit},
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(result["error"])
            
            # 转换时间字符串为 datetime 对象（用于显示）
            sessions = result.get("sessions", [])
            for session in sessions:
                from datetime import datetime
                if isinstance(session.get("created_at"), str):
                    session["created_at"] = datetime.fromisoformat(session["created_at"])
                if isinstance(session.get("updated_at"), str):
                    session["updated_at"] = datetime.fromisoformat(session["updated_at"])
            
            return sessions
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否删除成功
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.delete(
                f"{self.base_url}/api/sessions/{session_id}",
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True
            else:
                raise Exception(result.get("error", "删除失败"))
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"会话不存在: {session_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def clear_session_messages(self, session_id: str) -> bool:
        """
        清除会话的所有消息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否清除成功
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.post(
                f"{self.base_url}/api/sessions/{session_id}/clear",
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True
            else:
                raise Exception(result.get("error", "清除失败"))
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"会话不存在: {session_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话详情（包含消息列表）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话详情和消息列表
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.get(
                f"{self.base_url}/api/sessions/{session_id}",
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result
            else:
                raise Exception(result.get("error", "获取失败"))
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"会话不存在: {session_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def create_session(self) -> str:
        """
        创建新会话
        
        Returns:
            新会话的 ID
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.post(
                f"{self.base_url}/api/sessions",
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("session_id")
            else:
                raise Exception(result.get("error", "创建失败"))
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def search_sessions(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索包含关键词的会话
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的会话列表
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.get(
                f"{self.base_url}/api/sessions/search",
                params={"keyword": keyword, "limit": limit},
                timeout=10.0,
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(result["error"])
            
            # 转换时间字符串为 datetime 对象
            sessions = result.get("sessions", [])
            for session in sessions:
                from datetime import datetime
                if isinstance(session.get("created_at"), str):
                    session["created_at"] = datetime.fromisoformat(session["created_at"])
                if isinstance(session.get("updated_at"), str):
                    session["updated_at"] = datetime.fromisoformat(session["updated_at"])
            
            return sessions
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def generate_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        生成会话摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            摘要信息
        """
        try:
            # 使用 requests 库，因为 httpx 在某些情况下可能返回 502
            import requests
            response = requests.post(
                f"{self.base_url}/api/sessions/{session_id}/summary",
                timeout=60.0,  # 生成摘要可能需要更长时间
                proxies=self._get_no_proxy_config()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result
            else:
                raise Exception(result.get("error", "生成失败"))
        except requests.RequestException as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"会话不存在: {session_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
