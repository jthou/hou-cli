# 天气预报输出数据流设计文档

## 数据流概览

```
WeatherTool.execute()
    ↓
ToolResult(data={...})  # 原始 JSON 数据
    ↓
Orchestrator._chat_with_tools()
    ↓
json.dumps(tool_result.data)  # 转换为 JSON 字符串
    ↓
LLM (DeepSeek)  # LLM 基于工具结果生成 Markdown 格式的回复
    ↓
Markdown 文本（包含表格、图标等）
    ↓
Orchestrator.stream_process()  # 逐字符流式输出
    ↓
Backend API /api/chat/stream  # SSE 格式包装
    ↓
Frontend IPCClient.stream_send()  # 解析 SSE，提取 content
    ↓
Frontend StreamRenderer.render_stream()
    ├─→ 流式显示文本到终端（实时反馈，让用户看到进度）
    └─→ 同时收集完整内容到 full_content
    ↓
流式完成后清除临时显示（transient=True）
    ↓
RendererFactory.get_renderer()  # 选择渲染器
    ↓
WeatherRenderer.render()  # 解析表格，转换为 Rich Table
    ↓
Rich Console 输出到终端（替代之前的文本显示）
```

## 详细流程

### 1. WeatherTool.execute() - 工具执行

**位置**: `backend/core/agent/tools/builtin/weather_tool.py:273-348`

**返回数据结构**:
```python
ToolResult(
    success=True,
    data={
        "location": "北京",
        "current": {
            "temp": "3",
            "text": "晴",
            "windDir": "西风",
            "windScale": "2",
            "humidity": "23",
            # ... 更多字段
        },
        "air_quality": {
            "aqi": "33",
            "level": "1",
            "pm2p5": "6",
            # ... 更多字段
        },
        "forecast": [
            {
                "fxDate": "2026-01-03",
                "tempMax": "6",
                "tempMin": "-4",
                "textDay": "晴",
                "windDirDay": "西北风",
                "windScaleDay": "1-3",
                "humidity": "24",
                # ... 更多字段
            },
            # ... 更多天
        ],
        "code": "200"
    }
)
```

### 2. Orchestrator._chat_with_tools() - 工具结果处理

**位置**: `backend/core/agent/orchestrator.py:382-519`

**关键代码**:
```python
# 执行工具
tool_result = self.tool_registry.execute(tool_name, **tool_args)

# 将工具结果转换为 JSON 字符串
tool_result_content = json.dumps(tool_result.data, ensure_ascii=False)

# 添加到消息历史
tool_results.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "name": tool_name,
    "content": tool_result_content  # JSON 字符串
})

messages.extend(tool_results)

# 再次调用 LLM，让 LLM 基于工具结果生成回复
response = await self.llm_service.chat(messages=messages, tools=tools)
```

**问题**: 工具结果以 JSON 字符串形式传递给 LLM，LLM 需要解析 JSON 并格式化为 Markdown。

### 3. LLM 生成回复

**位置**: `backend/core/agent/orchestrator.py:243-300` (system_prompt)

**System Prompt 指令**:
- 要求使用 Markdown 表格格式
- 添加天气图标和风力图标
- 包含穿衣建议、带伞建议、空气质量信息

**LLM 输出示例**:
```markdown
## 当前天气
- ☀️ 晴，温度 3°C，体感温度 0°C
- 🍃 西北风1级，风速 4km/h
- 💧 湿度 24%，能见度 30公里

## 未来一周天气预报
| 日期 | 天气 | 最高温度 | 最低温度 | 风向 | 湿度 |
|------|------|---------|---------|------|------|
| 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
| 1月4日 | ☀️ 晴 | 5°C | -5°C | 🍃 东风1-3级 | 29% |

## 总结
...
```

### 4. Orchestrator.stream_process() - 流式输出

**位置**: `backend/core/agent/orchestrator.py:211-380`

**关键代码**:
```python
# 调用 _chat_with_tools 获取完整响应
full_response = await self._chat_with_tools(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    tools=tools
)

# 逐字符流式输出
for char in full_response:
    yield char
```

**问题**: 流式输出是逐字符的，表格在流式过程中不完整。

### 5. Backend API /api/chat/stream - SSE 包装

**位置**: `backend/api/routes.py:100-131`

**关键代码**:
```python
async for chunk in orchestrator.stream_process(request.message, context=context):
    # SSE 格式：data: {json}\n\n
    yield f"data: {json.dumps({'content': chunk, 'status': 'streaming'})}\n\n"
```

**输出格式**: Server-Sent Events (SSE)
```
data: {"content": "##", "status": "streaming"}\n\n
data: {"content": " 当", "status": "streaming"}\n\n
data: {"content": "前", "status": "streaming"}\n\n
...
```

