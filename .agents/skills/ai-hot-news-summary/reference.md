# 参考：今日 AI 热点（Cursor / hou-cli Agent 共用 Skill）

## 双入口说明

| 入口 | 说明 |
|------|------|
| **Cursor** | 仓库内 `.cursor/skills/ai-hot-news-summary/`（若存在；可能被 .gitignore）与本目录内容应对齐；以**本仓库已跟踪**的 `.agents/skills/ai-hot-news-summary/SKILL.md` 为准。 |
| **hou-cli Web / 任务队列** | 任务类型 **`ai_hot_news_digest`**：Worker 内多轮 `web_search` + LLM，与 SKILL 结构一致。 |

## 网页搜索调用链（对话 Agent / web_search 任务）

`GoogleSearchTool.execute` → `unified_search.web_search()` →

- 若 `os.environ["TAVILY_API_KEY"]` 非空：优先 `tavily_search_service.tavily_search`；异常则记录 warning 并回退。
- 否则或回退：`google_search_service.browser_search.search`（POST `https://html.duckduckgo.com/html/`）。

## 今日 AI 热点任务（`ai_hot_news_digest`）

- **Handler**：`backend/infrastructure/execution/task_handlers.py` → `process_ai_hot_news_digest_task`
- **固定多查询**：`backend/services/ai_hot_news_digest/queries.py` → `default_ai_hot_news_queries()`（5 轮，日期按服务器 UTC 注入）
- **LLM 成文**：`backend/services/ai_hot_news_digest/report_generate.py` → `generate_ai_hot_news_markdown()`
- **前端**：`/ai-hot-news` → `frontend/react-app/src/pages/AiHotNews.jsx`
- **任务注册**：`TASK_TYPES["ai_hot_news_digest"]`，`register_default_handlers`

## 环境变量

- `TAVILY_API_KEY`：启用 Tavily；有审计库（可关 `TAVILY_AUDIT_DISABLED`）。
- 无 Google Custom Search：项目已以 Tavily + DuckDuckGo 为主路径。

## 相关文件路径（搜索实现）

- `backend/services/google_search_service/unified_search.py`
- `backend/services/google_search_service/browser_search.py`
- `backend/services/tavily_search_service/tavily_search.py`
- `backend/infrastructure/execution/task_handlers.py`（`process_web_search_task`、`process_ai_hot_news_digest_task`）

## 摘要产出规范

- 深度结构、篇幅与分主题要求以同目录 **SKILL.md** 为准；后端 `report_generate.py` 的章节与 SKILL 对齐。
