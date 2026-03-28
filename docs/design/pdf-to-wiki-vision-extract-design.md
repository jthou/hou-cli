# PDF 转 Wiki：视觉页图抽取（多页渲染 + OCR/VL）设计

**时间**：2026-03-28；**修订**：2026-03-28（审查回填）  
**范围**：在现有 `pdf_to_wiki` 任务上增加可选抽取模式，与当前 **文本层提取**（pdfminer / pdfplumber）并存。  
**不纳入首版**：从 PDF 嵌入式位图中抽取并上传 MediaWiki 文件（可另立文档）。

---

## 0. 适用范围（部署假设）

本功能默认按 **内网 / 自用工具** 落地：**不展开**对外交付下的 AGPL 许可评估、数据出境、供应商 DPA 等产品合规条目。技术选型仍记录 **PyMuPDF（AGPL-3.0）**；若将来改为对外分发或闭源产品化，需 **另起一轮许可审计**，必要时切换为 `pdf2image` + Poppler 等路径。

与此一致：**任务结果访问控制**与现有 `pdf_to_wiki` 文本路径相同，本设计 **不引入**新的权限模型假设。

---

## 1. 背景与目标

### 1.1 现状

- 任务入口：`backend/infrastructure/execution/task_handlers.py` → `process_pdf_to_wiki_task`。
- 抽取逻辑：`backend/utils/pdf_extract.py` → `extract_text_from_pdf`（文本层，无整页光栅）。
- 局限：公式多为位图或复杂排版、插图不占文本层时，**纯文本路径质量差或缺失**。

### 1.2 目标

- 保留默认行为 **`extract_mode=text`（或缺省）**，与线上一致。
- 新增 **`extract_mode=vision`**：**按页将 PDF 栅格化为 PNG**（等价于「多页截图」），再调用**已有视觉模型**（与 `web_reader` OCR 同源的 `LLMService` + 图像消息），输出 **Markdown**（含公式 `$` / `$$` 约定与 OCR 提示词对齐）。
- 后续流水线尽量复用：**分块标题、可选翻译、`md_to_wiki`、写 Wiki、multi/single 模式**。

### 1.3 非目标（首版）

- 浏览器式「真截图」；首版采用 **库内渲染** 即可。
- 自动把 PDF 内嵌图片转成 `[[File:…]]` 并上传（工作量大，单独规划）。
- **混合模式**（同一 PDF 自动在 text / vision 间择优或逐页混用）：不承诺；避免与产品预期纠缠。
- **插图保留**：`vision` 仅保证「页上可见内容」以 **Markdown 文字/公式/表格** 形式尽量复原；位图插图一般不会变成 Wiki 上的独立图片文件，**UI 与文档需说明**，避免「页图模式 = 图上所有像素都进 Wiki」的误解。

### 1.4 已知质量局限（预期管理）

- **非确定性**：同 PDF 多次运行，VL 输出可能略有差异；自动化测试只保证 **结构契约**（页序、占位、无崩溃），不做整文 golden diff。
- **版式**：多栏、脚注、复杂表格、手写批注等 **读序错误** 高发，属 VL 路径已知局限；不列为首版必修复项。

---

## 2. 方案概览

```
PDF 文件
    │
    ├─ extract_mode=text（默认）
    │       └─ extract_text_from_pdf（现有）
    │
    └─ extract_mode=vision
            └─ 每页：render_page_to_png_bytes
                    └─ LLM 视觉调用（OCR 风格 system/user prompt）
                    └─ 拼接为 chunk Markdown（§3.1 页分隔符约定）
            └─ 与现有逻辑汇合：翻译 → md_to_wiki → MediaWiki
```

**分块策略**

- 与现有「按页范围 chunk」对齐：`PDF_TO_WIKI_PAGES_PER_CHUNK`（默认 10 页）内，对 **每一页顺序**：渲染 → VL → 拼接 → **释放该页位图**（见 S5），再处理下一页。
- 若单页渲染尺寸过大触发 API 限制：对该页 **降缩放** 或 **拆成上下半屏两次识别**（CP4 后优化）。

### 2.1 页分隔符与失败占位（**必须实现一致**，避免分叉）

统一写入 **Python 常量**（例如 `backend/utils/pdf_vision_constants.py`）及 **单测**，翻译 / `md_to_wiki` / 人工 diff 均依赖此契约。

