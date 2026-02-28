# LaTeX/数学公式在各格式下的支持方案

## 1. 现状与能力

| 平台 | 原生公式能力 | 说明 |
|------|--------------|------|
| **MediaWiki** | 有（已装 Math 扩展 + MathJax） | 使用 `<math>...</math>`，支持 TeX/LaTeX 子集；可选 `display="block"` 行间公式。 |
| **微信公众号** | 无 | 不支持 LaTeX，也不支持引入外部 JS/CSS（如 MathJax）。常见做法：**公式转成图片**（推荐 SVG）后插入正文。 |
| **本应用 Markdown** | 约定语法 | 统一用 `$...$` 行内、`$$...$$` 行间，作为编辑与转换的**中间格式**。 |

## 2. 统一约定：Markdown 为公式的“源格式”

- 在应用内编辑时，**一律用 Markdown 书写公式**：行内 `$E=mc^2$`，行间 `$$\int_0^1 x\,dx$$`。
- 导出到 MediaWiki 或公众号时，由各自转换层把 `$`/`$$` 转为目标格式（见下）。

## 3. 各端方案

### 3.1 MediaWiki（已有 MathJax）

- **Wiki → MD**：`<math>...</math>` → `$...$`，`<math display="block">...</math>` → `$$...$$`（在 wikiMdConvert 中实现）。
- **MD → Wiki**：`$...$` → `<math>...</math>`，`$$...$$` → `<math display="block">...</math>`（同上）。
- 页面由 Math 扩展 + MathJax 渲染，**无需额外服务**。

### 3.2 微信公众号（无原生公式）

- **思路**：公式不直接以 LaTeX 形式发到公众号，而是**先转成图片，再作为正文图片上传并插入**。
- **流程建议**：
  1. 用户在本应用用 Markdown 写正文（含 `$...$` / `$$...$$`）。
  2. 提交公众号草稿时，在 **MD→HTML** 的流水线中增加一步：
     - 识别所有公式片段；
     - 调用 **LaTeX→图片** 服务（见下）得到图片 URL 或二进制；
     - 通过「上传图文消息内的图片」拿到微信可用的 URL；
     - 在生成的 HTML 里用 `<img src="上述URL">` 替换对应公式。
  3. 正文中只保留 HTML + 图片，公众号可正常显示。

- **LaTeX→图片 实现方式**：已采用 **A. 公网 API**：后端 `GET /api/latex/render?formula=...` 代理 CodeCogs 返回 PNG（公众号仅支持 jpg/png）；前端提交公众号草稿时先拉取公式图，再上传至「上传图文消息内的图片」，在 HTML 中用 `<img src="微信返回的 URL">` 替换。可选后续：**B. 后端自建** KaTeX/MathJax-node 以可控、可缓存。

### 3.3 本应用内预览

- **已实现**：在公众号草稿预览（`WechatDraftPreview`）中引入 **KaTeX**，`renderMathInElement` 对 HTML 中的 `$...$`、`$$...$$` 做实时渲染，仅预览用，不改变存储格式。
- 与「发到公众号」解耦：预览用 KaTeX，发稿用「公式→PNG→上传→替换」流水线。

## 4. 实现状态与后续

| 项目 | 状态 | 说明 |
|------|------|------|
| wikiMdConvert 中 `<math>` ↔ `$`/`$$` | 建议实现 | 保证 Wiki 与 MD 间公式可往返。 |
| mdToHtml（公众号）中公式处理 | 已实现 | 提交时 `prepareMetadataForSubmitAsync` → 公式→PNG（CodeCogs）→ 上传微信 → HTML 中 `<img>` 替换。 |
| 后端 LaTeX 渲染接口 | 已实现 | `GET /api/latex/render?formula=...` 代理 CodeCogs 返回 PNG。 |
| 前端预览用 KaTeX | 已实现 | WechatDraftPreview 内渲染 `$`/`$$`，与发布流水线独立。 |

## 5. 小结

- **MediaWiki**：已支持公式，只需在 **wikiMdConvert** 里做好 `<math>` 与 `$`/`$$` 的互转。
- **微信公众号**：不支持 LaTeX，采用 **「公式 → 图片 → 上传正文图 → 在 HTML 中替换」** 的方案；可先占位或接公网 API，再考虑自建渲染服务。
- **统一约定**：应用内一律用 Markdown 的 `$...$` / `$$...$$` 作为公式的源格式，由各转换层负责映射到目标平台。
