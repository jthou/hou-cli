# 微信公众号工具接入任务管理体系 - 设计文档

## 1. 目标

将微信公众号（个人号可用）能力接入现有任务管理体系，使「写公众号草稿」可通过任务队列创建、执行、查看结果，并支持定时任务（如定时写入草稿）。不实现发布、统计等需认证的接口。

## 2. 任务类型设计

### 2.1 类型定义

- **task_type**：`wechat_mp_draft`
- **名称**：公众号草稿
- **描述**：向微信公众号草稿箱新增或更新一篇图文草稿（个人号可用；发布需在手机端「公众号助手」操作）。

### 2.2 子操作

用 `metadata.operation` 区分：

| operation | 说明 | 必填 metadata |
|-----------|------|----------------|
| `add`     | 新增草稿 | `title`, `content`（正文 HTML） |
| `update`  | 更新已有草稿 | `media_id`，以及要更新的字段（如 `title`、`content`） |

可选字段（与微信 API 对齐）：`author`、`digest`、封面（先通过「上传图文消息图片」得到 URL 或 thumb_media_id，再填入草稿）。为简化首版，可只做 `title` + `content`，其余可选。

### 2.3 metadata_schema（建议）

```json
{
  "operation": {
    "type": "string",
    "required": true,
    "description": "操作类型",
    "enum": [
      {"value": "add", "label": "新增草稿"},
      {"value": "update", "label": "更新草稿"}
    ],
    "default": "add"
  },
  "title": {
    "type": "string",
    "required": true,
    "description": "标题",
    "placeholder": "文章标题"
  },
  "content": {
    "type": "string",
    "required": true,
    "description": "正文（HTML）",
    "placeholder": "<p>正文内容...</p>"
  },
  "author": {
    "type": "string",
    "required": false,
    "description": "作者"
  },
  "digest": {
    "type": "string",
    "required": false,
    "description": "摘要"
  },
  "media_id": {
    "type": "string",
    "required": false,
    "description": "草稿 media_id（operation=update 时必填）",
    "placeholder": "从草稿列表或详情获取"
  }
}
```

- 校验规则：`operation === "update"` 时，`media_id` 必填；`operation === "add"` 时不必填。可在 `validate_task_creation` 中为 `wechat_mp_draft` 增加该逻辑。

### 2.4 Handler 返回 result 形状（与现有约定一致）

成功时：

```json
{
  "status": "success",
  "summary": "已新增草稿：xxx",
  "data": {
    "media_id": "xxx",
    "operation": "add",
    "message": "草稿已保存，可在公众号助手发布"
  }
}
```

失败时：由 Worker 写入 `tasks.error`；若 Handler 返回统一错误结构（如 `_err(...)`），可保留 `status: "error"` 写入 result，由前端 TaskResultDisplay 统一展示。

## 3. 后端改动清单

| 项目 | 文件 | 说明 |
|------|------|------|
| 任务类型定义 | `backend/infrastructure/execution/task_handlers.py` | 在 `TASK_TYPES` 中新增 `wechat_mp_draft`（name、description、metadata_schema） |
| 处理器实现 | 同上 | 新增 `process_wechat_mp_draft_task(task_info)`，内部调用 `WeChatMPClient`（需在 client 中实现 `add_draft` / `update_draft`） |
| 注册处理器 | 同上 | 在 `register_default_handlers()` 中 `worker.register_handler("wechat_mp_draft", process_wechat_mp_draft_task)` |
| 创建校验 | 同上 | 在 `validate_task_creation` 中为 `wechat_mp_draft` 增加：operation=update 时 media_id 必填 |
| 任务名生成 | `backend/api/task_queue_routes.py` | 在 `_generate_task_name` 中为 `wechat_mp_draft` 生成名称（如「公众号草稿 《标题》 12-01 10:00」） |
| 定时任务名称 | 同上 | 定时任务创建/展示用的 type_names 中增加 `wechat_mp_draft` →「公众号草稿」 |
| 超时（可选） | `backend/infrastructure/execution/task_worker.py` | `TASK_TIMEOUT_SECONDS["wechat_mp_draft"] = 60`（1 分钟，写草稿通常很快） |

## 4. Service 层前置依赖

当前 `wechat_mp_service/client.py` 仅有「获取 token、草稿列表、草稿详情」。接入任务前需在 client 中实现：

- **add_draft**：入参 title、content、可选 author/digest/封面；调用微信「新增草稿」接口，返回 media_id。
- **update_draft**：入参 media_id + 要更新的字段；调用微信「更新草稿」接口。

上传封面图若首版不做「本地上传文件」，可仅支持在 content 中写死图片 URL 或后续再加「上传图文消息图片」任务/参数。

