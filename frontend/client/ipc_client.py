"""IPC 客户端 (TCP Localhost)"""
import json
import httpx
from pathlib import Path
import platform
import time
import os
from typing import Optional, AsyncIterator, List, Dict, Any
import asyncio
from dotenv import load_dotenv
from frontend.client.stream_receiver import StreamReceiver

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

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
        """加载端口号（优先从 .env 读取 BACKEND_PORT，如果不可用则尝试发现）"""
        # 1. 优先从环境变量读取（从 .env 文件加载）
        # 加载 .env 文件（优先级：用户配置目录 > 项目根目录 > 当前目录）
        from shared.platform_utils import get_app_data_dir
        config_dir = Path.home() / ".config" / "hou-cli"
        env_paths = [
            config_dir / ".env",  # 用户配置目录
            PROJECT_ROOT / '.env',  # 项目根目录
            Path.cwd() / '.env',  # 当前目录
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                break
        
        # 从环境变量读取 BACKEND_PORT
        backend_port_str = os.getenv("BACKEND_PORT")
        if backend_port_str:
            try:
                port = int(backend_port_str.strip())
                # 验证端口是否可用
                if self._verify_port(port):
                    return port
            except (ValueError, TypeError):
                pass
        
        # 2. 如果环境变量未设置或端口不可用，尝试从端口文件读取（向后兼容）
        port_file = self._get_port_file()
        if port_file.exists():
            try:
                port = int(port_file.read_text().strip())
                # 验证端口是否可用
                if self._verify_port(port):
                    return port
            except (ValueError, FileNotFoundError):
                pass
        
        # 3. 如果都失败，尝试发现后端端口
        discovered_port = self._discover_backend_port()
        if discovered_port:
            return discovered_port
        
        # 4. 如果都失败，抛出异常
        raise ConnectionError("无法连接到后端服务：请检查 .env 文件中的 BACKEND_PORT 配置或确保后端服务正在运行")
    
    def _verify_port(self, port: int) -> bool:
        """验证端口是否可用（通过健康检查）"""
        try:
            temp_client = httpx.Client(timeout=2.0, trust_env=False)
            response = temp_client.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
            temp_client.close()
            return response.status_code == 200
        except Exception:
            return False
    
    def _discover_backend_port(self) -> Optional[int]:
        """尝试发现后端端口（扫描常见端口范围）"""
        # 从端口文件读取的端口附近开始扫描（如果存在）
        port_file = self._get_port_file()
        start_port = None
        if port_file.exists():
            try:
                start_port = int(port_file.read_text().strip())
            except (ValueError, FileNotFoundError):
                pass
        
        # 扫描范围：从 start_port 开始，前后各扫描 100 个端口
        # 如果没有 start_port，从 8000 开始扫描到 8100
        if start_port:
            ports_to_try = []
            # 先尝试 start_port 本身
            ports_to_try.append(start_port)
            # 然后尝试 start_port 附近的端口（±100）
            for offset in range(1, 101):
                if start_port + offset <= 65535:
                    ports_to_try.append(start_port + offset)
                if start_port - offset >= 1024:
                    ports_to_try.append(start_port - offset)
        else:
            # 从 8000 开始扫描到 8100
            ports_to_try = list(range(8000, 8101))
        
        # 尝试每个端口
        for port in ports_to_try:
            if self._verify_port(port):
                # 发现可用端口，更新端口文件
                try:
                    port_file.write_text(str(port))
                except Exception:
                    pass  # 忽略写入错误
                return port
        
        return None
    
    def _connect(self):
        """连接到后端服务"""
        try:
            self.port = self._load_port()
            self.base_url = f"http://127.0.0.1:{self.port}"
        except ConnectionError as e:
            # 如果加载端口失败，尝试发现后端
            discovered_port = self._discover_backend_port()
            if discovered_port:
                self.port = discovered_port
                self.base_url = f"http://127.0.0.1:{self.port}"
            else:
                raise ConnectionError(f"无法连接到后端服务\n提示: 请检查后端服务是否正常运行")
        
        # 先验证连接（使用临时客户端）
        if not self.health_check():
            # 如果健康检查失败，再次尝试发现端口
            discovered_port = self._discover_backend_port()
            if discovered_port:
                self.port = discovered_port
                self.base_url = f"http://127.0.0.1:{self.port}"
                # 再次验证
                if not self.health_check():
                    raise ConnectionError(f"无法连接到后端服务：{self.base_url}\n提示: 请检查后端服务是否正常运行")
            else:
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
        
        # 创建流式接收器
        self.stream_receiver = StreamReceiver(self.base_url, self.async_client)
    
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
        import json
        import time
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ipc_client.py:stream_send:entry","message":"stream_send被调用","data":{"message_length":len(message) if message else 0,"session_id":session_id,"base_url":self.base_url},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ipc_client.py:stream_send:before_receive_stream","message":"准备调用receive_stream","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 使用 StreamReceiver 接收流式数据
        chunk_count = 0
        try:
            # 从环境变量读取超时配置，默认300秒（5分钟）
            import os
            stream_timeout = float(os.getenv("STREAM_TIMEOUT", "300.0"))
            async for chunk in self.stream_receiver.receive_stream(message, session_id, timeout=stream_timeout):
                chunk_count += 1
                # #region agent log
                if chunk_count <= 3:  # 只记录前3个chunk
                    try:
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ipc_client.py:stream_send:yield_chunk","message":"准备yield chunk","data":{"chunk_count":chunk_count},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                            f.flush()
                    except: pass
                # #endregion
                yield chunk
        except Exception as e:
            # #region agent log
            try:
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ipc_client.py:stream_send:exception","message":"stream_send异常","data":{"error":str(e),"chunk_count":chunk_count},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
            raise
    
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
