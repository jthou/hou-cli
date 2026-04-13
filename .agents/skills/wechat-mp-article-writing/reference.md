# 参考：微信公众号长文 Skill 与代码对照

## 核心路径

| 主题 | 路径 |
|------|------|
| 写作系统提示（人设、两类任务、输出规则） | `backend/core/agent/system_prompt_templates.py` |
| user 消息参考块 / 改稿注入 | `backend/core/agent/article_writing_message_contract.py` |
| 编排里选用写作提示、跳过技能预匹配 | `backend/core/agent/orchestrator.py`（`article_writing`） |
| 技能预匹配门控 | `backend/core/agent/skill_prematch.py` |
| 前端参考拼接 | `frontend/react-app/src/utils/referenceUtils.js` |
| 写作页 | `frontend/react-app/src/pages/ArticleWriting.jsx` |
| 公众号草稿任务 | `backend/infrastructure/execution/task_handlers.py` → `wechat_mp_draft` / `process_wechat_mp_draft_task` |
| 微信 API 封装 | `backend/services/wechat_mp_service/client.py` |
| Markdown→草稿 HTML（MCP/脚本） | `backend/services/wechat_mp_service/article_markdown_html.py` |
| 公众号草稿 MCP | `scripts/mcp_wechat_mp_draft_server.py` → 工具 **`hou_wechat_mp_draft_publish`** |

## `wechat_mp_draft` 摘要

- **add**：新建草稿；`title`、HTML `content`；封面 `thumb_media_id` 可选。  
- **update**：需 `media_id`；更新已有草稿。  
- 失败返回统一错误结构（见 handler 内 `_err`）。

## MCP 写入草稿箱

- 服务：`scripts/mcp_wechat_mp_draft_server.py`（Cursor `mcpServers` 中配置 `command` + `cwd` 指向仓库根）。
- 工具：**`hou_wechat_mp_draft_publish`** — `operation`=`add`|`update`；`article_markdown` 与 `article_html` 二选一（同时有则优先 HTML）；`title`/`digest`/`author`/`thumb_media_id`/`content_source_url` 可选；`update` 时必填 **`media_id`**。
- 摘要超过 120 字会在 MCP 内截断；无效 `thumb_media_id` 时与 Web 任务一致会**自动省略封面重试**。

## CLI 复现写作编排（可选）

- `scripts/replay_article_writing_cli.py`：本地输入参考 + 提问，走与线上一致的 article_writing 路径。
