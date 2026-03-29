# PDF 转 Wiki：视觉页图抽取（多页渲染 + OCR/VL）设计

**时间**：2026-03-28；**修订**：2026-03-28（与实现对齐 + 文档闭合）  
**范围**：在现有 `pdf_to_wiki` 任务上增加可选抽取模式，与当前 **文本层提取**（pdfminer / pdfplumber）并存。  
**不纳入首版**：从 PDF 嵌入式位图中抽取并上传 MediaWiki 文件（可另立文档）。

### 文首说明：实现 / 测试 / 发布文档三分

| 维度 | 状态 |
|------|------|
| **运行时实现** | 已合入：`metadata.extract_mode` 为 `text`（默认）或 `vision`；`backend/utils/pdf_page_render.py`（API 名 **`render_pdf_page_to_png`**）、`pdf_vision_extract.py`、`pdf_vision_constants.py`；`task_handlers.process_pdf_to_wiki_task` vision 分支；`pymupdf` 在 `pyproject.toml` / `requirements.txt`；`make install-deps` 显式安装 `pymupdf>=1.24.0`。 |
| **自动化测试** | **部分**：`tests/test_pdf_vision_helpers.py`（常量 + 渲染 fixture）；`test_task_handlers.TestValidateTaskCreation`（`extract_mode` 校验）。**未覆盖**：mock VL 的拼接单测、模型链单测、日志断言、端到端集成（见 §5）。 |
| **配套文档 / 对外发布** | **§7 为「产品化勾选」**；与「代码已可在内网跑」不同步——未全部勾选不代表实现被回滚，只表示全局文档未统一刷新。 |

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
- 新增 **`extract_mode=vision`**：**按页将 PDF 栅格化为 PNG**（等价于「多页截图」），再调用**已有视觉模型**（与 `web_reader` 同源的 `OCR_PROMPT` + `LLMService` + 图像消息），输出 **Markdown**。
- 后续流水线尽量复用：**分块标题、可选翻译、`md_to_wiki`、写 Wiki、multi/single 模式**。

### 1.3 非目标（首版）

- 浏览器式「真截图」；首版采用 **库内渲染** 即可。
- 自动把 PDF 内嵌图片转成 `[[File:…]]` 并上传（工作量大，单独规划）。
- **混合模式**（同一 PDF 自动在 text / vision 间择优或逐页混用）：不承诺。
- **插图保留**：`vision` 仅保证页上内容以 **Markdown 文字/公式/表格** 尽量复原；位图插图一般不会成为 Wiki 独立图片文件。

### 1.4 已知质量局限（预期管理）

- **非确定性**：同 PDF 多次运行，VL 输出可能略有差异；自动化以 **无崩溃、基本结构** 为主，不做整文 golden diff。
- **版式**：多栏、脚注、复杂表格、手写批注等 **读序错误** 高发；不列为首版必修复项。

---

## 2. 方案概览与契约

```
PDF 文件
    │
    ├─ extract_mode=text（默认） → extract_text_from_pdf
    │
    └─ extract_mode=vision
            └─ 每页：render_pdf_page_to_png → LLM（OCR_PROMPT）→ 按 §2.1 拼接
            └─ 翻译 → md_to_wiki → MediaWiki（§2.6）
```

**分块**：与 `PDF_TO_WIKI_PAGES_PER_CHUNK` 一致；chunk 内顺序逐页 render → VL，不攒全 chunk PNG。

---

### 2.1 页分隔符与失败占位

实现与下表一致（`pdf_vision_constants.py`）：

| 语义 | 格式 | 说明 |
|------|------|------|
| 第 *k* 页起始 | `\n\n<!-- pdf-vision:page K -->\n\n` | 不用 `## 第 K 页`。 |
| 第 *k* 页失败 | `（第 K 页：识别失败）` 或同句内含 `str(e)` 截断至约 **200 字**（换行压平） | **未做**错误信息白名单 / 脱敏；内网场景直接依赖异常文案；若外网或共享日志需后续收紧。 |

HTML 注释在 Wiki 源文中的保留与否取决于站点配置；不作为强契约。

### 2.2 `extract_mode` 校验

- **缺省** → `text`。
- **非法值** → 创建任务失败（API / `validate_task_creation`）；handler 内二次校验。
- 入口清单：HTTP 创建、`validate_task_creation`；其它入队路径须同步。

### 2.3 视觉模型解析顺序（**与实现对齐**）

`resolve_pdf_vision_model(explicit: Optional[str])` 支持 **显式参数**，供将来从 metadata 接线。

**当前任务路径**：`extract_pdf_page_range_vision_markdown(..., model=None)` **始终未传**显式模型 → 实际顺序为：

1. ~~`metadata.pdf_vision_model`~~ **未接线**（schema 未暴露，handler 未传）
2. `PDF_VISION_MODEL`
3. `WEB_READER_OCR_MODEL`
4. `BROWSER_TOOL_VISION_MODEL`
5. 代码硬编码默认（与历史 web_reader 默认一致）

`PDF_VISION_ZOOM` 仅影响渲染。

### 2.4 日志（**设计为上限，实现为子集**）

- **禁止**：完整 base64 / data URL 写入日志。
- **当前实现**：以 `logger.warning` 记录 **页码 + 异常摘要** 为主；**未**打 sha256、PNG 字节长等字段——视为允许的 **实现子集**；若将来要对齐设计表，再增量补字段。

### 2.5 并发与重试（**实现对齐说明**）

