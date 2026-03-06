# 流式响应问题分析与改造方案

## 一、现象

用户反馈：对话都不是流式响应的，内容一次性显示而非逐字/逐块输出。

## 二、根因分析

### 2.1 调用链路

```
前端 fetch('/api/chat/stream') 
  → 后端 chat_routes.chat_stream()
  → orchestrator.stream_process()
  → _chat_with_tools_stream()  [有 tools 时]
  → llm_service.chat()  ← 非流式！
```

### 2.2 关键代码位置

| 组件 | 文件 | 说明 |
|------|------|------|
| 流式入口 | `backend/api/chat_routes.py` | `StreamingResponse` + `orchestrator.stream_process`
| 编排流式 | `backend/core/agent/orchestrator.py` | `stream_process` 第 2084 行 |
| 工具调用 | `orchestrator.py` | `_chat_with_tools_stream` 第 2639 行 |
| LLM 调用 | `backend/services/llm/llm_service.py` | `chat()` 使用 `stream=False` |

### 2.3 根因

1. **`stream_process` 始终使用 `article_writing` 工具**（第 2085 行）：
   ```python
   tools = get_tools_for_llm_by_agent("article_writing", ...)
   ```
   `article_writing` 配备 browser、google_search、web_fetch、mediawiki，故 `tools` 恒非空。

2. **有 tools 时走 `_chat_with_tools_stream`**，内部使用 `llm_service.chat()`（非流式）：
   ```python
   response = await self.llm_service.chat(messages=messages, tools=tools, ...)
   ```
   `chat()` 使用 `stream=False`，等待完整响应后一次性返回。

3. **纯文本回复时一次性 yield**（第 2647-2650 行）：
   ```python
   if isinstance(response, str):
       yield response  # 整段一次性返回
       return
   ```

4. **无 tools 分支**（第 2163 行）使用 `stream_chat`，是流式的，但当前 `tools` 恒非空，该分支从未执行。

## 三、前后端通信实现

### 3.1 后端

- **SSE 格式**：`data: {"content": "...", "status": "streaming"}\n\n`
- **chat_routes**：对 orchestrator 的每个 `chunk` 调用 `format_chunk(chunk, "streaming")` 后 yield
- **问题**：orchestrator 一次 yield 整段文本，故只产生一个 SSE 事件

### 3.2 前端

- **ArticleWriting / WorkAssistant**：`fetch` + `res.body.getReader()` + `reader.read()` 循环
- **解析**：按 `\n\n` 分割，取 `data: ` 行解析 JSON，过滤 `__DEBUG__`、`__TOOL__`、`__STATUS__`
- **消费**：`obj.status === 'streaming' && obj.content` 时 `fullContent += raw`，`setStreamingContent(fullContent)`

前端逻辑正确，问题在于后端一次只发一个 content 块。

### 3.3 代理

- **Vite**：`proxy: { '/api': 'http://127.0.0.1:8081' }`
- **已知**：Vite 代理对 SSE 有缓冲/关闭事件转发问题，可后续加 `timeout: 0` 等优化

## 四、改造方案

### 4.1 方案 A：纯文本响应分块 yield（快速修复）

在 `_chat_with_tools_stream` 中，当 LLM 返回纯文本时，改为分块 yield：

```python
if isinstance(response, str):
    # 模拟流式：分块发送，提升 UX
    chunk_size = 40  # 字符
    for i in range(0, len(response), chunk_size):
        yield response[i:i + chunk_size]
        await asyncio.sleep(0)  # 让出事件循环，确保及时发送
    return
```

### 4.2 方案 B：LLM 支持 tools 的流式调用（长期）

- 在 `llm_service` 中增加 `stream_chat_with_tools`，使用 `stream=True` + `tools`
- 解析流式 chunk，区分 content 与 tool_calls
- 当收到完整 tool_calls 时执行工具，否则继续累积 content 并 yield
- 实现复杂度高，需适配 OpenAI API 的流式 tool_calls 格式

### 4.3 方案 C：按 context 选择 agent

- `work_assistant` 使用 `chat` 或新建 `work_assistant` agent，可配置更少工具
- 当 tools 为空时走 `stream_chat` 分支，实现真正的流式
- 需权衡：工具少可能影响能力

## 五、建议

优先实施 **方案 A**，快速改善体验；后续可评估方案 B 或 C。

---

## 六、方案 B 实施记录（已实现）

- **llm_service.stream_chat_with_tools**：使用 `stream=True` + tools，content 实时 yield，tool_calls 累积后写入 `out_result`
- **_chat_with_tools_stream**：改用 `stream_chat_with_tools` 替代 `chat()`，纯文本回复实现真正的 token 级流式
