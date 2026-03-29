# PPT 助手设计

**时间**：2026-03-28；**修订**：2026-03-28（初稿）  
**范围**：在 Hou CLI（前后端 + 任务队列 + Agent 工具 + 既有 LLM / 可选视觉管线）上规划 **PowerPoint（.pptx）相关助手能力**；与现有 `pdf_to_wiki`、PDF vision 抽取、工作助手等 **概念对齐**，**不要求**与 Microsoft Office 二进制 `.ppt` 格式兼容。  
**仓库现状**：**尚无** `pptx` 读写或 PPT 专用任务类型；本文档为 **设计**；实现后应回本页更新「实现 / 测试 / 文档」三分表。

### 文首说明：实现 / 测试 / 发布文档三分

| 维度 | 状态 |
|------|------|
| **运行时实现** | **未开工**。预期涉及：`python-pptx`（或等价库）读写 OOXML；可选幻灯片光栅化链路；`task_handlers` 新 handler 或 Agent `builtin` 工具；路径校验复用 `pdf_to_wiki` 同类规则（用户主目录内等）。 |
| **自动化测试** | **未开工**。建议：fixture `.pptx`（最少页、含标题/正文/备注）；结构解析单测；mock LLM 的「大纲生成 → 写回」单测；**不**对 VL 做 golden diff。 |
| **配套文档 / 对外发布** | 本文档；实现后勾选 §7，并视需要更新 `task-types-and-api.md`、前端任务表单。 |

---

## 0. 适用范围（部署假设）

- 默认 **内网 / 自用工具**：不在本文展开对外产品所需的完整合规（许可证、数据出境、DPA 等）。
- **技术依赖**：`python-pptx` 采用 **MIT 许可**，与 PyMuPDF（AGPL）等 **分开评估**；若引入 **LibreOffice / unoconv** 等做导出 PNG，需额外记录部署与许可。
- **权限模型**：与现有文件类任务一致——输入/输出路径约束、无新租户级隔离假设；若将来外网部署，需收紧错误信息与日志脱敏（比照 `pdf-to-wiki-vision-extract-design.md` §2.1、§2.4 思路）。

---

## 1. 背景与目标

### 1.1 现状

- 文档入库已有 **PDF → 文本 / 视觉** 路径（`pdf_to_wiki`、`extract_mode=text|vision`），可整页渲染 + VL 输出 Markdown。
- **没有** 针对 **Office Open XML 演示文稿（.pptx）** 的任务类型或 Agent 工具；用户若需「幻灯片结构化编辑 + LLM」需在系统外完成。

### 1.2 目标（产品）

按优先级可分三层，**可分期交付**：

1. **编剧层（P0）**：对话生成 **大纲、逐页要点、讲者备注、润色**；输出 **Markdown 或 JSON slide spec**，用户可复制或再由工具写入 `.pptx`。
2. **结构化层（P1）**：在受控路径下 **读取 / 修改** `.pptx`（枚举幻灯片、读文本框、按模板替换、写备注）；支持 **Agent function calling** 或 **异步任务**（大文件 / 批量）。
3. **视觉理解层（P2，可选）**：对版式复杂、图表为主的页，**导出为位图** 后走既有 **VL/OCR** 能力（与 PDF vision、`web_reader` 同源 prompt 体系），与 **python-pptx 读出的文本** 合并或分页标注。

### 1.3 非目标（首版）

- 支持旧式 **`.ppt`（二进制）**；**`.pptx` only**。
- 完美还原 **动画、切换效果、SMIL、自定义母版细微差异**；首版以 **占位符与文本形变** 为主。
- **WYSIWYG** 可视化编辑器（网页上拖拽排版）；归产品另立项。
- 将 PPT 内 **所有图片** 自动上传 MediaWiki 并建立 `[[File:…]]`（工作量大，可与 PDF 插图策略单独立项）。

### 1.4 已知局限（预期管理）

