# PPT Assistant 增强版设计（对齐 banana-slides 思路）

**时间**：2026-04-01  
**定位**：在现有 `backend/services/ppt_assistant`、HTTP/CLI、前端 `PptAssistant.jsx` 与 [`ppt-assistant-design.md`](./ppt-assistant-design.md) 的基础上，参考开源项目 **banana-slides**（本地可参考 clone）在「文案生成」上的工程化经验，规划一条**可分期落地**的「最强」PPT 文案助手路线。  
**不重复**：数据契约细节与 MVP 范围仍以 `ppt-assistant-design.md` 为准；本文聚焦**问题—目标—技术—步骤**。

---

## 0. 重新对齐：目标与技术方案的匹配标准（定义“gap”如何消失）

你提出的“gap”指的是：**目标很高，但技术方案本质上做不到**。因此本文把“可达性”作为约束，先给出匹配标准：

- **强 refine 可达**：必须具备 **locks + patch + deterministic merge**，否则无法保证“局部最小影响且不覆盖用户编辑”。  
- **页级素材强对齐可达**：必须具备 **sources 绑定 + validator 检查跨页挪用 + repair**，否则素材串页不可控。  
- **并行+流式+可取消可恢复可达**：必须有 **run_id/job 状态存储**，否则 SSE 只是展示通道，断线恢复/取消成本控制做不到。  
- **分步模型可达**：必须所有中间态过 **validator/repair**，否则分步会放大漂移与解析失败。  

后文的“技术方案”与“实施步骤”都以此为硬约束；不满足这些约束的方案，即使写了接口与分期，也属于“目标—方案不匹配”的 gap。

## 1. 要解决的问题

### 1.1 用户与产品侧

| 问题 | 说明 |
| ------ | ------ |
| **输入形态单一** | 当前主路径是「长文 + 少量 meta」；缺少「逐页素材包」：每页的既有标题/要点、配图说明、表格摘要、用户备注、**额外结构化字段**（如渠道口径、合规禁用词）等与模型对齐的标准载体。 |
| **输出可编辑性与回溯弱** | `slide_deck` 已有 bullets / `speaker_notes`；与 banana-slides 类方案相比，缺少**页面级扩展字段**（例如：副标题、口播分段、素材引用 ID、生成置信提示），不利于二次编辑与 diff。 |
| **长文本与多页场景的延迟/成本** | 分块抽取 + 合并已缓解上下文问题；多页或「每页长描述」时仍是**串行**调用为主，缺少可选的**并行**与**流式**体验，用户感知等待长。 |
| **增量迭代成本高** | 用户常说「只改第 3 页口径」「把某条改成更像 Keynote」；当前多为整段重跑或手动改 JSON，缺少**针对单页 / 单 claim 的 refine** 与**版本化草稿**。 |
| **模型策略粗粒度** | 单次请求通常绑定**一个**可选 `model`。抽取、合并、分页、口播扩写、润色对模型能力需求不同；banana-slides 倾向**按步骤 / 按任务**选模型与参数，当前未系统化。 |
| **运维与可观测性** | 提示词与步骤若分散在路由与 service 中，难以做 A/B、缓存 provider 客户端、统一重试与计费归因。 |

### 1.2 工程侧

| 问题 | 说明 |
| ------ | ------ |
| **缺少「生成模式」开关** | 无等价于 banana-slides 的 `description_generation_mode`：**流式**（早停、逐段展示）vs **并行**（多页同时生成再组装）的策略选择与降级路径。 |
| **缺少结构化任务层** | 未抽象「Project / Deck / Page 任务」队列：重试、部分失败继续、进度 SSE、可取消（与现有 Hou CLI 任务体系optional 对齐）。 |
| **前后端契约可演进性** | `ppt_elements` / `slide_deck` 版本号为 1；增强字段需**向后兼容**的 schema 演进与迁移规则。 |

---

## 2. 要达到的目标

### 2.1 体验目标

1. **同一套中间结构**（延续 `ppt_elements` → `slide_deck`），但支持**从「大纲稿」到「逐页定稿」**渐进深化，而不是只有一次性生成。  
2. **输入侧**支持：**长文**、**分块上传**、**每页素材卡**（文字 + 图片占位说明 + extra fields），与 banana-slides「多维输入」对齐。  
3. **输出侧**每页除 bullets / notes 外，具备**可扩展字段**（extra），并能在前端以表单编辑后再「仅重生成受影响部分」。  
4. **生成过程**可选：**流式**展示（SSE/分块 token 或分段 JSON）、**并行**生成多页描述（`ThreadPoolExecutor` / `asyncio.gather` 可控并发），失败页可单页重试。  
5. **模型与参数**：**按步骤配置**（extract / merge / deck / refine / polish），与现有 `useSelectableModels`、后端 model 路由打通；可选「快模型草稿 + 强模型定稿」流水线。  

