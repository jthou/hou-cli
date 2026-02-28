# 公众号草稿预览组件 · 编辑模式设计

## 1. 三种编辑方式对比

| 方式 | 编辑对象 | 预览/输出 | 优点 | 缺点 |
|------|----------|----------|------|------|
| **源码编辑** | 原始 HTML | HTML | 与接口一致、无转换、实现简单 | 需懂 HTML，易误删标签 |
| **Markdown 编辑** | Markdown 文本 | 转为 HTML 显示/提交 | 专注内容、易写易读、只关心文字和图片 | 需 MD→HTML 转换；已有草稿为 HTML 时需 HTML→MD（有损） |
| **WYSIWYG** | 富文本 | HTML | 直观 | 实现复杂、易产生冗余标签 |

## 2. 内容优先方案：编辑 Markdown，预览与发文用 HTML（推荐）

**思路**：用户只关心「文字 + 图片」，编辑时写 **Markdown**；预览和提交到公众号时统一用 **HTML**。

- **编辑**：在编辑器里写 Markdown（标题、段落、加粗、列表、链接、图片等）。
- **预览**：把当前 Markdown 转成 HTML，用现有 `WechatDraftPreview` 渲染，风格与公众号一致（明亮、GitHub 风）。
- **写入公众号**：提交时把 Markdown 转成 HTML（同一套转换规则），作为草稿的 `content` 调接口。

**数据流**：

```
[ 编辑 ]  Markdown 文本  →  MD→HTML  →  [ 预览 ] HTML 渲染（只显示文字和图片）
                ↓
           提交/保存时
                ↓
            MD→HTML  →  公众号草稿 API（content = HTML）
```

**与现有草稿的关系**：

- **新建草稿**：编辑区初始为空或模板，用户写 Markdown → 预览即 HTML → 保存时 MD→HTML 写入。
- **从公众号拉取的草稿**：接口给的是 HTML。可选做法：
  - **A**：只读预览用 HTML；要编辑时，用 **HTML→Markdown** 转成 Markdown 再在编辑器中改，保存时再 **Markdown→HTML** 写回（需引入 HTML→MD，转换可能不完美）。
  - **B**：已有草稿仅支持「只读预览 + 新建更新任务时填 HTML」；只有「新建」或从本端创建的草稿才用 Markdown 编辑。先实现 B 更简单，A 可后续加。

**实现要点**：

- 前端：Markdown 编辑器（如 textarea + 简单工具栏，或集成 marked + 高亮）；预览区复用 `WechatDraftPreview`，传入 `mdToHtml(markdown)` 的结果。
- MD→HTML：用同一套规则（如 marked + 自定义 renderer），输出符合公众号的 HTML（只保留支持的标签、行内样式与图片 URL 规则），可复用现有 GitHub 风格类名或行内样式。

## 3. 备选方案：预览 + 源码（HTML）编辑双模式

- **默认**：仅预览（只读），按 HTML 渲染，明亮风格。
- **编辑**：提供「编辑」入口后进入**源码模式**，在文本框内编辑**原始 HTML**；保存时直接拿字符串提交，不经过富文本转换。
- **理由**：与接口一致、实现简单；适合需要精细控制 HTML 的场景。

## 4. 组件设计（Markdown 编辑 + HTML 预览）

**编辑区**：Markdown 文本（textarea 或简单编辑器），用户只写文字和图片语法。

**预览区**：复用 `WechatDraftPreview`，传入 `mdToHtml(markdown)` 得到的 HTML，只显示「文字 + 图片」的渲染结果，不暴露 HTML 结构。

**数据流**：

| 场景     | 编辑区内容 | 预览区       | 提交到公众号   |
|----------|------------|--------------|----------------|
| 新建     | Markdown   | MD→HTML 渲染 | MD→HTML 作为 content |
| 从接口拉取的草稿 | 可选：HTML→MD 后编辑，或只读 | HTML 直接渲染 | 若编辑过 MD，则 MD→HTML |

**组件拆分建议**：

- **WechatDraftPreview**：保持现状，只负责「接收 HTML，按明亮风格渲染」，不关心来源是 MD 还是 HTML。
- **Markdown 编辑器 + 预览联动**：一个新组件（如 `WechatDraftEditor`），内部包含：左侧或上方为 Markdown 输入，右侧或下方为 `WechatDraftPreview html={mdToHtml(markdown)}`；对外暴露 `value`（Markdown）、`onChange(md)`，提交时由父组件或本组件内将 `value` 转为 HTML 再调接口。

**MD→HTML**：使用同一套规则（如 marked + 自定义 renderer），输出带 GitHub 风格行内样式的 HTML，并遵守公众号限制（图片 URL 需为上传接口返回的地址）。

## 5. 与草稿页的配合

- 草稿详情**只读预览**：`<WechatDraftPreview html={detailContent} />`（内容来自接口的 HTML）。
- **新建/编辑正文（Markdown 优先）**：使用 `WechatDraftEditor`（Markdown 编辑 + 同屏 HTML 预览），提交时 MD→HTML 写入任务 metadata 或直接调草稿接口。

## 6. 小结

- **内容优先**：编辑用 **Markdown**，预览与发文用 **HTML**；预览只展示文字和图片，不展示 HTML 源码。
- **实现**：MD→HTML 统一转换；预览沿用 `WechatDraftPreview`；新组件负责 Markdown 编辑与预览联动，提交前将 Markdown 转为 HTML。

## 7. 已做修改（实现清单）

- **依赖**：`frontend/react-app/package.json` 增加 `marked`。
- **工具**：`frontend/react-app/src/utils/mdToHtml.js`，`marked` 将 Markdown 转为 HTML。
- **组件**：`frontend/react-app/src/components/WechatDraftEditor.jsx`，左侧 Markdown 输入、右侧 `WechatDraftPreview` 实时预览。
- **表单**：`TaskMetadataFormFields` 支持 `customFieldRender`，当返回非 null 时替代该字段默认渲染。
- **草稿页**：`WechatDraftPage` 新建草稿时，正文用 `WechatDraftEditor`（Markdown），提交前 `mdToHtml(formMetadata.content)` 写入任务 metadata。
- **任务管理**：`CreateTaskModal` 中任务类型为 `wechat_mp_draft` 且 operation 为 add 时，正文用 `WechatDraftEditor`，提交前对 `metadata.content` 做 `mdToHtml` 再发送。
- **编辑已有草稿**：仍为 HTML（从接口拉取），表单中 content 为默认 textarea，不做 HTML→Markdown 转换。