- **非确定性**：同一份 spec 多次生成，措辞可能不同；测试以 **结构合法、不崩溃** 为主。
- **版式**：多栏、文本框重叠、分组对象过深时，`python-pptx` 遍历顺序可能与屏幕读序不一致；vision 路径可补语义但仍有 **读序 / 漏读** 风险。

---

## 2. 能力分层与数据流

### 2.1 总体架构（与现有系统对齐）

```
用户意图
    │
    ├─ 纯对话 / 无文件 ─────────────────→ Agent（LLM）→ Markdown 或 JSON spec
    │
    ├─ 需读本地 .pptx ──────────────────→ 路径校验 → python-pptx 解析
    │                                         ├─ extract_mode=structure（默认）→ 文本/结构摘要 → LLM
    │                                         └─ extract_mode=vision（可选）→ 幻灯片 PNG → VL → 与 structure 合并
    │
    └─ 需写回 .pptx / 导出 ─────────────→ LLM 或规则 → python-pptx 写文件 → 输出路径（任务 result 或工具返回）
```

**与 PDF 管道的类比**：

| PDF | PPT（本设计） |
|-----|----------------|
| `extract_mode=text` | `structure`：OOXML 文本层 / 形状树 |
| `extract_mode=vision` | 按页/按幻灯片光栅化 + VL |
| `pdf_to_wiki` 任务 | 可选 `pptx_to_wiki` / `pptx_extract`；或仅 Agent 工具不落队列 |

### 2.2 JSON slide spec（建议契约，供 P0/P1 交界）

首版建议 **稳定、易解析** 的轻量 schema（示例，实现时可增 `version` 字段）：

```json
{
  "title": "演示标题",
  "slides": [
    {
      "index": 1,
      "title": "章节标题",
      "bullets": ["要点一", "要点二"],
      "speaker_notes": "口播提示，可选"
    }
  ]
}
```

- **P0**：仅 LLM 输出该结构（或 Markdown 等价物），**不写文件**。
- **P1**：工具读入该结构，映射到 **模板 `.pptx`** 的布局（见 §2.3）。

### 2.3 模板写回策略（P1）

- **推荐**：仓库或用户目录下 **固定母版 .pptx**，内含命名占位符或固定 slide layout。
- **流程**：`slide spec` → 按 index `add_slide` / 克隆版式 → 写入 `title`、`bullets`、`speaker_notes`。
- **禁止**：让 LLM 直接操纵 ZIP 内 XML 原始字节；统一经 `python-pptx` API，降低损坏文件风险。

### 2.4 幻灯片光栅化（P2）

可选实现路径（按部署复杂度递增，**择一或组合**）：

1. **pptx → pdf → PyMuPDF 按页渲染**：复用现有 PDF 渲染基础设施（注意 **许可** 与 **页序** 是否与幻灯片 index 一一对应）。
2. **LibreOffice `--headless`**：导出 PDF 或 PNG；依赖机器安装，CI 需 skip 或可容器化。
3. **仅 Windows + COM**：不列为默认方案。

**分页标记**（若输出并入 Wiki 或长 Markdown）：建议与 PDF vision 风格一致，采用 HTML 注释作弱契约，例如 `<!-- pptx-vision:slide K -->`，失败占位句与 PDF §2.1 同类（截断异常、内网日志假设）。

### 2.5 模型与配置

- **编剧 / 结构化摘要**：沿用工作助手或通用 Chat 的模型解析顺序；可 env 覆盖。
- **vision**：优先复用 `WEB_READER_OCR_MODEL` / `BROWSER_TOOL_VISION_MODEL` 等既有链；可增设 `PPTX_VISION_MODEL`（实现时接线 metadata 或 env）。

---

## 3. 任务队列 vs Agent 工具

### 3.1 何时用异步任务

- 幻灯片数量大、需 **进度条**、**可重试**、或 **pptx_to_wiki** 长流水线（解析 → 翻译 → 写 Wiki）。
- 与 `pdf_to_wiki` 相同：`TASK_TYPES` 注册、`process_*_task`、超时与并发限制（建议默认同量级或单独 `TASK_TIMEOUT_SECONDS["pptx_*"]`）。

