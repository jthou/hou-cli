---
name: ai-hot-news-summary
description: Searches the web for today's AI trending news and returns a rich, multi-section cited digest using hou-cli's google_search stack (Tavily when TAVILY_API_KEY is set, else DuckDuckGo). Applies to Cursor IDE agents and hou-cli runtime agents. Use when the user asks for 今日 AI 热点、AI 资讯摘要、latest AI news with depth—or use task type ai_hot_news_digest in the Web UI / task queue for the same pipeline server-side.
---

# 今日 AI 热点：联网检索与**深度**摘要

## 适用范围（必读）

| 场景 | 做法 |
|------|------|
| **Cursor / 对话 Agent** | 按本文多轮调用 `google_search`（或等价），再按章节写 Markdown。 |
| **hou-cli Web「今日 AI 热点」/ 任务队列** | 提交任务类型 **`ai_hot_news_digest`**（路由 `/ai-hot-news`），Worker 内已编排多轮 `web_search` + LLM，产出结构与本文一致；实现见 `backend/services/ai_hot_news_digest/`。 |

仓库内**以本文件与 `reference.md` 为唯一受版本控制的 Skill 正文**（`.cursor/skills/` 若存在为本地副本，请与此对齐）。

## 目标

用**真实联网结果**回答「今天 AI 圈发生了什么」，输出**足够厚、可核对**的摘要：**不是标题堆砌**，而是带**背景、要点展开、数字/主体、交叉观察**与**完整引用**；禁止凭训练记忆编造「今日」事实。

## 「今天」日期：如何获得（必读，防错）

对话里注入的 **`Today's date` 等字段可能过期、与真实日历不同步**，**禁止**仅凭其构造「今日」检索词或写摘要标题日期。

| 场景 | 做法 |
|------|------|
| **Cursor / 本机 Agent** | 在联网检索与写文**之前**，用终端执行 **`date`**（或等价）读取**当前机器日历**。示例：`date +%Y-%m-%d`；需要中国常用日历：`TZ=Asia/Shanghai date +%Y-%m-%d`；需要 UTC：`date -u +%Y-%m-%d`。将输出写入摘要文首「检索基准日期」，检索 query 里的「today / 今日」须与该日期一致。 |
| **hou-cli Worker** `ai_hot_news_digest` | `queries.py` 使用**服务器进程**的 `datetime.now(timezone.utc)`；与用户本地「今天」可能差 ±1 日，以任务结果 `meta.retrieval_date` / `timezone_note` 为准。 |

**此前误用会话静态日期属错误**；执行本 Skill 时**必须先 `date`（或 Worker 侧已定义的时间源）再搜**。

## 与本项目工具的关系

| 能力 | 位置 |
|------|------|
| Agent 工具 | `google_search`（`backend/core/agent/tools/builtin/google_search_tool.py`） |
| 统一搜索 | `backend/services/google_search_service/unified_search.py` 的 `web_search()` |
| 系统提示约束 | `CHAT_SYSTEM_PROMPT`：须先搜索；联网信息须链接+摘录、区分来源 |
| 服务端热点任务 | `ai_hot_news_digest` → `process_ai_hot_news_digest_task`（`task_handlers.py`） |

## 检索策略（多轮、多角）

1. **确认日期**：摘要开头写清**检索所依据的日期/时区**；须与上一节 **`date`（或任务 meta）** 一致。用户明确说「按我本地」时可再用用户给出的日期覆盖，否则**以机器 `date` 为准**。
2. **多查询**：至少 **6～9 次** `google_search`（或等价工具），**避免只搜大厂公关与监管**；须覆盖：
   - 泛搜：`AI news today`、`人工智能 最新 动态` + 当日/当月日期
   - **智能体 / Agent**：`AI agent`、`multi-agent`、`autonomous agent workflow`
   - **可进化智能体 / OpenClaw 系**（社区常称「龙虾」；生态内多 **xxxclaw** 命名变种）：`OpenClaw`、`evolvable agent`、`xxxclaw` 等与框架/开源动态相关的检索（服务端默认已单列一轮，见 `queries.py`）
   - **行业落地**：`enterprise AI adoption`、`vertical AI`、`制造/医疗/金融` + AI（按语境）
   - **具身 / 自动化**：`robotics AI`、`embodied AI`、`industrial automation`（与当周素材相关时）
   - **技术趋势与工程化**：`RAG`、`inference`、`MCP`、`open source LLM`、`context engineering`
   - 投融资：`AI startup funding`（保留但勿独占篇幅）
   - 产品/模型：新模型、开源权重、评测（**不必**把每条都写成 OpenAI/Google 头条）
   - 政策/安全：`AI regulation`、安全与滥用（**控制篇幅**，勿盖过应用与工程）
