# 写作 / 参考块：单次对话 user 消息契约

**时间**：2026-03-21  
**理由**：CLI、pytest 脚本与 UI 曾使用不同模板（如「【参考信息】+【用户提问】」vs `formatReferenceContext` +「【用户本次提问】」），导致复现与线上不一致。  
**方法**：单一事实来源 + 双端实现同步。

## 规则（须与实现一致）

1. **无有效参考块**（无块或所有 `content` 去空白后为空）：发往模型的 `message` **等于**用户输入字符串（trim），**不**添加「【用户本次提问】」等标记。
2. **有有效参考块**：`REFERENCE_INTRO` + 各块 `【参考i：标题】\n正文` + `\n\n---\n\n` + `【用户本次提问】\n` + 用户输入（trim）。

## 代码位置

| 角色 | 路径 |
|------|------|
| Python 契约 API | `backend/core/agent/article_writing_message_contract.py` |
| 编排：doc-coauthoring 触发 | `task_triggers_doc_coauthoring()`，由 `orchestrator.stream_process` 写作分支调用 |
| 前端拼装 | `frontend/react-app/src/utils/referenceUtils.js`：`formatReferenceContext`、`buildArticleWritingMessageForModel` |
| 调用方页面 | `ArticleWriting.jsx`、`WorkAssistant.jsx`、`GeneralChat.jsx` |
| CLI 复现 | `scripts/replay_article_writing_cli.py`（`--raw` 除外） |

## 字数要求（编排层）

当 `task` 中含 `N字左右`、`约N字`、`N字以内`、`不少于N字` 等模式时，`orchestrator` 与 `replay_article_writing_cli --dump-prompt` 会在 user 消息末尾追加 **【系统检出·用户字数要求】**（见 `article_writing_message_contract.build_article_word_count_constraint_injection`），与 system 提示中「左右 = ±15%」说明一致，减少模型明显偏短。

## 长文分节版式（编排层）

当检出「完整长文」需求（如「新写全文」「写一篇…文章」、目标字数 ≥800 等）且用户**未**禁止 Markdown 分节时，在 user 末尾追加 **【系统检出·长文版式】**（`build_article_sectioning_hint_injection`）：要求 `## 引言`、主体至少 4 个同级小节（建议 `## 01 …` 或 `## 一、…` 二选一）、末尾 `## 结论`（若用户明确不要结论标题则改为末段自然收束）。与 `orchestrator` 写作分支、`replay_article_writing_cli` 对齐。

## 右侧草稿与改稿范围（编排层，2026-03-13）

当 `ContextManager.get_current_article(session_id)` 非空时，`orchestrator.stream_process` 写作分支在 user 前部插入 **`build_article_draft_scope_prefix`**：【改稿范围（须遵守）】+【当前文章（右侧草稿）】+ `---`，再拼接画像与 `task`（参考块 + 【用户本次提问】）。与 `system_prompt_templates` 中「全文 vs 局部」规则一致：**默认按最后一次提问做局部改写/答疑**，仅用户**明确**全文重写时才输出整篇。CLI：`replay_article_writing_cli --article-file` 用于 `--dump-prompt` 对齐拼装（无 session 时直连 LLM 仍不带会话内草稿）。

## 变更约定

修改 `REFERENCE_INTRO`、`USER_QUESTION_MARKER`、参考块标题格式或「有/无参考」分支逻辑时，**必须**同时修改 Python 与 `referenceUtils.js`，并跑：

- `pytest backend/core/agent/tests/test_article_writing_message_contract.py`
- `cd frontend/react-app && npm test`（含 `referenceUtils.test.js`）
