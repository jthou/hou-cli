# 流式响应实现方案

## 问题：IPC 能否支持流式响应？

**答案：完全可以！**

### 技术原理

1. **TCP Localhost 本身就是流式协议**
   - TCP 协议天然支持流式数据传输
   - 不需要额外的协议层

2. **FastAPI 支持 SSE (Server-Sent Events)**
   - 使用 `StreamingResponse` 和 `text/event-stream` 内容类型
   - 可以逐块发送数据

3. **httpx 支持流式接收**
   - 使用 `stream=True` 参数
   - 可以逐块接收响应

## 实现方案

### 方案 1：SSE (Server-Sent Events) - 推荐

**优点**：
- 标准 HTTP 协议，兼容性好
- 自动重连机制
- 跨平台支持

**实现**：
```python
# 后端
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in llm_service.stream_chat(request.message):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

```python
# 前端
async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        f"{base_url}/api/chat/stream",
        json={"message": message}
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(data["content"], end="", flush=True)
```

### 方案 2：直接流式 JSON

**优点**：
- 更简单，不需要 SSE 格式
- 直接返回 JSON 块

**实现**：
```python
# 后端
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in llm_service.stream_chat(request.message):
            yield json.dumps({"content": chunk}) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"  # Newline Delimited JSON
    )
```

```python
# 前端
async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        f"{base_url}/api/chat/stream",
        json={"message": message}
    ) as response:
        buffer = ""
        async for chunk in response.aiter_bytes():
            buffer += chunk.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line:
                    data = json.loads(line)
                    print(data["content"], end="", flush=True)
```

## 推荐方案

**使用 SSE (方案 1)**，因为：
1. 标准协议，兼容性好
2. 浏览器和 HTTP 客户端都原生支持
3. 自动处理连接管理

## 实现步骤

1. ✅ 后端添加流式聊天接口
2. ✅ LLM 服务支持流式调用
3. ✅ 前端 IPC 客户端支持流式接收
4. ✅ 前端 UI 实时显示流式输出