3. **参数**：`num_results` 建议 **10～20**（Tavily 单次上限 20）；重要主题可对同一主题换关键词**二次检索**补洞。
4. **去重合并**：同一事件多来源时，**合并为一条叙述**，正文可写「另据 ×× 报道…」并**多链接**。
5. **篇幅平衡**：正文勿以大厂动态 + 政策为主；智能体、垂直落地、技术栈与生态（含 **OpenClaw / xxxclaw** 等可进化智能体动向）应占**足够展开**（服务端 `ai_hot_news_digest` 默认检索词已按此配比，见 `backend/services/ai_hot_news_digest/queries.py`）。

## 输出结构与深度要求

摘要须包含以下区块（无素材的区块可写「本日检索未覆盖」一句，不硬编）：

### 1. 执行摘要（必读）

- **3～6 句**连贯中文（或用户语言），概括**当日/当周最重要 2～4 件事**、**为何重要**（对产业/用户/监管的影响各用一两笔点到即可）。

### 2. 分主题正文（必读，要有厚度）

按素材**自拟小标题**（不必全有，但有内容的主题要展开），**优先**写清智能体、行业落地、技术趋势，再写大厂与政策，例如：

- **智能体与工具链**：Agent 框架、多智能体、工作流、开发者工具与平台；**谁、解决什么场景、与单纯 Chat 的差异**。若素材涉及 **OpenClaw** 及社区 **xxxclaw** 命名系可进化智能体，须单独成段说明生态与变种，勿与「大模型头条」混写。
- **行业应用与垂直场景**：制造、医疗、金融、零售等落地；**案例级信息**（主体、场景、效果或规模）若检索中有则写入。
- **模型、算力与工程化**：开源模型、推理/RAG/上下文工程、评测与基准；新 API/定价若检索中有则写入。
- **投融资与公司动向**：每条 **2～4 句**；金额、轮次、投资方等以检索为准。
- **政策、标准与安全**：法规与治理**控制篇幅**，勿挤压应用与工程类主题。

**单条「热点」最低标准**（不满足则并入他条或省略）：

- 除链接外，正文 **不少于约 80～150 字**（该条合计），含**至少一项**具体信息：数字、公司/人名、产品名、时间或监管主体。
- 紧跟 **1 条短摘录**（工具返回的 snippet 或抓取正文原句，**≤180 字**，引号标出）。
- **至少 1 个 Markdown 链接**；多来源同一事件可 **2～3 个链接**。

### 3. 交叉观察（选填，有则写）

- **1 段（4～8 句）**：不同主题之间的联系（例如「融资收紧 + 推理成本下降 → 中小模型策略」）；**仅基于检索内容归纳**，勿纯臆测；可写「检索未覆盖长期趋势，以下为当日信息粗浅串联」。

### 4. 检索说明（必读，简短）

- 列出**使用过的关键词/查询意图**（不必贴全文 query）、**大致结果条数**或「某主题结果较少」；若失败则说明**未调用工具或环境限制**，不得假装已搜。

### 5. 参考资料（必读）

- **穷尽列出**正文用过的来源：`- 「摘录原文…」 — [标题或站点](URL)`；**摘录与正文引用对应**。
- 若来源 **超过 15 条**，正文可只列核心，参考资料仍应**完整**或附「另见」子列表。

## 篇幅与语言

- **总篇幅**：中文建议 **约 1200～3500 字**（或用户要求更长时再扩）；英文则 **约 800～2500 词**量级。用户明确要「短讯」时可降级，但**默认按深度摘要**执行。
- **语言**：与用户一致；中英混排时保持术语一致。
- **中文术语（必读）**：**时间**：2026-04-11；**理由**：中文读者与媒体普遍用「智能体」指 AI Agent；**方法**：中文正文里泛指 **agents / autonomous agents** 时写 **「智能体」**，避免孤立使用英文 **Agent**；产品/项目官方英文名（如「Microsoft Agent Framework」）保留原名，首次出现可括注「（智能体…）」。检索 query 仍可用英文关键词。

## 禁止

- 无工具调用却声称已做「今日」联网检索。
- 只有标题+链接、无展开与摘录。
- 编造检索中未出现的金额、日期、发言人或文件名称。

## 在仓库内验证（可选）

- `web_search` 任务、`TAVILY_API_KEY`、DuckDuckGo 回退：见 [reference.md](reference.md)。
- 服务端一键摘要：任务类型 **`ai_hot_news_digest`**，见 [reference.md](reference.md)。

## 输出模板（加长版，可复制）

```markdown
# 今日 AI 热点深度摘要（检索日期：YYYY-MM-DD｜时区：…）

## 执行摘要
（3～6 句总览）

## 智能体与开发者生态
…

## 行业应用与垂直场景
…

## 模型、算力与工程化趋势
…

## 投融资与公司动向
…

## 政策、标准与安全
…

## 交叉观察
（1 段，4～8 句，基于当日素材）

## 检索说明
- 使用的查询方向：…
- 结果概况：…

## 参考资料
- 「…」 — [标题](URL)
```

## 延伸阅读

- 引用与多源格式：`backend/core/agent/system_prompt_templates.py` → `CHAT_SYSTEM_PROMPT`。
- 实现路径：[reference.md](reference.md)。