## 5. 前端改动清单（任务结果 + 创建/定时表单）

| 项目 | 文件 | 说明 |
|------|------|------|
| 结果展示 | `frontend/react-app/src/components/TaskResultDisplay.jsx` | 增加 `taskType === 'wechat_mp_draft'` 分支：展示 `result.summary`、`result.data.media_id`、提示「可在公众号助手发布」 |
| 创建任务 | 无需改 | 创建任务弹窗通过 `GET /api/task-queue/task-types` 拉取 schema，动态渲染表单，已有逻辑可复用于 `wechat_mp_draft` |
| 定时任务 | 无需改 | 定时任务类型列表来自同一接口，加入 `wechat_mp_draft` 后即可在「创建定时任务」中选择 |

可选：若希望列表/详情中对「公众号草稿」有图标或标签，可在任务卡片/详情中根据 `task_type === 'wechat_mp_draft'` 做样式区分。

---

## 5.1 前端：显示与编辑草稿（扩展）

若要支持在 Web 上**查看公众号草稿列表、查看单篇草稿详情、并基于某篇草稿发起「更新」任务**（即“编辑草稿”），需要以下能力。

### 5.1.1 显示草稿

- **列表**：展示当前公众号草稿箱中的草稿（标题、更新时间、media_id 等）。
- **详情**：点击某条草稿后，展示该篇的标题、作者、摘要、正文（HTML 只读或可折叠），以及 media_id（便于复制用于「更新草稿」任务）。

实现前提：后端提供**只读**接口，由前端调用并渲染。

| 能力 | 说明 |
|------|------|
| 草稿列表 | 后端 `GET /api/wechat-mp/drafts?offset=0&count=20`，内部调 `WeChatMPClient.get_draft_list()`，返回 `total_count`、`item`（含 media_id、update_time、可选 content 摘要）。 |
| 草稿详情 | 后端 `GET /api/wechat-mp/drafts/{media_id}`，内部调 `WeChatMPClient.get_draft(media_id)`，返回单篇完整内容（如 content.news_item）。 |

前端可增加：

- **入口**：在任务管理页增加 Tab「公众号草稿」，或侧栏/顶部「草稿箱」入口。
- **列表页/弹窗**：请求 `GET /api/wechat-mp/drafts`，表格或卡片展示：标题（可从 item 中取第一条 news_item.title）、更新时间、media_id（短显）；操作：「查看」「编辑」。
- **详情弹窗/抽屉**：点击「查看」后请求 `GET /api/wechat-mp/drafts/{media_id}`，展示 title、author、digest、content（HTML 用 `dangerouslySetInnerHTML` 或 iframe 只读展示，注意 XSS 过滤）；底部可展示 media_id 并提供「编辑」按钮。

### 5.1.2 编辑草稿

「编辑」= 基于已有草稿内容，修改后**提交为一条「更新草稿」任务**（不直接调微信接口，走任务队列，与现有「写草稿」设计一致）。

- **流程**：在草稿详情中点击「编辑」→ 打开「创建任务」弹窗，并预填：
  - 任务类型：`wechat_mp_draft`
  - `operation`：`update`
  - `media_id`：当前草稿的 media_id
  - `title`、`content`（及可选 author、digest）：从草稿详情预填，用户可修改
- 用户点击「创建任务」后，提交 `POST /api/task-queue/tasks`，body 为 `task_type: "wechat_mp_draft"`, `metadata: { operation, media_id, title, content, ... }`。Worker 执行后即完成一次「更新草稿」。

因此：

- **显示草稿**：依赖后端 5.1.1 的两个只读 API + 前端草稿列表/详情 UI。
- **编辑草稿**：不新增后端写接口；前端在草稿详情中提供「编辑」→ 预填创建任务表单并提交即可。

### 5.1.3 后端新增（仅只读）

| 项目 | 文件 | 说明 |
|------|------|------|
| 草稿列表 | 新建 `backend/api/wechat_mp_routes.py` 或并入现有 router | `GET /api/wechat-mp/drafts?offset=0&count=20&no_content=1`，调用 `WeChatMPClient.get_draft_list()`，返回 JSON。 |
| 草稿详情 | 同上 | `GET /api/wechat-mp/drafts/{media_id}`，调用 `WeChatMPClient.get_draft(media_id)`，返回 JSON（注意 media_id 可能含特殊字符，可用 path 或 query 传递）。 |
| 路由注册 | `backend/main.py` 或路由聚合处 | 挂载上述路由；需校验 .env 已配置微信 appid/secret，否则可返回 503 或空列表。 |

### 5.1.4 前端新增（显示 + 编辑）