### 2.2 工程目标

1. **单一业务内核**：HTTP、CLI、（未来）异步任务共用 `backend/services/ppt_assistant` 入口，符合既有 §6.5 模块化原则。  
2. **可测试**：无 LLM 的分块、归并、归一化、契约校验保持高覆盖；集成测试 mock LLM，不断言措辞 golden。  
3. **可配置**：生成模式、并发上限、每步模型、`user_requirements` 优先级等行为由**配置 + 环境变量**暴露，避免硬编码在路由内。  

### 2.3 非目标（本路线图不承诺）

- 完美 WYSIWYG 幻灯片编辑器、复杂矢量图表自动生成。  
- 与 Wiki / `pdf_to_wiki` 默认打通（可作为后续独立集成项）。  
- 替代专业设计工具的母版级像素还原（仍以 `python-pptx` + 有限模板为主，见原设计 §0.5.2）。  

---

## 3. 采用的技术与架构要点

### 3.1 数据与契约

- **延续** `ppt_elements`（§3.1）与 `slide_deck`（§3.2），新增 **optional** 字段而非破坏性变更：  
  - `ppt_elements.meta`：`extra: dict`、**逐页素材** `page_inputs[]`（可选，对齐 banana-slides 的「页级上下文」）。  
  - `slide_deck.slides[]`：`subtitle`、`speaker_script_segments[]`、`assets[]`（引用 ID）、`extra: dict`。  
- **版本策略**：`version` 递增 + 后端「宽松解析 + 默认补空」，前端旧数据仍可编辑。  

#### 3.1.2 为强 refine 与强对齐补的“可验证字段”（建议 v2 起）

- **绑定与追踪**：`slides[].sources[]`（引用 `page_inputs` 或 elements 的 id/index），用于 validator 检查“本页只用本页素材”。  
- **锁定语义**：`slides[].locks`（对象），明确哪些字段/路径由用户锁定不可被模型覆盖。  
- **编辑分层（可选）**：`slide_deck.user_edits`（按 slide 存储用户 edits），与模型生成字段 deterministic merge。  

以上字段的目的不是“多加字段”，而是让关键目标变成**可验证**、可修复、可回归测试的工程对象。

### 3.1.1 为了“最强目标”必须新增的三个硬能力

如果目标真的要达到「页级素材强对齐」「强 refine（局部最小影响且不覆盖用户编辑）」「并行+流式+可取消且可恢复」，仅靠“LLM 一次性吐 JSON + 少量后处理”是**不够**的。需要把下面三块作为**硬依赖**写进技术方案，否则目标与实现会天然不匹配。

1. **Validator + Repair loop（结构稳定器）**
   - **做什么**：对每个阶段产物（elements / plan / slide / deck）执行 schema 校验与规则校验（例如：单页 bullets 上限、每页必须引用自身 page_inputs 的 assets、禁止跨页串素材）。失败时进入 **repair prompt**（携带校验错误列表），限定重试次数；仍失败则降级为可读 Markdown 或返回部分成功。
   - **为什么必须**：分步模型、并行生成、多源输入会显著增加结构漂移与漏字段；没有修复闭环，“最强”会变成“不稳定”。

2. **可控更新机制（locks + patch merge，deterministic）**
   - **做什么**：把“用户编辑”与“模型生成字段”分离或显式标注锁定；Refine 请求携带 patch（建议 JSON Patch / 自定义 ops），后端只允许改动目标 slide/字段路径；生成新内容后用确定性合并策略写回，避免模型推翻用户编辑。
   - **为什么必须**：否则 refine 只是“再生成”，无法保证最小影响、无法保证用户编辑不被覆盖。

3. **轻量任务编排层（stage/page 状态，可取消，可部分成功，可恢复）**
   - **做什么**：把 pipeline 变成可观测的 job：`project_id/run_id`、stage 状态、每页状态、重试计数、取消信号；支持并行 Draft 时逐页产出、逐页失败；流式时按事件协议推送；断线后可用 run_id 拉取当前进度或最终结果。
   - **为什么必须**：不引入任务层，SSE/并行/取消只能做到“断连接不再推送”，无法控制成本与资源，也无法稳定提供“失败页重试/断线恢复”体验。

