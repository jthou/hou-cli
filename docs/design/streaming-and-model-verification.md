# 流式与模型选择 - 核查清单

## 一、后端

### 1.1 模型选择（model-selectable-at-use-time）

| 项目 | 状态 | 说明 |
|------|------|------|
| ChatRequest.model | ✅ | `chat_routes.py` 支持 model 参数 |
| context["model"] 传递 | ✅ | 非空时写入 context |
| _resolve_user_model | ✅ | 解析 chat/code/reasoning 或具体模型名 |
| _select_model(context) | ✅ | 优先使用 context.model |
| 用户指定时跳过工具推荐切换 | ✅ | _chat_with_tools_stream 检查 context.get("model") |

### 1.2 流式响应（方案 B）

| 项目 | 状态 | 说明 |
|------|------|------|
| stream_chat_with_tools | ✅ | llm_service 新增，stream=True + tools |
| content 实时 yield | ✅ | 每 token 立即 yield |
| tool_calls 累积 | ✅ | 按 index 累积，finish_reason=tool_calls 时写入 out_result |
| _chat_with_tools_stream 改用流式 | ✅ | 调用 stream_chat_with_tools 替代 chat() |
| finish_reason 处理 | ✅ | stop/end_turn/length 均 break |
| _yield_text_in_chunks 保留 | ✅ | 工具执行后最终文本仍用分块（response.content 路径） |

### 1.3 API

| 项目 | 状态 | 说明 |
|------|------|------|
| GET /api/models/selectable | ✅ | 返回 auto + 具体模型名，去重 |
| POST /api/chat model 参数 | ✅ | 非流式 |
| POST /api/chat/stream model 参数 | ✅ | 流式 |

### 1.4 会话

| 项目 | 状态 | 说明 |
|------|------|------|
| type=work_assistant 过滤 | ✅ | session list 支持 type 过滤 |
| 创建会话 metadata.type | ✅ | context_type 写入 type |

## 二、前端

### 2.1 模型选择

| 页面 | 状态 | 说明 |
|------|------|------|
| useSelectableModels | ✅ | 从 /api/models/selectable 拉取 |
| ArticleWriting | ✅ | 下拉展示具体模型名 |
| PdfReader | ✅ | 同上 |
| WorkAssistant | ✅ | 同上 |

### 2.2 工具调用展示

| 页面 | 状态 | 说明 |
|------|------|------|
| ArticleWriting streamingToolCalls | ✅ | 解析 __TOOL__，展示工具名+结果 |
| WorkAssistant streamingToolCalls | ✅ | 同上 |
| 成功/失败样式 | ✅ | 绿色/橙色卡片 |

### 2.3 工作助手

| 项目 | 状态 | 说明 |
|------|------|------|
| 路由 /work-assistant | ✅ | App.jsx |
| 侧边栏入口 | ✅ | Sidebar |
| 会话列表 type=work_assistant | ✅ | 左侧会话 |
| 新建会话 | ✅ | POST /api/sessions |
| 流式 + model 参数 | ✅ | /api/chat/stream |
| buffer 末尾 streamingContent 更新 | ✅ | 已修复：buffer 块内也更新 setStreamingContent |

### 2.4 代理

| 项目 | 状态 | 说明 |
|------|------|------|
| Vite /api timeout: 0 | ✅ | 避免 SSE 提前关闭 |

## 三、已知问题与遗漏

| 项目 | 说明 |
|------|------|
| test_chat_endpoint_empty_message | 既有：空消息时 API 返回 success，测试期望 error |
| stream+tools 兼容性 | 若某提供商不支持 stream 与 tools 同时使用，需 fallback 到 chat() |
| PdfReader 非流式 | 使用 /api/chat，如需流式需改为 /api/chat/stream |

## 四、测试命令

```bash
# 模型选择
pytest backend/core/agent/tests/orchestration/test_model_selectable_at_use_time.py -v

# Chat API（跳过空消息测试）
pytest backend/api/tests/test_chat_routes.py -v -k "not empty_message"

# 前端构建
cd frontend/react-app && npm run build
```