| 语义 | 格式 | 说明 |
|------|------|------|
| 第 *k* 页（1-based，与 PDF 页码一致）起始标记 | 单独一行：`\n\n<!-- pdf-vision:page K -->\n\n` | **禁止**用 `## 第 K 页` 作分隔，以免干扰标题层级与 Wiki 目录。 |
| 第 *k* 页 VL 失败 | 在对应页标记后追加：`（第 K 页：识别失败）` 单独成段；若 API 返回可公开简短原因，可追加同一括号内，**一行内无换行** | 纯正文段落，`md_to_wiki` 不会当成标题。 |

说明：HTML 注释在 MediaWiki 源文中通常保留；若个别 Wiki 配置过滤注释，仅影响「人读源文」的辅助标记，不影响正文段落结构。

### 2.2 `extract_mode` 校验语义（**拍板**）

- **缺省**或 **未传**：视为 **`text`**，与线上一致。
- **非法值**（非 `text` / `vision`）：**任务创建失败** —— API **400** / 队列入参校验拒绝；**禁止**静默回退为 `text`，以免用户误认为已启用 vision。
- 实现须 **所有入队入口一致**（见 §3.1 清单）。

### 2.3 视觉模型与环境变量（**优先级写死**）

解析顺序 **自上而下，命中即停**：

1. `metadata.pdf_vision_model`（若首版未暴露则跳过）
2. `PDF_VISION_MODEL`
3. `WEB_READER_OCR_MODEL`
4. `BROWSER_TOOL_VISION_MODEL`
5. 代码内硬编码默认（与当前 web_reader 默认视觉模型对齐）

`PDF_VISION_ZOOM`（或 DPI）仅影响渲染，不改变上述模型链。

### 2.4 日志与排错（内网仍建议遵守，避免撑爆日志与排障困难）

- **禁止**将完整 `data:image/png;base64,...` 或整段 base64 写入日志、异常栈附加字段、APM 正文。
- 允许字段示例：`extract_mode`、`pdf_path` 的 basename、**页码**、PNG **字节长度**、可选 **sha256 前 16 位 hex**、LLM **request id**、耗时。

### 2.5 成本、超时、重试、并发（首版约定）

- **调用模型**：顺序处理，**一页一请求**（chunk 内 for 循环）；**禁止**无界并行 VL，避免与 `web_reader` 等 **共用 API Key 时配额打爆**。
- **重试**：仅对 **网络超时、429、5xx** 等 **可重试错误** 退避重试（建议 **最多 3 次**，指数退避 + 抖动）；**4xx 业务错误**（除 429）不重试。单页失败 **不重试整个 chunk**，只写 §2.1 占位并继续。
- **任务总时长**：继承现有 worker 对 `pdf_to_wiki` 的配置；文档与 UI 提示：大 PDF + vision **耗时长、调用次数 ≈ 总页数**。
- **首版可选元数据**：`page_to` / `page_from`（与审查中 max_pages 类似）若已有则复用；否则在 **后续迭代** 增加 `max_pages`/`page_range`，避免首版 scope 膨胀。

### 2.6 下游上下文与翻译分块

- Vision 产出的 `raw_text` 往往 **长于** 文本路径；进入 **翻译** 前须与 text 路径使用 **同一套** 字符/段落分块与上限（`PDF_TO_WIKI_CHUNK_CHARS`、`_chunk_text_by_paragraphs`）；若单 chunk 仍超长，采用 **同等或更严** 的截断/二次分块策略，并在日志打 **warning**（不静默丢字）。

---

## 3. 实现步骤（顺序建议）

### 3.1 元数据校验入口清单（须全部对齐 §2.2）

- HTTP：`backend/api/task_queue_routes.py`（创建任务）
- Handler：`process_pdf_to_wiki_task` 内 **二次校验**（防御编程，与队列篡改无关）
- 若存在：CLI、定时任务、内部 `create_task` 封装 —— 同一 `enum` 约束

