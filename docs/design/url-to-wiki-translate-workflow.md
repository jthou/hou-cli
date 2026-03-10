# 设计：URL 抓取 → 翻译成中文 → 存入同名 MediaWiki

## 1. 需求

- **输入**：任意文章 URL，例如 [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- **目标**：获取页面正文、尽量保持原文结构与信息，翻译成中文，写入 MediaWiki，页面标题与原文同名（或从 URL/标题派生）

## 2. 当前系统能力与缺口

| 环节 | 当前能力 | 缺口 |
|------|----------|------|
| **抓取 URL 正文** | 无通用「抓取任意 URL 返回正文」的任务或工具；browser 工具存在但默认未启用；orchestrator 中仅列出 `web_fetch` 名称，未实现 | 需要 **fetch_url / web_fetch** 能力：给定 URL，返回清洗后的正文（纯文本或 Markdown） |
| **翻译成中文** | 无专用「长文翻译」任务类型；Agent 可用 LLM 做翻译，但需先拿到正文 | 若用 Agent 流程：有 fetch 后即可由 LLM 翻译；若用纯任务管道：需新增「翻译」任务或复用 Agent 任务 |
| **写入 MediaWiki** | 已有 `mediawiki_write` 任务与 MediaWiki 工具，支持按标题创建/编辑、内容为 wikitext | 无缺口；标题可用户指定或由上游提供 |
| **同名 / 标题映射** | 无 | 需约定：从 URL path 或 HTML `<title>` 解析出标题，再映射为 Wiki 页面名（如 `writing-tools-for-agents` 或 `Writing effective tools for AI agents`） |

**结论**：当前系统**不能**端到端完成该工作流；主要缺失「**抓取任意 URL 正文**」这一环，以及是否用任务管道还是 Agent 完成「翻译 + 写 Wiki」的明确流程。

## 3. 推荐方案：Agent 工具 + 对话/编排

思路：为 Agent 提供 **fetch_url** 工具，由**对话式 Agent** 在一次会话中完成「抓取 → 翻译 → 写入 Wiki」；无需必先上任务管道。

### 3.1 新增：fetch_url / web_fetch 工具

- **功能**：请求 URL，返回清洗后的正文（优先用 readability / 正文提取，避免整页 HTML）。
- **输入**：`url`（必填）、可选 `output_format`（`text` | `markdown`）、可选 `max_length`。
- **输出**：正文内容 + 可选 `title`（从 `<title>` 或 URL path 解析），便于后续用作 Wiki 标题。
- **实现**：后端新工具（如 `backend/core/agent/tools/builtin/web_fetch_tool.py`），用 httpx 请求 + 正文提取（如 `readability-lxml` 或 `trafilatura`），返回结构化结果。

### 3.2 流程（对话式）

1. 用户说：「把 https://www.anthropic.com/engineering/writing-tools-for-agents 的内容翻译成中文，保持原文结构，然后存到 MediaWiki，用同名页面。」
2. Agent 调用 **fetch_url** 工具 → 得到正文 + 标题。
3. Agent 用 LLM 将正文翻译成中文（可带 prompt：保持标题层级、列表、代码块等结构）。
4. Agent 将翻译结果转为 wikitext（可先用现有 `htmlToMd`/`mdToWiki` 或直接写简单 wikitext）；若工具返回 Markdown，可用 `mdToWiki`。
5. Agent 调用 **MediaWiki 工具** `create` 或 `edit`，标题用「同名」：从 fetch_url 返回的 `title` 映射（如去掉非法字符、空格改下划线等），写入 Wiki。

### 3.3 同名规则

- **方案 A**：用 fetch_url 返回的 HTML `<title>` 或 Open Graph title，做规范化后作为 Wiki 标题（如 `Writing effective tools for AI agents`）。
- **方案 B**：用 URL path 最后一段（如 `writing-tools-for-agents`）作为 Wiki 标题。
- **建议**：优先用 **方案 A**，更贴近「同名」语义；若取不到 title 再回退到 path 或由用户指定。

## 4. 可选扩展：任务管道

若希望**不通过对话、直接提交任务**完成同一流程，可：

- **方案 A**：新增任务类型 **url_to_wiki**  
  - metadata：`url`（必填）、`wiki_title`（可选，默认由系统从 URL/标题派生）、`language`（如 `zh`）、可选 `preserve_structure`。  
  - 执行：抓取 URL → 正文提取 → 调用 LLM 翻译 → 转 wikitext → 调用 mediawiki_write 逻辑写入。  
  - 优点：一次创建、可排队、可重试、与现有任务体系一致。

- **方案 B**：管道链 **url_fetch → 翻译任务 → mediawiki_write**  
  - 新增任务类型 `url_fetch`（输出：正文 + title）、`translate`（输入：文本，输出：中文）；管道模板「URL 抓取 → 翻译为中文 → 写入 MediaWiki」，用户填 URL 与可选 Wiki 标题。  
  - 优点：模块化、可复用翻译任务；缺点：需定义并实现两个新任务类型与管道模板。

**建议**：一期先做 **fetch_url 工具 + Agent 流程**，满足「抓取 → 翻译 → 同名 Wiki」；若后续有批量或定时需求，再增加 **url_to_wiki** 任务或管道。

## 5. 性能优化与扩展性

### 5.1 并发控制

- **限制同时处理的 URL 数量**：建议 ≤5 个并发请求，避免资源耗尽和触发目标站点限流
- **实现队列机制**：使用任务队列（如现有 `task_queue`）管理 URL 抓取请求，支持优先级调度
- **优先级调度**：重要 URL（如用户主动提交）优先处理，批量导入的 URL 可降低优先级
- **超时控制**：单个 URL 抓取超时时间建议 30 秒，翻译超时建议 60 秒

### 5.2 长文处理

- **自动分段翻译**：超过 5000 字符的正文自动分段，每段独立翻译后合并
- **保持段落间逻辑连贯性**：分段时按段落边界（`<p>`、`\n\n`）切分，避免在句子中间断开；翻译时保留上下文提示（如「这是文章的第 2 段，前文讨论了...」）
- **支持断点续传和增量更新**：若翻译中断，记录已处理段落，支持从断点继续；若 Wiki 页面已存在，支持增量更新（仅更新变更部分）
- **缓存机制**：相同 URL 的抓取结果可缓存（TTL 建议 24 小时），避免重复请求

## 6. 安全设计

### 6.1 URL 过滤

- **可信域名白名单**：维护可信域名列表（如 `anthropic.com`、`github.com` 等），默认仅允许白名单内的 URL；可通过配置扩展
- **恶意网站检测**：集成 URL 安全检测服务（如 Google Safe Browsing API 或本地黑名单），拒绝访问已知恶意站点
- **请求频率限制**：限制单用户请求频率（建议 ≤10 次/小时），防止滥用和 DoS 攻击
- **URL 格式校验**：严格校验 URL 格式，拒绝 `file://`、`javascript:` 等危险协议

### 6.2 内容安全

- **敏感词过滤**：翻译前后进行敏感词检测，支持自定义屏蔽词库（可配置）
- **内容审核工作流**：可选启用内容审核（如调用审核 API 或人工审核），对翻译结果进行二次检查
- **输入输出长度限制**：限制单次抓取的正文长度（建议 ≤100KB），防止内存溢出
- **错误信息脱敏**：返回错误时避免泄露内部路径、API Key 等敏感信息

## 7. 监控与告警

### 7.1 关键指标

- **URL 抓取成功率**：成功抓取并提取正文的 URL 占比（目标 ≥95%）
- **翻译准确率评估**：通过人工抽样或自动评估（如 BLEU、语义相似度）评估翻译质量
- **维基写入成功率**：成功写入 MediaWiki 的请求占比（目标 ≥98%）
- **平均处理时长**：从 URL 提交到 Wiki 写入完成的总耗时（目标 ≤5 分钟/篇）
- **并发数统计**：当前正在处理的 URL 数量，用于监控系统负载

### 7.2 告警机制

- **失败率告警**：当 URL 抓取失败率超过阈值（如 20%）时触发告警，通知管理员检查网络或目标站点状态
- **处理时间异常告警**：当平均处理时长超过阈值（如 10 分钟）时告警，可能表示系统负载过高或翻译服务异常
- **系统资源使用率告警**：监控 CPU、内存、网络使用率，超过阈值（如 CPU >80%、内存 >85%）时告警
- **安全事件告警**：检测到恶意 URL 或敏感内容时立即告警，记录日志并阻止处理

## 8. 实现清单（一期）

| 项目 | 说明 | 优先级 |
|------|------|--------|
| **web_fetch_tool** | 已实现：`backend/core/agent/tools/builtin/web_fetch_tool.py`；可选依赖 trafilatura（见 requirements 注释） | P0 ✅ |
| **Agent 注册** | 在 orchestrator 中注册 web_fetch 工具，并确保 MediaWiki 工具已注册 | P0 ✅ |
| **Prompt 约定** | 在系统 prompt 中说明：用户要求「把某 URL 翻译成中文存到同名 Wiki」时，先 fetch_url → 再翻译 → 再 mediawiki create/edit，标题从 fetch 结果或 URL 派生 | P0 ✅ |
| **标题规范化** | 工具或 Agent 内：将 title 转为 Wiki 合法标题（空格、特殊字符等处理） | P0（由 Agent 在写 Wiki 时处理） |
| **长文分段处理** | 超过 5000 字按段落分段翻译（Agent prompt + url_to_wiki 任务内 _chunk_text_by_paragraphs） | P1 ✅ |
| **单元测试** | `backend/core/agent/tools/tests/test_web_fetch_tool.py`：校验、抓取 mock | P1 ✅ |
| **url_to_wiki 任务** | 任务类型 url_to_wiki：抓取 → 分段翻译 → 写入 MediaWiki（task_handlers + 前端展示） | P2 ✅ |
| **告警机制** | 实现失败率、处理时间异常的告警通知 | P2 |
| **内容安全过滤** | 实现敏感词过滤和自定义屏蔽词库 | P2 |

## 9. 方案评估与推荐

### 9.1 综合评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **完整性** | 7/10 | 覆盖了核心功能，补充性能、安全、监控后可达 9/10 |
| **实用性** | 8/10 | 提供了清晰的实施步骤和代码结构，符合现有架构 |
| **前瞻性** | 6/10 | 对扩展场景（批量处理、定时任务）考虑不够充分，需补充 |
| **规范性** | 8/10 | 符合项目现有架构和命名规范，与现有任务体系兼容 |
| **可测试性** | 6/10 | 缺乏详细的测试策略和边界场景，需补充单元测试和集成测试 |
| **总体评分** | **7.0/10** | 核心方案清晰，需补充非功能性需求 |

### 9.2 最佳方案推荐

综合考虑完整性和实用性，推荐采用**混合方案**：

1. **核心采用 Agent 工具方案**（文档推荐的一期方案）
   - 快速上线，满足单次「抓取 → 翻译 → 同名 Wiki」需求
   - 通过对话式交互，用户体验友好
   - 实现成本低，复用现有 Agent 和 MediaWiki 工具

2. **补充任务管道扩展**（二期批量处理）
   - 新增 `url_to_wiki` 任务类型，支持批量 URL 处理
   - 支持定时任务和计划任务（如每日同步某博客文章）
   - 与现有任务队列体系无缝集成

3. **增加安全和监控机制**（按上述建议完善）
   - 实现 URL 白名单、频率限制、内容安全过滤
   - 建立监控指标和告警机制，保障系统稳定运行
   - 支持性能优化（并发控制、长文分段、缓存）

**实施路径**：
- **Phase 1**（1-2 周）：实现 `web_fetch_tool` + Agent 流程 + 基础安全（URL 白名单、频率限制）
- **Phase 2**（2-3 周）：补充性能优化（并发控制、长文分段）+ 基础监控
- **Phase 3**（1-2 周）：实现 `url_to_wiki` 任务类型 + 告警机制 + 内容安全过滤

这样的组合既保证了初期快速上线，又为后续扩展留下了空间，是目前最完整和实用的解决方案。

## 10. url_to_wiki 与任务管理体系

本节厘清 **url_to_wiki** 在任务管理体系中的位置、与现有任务类型/工具的关系，以及所有集成点，便于统一使用与扩展。

### 10.1 任务管理体系结构总览

当前体系包含三类使用方式，共用同一套**任务类型定义**（`TASK_TYPES`）与**任务队列**（`tasks` 表 + Worker 执行）：

| 维度 | 说明 | 相关 API / 前端 |
|------|------|-----------------|
| **即时任务** | 用户创建后入队，Worker 按优先级拉取执行；无依赖或带 `depends_on_task_id` + `input_bindings` | `POST /api/task-queue/tasks`；任务管理页「创建任务」 |
| **定时任务** | 按 `schedule_type`（interval/cron）在指定时间创建「即时任务」并写入队列，任务带 `created_by_schedule_id` | `POST /api/task-queue/scheduled-tasks`；任务管理页「定时任务」Tab |
| **管道** | 多个任务通过 `depends_on_task_id` + `input_bindings` 串联；上游 result 解析后合并进下游 metadata；可选 `pipeline_id` 分组展示 | 管道模板（如「视频提音频 → 语音转文字」）；创建任务时可选「输入来自某任务」 |

任务类型的**可链接性**由 `pipeline_outputs`（上游产出）与 `metadata_schema` 中的 **pipeline_accept**（下游可接受）描述；API 提供「可链接的上游任务类型」与推荐绑定，供前端展示。

### 10.2 url_to_wiki 在体系中的位置

- **类型**：与 `mediawiki_write`、`wechat_mp_draft`、`video_download` 等并列的**独立任务类型**。
- **输入**：仅来自用户表单（`metadata.url` 必填，`metadata.wiki_title`、`metadata.language` 可选）；**不**声明 `pipeline_accept`，即不参与「上游任务输出 → 本任务输入」的管道绑定。
- **输出**：执行结果写入 `result`（含 `status`、`summary`、`data.url`、`data.wiki_title`）；**不**声明 `pipeline_outputs`，即当前没有下游任务类型消费「url_to_wiki 的产出」。
- **结论**：url_to_wiki 是**叶子任务**，只支持「用户填 URL → 排队执行 → 写 Wiki」；可单独创建、可加入定时任务，**不**作为管道中的一环（上游或下游）。

### 10.3 与现有工具 / 任务类型的关系

| 对象 | 与 url_to_wiki 的关系 | 说明 |
|------|------------------------|------|
| **web_fetch 工具** | 能力复用，入口不同 | Agent 对话时由 Orchestrator 调用 `web_fetch` 工具；url_to_wiki 任务内部调用 `WebFetchTool().execute(url=url)`，同一套抓取与正文提取逻辑（白名单、限频、并发、trafilatura 回退）两处共用。 |
| **mediawiki_write 任务** | 逻辑包含，非调用关系 | url_to_wiki 内部最后一步是「写入 MediaWiki」，与 mediawiki_write 的写入逻辑等价（均通过 `MediaWikiTool().execute(operation=..., title=..., content=...)`），但 url_to_wiki **不**通过「先创建 mediawiki_write 任务再执行」实现，而是本任务内直接调 MediaWiki 工具；两者是并列任务类型，用户可选「只写已有内容」用 mediawiki_write，「抓取+翻译+写」用 url_to_wiki。 |
| **MediaWiki 工具** | 被 url_to_wiki 使用 | 任务 handler 在「翻译完成后」调用 `MediaWikiTool().execute(operation="edit", title=wiki_title, content=translated, ...)`，与 Agent 使用同一工具。 |
| **LLMService** | 被 url_to_wiki 使用 | 任务 handler 内调用 `LLMService().chat(...)` 做「正文 → 中文 wikitext」翻译（含长文分段），与 Agent 使用同一 LLM 配置。 |
| **Agent 对话流程** | 等价能力，不同入口 | 用户对 Agent 说「把某 URL 翻译成中文存到同名 Wiki」时，由 prompt 驱动：web_fetch → LLM 翻译 → mediawiki 工具写入；与「创建 url_to_wiki 任务」在效果上等价，但前者是对话式、一次性，后者是队列化、可定时、可重试、可查历史。 |

关系可简化为：

- **web_fetch**：Agent 与 url_to_wiki 任务**共用**的抓取能力。
- **mediawiki_write**：仅「写已有内容」；**url_to_wiki**：抓取 + 翻译 + 写，二者互补，不互相调用。
- **管道**：当前无「产出 URL 的上游任务」且 url_to_wiki 不声明 pipeline_accept，故**不参与**管道编排；若未来有「批量 URL 列表」类上游，再考虑 pipeline_outputs / pipeline_accept 与管道模板。

### 10.4 任务管理体系内的集成点

以下清单确保 url_to_wiki 在「任务管理」中与其它类型一致可用：

| 集成点 | 说明 | 状态 |
|--------|------|------|
| **任务类型定义** | `backend/infrastructure/execution/task_handlers.py` 中 `TASK_TYPES["url_to_wiki"]`：name、description、metadata_schema（url、wiki_title、language） | ✅ 已实现 |
| **任务处理器** | `process_url_to_wiki_task` 注册为 `url_to_wiki` 的 handler；超时在 `task_worker.TASK_TIMEOUT_SECONDS["url_to_wiki"]`（如 15 分钟） | ✅ 已实现 |
| **任务创建 API** | `POST /api/task-queue/tasks` 接受 `task_type: "url_to_wiki"`，metadata 校验走通用 schema；任务名生成在 `_generate_task_name` 中对 url_to_wiki 做分支（如「URL→Wiki {url 前 40 字}」） | ✅ 已实现 |
| **任务类型列表 API** | `GET /api/task-queue/task-types` 返回的 `task_types` 包含 url_to_wiki，供前端下拉与表单生成 | ✅ 由 TASK_TYPES 统一提供 |
| **即时任务创建 UI** | 任务管理页「创建任务」：类型下拉含「URL 翻译存 Wiki」；表单由 `metadata_schema` 驱动（url 必填，wiki_title、language 可选），无需单独写死字段 | ✅ 通用表单支持 |
| **定时任务** | 定时任务创建/编辑时，`task_type` 可选 url_to_wiki；metadata 同即时任务；调度逻辑无需区分类型 | ✅ 通用定时逻辑支持 |
| **任务详情 / 结果展示** | 任务列表与详情中，`task_type === 'url_to_wiki'` 时用 `TaskResultDisplay` 展示 summary、源 URL、Wiki 页面标题 | ✅ 已实现 |
| **管道** | url_to_wiki 无 pipeline_outputs / pipeline_accept，不参与「可选上游 / 推荐绑定」；管道模板中**暂无**「批量 URL → 多个 url_to_wiki」等模板，可后续按需加 | ⭕ 当前不参与管道；模板可扩展 |

### 10.5 使用方式汇总

| 使用方式 | 入口 | 适用场景 |
|----------|------|----------|
| **对话** | 与 Agent 对话：「把 https://... 的内容翻译成中文并存到同名 Wiki」 | 单次、即时、无需进任务列表 |
| **即时任务** | 任务管理 → 创建任务 → 类型选「URL 翻译存 Wiki」→ 填 url（必填）、wiki_title（可选）→ 提交 | 单次、可排队、可重试、可查历史与结果 |
| **定时任务** | 任务管理 → 定时任务 → 新建 → 类型选「URL 翻译存 Wiki」→ 填 metadata + 调度（interval/cron） | 定期同步某 URL 到 Wiki（如每日/每周） |

### 10.6 Wiki 分类标签（Category）

写入的译文页面会自动带上以下 **[[Category:xxx]]**，便于按来源与时间查找、评审：

| 分类 | 来源 | 含义 |
|------|------|------|
| **hou-cli** | MediaWiki 工具统一写入 | 由本系统（hou-cli）创建/编辑的页面 |
| **网文抓取** | url_to_wiki 默认追加 | 来自 URL 抓取并翻译的网文，便于筛选 |
| **YYYY年M月D日** | url_to_wiki 自动追加 | 写入日（如 2025年2月27日），按日查找 |
| **YYYY年第N周** | url_to_wiki 自动追加 | 写入周（ISO 周，如 2025年第9周），按周查找 |
| **YYYY年M月** | url_to_wiki 自动追加 | 写入月（如 2025年2月），按月查找 |

- **默认行为**：不填 `metadata.categories` 时，任务会追加 `[[Category:网文抓取]]` 以及当日、当周、当月的三个日期分类；MediaWiki 工具再自动加 `[[Category:hou-cli]]`（不重复添加已存在的同名分类）。
- **自定义**：任务 metadata 可传 `categories`（字符串数组），在该列表基础上再追加上述三个日期分类；可用于增加主题分类。

### 10.7 可选扩展（后续）

- **管道**：若有「产出 URL 列表」的上游任务（如某爬虫任务），可为 url_to_wiki 增加 `pipeline_accept`（如接受 `result.data.url`），并提供管道模板「上游产出 N 个 URL → 创建 N 个 url_to_wiki 任务」。
- **批量创建**：前端或 API 支持「多个 URL 一次提交」→ 后端拆成多个 url_to_wiki 任务（同 pipeline_id 可选），便于批量搬运。
- **结果复用**：若未来有「基于 Wiki 页面再做后续处理」的任务类型，可为 url_to_wiki 增加 `pipeline_outputs`（如 `result.data.wiki_title`），供下游消费。

---

## 11. 参考

- 用户提供的目标 URL：[Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)（Anthropic 工程博客）
- 现有能力：`mediawiki_write` 任务、MediaWiki 工具、`wikiMdConvert`（MD↔Wiki）、`mdToHtml`（MD↔HTML）
- 任务管道设计：`docs/design/task-pipeline-design.md`
- 定时任务设计：`docs/design/scheduled-tasks-implementation.md`