- **并发**：顺序 **一页一请求**；禁止无界并行（当前实现满足）。
- **重试**：`ocr_single_page_png_to_markdown` 直接调用 `LLMService.chat`；**除 LLMService 内置重试外，无**针对 429/5xx 的单页级退避策略。§2.5 原先写的「最多 3 次指数退避」为 **建议 / 后续迭代**，**不作为首版实现契约**。

### 2.6 翻译阶段与 §2.1 标记

Vision 的 `raw_text` 含 `<!-- pdf-vision:page K -->` 与中文失败占位。翻译路径与 text 相同：**整段或分块**送入 `llm.chat(system_prompt=翻译提示, user_prompt=…)`。

**契约（收紧为「务实」）**：

- **硬保证**：翻译后 pipeline **不崩溃**、输出可写 Wiki。
- **软保证**：模型 **可能改写、删除或翻译** HTML 注释与失败占位句的字面；**不保证**页注释与占位 **逐字保留**。若需严格保留，应后续改为「跳过注释块的翻译」或后处理还原（非首版）。

### 2.7 页数与畸形 / 加密 PDF

- **总页数**：任务以 **pdfplumber** 与现有 chunk 划分一致；渲染用 **PyMuPDF**。极少数 PDF 两者页数不一致时，以 **pdfplumber 的 `total_pages` 与 chunk 范围** 为准；若 PyMuPDF 对某页渲染越界或失败 → **按 §2.1 单页失败占位** 继续，不强行整任务失败（除非文件级打不开，与 text 路径一致）。
- **加密 / 权限 PDF**：依赖库抛错形态因文件而异；**文件级无法打开** → 与 text 路径相同，任务失败；单页级问题 → 占位。

### 2.8 进度文案（**当前实现**）

`worker.update_task_progress` 仅更新到 **chunk 粒度**：「第 i+1/n 块（第 p_from–p_to 页）+ 阶段文案」。**chunk 内**多页 VL **无**逐页进度条。**全局页码进度** 若需要，应单独立项，不本文档「或」表述悬空。

---

## 3. 实现步骤（与仓库对照）

| 步骤 | 仓库事实 |
|------|-----------|
| S2 | `pdf_page_render.render_pdf_page_to_png(pdf_path, page_index_0based, zoom)`（设计稿曾写 `render_single_page_to_png`，**以仓库名为准**）。 |
| S5–S6 | `extract_pdf_page_range_vision_markdown` 内逐页 render → VL → 拼接。 |
| S10 | **按块**进度；见 §2.8。 |
| 其余 | 与设计一致处不重复。 |

---

## 4. Checkpoints（调整期望）

| ID | 说明 |
|----|------|
| CP0 | text 回归。 |
| CP1 | 渲染：见 `tests/test_pdf_vision_helpers.py`（**非**独立文件 `test_pdf_page_render.py`）。 |
| CP2 | VL 拼接 / mock：**待补**（见 §5）。 |
| CP3 | `extract_mode` 非法：已有 handler 校验单测。 |
| CP4–CP5 | 大 chunk / 模型链单测 / §7 文档：**部分待补**。 |

---

## 5. 测试与验证方法

### 5.1 已有

- `tests/test_pdf_vision_helpers.py`：页标记/失败文案；`render_pdf_page_to_png` + 最小 fitz PDF；缺失文件。
- `test_task_handlers`：`test_pdf_to_wiki_extract_mode_*`。

### 5.2 待补（与 §4 一致）

- mock `LLMService.chat`：多页拼接顺序、注释位置。
- mock `getenv`：模型链优先级。
- 集成：小 PDF + vision（可选，依赖真实 API Key）。

### 5.3 集成 / 手测（建议）

| 场景 | 期望 |
|------|------|
| text 回归 | 与改造前接近 |
| vision 扫描件 | 公式 `$`/`$$` 多于 text 路径 |
| 翻译 + vision | 结构不崩；页注释可能被模型改写（§2.6） |
| multi 模式 | 子页/目录与现有一致 |

### 5.4 回归

- 默认不传 `extract_mode` → 等同 text（CP0）。

---

## 6. 风险与对策（摘要）

| 风险 | 对策 |
|------|------|
| VL 费用与耗时长 | 默认 text；UI 说明；后续 `max_pages` 等 |
| 单图超像素上限 | 降 `PDF_VISION_ZOOM` |
| 翻译抹掉页注释 | §2.6 已降低为软保证；需严格保留则后续改实现 |
| 单页重试 | §2.5：后续可加，非首版 |

---

## 7. 文档与配置变更清单

> **说明**：下列勾选表示 **全局文档 / 发布流程** 是否已跟进；**与代码是否存在无关**。

- [x] `pyproject.toml` / `requirements.txt` / `Makefile install-deps`：`pymupdf>=1.24.0`
- [ ] `docs/design/task-types-and-api.md`：`extract_mode`、`pdf_vision_model`（若暴露）— **待补**
- [x] 前端：`TaskParamsForm` 在 `extract_mode=vision` 时的提示文案
- [x] 本文档：`pdf-to-wiki-vision-extract-design.md` 与实现对齐（本修订）

---

## 8. 可选后续

- PDF 内嵌位图提取 + MediaWiki 上传。
- metadata **`pdf_vision_model`** 接线；单页 VL **显式退避重试**。
- chunk 内 **逐页** `update_task_progress`。
- 翻译流水线 **保留** `<!-- pdf-vision:page K -->` 字面（转义或跳译）。
