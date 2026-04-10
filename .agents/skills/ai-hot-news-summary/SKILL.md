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

## 与本项目工具的关系

| 能力 | 位置 |
|------|------|
| Agent 工具 | `google_search`（`backend/core/agent/tools/builtin/google_search_tool.py`） |
| 统一搜索 | `backend/services/google_search_service/unified_search.py` 的 `web_search()` |
| 系统提示约束 | `CHAT_SYSTEM_PROMPT`：须先搜索；联网信息须链接+摘录、区分来源 |
| 服务端热点任务 | `ai_hot_news_digest` → `process_ai_hot_news_digest_task`（`task_handlers.py`） |

## 检索策略（多轮、多角）

1. **确认日期**：摘要开头写清**检索所依据的日期/时区**；用户说「今天」则以用户语境日期为准。
2. **多查询**：至少 **3～5 次** `google_search`（或等价工具），覆盖不同切面，例如：
   - 泛搜：`AI news today`、`人工智能 最新 动态` + 当日/当月日期
   - 投融资：`AI startup funding`、`大模型 融资`
   - 产品/模型：`LLM release`、`OpenAI Google Anthropic` + `announcement`
   - 政策/标准：`AI regulation`、`NIST AI`、`欧盟 AI 法案`（按语境）
   - 安全：`AI security`、`LLM abuse`、`prompt injection`（按当周热点）
3. **参数**：`num_results` 建议 **10～20**（Tavily 单次上限 20）；重要主题可对同一主题换关键词**二次检索**补洞。
4. **去重合并**：同一事件多来源时，**合并为一条叙述**，正文可写「另据 ×× 报道…」并**多链接**。

## 输出结构与深度要求

摘要须包含以下区块（无素材的区块可写「本日检索未覆盖」一句，不硬编）：

### 1. 执行摘要（必读）

- **3～6 句**连贯中文（或用户语言），概括**当日/当周最重要 2～4 件事**、**为何重要**（对产业/用户/监管的影响各用一两笔点到即可）。

### 2. 分主题正文（必读，要有厚度）

按素材**自拟小标题**（不必全有，但有内容的主题要展开），例如：

- **投融资与公司动向**：每条 **2～4 句**；**尽量保留**金额、轮次、估值、投资方、合作方等**检索结果中出现的具体信息**；说明「谁、做了什么、对谁有影响」。
- **模型、产品与发布**：新模型/新 API/新 Agent 产品；**能力变化、开放范围、定价或限制**若检索中有则写入。
- **企业与落地**：行业采用、云厂商、芯片/算力相关若与 AI 强相关则单独成段。
- **政策、标准与地缘**：法规、标准倡议、政府/军方采购与使用边界等。
- **安全、滥用与治理**：攻击面、滥用案例、厂商回应、缓解措施。

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

## 投融资与公司动向
### 事件一：…
（2～4 句展开，含具体信息）
> 「…摘录 ≤180 字…」
— [来源 A](URL) · [来源 B](URL)

## 模型与产品
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