### 6. Frontend IPCClient.stream_send() - SSE 解析

**位置**: `frontend/client/ipc_client.py:148-210`

**关键代码**:
```python
async for line in response.aiter_lines():
    if line.startswith("data: "):
        data_str = line[6:]  # 移除 "data: " 前缀
        data = json.loads(data_str)
        
        if data.get("status") == "streaming":
            content = data.get("content", "")
            if content:
                yield content  # 逐块 yield 给前端
```

### 7. Frontend StreamRenderer.render_stream() - 渲染

**位置**: `frontend/ui/stream_handler.py:120-166`

**渲染策略**:
1. **流式输出阶段**：实时显示文本内容（让用户看到进度）
2. **同时收集**：将所有 chunk 收集到 `full_content`
3. **流式完成后**：使用 `transient=True` 清除临时文本显示
4. **最终渲染**：使用渲染器渲染完整内容，替代之前的文本输出

**关键代码**:
```python
full_content = ""

# 使用 Live 组件实时更新（transient=True 表示流式输出完成后清除）
# 流式输出时实时显示文本，让用户看到进度
with Live(console=console, refresh_per_second=10, transient=True) as live:
    async for chunk in stream:
        # 清理无效的 Unicode 字符
        chunk = self._clean_unicode(chunk)
        full_content += chunk
        
        # 流式显示时，直接显示文本（实时反馈）
        live.update(full_content)

# 流式输出完成后，Live 组件会清除临时显示（transient=True）
# 现在使用完整的渲染器进行最终渲染，替代之前的文本输出
if full_content:
    renderer = self.factory.get_renderer(full_content)
    rendered = renderer.render(full_content)
    
    # 如果返回的是列表（多个渲染对象），逐个打印
    # 这会替代之前流式显示的文本内容
    if isinstance(rendered, list):
        for item in rendered:
            console.print(item)
    else:
        console.print(rendered)
```

**关键特性**:
- ✅ **实时反馈**：流式输出时用户能看到实时进度
- ✅ **自动替换**：流式完成后自动用美化后的内容替代文本
- ✅ **无重复显示**：`transient=True` 确保不会重复显示内容

### 8. RendererFactory.get_renderer() - 选择渲染器

**位置**: `frontend/ui/renderer.py:117-144`

**渲染器优先级**:
1. `CodeRenderer` - 代码块
2. `WeatherRenderer` - 天气信息（包含表格）
3. `MarkdownRenderer` - Markdown 内容
4. `TextRenderer` - 默认文本

### 9. WeatherRenderer.render() - 表格渲染

**位置**: `frontend/ui/weather_renderer.py:34-110`

**关键逻辑**:
1. 使用正则表达式匹配表格
2. 解析表格行数据
3. 创建 Rich Table 对象
4. 返回 `[Markdown(表格前内容), Table, Markdown(表格后内容)]`

## 当前问题分析

### 问题 1: LLM 输出格式不一致
- LLM 可能生成不同格式的表格
- 列名可能略有差异（如"日期" vs "时间"）
- 表格结构可能不完整

### 问题 2: 流式输出导致表格不完整（已解决）
- ✅ **已解决**：流式输出时显示文本，完成后用渲染器内容替换
- ✅ **策略**：使用 `transient=True` 的 Live 组件，流式完成后清除临时显示
- ✅ **效果**：用户看到实时进度，最终看到美化后的表格

### 问题 3: 渲染器选择可能失败
- 如果 `WeatherRenderer.can_render()` 返回 False，会降级到 `MarkdownRenderer`
- `MarkdownRenderer` 无法将表格转换为 Rich Table

### 问题 4: 表格正则匹配不够健壮
- 当前正则要求特定的列名和顺序
- 如果 LLM 输出格式略有差异，可能匹配失败

## 改进建议

### 建议 1: 增强表格检测
- 使用更灵活的正则表达式
- 支持列名变体和顺序变化
- 添加表格结构验证

### 建议 2: 优化流式渲染策略（已实现）
- ✅ **已实现**：流式输出时实时显示文本内容（让用户看到进度）
- ✅ **已实现**：流式完成后使用 `transient=True` 清除临时显示
- ✅ **已实现**：使用渲染器渲染完整内容，替代之前的文本输出
- ✅ **效果**：用户看到实时反馈，最终看到美化后的 Rich Table

### 建议 3: 改进 LLM 输出格式
- 在 system_prompt 中更明确地指定表格格式
- 提供表格模板示例
- 要求 LLM 严格遵循格式

### 建议 4: 添加降级处理
- 如果 `WeatherRenderer` 匹配失败，尝试从 Markdown 中提取表格
- 提供表格格式验证和修复机制

