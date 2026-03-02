# 写文章：最终文章输出 UI 逻辑

## 一、目标

写文章工具产出的**最终文章**有两个出处：

1. **输出到 MediaWiki**：将当前文章（Markdown）转为 Wikitext 后发布/更新指定页面。
2. **输出到微信公众号草稿箱**：将当前文章作为正文，创建一篇公众号草稿（通过任务队列，需填标题、封面等）。

二者均在「文章预览」区提供入口，用户完成对话与编辑后，按需选择输出目标。

---

## 二、现有能力

| 能力 | 说明 |
|------|------|
| **MediaWiki** | `POST /api/mediawiki/pages/{title}`，body: `{ content: string (wikitext), summary?: string }`。页面不存在时会创建。 |
| **公众号草稿** | 创建任务 `task_type: wechat_mp_draft`，`metadata`: `{ operation: 'add', title, content (HTML), author?, digest?, thumb_media_id }`。正文需为 HTML，由前端用 `prepareMetadataForSubmitAsync` 将 Markdown 转为带内联样式的 HTML（含公式转图等）。封面 `thumb_media_id` 必填，可通过 `/api/wechat-mp/upload-cover` 上传获取。 |

---

## 三、UI 逻辑

### 3.1 入口位置

- 在**文章预览**区顶部操作栏（与「编辑」「复制」「加入输入框」「局部插入」「历史版本」同一行）增加 **「输出」** 下拉或两个按钮：
  - **发布到 MediaWiki**
  - **同步到公众号草稿**
- 仅当**有文章内容**（`previewContent` 非空）时展示；编辑模式下也可展示（以当前 `previewContent` 为准，即编辑前内容，或约定为「当前文章」快照）。

### 3.2 发布到 MediaWiki

- 点击后打开弹窗：
  - **页面标题**（必填）：对应 MediaWiki 页面名，直接用于 `POST /api/mediawiki/pages/{title}`。
  - **编辑摘要**（选填）：对应 `summary`。
- 提交时：
  - 正文：将 `previewContent`（Markdown）用 `mdToWiki` 转为 Wikitext，作为 `content`。
  - 请求：`POST /api/mediawiki/pages/{encodeURIComponent(title)}`，body `{ content, summary }`。
- 成功：关闭弹窗并 toaster 提示；失败：toaster 报错。

### 3.3 同步到公众号草稿

- 点击后打开弹窗，表单字段：
  - **标题**（必填）：公众号图文标题。
  - **正文**：只读展示或简短说明「将使用当前文章内容」，不在此处再编辑（如需改可先在预览区编辑后再打开本弹窗）。
  - **作者**（选填）
  - **摘要**（选填）：图文摘要。
  - **封面**（必填）：上传图片或填写已有 `thumb_media_id`，与公众号草稿页逻辑一致。
- 提交时：
  - 构建 `metadata`: `{ operation: 'add', title, content: previewContent (Markdown), author, digest, thumb_media_id }`。
  - 调用 `prepareMetadataForSubmitAsync('wechat_mp_draft', metadata)` 得到提交用 payload（正文 MD→HTML、公式转图等）。
  - `POST /api/task-queue/tasks`，body: `{ task_type: 'wechat_mp_draft', priority: 2, max_retries: 3, metadata }`。
- 成功：关闭弹窗并 toaster 提示「任务已创建」；失败：toaster 报错。

### 3.4 与现有页面关系

- **MediaWiki**：不依赖任务队列，直接调 MediaWiki 接口；若项目内有「MediaWiki 写入」任务，写文章输出与之并列，此处为「当前文章直达发布」。
- **公众号草稿**：与「公众号草稿」页一致，均为创建 `wechat_mp_draft` 任务；写文章页相当于「从当前文章预填正文」的快捷入口，封面等仍在该弹窗内完成。

---

## 四、实施要点

- 正文格式：MediaWiki 用 `mdToWiki(previewContent)`；公众号用 `previewContent` 作 Markdown 交给 `prepareMetadataForSubmitAsync` 转 HTML。
- 封面上传：复用 `/api/wechat-mp/upload-cover` 与现有公众号草稿页的上传/填写 media_id 方式。
- 错误处理：网络或接口错误时 toaster 提示，不关闭弹窗以便用户重试或修改后再提交。
