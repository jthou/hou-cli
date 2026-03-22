# 写作意图解读（Intent Interpreter）与主写作 Agent 串联

## 1. 模块

- `backend/core/agent/intent_interpreter.py`
  - `explain_writing_instruction_intent(user_instruction)`：仅从**用户指令**抽结构化意图（不读模型输出）。
  - `judge_writing_output_vs_instruction(...)`：语义验收（测试/离线质检用）。
  - `format_intent_for_writing_prompt(intent)`：格式化为写作主模型 `user_prompt` 尾部的固定块。

## 2. 生产路径（与写作 Agent 结合）

- **位置**：`orchestrator.py` 流式编排中，`article_writing` 且无工具分支，在 **`stream_chat` 之前**。
- **开关**：`ENABLE_WRITING_INTENT_INJECTION=true`（默认 `false`，避免每轮多一次 LLM）。
- **输入**：原始 `task`（用户本条消息），**不**用已拼草稿/画像后的整段 `user_prompt`，避免意图模型被长参考带偏。
- **输出**：`format_intent_for_writing_prompt` 结果追加到当前 `user_prompt` 末尾，与草稿前缀、画像、字数/分节注入共存。
- **模型**：优先 `INTENT_INTERPRETER_MODEL`；未设时回退为当轮 `selected_model`（与写作同网关/计费策略一致）。
- **失败策略**：意图调用异常时 `warning` 并**跳过注入**，不阻断主写作流（时间：2026-03-13；理由：可选增强；方法：见代码注释）。

## 3. 可观测性

- `orchestration_trace`：`event: writing_intent_injected`（在 `ORCH_TRACE_VERBOSITY` 非 `off` 时）。
- `debug`：`log_orchestrator_step("注入写作意图解读", ...)`。

## 4. 测试与脚本

- 解析/格式化单测：`backend/core/agent/tests/test_intent_interpreter_parse.py`
- 一次性解读 CLI：`scripts/explain_writing_intent_once.py`
- 写作回归（含 `--assert-mode intent`）：`scripts/test_article_writing_opening_rewrite.py`

## 5. 相关文档

- **[01-writing-vs-general-chat-stream-ui-design.md](./01-writing-vs-general-chat-stream-ui-design.md)**：中间区流式、`__CTX_META__`（写作素材说明，与意图解读不同轨）、前端 `ContextSelectionPanel`。
