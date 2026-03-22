# 脚本说明（节选）

时间：2026-03-13；理由：写作/编排调试入口分散；方法：集中索引常用命令。

## 写作助手

| 脚本 | 说明 |
|------|------|
| `test_article_writing_opening_rewrite.py` | 开篇改写复现；`--assert-mode intent\|substring\|none`；`--check-ctx-meta` 校验流内 `__CTX_META__`；见脚本内 `--help` |

**相关后端单测（项目根执行）**：`make test-stream-ctx`（`test_article_writing_context_meta` + `test_orchestrator_context_type_routing`）。

**设计文档**：`docs/design/01-writing-vs-general-chat-stream-ui-design.md`、`docs/design/01-intent-interpreter-for-writing-and-tests.md`。
