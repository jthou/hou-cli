"""IPC 客户端 (TCP Localhost)"""
import json
import httpx
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
        # 注意：httpx 对本地地址（127.0.0.1, localhost）默认会跳过代理
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
        """健康检查（带重试，使用 httpx）"""
        max_retries = 3
        retry_delay = 0.5
        
        # 使用临时客户端进行健康检查
        temp_client = httpx.Client(timeout=10.0, trust_env=False)
        
        try:
            for attempt in range(max_retries):
                try:
                    response = temp_client.get(f"{self.base_url}/health", timeout=10.0)
                    
                    if response.status_code == 200:
                        return True
                    elif response.status_code == 502 and attempt < max_retries - 1:
                        # 502 可能是服务还在启动，等待后重试
                        time.sleep(retry_delay)
                        continue
                    else:
                        return False
                except httpx.RequestError:
                    # 连接错误：服务可能未启动或端口错误
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return False
                except Exception:
                    # 其他错误
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return False
            
            return False
        finally:
            temp_client.close()
    
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
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
        url = f"{self.base_url}/api/chat/stream"
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        # 使用 httpx.AsyncClient 进行流式请求，已配置 trust_env=False 跳过代理
        # 增加超时时间到 300 秒（5分钟），以支持长时间运行的任务（如读取和编辑 MediaWiki 页面）
        try:
            async with self.async_client.stream(
                "POST",
                url,
                json=payload,
                timeout=300.0,  # 增加到 5 分钟，支持复杂任务
                headers={"Accept": "text/event-stream"}
            ) as response:
                # 检查状态码
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_text = error_text.decode('utf-8')[:500] if error_text else f"状态码: {response.status_code}"
                    raise Exception(f"流式请求失败: {error_text}")
                
                # 解析 SSE 格式
                try:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            try:
                                # 直接解析 JSON，不需要 unicode_escape（后端已使用 ensure_ascii=False）
                                # 如果后端使用了 ensure_ascii=False，JSON 中的 emoji 会保持原样
                                data = json.loads(data_str)
                                
                                if data.get("status") == "streaming":
                                    content = data.get("content", "")
                                    if content:  # 只yield非空内容
                                        yield content
                                elif data.get("status") == "done":
                                    return
                                elif data.get("status") == "error":
                                    raise Exception(data.get("error", "未知错误"))
                            except json.JSONDecodeError:
                                # JSON 解析失败，跳过这一行
                                continue
                except KeyboardInterrupt:
                    # 用户按 Ctrl+C，终止流式请求
                    # 关闭响应连接
                    await response.aclose()
                    raise  # 重新抛出，让调用者知道是用户中断
        except httpx.TimeoutException as e:
            raise ConnectionError(f"流式请求超时: 任务处理时间过长（超过 5 分钟）。请尝试将任务分解为更小的步骤。")
        except httpx.RequestError as e:
            error_msg = str(e)
            # 提供更友好的错误信息
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise ConnectionError(f"流式请求连接超时: {error_msg}\n提示: 任务可能过于复杂，请尝试分解为更小的步骤，或检查后端服务是否正常运行")
            else:
                raise ConnectionError(f"流式请求连接错误: {error_msg}\n提示: 请检查后端服务是否正常运行")
        except Exception as e:
            if "流式请求失败" in str(e) or "未知错误" in str(e):
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.get(
                f"{self.base_url}/api/sessions/list",
                params={"limit": limit},
                timeout=10.0
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
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.delete(
                f"{self.base_url}/api/sessions/{session_id}",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True
            else:
                raise Exception(result.get("error", "删除失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.post(
                f"{self.base_url}/api/sessions/{session_id}/clear",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True
            else:
                raise Exception(result.get("error", "清除失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.get(
                f"{self.base_url}/api/sessions/{session_id}",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result
            else:
                raise Exception(result.get("error", "获取失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.post(
                f"{self.base_url}/api/sessions",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("session_id")
            else:
                raise Exception(result.get("error", "创建失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.get(
                f"{self.base_url}/api/sessions/search",
                params={"keyword": keyword, "limit": limit},
                timeout=10.0
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
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            工具列表
        """
        try:
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.get(
                f"{self.base_url}/api/tools/list",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("tools", [])
            else:
                raise Exception(result.get("error", "获取失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
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
            # 使用 httpx 客户端，已配置 trust_env=False 跳过代理
            response = self.client.post(
                f"{self.base_url}/api/sessions/{session_id}/summary",
                timeout=60.0  # 生成摘要可能需要更长时间
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result
            else:
                raise Exception(result.get("error", "生成失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"会话不存在: {session_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
