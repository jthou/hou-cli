# 公众号草稿前后端逻辑梳理与问题修复

## 一、约定（正确逻辑）

- **后端**：任务类型 `wechat_mp_draft` 的 metadata 中 `content` 始终为 **HTML**；新增需 `thumb_media_id`，更新需 `media_id`。
- **前端**：用户**编辑**时统一用 **Markdown**（WechatDraftEditor）；提交前由 `prepareMetadataForSubmitAsync` 将 Markdown 转为 HTML（含公式→图、内联样式）。
- **media_id 来源**：从列表点进「编辑」时，media_id 必须来自**当前选中项**（列表/详情入口存下的 `media_id`），不能依赖接口返回的 draft 里是否带 media_id。

## 二、后端

| 位置 | 状态 | 说明 |
|------|------|------|
| `task_handlers.py` metadata_schema | ✅ | operation、title、content(HTML)、media_id 等定义清晰；media_id 描述已改为「从当前草稿列表选择」 |
| `process_wechat_mp_draft_task` | ✅ | add 校验 thumb_media_id，update 校验 media_id；content 按 HTML 提交微信 |
| `validate_task_creation` | ✅ | wechat_mp_draft 且 operation=update 时校验 media_id 必填，错误文案一致 |
| 草稿列表/详情 API | ✅ | 列表 no_content 可减体积；详情返回 draft，结构由微信 API 决定 |

## 三、前端问题与修复

### 1. TaskManagement：从草稿详情进「编辑」时 content 预填错误（已属凑合/乱写）

- **问题**：`onEdit` 里 `initialMetadata.content = news?.content ?? ''`，即把**接口返回的 HTML** 直接塞进表单。而 CreateTaskModal 里公众号草稿提交走 `prepareWechatDraftMetadataWithFormulaImages`，该函数**把 content 当 Markdown** 做公式提取和 `mdToHtmlForWechat`。结果是：预填的是 HTML，却被当 Markdown 再转一次 HTML，内容会错乱。
- **正确做法**：与 WechatDraftPage 一致，预填 **Markdown**。即 `content: htmlToMd(news?.content ?? '')`，并确保编辑时用 WechatDraftEditor（见下）。
- **修复**：TaskManagement 中引入 `htmlToMd`，在设置 `initialMetadata` 时对 `content` 使用 `htmlToMd(news?.content ?? '')`。

### 2. TaskParamsForm：更新草稿时 content 未用 WechatDraftEditor（凑合）

- **问题**：`customFieldRender` 里只有 `isWechatDraft`（即 operation 为 add 或空）时才用 WechatDraftEditor。operation=update 时 content 走 schema 默认渲染，变成**普通 textarea**，显示的是 HTML 或混乱内容，且提交时仍被当成 Markdown 转 HTML，逻辑不一致。
- **正确做法**：只要任务类型是 `wechat_mp_draft`，正文编辑统一用 **WechatDraftEditor**（Markdown），与 WechatDraftPage、ArticleWriting 一致；提交前统一由 `prepareMetadataForSubmitAsync` 转 HTML。
- **修复**：content 的 customFieldRender 条件改为 `taskType === 'wechat_mp_draft'`（不再用 `isWechatDraft`），这样 add/update 都用 WechatDraftEditor。

### 3. TaskParamsForm：media_id 下拉在「无预填」时未受控（小问题）

- **问题**：当 operation=update 且未预填 media_id 时，下拉框写死 `value=""`。若之后 metadata.media_id 被其他地方写入，下拉不会显示已选。应使用当前 `metadata.media_id` 作为 value。
- **修复**：下拉框 `value={mediaId}`（该分支下 mediaId 为空时即为 `""`，选中后会切到只读展示）。

### 4. WechatDraftPage（独立页）

- **状态**：openEditForm 已用 `selectedMediaId` 和 `htmlToMd(news?.content)`，编辑用 WechatDraftEditor，media_id 只读展示；逻辑正确，无需改。

### 5. ArticleWriting「同步到公众号草稿」

- **状态**：固定 operation=add，不展示 operation/media_id，正文为当前文章 Markdown，提交前转 HTML；逻辑正确。

## 四、数据流小结

```
列表/详情入口
  → 选中项 media_id 存入 draftDetail.media_id / selectedMediaId
  → 编辑时 initialMetadata.media_id = draftDetail.media_id | selectedMediaId
  → 详情 content 为 HTML → 预填时 content = htmlToMd(新闻HTML)

表单
  → 正文一律 WechatDraftEditor（Markdown）
  → media_id 有则只读展示，无则下拉选择

提交
  → prepareMetadataForSubmitAsync → prepareWechatDraftMetadataWithFormulaImages
  → content 从 Markdown 转 HTML → 后端收到 HTML，原样交微信
```

## 五、已做修改清单

1. **TaskManagement.jsx**：从草稿详情打开编辑时，`initialMetadata.content` 改为 `htmlToMd(news?.content ?? '')`，并 import `htmlToMd`。
2. **TaskParamsForm.jsx**：content 使用 WechatDraftEditor 的条件改为 `taskType === 'wechat_mp_draft'`；media_id 下拉 `value={mediaId}`。
