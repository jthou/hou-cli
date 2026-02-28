# 内容格式转换层（Markdown / HTML / MediaWiki）

## 1. 职责划分

| 模块 | 转换方向 | 用途 |
|------|----------|------|
| **mdToHtml.js** | MD ↔ HTML | 公众号草稿：编辑/预览用 MD，提交用 HTML；`prepareMetadataForSubmit` 在提交 wechat_mp_draft 时对 content 做 MD→HTML。 |
| **wikiMdConvert.js** | Wiki ↔ MD | MediaWiki：从 Wiki 拉取内容后以 MD 编辑、或把 MD 内容写入 Wiki（如 mediawiki_write 任务）。 |

- **Markdown** 作为中间通用格式：可与 HTML（公众号）、与 Wikitext（MediaWiki）互转。
- 不混用：公众号走 mdToHtml，Wiki 走 wikiMdConvert，避免交叉依赖。

## 2. 已实现

- **mdToHtml.js**：`mdToHtml`, `htmlToMd`, `prepareWechatDraftMetadata`, `prepareMetadataForSubmit`, `WECHAT_MP_DRAFT_TASK_TYPE`
- **wikiMdConvert.js**：`wikiToMd(wiki)`、`mdToWiki(md)`，覆盖标题、粗/斜体、链接、列表、**公式**（`<math>` ↔ `$`/`$$`）等；复杂模板/表格可能需人工微调。

**LaTeX/数学公式**：统一约定与各端方案见 [latex-math-support.md](./latex-math-support.md)。MediaWiki 已装 MathJax，Wiki↔MD 已做公式占位与互转；公众号不支持公式，需「公式→图→上传正文图」或占位提示。

## 3. 集成状态

- **mediawiki_write 任务**：已支持。表单中勾选「正文为 Markdown（提交时转为 Wiki 语法）」后，提交前经 `prepareMetadataForSubmit` / `prepareMetadataForSubmitAsync` 对 `metadata.content` 调用 `mdToWiki` 再发送；未勾选则按原 wikitext 提交。
- **从 Wiki 拉取后编辑**：若提供「拉取页面 → 在应用内编辑」流程，可用 `wikiToMd(apiContent)` 得到 Markdown 再放入编辑器，保存时再 `mdToWiki` 写回。

## 4. 依赖

- mdToHtml：`marked`, `turndown`
- wikiMdConvert：无额外依赖（纯逻辑）
