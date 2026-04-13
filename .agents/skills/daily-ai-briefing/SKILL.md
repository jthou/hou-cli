---
name: daily-ai-briefing
description: 指导 hou-cli 首页「简报与研判」（home_briefing_report）：事实包来源、多角度预查询、API、Worker、以及简报产出质量标准（正文可点击出处、细节密度）。在用户或对话涉及每日简报、AI 新闻摘要、首页简报生成、home-briefing、Fact Pack、简报质量与 prompt 时使用。
---

# 每日 AI 新闻摘要（首页简报）

## 产品与术语

- **界面文案**：首页「**简报与研判**」，按钮「**生成最新简报**」。
- **内部任务类型**：`home_briefing_report`（任务创建 UI 中**隐藏**，由首页或 API 触发）。
- **用户口语「每日 AI 新闻摘要」**：与本功能同一套 pipeline；正文为 LLM 根据事实包撰写的 Markdown，**不是**独立爬虫频道。

## 产出质量标准（合格 / 不合格）— Skill 层约定

以下用于评审与改 prompt；**运行时 enforcement** 在 `backend/services/home_briefing/report_generate.py` 的 `SYSTEM_PROMPT` / `PROMPT_VERSION`。

**合格（最低线）**

- **可核对出处**：凡事实包条目 `url` 非空，在「执行摘要」「分主题分析」中**首次引用该 [Fx] 的段落内**，必须出现与事实包 **完全一致** 的 Markdown 链接：`[来源或标题简写](url)`，与 `[Fx]` 同段或紧邻；读者不依赖文末列表即可点击进原文。
- **细节**：每个被引用的 [Fx] 须体现 `title` / `summary` 中的**至少一条可核对信息**（机构名、日期、数字、产品名、引述片段等），禁止只有笼统观点加 [Fx] 而无摘要细节。
- **诚实局限**：写不清的条目放在「本期局限」，不编造事实包没有的内容。

**不合格（需改 prompt 或事实包质量，而非只改 Skill 文案）**

- 正文大量 `[Fx]` 叙事但**几乎无可点击链接**（在存在带 `url` 条目的前提下）。
- 只有宏观概括、**复述不到摘要里的具体信息**。
- 链接全部堆在文末，正文无可点来源。

**Agent 收到「简报没出处 / 太空」时**：先对照本节；再打开 `report_generate.py` 调整 `PROMPT_VERSION` 与 `SYSTEM_PROMPT`，并跑 `backend/services/home_briefing/tests/test_report_generate.py`。

## 数据从哪来（事实包）

`backend/services/home_briefing/fact_pack.py` 中 **`SOURCE_TASK_TYPES`** 定义了**历史任务**事实来源：

- `weather_query`
- `web_search`
- `web_search_compare`

在时间窗内（默认 **168 小时 / 7 天**，可调）已 **completed** 的上述任务，经 `build_fact_pack_from_tasks` 打成 `fact_pack`。

**多角度实时查询后再摘要（推荐）**：`POST /api/home-briefing/generate` 可传 **`multi_aspect_prefetch: true`**（首页「生成最新简报」已默认开启）或 **`prefetch_queries: ["关键词1", ...]`**。Worker 在合并历史任务前，先并发执行 `unified_search`（环境有 **`TAVILY_API_KEY`** 时优先 Tavily，否则 DuckDuckGo），将结果**插在事实包最前**，再交给 LLM。可选 **`prefetch_results_per_query`**（默认 8，最大 20）。

**空简报常见原因**：既未开预查询、近期又没有上述三类任务的完成记录 → 事实包为空，生成侧会落到「简报 · 暂无数据」类结果。

> 设计文档 `docs/design/01-home-briefing-report-agent-design.md` 曾规划扩展如 `ai_news` 等 `task_type` 白名单；**以代码中 `SOURCE_TASK_TYPES` 为准**，扩展时需同时改 fact_pack 与（若需要）任务注册。

## 后端流程

1. **触发**：`POST /api/home-briefing/generate` → 入队 `home_briefing_report`，可选 `metadata`：`window_hours`、`max_facts`、`model`、`multi_aspect_prefetch`、`prefetch_queries` 等（见 `backend/api/home_briefing_routes.py`）。
2. **执行**：`process_home_briefing_report_task`（`backend/infrastructure/execution/task_handlers.py`）→ 可选预查询 → 事实包 → `generate_briefing_markdown`（`report_generate.py`）。
3. **结果结构**：`result.briefing` 含 `schema_version`、`meta`、`markdown`、`fact_refs`、`fact_pack`（见 `TASK_TYPES["home_briefing_report"].output_spec`）。

## 读取最新简报

- **`GET /api/home-briefing/latest`**：聚合队列中 `home_briefing_report` 多状态任务，由 `build_latest_home_briefing_payload`（`backend/services/home_briefing/latest_payload.py`）返回：
  - 最近一次**成功**的 `briefing` 正文；
  - **`show_degraded_banner`**：本期失败时仍展示上一期成功正文 + 琥珀提示；
  - **`last_attempt`**、`pending_in_queue` 等供前端展示排队/失败原因。

## 前端（首页）

- **文件**：`frontend/react-app/src/pages/Home.jsx`
- 加载：`GET /api/home-briefing/latest`
- 生成：`POST /api/home-briefing/generate` 后 **轮询** `GET /api/task-queue/tasks/{task_id}` 至终态（约 2s 间隔，有超时次数上限），再 `loadBriefing()`。

## 测试与回归

- `backend/services/home_briefing/tests/`：`test_fact_pack.py`、`test_report_generate.py`、`test_latest_payload.py`
- 任务类型注册与隐藏：`backend/infrastructure/execution/tests/test_task_handlers.py` 中 `TestImageGenerationHandler::test_home_briefing_report_*`（`home_briefing_report` 不在创建下拉中但仍注册）

## 延伸阅读（按需打开）

- 架构与分期：`docs/design/01-home-briefing-report-agent-design.md`
