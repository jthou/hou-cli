# 通用对话：多源信息（历史 / 已完成任务 / 联网）

**时间**：2026-03-13  
**理由**：用户希望回答能综合会话历史、任务队列已完成的记录与联网检索，并展示摘录与链接。  
**方法**：

1. **历史**：沿用 `ENABLE_HYBRID_CHAT_HISTORY` + `select_hybrid_chat_messages`（最近条数 + 关键词检索更早消息），由 Orchestrator 拼入 user 消息。
2. **已完成任务**：`build_completed_tasks_reference_block(current_user_query=...)` 优先使用 **SQLite FTS5**（`tasks_fts`，`unicode61` 分词，`body` 含 `task_name`/`task_type`/`message`/`result.summary`），`MATCH` + `bm25` 排序；命中不足 `LIMIT` 时用最近完成补位。FTS 无结果或关闭时回退「候选池 + 关键词打分」（见 `completed_tasks_prompt`、`task_queue_db.search_completed_tasks_fts`）。
3. **联网**：既有 `google_search` / `browser_search` / `web_fetch`；系统提示 `CHAT_SYSTEM_PROMPT` 要求对外信息附 Markdown 链接与原文摘录（见「多源信息与引用展示」）。

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `GENERAL_CHAT_INJECT_COMPLETED_TASKS` | `true` | 设为 `false` 关闭「近期已完成任务」块注入 |
| `GENERAL_CHAT_COMPLETED_TASKS_LIMIT` | `15` | 注入条数上限（1–50） |
| `GENERAL_CHAT_COMPLETED_TASKS_RELEVANCE` | `true` | `true`：先拉 POOL 条再按问题相关性取 LIMIT；`false`：仅时间倒序取 LIMIT 条 |
| `GENERAL_CHAT_COMPLETED_TASKS_POOL` | `80` | 关键词回退模式下的候选池大小（上限 200） |
| `GENERAL_CHAT_COMPLETED_TASKS_USE_FTS` | `true` | `true`：优先 FTS5（需 SQLite 编译 `ENABLE_FTS5`）；`false`：仅用关键词打分 |
| `ENABLE_HYBRID_CHAT_HISTORY` | `true` | 混合会话历史 |
| `CHAT_HISTORY_RECENT_MESSAGES` | `12` | 混合历史：尾部保留条数 |
| `CHAT_HISTORY_RETRIEVE_TOP_K` | `8` | 混合历史：关键词检索条数 |

## 相关代码

- `backend/core/agent/orchestrator.py` — `is_general_chat` 分支组装 `user_prompt`
- `backend/core/agent/system_prompt_templates.py` — `CHAT_SYSTEM_PROMPT`
- `backend/core/agent/completed_tasks_prompt.py`
- `backend/infrastructure/storage/task_queue_db.py`（`tasks_fts` 迁移、触发器、`search_completed_tasks_fts`）
- `backend/infrastructure/storage/fts5_match.py`（`MATCH` 子句构造）
- `backend/core/context/hybrid_history.py`
