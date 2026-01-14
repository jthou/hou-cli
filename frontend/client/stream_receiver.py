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
        import time
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:entry","message":"前端开始发送流式请求","data":{"base_url":self.base_url,"message_length":len(message) if message else 0,"session_id":session_id},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        url = f"{self.base_url}/api/chat/stream"
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:before_request","message":"准备发送HTTP请求","data":{"url":url,"payload_keys":list(payload.keys())},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        try:
            # #region agent log
            try:
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:before_async_with","message":"准备发送HTTP流式请求","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
            
            async with self.async_client.stream(
                "POST",
                url,
                json=payload,
                timeout=timeout,
                headers={"Accept": "text/event-stream"}
            ) as response:
                # #region agent log
                try:
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:after_async_with","message":"收到HTTP响应","data":{"status_code":response.status_code},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
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
                
                # #region agent log
                try:
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:before_iter_bytes","message":"准备开始接收流式数据","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
                # 解析 SSE 格式
                buffer = b""
                chunk_count = 0
                async for chunk in response.aiter_bytes():
                    chunk_count += 1
                    # #region agent log
                    if chunk_count <= 3:  # 只记录前3个chunk，避免日志过多
                        try:
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_receiver.py:receive_stream:received_bytes","message":"收到字节数据","data":{"chunk_count":chunk_count,"chunk_size":len(chunk)},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                    # #endregion
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