### 3.2 生成管线（Pipeline）

在现有 `extract_ppt_elements` / `generate_slide_deck` 之外，抽象**显式阶段**（内部可组合调用）：

| 阶段 | 职责 | banana-slides 对应思想 |
| ------ | ------ | ------------------------ |
| **Ingest** | 校验输入、组装 `ProjectContext`（meta + 页级素材 + 附件摘要） | 结构化设置与多源输入 |
| **Extract** | 长文 → `ppt_elements`（已有分块/合并） | 统一 Prompt + JSON 输出 |
| **Plan** | 从 `ppt_elements` 生成「页级提纲 / 顺序 / 过渡页」结构（多页模式） | 任务拆分 |
| **Draft** | 每页初稿（可并行） | parallel 模式 |
| **Stream polish**（可选） | 对单页或整 deck 流式润色 | streaming 模式 |
| **Refine** | 用户给定 delta（改第 k 页、改某 claim）局部重算 | 增量迭代 |
| **Normalize** | `enforce_single_slide_deck` 等确定性后处理 | 输出契约稳定 |

> 关键补强：每个阶段都必须接入 §3.1.1 的 Validator/Repair；Refine 必须走 locks+patch 的确定性合并；并行与流式必须落在“轻量任务编排层”之上，否则无法达成目标体验与稳定性。

### 3.3 模型与 Provider

- **沿用** `LLMService`、DashScope/兼容 OpenAI 接口；按阶段注入不同 `model` 与 `temperature`。  
- **配置来源**：  
  - 短期：扩展 `RunRequest` / 环境变量（如 `PPT_ASSISTANT_MODEL_EXTRACT`）。  
  - 中期：与 `/api/models/selectable`、写作配置共用一层「profile」或 `writing_profile.json` 风格条目，避免前端写死。  
- **客户端复用**：对同一 provider 复用 httpx client / 连接池（与全仓 `httpx_default_network_kwargs` 一致），减少冷启动（对标 banana-slides 的 provider 缓存思路）。  

### 3.4 流式与并行

- **流式**：FastAPI `StreamingResponse` / SSE；LLM 侧若 API 支持 `stream=True`，将 token 或「段落边界」推前端；若不支持，可对 **按页 chunk** 的 JSON 分块 flush（降级）。  
- **并行**：多页 `Draft` 使用 `asyncio.Semaphore` 限制并发；抽取合并保持顺序一致性；并行结果写入**带 index 的列表**再排序归并。  
- **开关**：`generation_mode: stream | parallel | sequential`（可并存：parallel draft + stream polish）。  
- **为达标必须补**：流式/并行不是“返回方式”，而是“任务运行方式”。必须有 run_id、逐页状态、取消与重试；否则无法做到“失败页重试、断线恢复、成本可控”的高目标。

### 3.5 提示词与 Agent

- **提示词**：集中 `backend/services/ppt_assistant/prompts.py`（已有），按阶段拆分模块或子包，**禁止**在 route 内写长 prompt。  
- **Agent**：不强制首轮上自主 Agent；**Refine** 阶段可接入现有 Agent 工具（检索、事实核对）作为 **optional 插件**，以免过度工程。  

### 3.6 前端

- **延续** `PptAssistant.jsx` 两栏布局；增加：生成模式选择、按页卡片编辑、`extra` 折叠面板、SSE 消费与中断按钮。  
- **复用** `useSelectableModels`，扩展为「全局默认 + （可选）高级：分步模型」折叠配置。  

---

## 4. 实施步骤（建议分期）

### 阶段 A：先把“结构稳定”做出来（Validator/Repair + 产物分层）

1. **引入 schema 校验与规则校验**：定义 elements/plan/slide/deck 的最小 schema（v1/v2 兼容），并实现 validator（不依赖 LLM）。  
2. **Repair prompt 闭环**：所有 LLM 输出必须先 parse→validate；失败就走 repair（携带错误列表），限制重试次数与降级策略。  
3. **产物分层**：把 `deck_plan`（页级提纲/页数/顺序）独立成中间态，避免直接从 elements 一步到 deck 导致不可控漂移。  
4. **模块拆分落地**：在 `backend/services/ppt_assistant` 内形成 orchestrator（pipeline 类），HTTP/CLI 复用同一入口。

