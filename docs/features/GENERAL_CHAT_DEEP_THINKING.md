# 通用对话 · 深度思考开关

**时间**：2026-03-13  
**理由**：多工具、多来源时用户希望显式启用推理模型，而不改 `.env`。  
**方法**：前端 `deep_thinking: true` → 后端 `context["model"] = "reasoning"` → 编排器 `_resolve_user_model("reasoning")` → `REASONING_MODEL`。

## 行为

- 开启后：**本轮请求**强制使用环境变量 **`REASONING_MODEL`**（与模型下拉里选「推理」等价）。
- **优先于**同请求中的 `model` 字段；此时前端不发送 `model`，并禁用模型下拉。
- 状态保存在 **`sessionStorage`** 键 `general_chat_deep_thinking`（`1`/`0`），刷新页面保留。
- **工具轮不降级**：请求会带 `deep_thinking: true`，后端写入 `context["deep_thinking"]`；编排器对 `google_search` 等**不再**按工具元数据切到对话模型，`model_switcher` 的执行结果分析切模型亦关闭，避免打断深度思索进程。

## API

`POST /api/chat`、`POST /api/chat/stream` 请求体可选：

```json
{ "message": "…", "deep_thinking": true }
```

`GET /api/models/selectable` 响应含 **`reasoning_model`**（与 `ModelConfigManager.get_reasoning_model()` 一致），前端在勾选深度思考时用其展示「当前模型」，不再显示禁用的下拉。

## CLI 对齐

```bash
python scripts/test_general_chat_stream.py --deep-thinking --task "你的任务"
```
