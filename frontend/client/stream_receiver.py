"""流式接收模块 - 负责从后端接收流式数据"""
import json
from typing import AsyncIterator, Optional
import httpx
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class StreamReceiver:
    """流式数据接收器，负责从 HTTP SSE 流中接收数据"""
    
    def __init__(self, base_url: str, async_client: httpx.AsyncClient):
        self.base_url = base_url
        self.async_client = async_client
    
    async def receive_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        timeout: float = 300.0
    ) -> AsyncIterator[str]:
        """
        接收流式数据
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选）
            timeout: 超时时间（秒）
            
        Yields:
            流式数据块（原始字符串）
        """
        url = f"{self.base_url}/api/chat/stream"
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        try:
            async with self.async_client.stream(
                "POST",
                url,
                json=payload,
                timeout=timeout,
                headers={"Accept": "text/event-stream"}
            ) as response:
                # 检查状态码
                if response.status_code != 200:
                    error_text = await response.aread()
                    if error_text:
                        try:
                            error_text = error_text.decode('utf-8', errors='replace')[:500]
                        except Exception:
                            error_text = f"状态码: {response.status_code} (无法解码错误信息)"
                    else:
                        error_text = f"状态码: {response.status_code}"
                    raise Exception(f"流式请求失败: {error_text}")
                
                # 解析 SSE 格式
                buffer = b""
                async for chunk in response.aiter_bytes():
                    buffer += chunk
                    # 按行分割
                    while b"\n" in buffer:
                        line_bytes, buffer = buffer.split(b"\n", 1)
                        if not line_bytes:
                            continue
                        
                        # 安全解码行
                        try:
                            line = line_bytes.decode('utf-8', errors='replace')
                        except Exception:
                            try:
                                line = line_bytes.decode('latin-1', errors='replace')
                            except Exception:
                                continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            try:
                                # 解析 JSON
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
                            except UnicodeDecodeError:
                                continue
        except httpx.TimeoutException:
            raise ConnectionError("流式请求超时: 任务处理时间过长（超过 5 分钟）。请尝试将任务分解为更小的步骤。")
        except httpx.RequestError as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise ConnectionError(f"流式请求连接超时: {error_msg}\n提示: 任务可能过于复杂，请尝试分解为更小的步骤，或检查后端服务是否正常运行")
            else:
                raise ConnectionError(f"流式请求连接错误: {error_msg}\n提示: 请检查后端服务是否正常运行")
        except Exception as e:
            if "流式请求失败" in str(e) or "未知错误" in str(e):
                raise
            raise Exception(f"请求失败：{str(e)}")