| 项目 | 文件 | 说明 |
|------|------|------|
| 草稿列表 | 新页面或 `TaskManagement.jsx` 内 Tab / 子视图 | 请求 `GET /api/wechat-mp/drafts`，展示表格/卡片；支持分页（offset/count）。 |
| 草稿详情 | 弹窗或抽屉组件 | 请求 `GET /api/wechat-mp/drafts/{media_id}`，展示 title、author、digest、content（只读）；展示 media_id；按钮「编辑」。 |
| 编辑入口 | 同上 | 「编辑」→ 打开已有「创建任务」弹窗（CreateTaskModal 或等价组件），预填 task_type=`wechat_mp_draft`、metadata=`{ operation: "update", media_id, title, content, author, digest }`；用户可改后提交。 |
| 路由/菜单 | 前端路由或任务管理页 Tab | 增加「公众号草稿」或「草稿箱」入口，指向草稿列表视图。 |

### 5.1.5 小结

| 能力 | 是否支持 | 实现方式 |
|------|----------|----------|
| 显示草稿列表 | ✅ 可支持 | 后端 GET /api/wechat-mp/drafts + 前端草稿列表页/弹窗 |
| 显示草稿详情 | ✅ 可支持 | 后端 GET /api/wechat-mp/drafts/:id + 前端详情弹窗（只读 HTML） |
| 编辑草稿 | ✅ 可支持 | 前端「编辑」= 预填「创建任务」表单（operation=update、media_id、title、content）并提交，走现有 `wechat_mp_draft` 任务 |

首版若不做「草稿箱」专属入口，仍可仅靠「创建任务」选「公众号草稿」、operation=更新、手动填 media_id 和标题/正文完成编辑；增加上述 API 与前端列表/详情/预填编辑后，体验更完整。

**安全**：草稿正文为 HTML，详情页展示时需做 XSS 防护（如仅允许安全标签的白名单、或使用 iframe sandbox）。

## 6. 定时任务支持

- 与现有定时任务一致：创建定时任务时 `task_type: "wechat_mp_draft"`，`metadata` 与普通任务相同。
- 到点后由 heartbeat 触发生成一条普通任务（task_type + metadata），Worker 执行 `process_wechat_mp_draft_task`。
- 无需额外配置，只要后端注册了类型与处理器即可。

## 7. 管道编排（可选）

- 当前不要求 `wechat_mp_draft` 作为下游接收上游输出（如「上游生成正文 → 本任务写草稿」）。若后续要做，可在 `TASK_TYPES["wechat_mp_draft"].metadata_schema` 中为 `content` 增加 `pipeline_accept`，并在 `get_linkable_upstream_types` 中声明可链接的上游类型；首版可省略。

## 8. 测试约定

- **task_type 白名单**：`test_task_queue_routes.py` 中创建任务使用 `wechat_mp_draft` 且合法 metadata 应成功；无效 `task_type` 仍 400。
- **metadata 校验**：`test_task_handlers.py` 中 `TestValidateTaskCreation` 增加 `wechat_mp_draft` 用例：operation=update 且缺少 media_id 时应失败。
- **Handler 返回形状**：`TestTaskHandlerResultShape` 或新增用例，断言 `process_wechat_mp_draft_task` 成功返回含 `status`、`summary`、`data.media_id`（mock WeChatMPClient）。
- **API**：`test_task_queue_routes.py` 中 GET task-types 应包含 `wechat_mp_draft`；创建定时任务时 `task_type: "wechat_mp_draft"` 应成功（mock 或真实 client，视环境而定）。

## 9. 实现顺序建议

1. **wechat_mp_service**：在 `client.py` 中实现 `add_draft`、`update_draft`（及必要时「上传图文消息图片」）。
2. **task_handlers**：在 `TASK_TYPES` 中新增 `wechat_mp_draft`，实现 `process_wechat_mp_draft_task`，并注册 + 校验。
3. **task_queue_routes**：`_generate_task_name` 与定时任务 type_names 补充 `wechat_mp_draft`。
4. **TaskResultDisplay**：增加 `wechat_mp_draft` 结果展示。
5. **测试**：按 §8 补充单测与接口测试。

## 10. 小结

| 维度 | 内容 |
|------|------|
| 任务类型 | `wechat_mp_draft`：公众号草稿（新增/更新） |
| 入参 | operation、title、content、可选 author/digest/media_id（update 必填） |
| 执行 | 调用 WeChatMPClient.add_draft / update_draft |
| 结果 | status、summary、data.media_id、data.message |
| 前端（任务） | TaskResultDisplay 新增分支；创建/定时表单由 schema 动态生成 |
| 前端（显示/编辑草稿） | 可选：GET 草稿列表与详情 API + 草稿列表/详情页 + 「编辑」= 预填并提交更新草稿任务 |
| 定时 | 与现有定时任务机制一致，无需额外开发 |