### 阶段 B：可控 refine（locks + patch merge）先于并行/流式

1. **定义 locks 与 patch 协议**：明确哪些字段用户可锁、模型可写；patch 以 slide index/id + 字段路径为最小粒度。  
2. **Refine 的确定性合并**：后端生成“候选新内容”后，用 deterministic merge 写回；校验通过才更新 revision。  
3. **局部重算策略**：先承诺“按 slide 重算”（而不是按 bullet/claim），并用 validator 防止跨页串改。

### 阶段 C：轻量任务编排层（run_id、逐页状态、取消、部分成功、恢复）

1. **run_id 与状态存储**：内存 +（可选）落盘/缓存，记录 stage 与每页状态、错误、重试次数。  
2. **取消语义**：前端取消→后端设置 cancel flag；每一步 LLM 调用前检查；对 stream 调用尽量传播中断。  
3. **部分成功与恢复**：并行 Draft 允许部分页成功；断线后可用 run_id 拉取当前进度或最终 deck。

### 阶段 D：页级素材强对齐（page_inputs + assets 绑定 + 反串页校验）

1. **一等输入**：`page_inputs` 不再“藏进 meta 字符串”，而是强 schema 输入（含 asset_id 引用）。  
2. **强对齐校验**：validator 检查“每页输出只使用本页允许的 assets/extra”，发现串页则触发 repair。  
3. **多模态汇合**：VL 输出也必须落到 page_inputs 的结构上（而不是落到自由文本里），保证可验证与可修复。

### 阶段 E：产品与运维 polish

1. 前端草稿版本号（localStorage 或 IndexedDB 单 key 多版本可选）。  
2. 指标：按 `run_id/stage/model/page_index` 归因耗时、失败原因、repair 次数、重试次数；支持 A/B（至少通过配置开关与日志维度）。  
3. 文档：更新 `ppt-assistant-design.md` 文首三分表；CLI 子命令与 HTTP 对齐 `refine` / `parallel`。  

---

## 5. 验收标准（节选）

- **兼容**：旧客户端不传新字段时行为与当前一致。  
- **正确性**：单测覆盖 v1/v2 解析、并行归并顺序、`enforce_single_slide_deck` 与 refine 后仍满足契约。  
- **体验**：多页 10 页量级在「并行 +  reasonable 并发」下 P95 延迟优于纯串行；流式模式首字节时间可感知缩短。  
- **可运维**：同一输入在 CLI 可复现 HTTP 步骤（延续 §6.5 原则）。  

### 5.1 “高目标可达”的硬验收（用于判定 gap 是否消失）

- **强 refine**：对 `target_slide_indexes=[k]` 的 refine，非目标 slide 的内容不应被模型改写；`locks` 指定的字段必须保持不变；patch 失败必须返回可解释错误而非静默忽略。  
- **页级素材强对齐**：任意 slide 若引用了非本页 `page_inputs` 的 asset/extra，validator 必须能检测并触发 repair（或直接判失败）；不得出现“串页成功但未报错”。  
- **并行+流式+取消+恢复**：断线后用 `run_id` 能恢复到已完成的页结果；取消后不再产生新的页结果写回状态（至少不写回 job store）。  
- **分步模型稳定**：任何一步输出结构不合法都必须被 repair 闭环兜住；不允许将“结构漂移/不可解析”直接传递到下一步扩大事故面。  

---

## 6. 与现有文档的关系

| 文档 | 角色 |
| ------ | ------ |
| [`ppt-assistant-design.md`](./ppt-assistant-design.md) | 原始范围、安全、测试分层、`.pptx` 与多模态总览 |
| **本文** | 以 banana-slides 为参考的**增强路线图**（输入输出、管线、流式/并行、分步模型） |

---

## 7. 参考对照（banana-slides → 本方案映射）

| banana-slides 思路 | 本方案落点 |
| -------------------- | ------------ |
| 页级文字 / 图片 / 额外字段 | `page_inputs` + `slide_deck.slides[].extra` |
| streaming vs parallel 生成模式 | `generation_mode` + SSE + `asyncio` 并行 Draft |
| 按任务选模型与 provider 缓存 | 分步 `model_overrides` + `LLMService` 统一工厂 / httpx 默认可选 |
| 强 JSON / 强契约输出 | `json_extract` + schema 版本 + normalize 后处理 |

（以上为设计映射；若上游 API 变更，以实现时代码为准。）