| 步骤 | 内容 | 说明 |
|------|------|------|
| S1 | 依赖 | `pyproject.toml` 增加 **PyMuPDF**；内网从简；对外场景见 §0。 |
| S2 | 渲染模块 | `backend/utils/pdf_page_render.py`：`render_single_page_to_png(pdf_path, page_index_0based, zoom) -> bytes`（推荐 **单页 API**）；**文件不存在 / 无法打开 PDF** → **抛明确异常**，由任务整体判失败，与 text 路径一致。非法页码：**调用方**避免生成；若传入则 **抛错或整任务失败**，与「跳过」二选一拍板——**推荐失败**，避免静默丢页。 |
| S3 | 常量模块 | `pdf_vision_constants.py`：页标记前缀、失败占位模板字符串。 |
| S4 | 复用提示词 | 与 `web_reader` OCR **单源** 共享公式/表格规则。 |
| S5 | VL 抽取 | `pdf_vision_extract.py`：`async` 单页入参 `(png_bytes, page_num_1based)`，内部组 `LLMService`；**禁止**在内存中 **累积** 整 chunk 的全部 PNG 再批量调用；模式为 **render → VL → 释放** 循环。 |
| S6 | 任务接入 | `process_pdf_to_wiki_task` 的 chunk 循环内分支 `vision`：按页拼 §2.1 分隔符与正文。 |
| S7 | 元数据 schema | `extract_mode`：`enum: ["text", "vision"]`，default `text`；非法 → 创建失败。 |
| S8 | 环境变量 | `PDF_VISION_ZOOM`、`PDF_VISION_MODEL`；模型解析 §2.3。 |
| S9 | 前端 | 下拉映射 `extract_mode`；提示 **耗时/费用、插图不保证单独成文件**。 |
| S10 | 进度 | `worker.update_task_progress`：vision 下 **全局页序** 或 **chunk 内页序** + 总页数。 |

---

## 4. Checkpoints（交付节点）

| ID | 名称 | 完成标准（Definition of Done） |
|----|------|--------------------------------|
| **CP0** | 基线冻结 | 默认 `text` 路径下，现有 `pdf_to_wiki` 行为与集成测试/手工跑通一致（回归）。 |
| **CP1** | 纯渲染可用 | 单测：fixture PDF → 单页 PNG 魔数正确；**文件缺失** → 任务级异常路径有测例。 |
| **CP2** | 单页 VL 闭环 | mock `LLMService`：拼接含 `<!-- pdf-vision:page 1 -->`；失败占位格式单测。 |
| **CP3** | 任务端到端 | 小 PDF + vision；**非法 extract_mode** 创建任务失败（单测）。 |
| **CP4** | 大 chunk / 降采样 | 验证顺序处理、内存不随页数线性暴涨全量持有 PNG；zoom 超限时降级或失败页占位。 |
| **CP5** | 前端与文档 | 表单 + 本 §5 清单勾选；**环境变量优先级** 有单测或文档固定表。 |

---

## 5. 测试与验证方法

### 5.1 单元测试

| 测试项 | 断言要点 |
|--------|----------|
| 页渲染 | PNG 魔数、单页 API；坏文件抛错 |
| 拼接 | marker 顺序 1..N；失败页仍有 marker + 失败段落 |
| `extract_mode` | 非法值 → 400 / 拒绝；不传 → text |
| 模型解析 | 设置 env 顺序，mock  getenv，断言选用模型链 |
| 日志 | mock logger：VL 调用路径 **不出现** 超长 base64（可选正则以长度截断断言） |

### 5.2 集成 / 手测

| 场景 | 期望 |
|------|------|
| text 回归 | 与改造前接近 |
| vision 扫描件 | 公式 `$`/`$$` 多于 text 路径 |
| 翻译 + vision | 结构不崩；超长有 warning |
| multi 模式 | 子页/目录与现有一致 |

### 5.3 回归与监控

- 默认不传 `extract_mode` ≡ **CP0**。
- 日志：`extract_mode`、总页数、VL 调用次数、总耗时（无 base64）。

---

## 6. 风险与对策（摘要）

| 风险 | 对策 |
|------|------|
| VL 费用与耗时长 | 默认 text；UI 说明；顺序调用；后续 `page_range`/`max_pages` |
| 单图超像素上限 | 降 zoom / 半页拆分 |
| 提示词漂移 | 与 web_reader **单源** |
| PyMuPDF 兼容 | 单页失败占位，继续；文件级错误整任务失败 |
| 并行误用 | 首版 **禁止**无界并行；文档写明 |

---

## 7. 文档与配置变更清单（发布时）

- [ ] `pyproject.toml` 依赖说明
- [ ] `docs/design/task-types-and-api.md` 更新 `extract_mode` 与 §2.2/2.3
- [ ] 前端任务类型说明（vision 局限：插图、耗时）

---

## 8. 可选后续（非本设计交付）

- PDF 内嵌位图提取 + MediaWiki 上传。
- text + vision **按页混用** 或自动择优。
- 与 `url_to_wiki` 共享全局限流。