### 3.2 何时用 Agent 工具

- 用户在对话中 **少量修改**（例如「把第 3 页标题改为…」「导出备注为 txt」）。
- 工具示例（命名示意）：`pptx_list_slides`、`pptx_read_slide_text`、`pptx_set_slide_text`、`pptx_apply_slide_spec`（内部读模板）。

**原则**：同一套 `python-pptx` 封装模块被 **任务 handler 与工具** 共用，避免两套逻辑漂移。

---

## 4. 安全与校验

- **路径**：与 `_validate_input_path_in_home` / `_validate_output_path_in_home` 一致；**禁止** 任意服务端路径。
- **文件大小与页数**：metadata 可选 `max_slides`、`max_file_mb`；超限 **明确错误码**，避免 OOM。
- **日志**：不记录 slide 内用户敏感长文本全文于 INFO（可调 DEBUG 或截断）；vision 路径 **禁止** 完整 base64 入日志（同 PDF vision 设计）。

---

## 5. 测试与验证

### 5.1 单元测试

- 最小 `.pptx`：1～3 页，标题 + bullet + notes；**读**断言与 **写后再读**  round-trip。
- 非法路径、损坏文件、空 deck：**可预期** 失败信息与结构。

### 5.2 集成 / 手测

| 场景 | 期望 |
|------|------|
| P0：仅生成 spec | JSON/Markdown 可被人工粘贴或下一步工具消费 |
| P1：模板写回 | 用 PowerPoint / LibreOffice 打开无报错，文本与备注位置正确 |
| P2：vision | 图表页语义可被 VL 摘要；与 structure 文本矛盾时以产品策略为准（例如 vision 块单独标注） |

### 5.3 回归

- 不启用 PPT 功能时，**零** 对现有 `pdf_to_wiki` 与 Agent 的破坏。

---

## 6. 风险与对策（摘要）

| 风险 | 对策 |
|------|------|
| python-pptx 无法表达复杂母版 | 收缩为「有限模板 + 占位符」；复杂版式人工定版 |
| 光栅化链路过重 | P2 默认关；按 env 启用；限制 `max_slides` |
| LLM 输出非法 JSON | schema 校验 + 一次「只输出 JSON」修复轮或降级为纯 Markdown |
| 许可（LibreOffice / PyMuPDF） | 文档与部署清单单独标注；闭源产品化时再审 |

---

## 7. 文档与配置变更清单（实现后勾选）

- [ ] `pyproject.toml` / `requirements.txt`：`python-pptx` 版本下界
- [ ] `docs/design/task-types-and-api.md`：若新增 `pptx_*` 任务类型
- [ ] 前端：任务创建表单、参数说明（`extract_mode`、`max_slides` 等）
- [ ] `backend/infrastructure/execution/task_handlers.py`（或拆分模块）与 `task_worker` 注册
- [ ] Agent：`builtin` 工具注册与权限说明
- [ ] 本文档：将 § 文首三分表更新为「已合入」事实

---

## 8. 分期交付建议

| 阶段 | 内容 | 验收 |
|------|------|------|
| **MVP** | P0 编剧 + Markdown/JSON spec | 对话可用、可导出文本 |
| **M1** | P1 读/写 + 模板 + Agent 工具 | round-trip 单测 + 手测打开 |
| **M2** | 可选 `pptx_to_wiki` 或与工作流联动 | 进度与错误结构对齐现有任务 |
| **M3** | P2 vision | 可选依赖安装说明；分页标记与 PDF vision 行为一致 |

---

## 9. 可选后续

- 从 **PDF / Word** 一键生成 slide spec（复用现有文档抽取）。
- 与工作助手 **MediaWiki** 双向同步（讲义页 ↔ Wiki 子页）。
- 批量生成缩略图预览 API（仅内网）。
