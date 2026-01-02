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

## 前端流式渲染实现

### 使用 Rich Live 组件避免重复显示

**问题**：流式输出时，如果先显示预览再渲染完整内容，会导致内容显示两次。

**解决方案**：使用 Rich Live 组件实时更新渲染内容，避免重复显示。

**实现**：
```python
from rich.live import Live
from rich.console import Console
from frontend.ui.renderer import RendererFactory

console = Console()
factory = RendererFactory()

async def render_stream(stream: AsyncIterator[str]):
    """流式渲染，避免重复显示"""
    full_content = ""
    
    # 使用 Live 组件实时更新
    with Live(console=console, refresh_per_second=10) as live:
        async for chunk in stream:
            full_content += chunk
            # 实时渲染当前内容
            renderer = factory.get_renderer(full_content)
            rendered = renderer.render(full_content)
            live.update(rendered)
    
    # 流式结束后，最终渲染一次（确保完整渲染）
    renderer = factory.get_renderer(full_content)
    rendered = renderer.render(full_content)
    console.print(rendered)
```

**优势**：
- ✅ 实时更新，用户可以看到实时输出
- ✅ 避免重复显示，内容只显示一次
- ✅ 支持 Markdown 和代码块的实时渲染
- ✅ 流式结束后确保完整渲染

### 简洁风格（参考 Cursor Agent）

**原则**：
- 不显示 Agent 前缀，直接显示内容
- 用户输入使用简洁的提示符（`▸` 或 `>`）
- 流式输出实时显示，不重复

**示例**：
```python
# 用户输入
console.print(f"[dim cyan]▸[/dim cyan] {user_input}")

# Agent 回复（流式，无前缀）
async def render_response(stream):
    # 使用 Live 组件实时渲染
    # ...
```

## 流式输出最佳实践

### 用户体验原则

1. **实时反馈**
   - 使用 Rich Live 组件实时更新
   - 用户可以看到实时输出
   - 提供流畅的交互体验

2. **避免重复**
   - 流式时实时渲染，结束后最终渲染一次
   - 确保内容只显示一次
   - 避免视觉混乱

3. **优雅降级**
   - 如果流式失败，降级到非流式
   - 提供清晰的错误提示
   - 确保用户始终能看到结果

4. **性能考虑**
   - 合理设置刷新频率（`refresh_per_second=10`）
   - 避免过于频繁的更新
   - 平衡实时性和性能

