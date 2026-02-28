# 微信公众号工具设计文档

## 概述

为 hou-cli 提供微信公众号相关能力。**当前仅支持个人未认证账号可用的接口**（不实现需认证的统计、发布等）。

- **实现范围**：access_token、草稿（列表/详情/新增/更新）、上传图文消息图片。
- **不实现**：发布草稿、发布状态查询、所有数据统计接口（用户增减、累计用户、图文阅读等均需认证号）。

其余能力（菜单、客服、用户标签、留言等）暂不实现。

## 账号类型与权限

| 能力           | 个人未认证订阅号 | 认证订阅号/服务号 |
|----------------|------------------|-------------------|
| access_token   | ✅               | ✅                |
| 草稿列表/详情  | ✅               | ✅                |
| 新增/更新草稿  | ✅（需先开启草稿箱） | ✅                |
| 上传图文图片   | ✅               | ✅                |
| 发布草稿       | ❌（回收或无效） | ✅                |
| 数据统计       | ❌（48001）      | ✅                |

个人号无法进行微信认证，故统计与发布相关接口不实现；若后续使用认证号，可在本设计基础上扩展。

## 功能范围（当前实现）

### 一、凭据与草稿（个人号可用）

| 能力 | 说明 | 官方文档 |
|------|------|----------|
| 获取 access_token | 接口调用凭据 | [获取接口调用凭据](https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html) |
| 获取草稿列表 | 分页查询草稿，可 no_content 减少体积 | [获取草稿列表](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_batchget.html) |
| 获取草稿详情 | 根据 media_id 获取单篇草稿全文 | [获取草稿详情](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_getdraft) |
| 上传图文消息图片 | 上传正文/封面用图片，获取 URL 填入草稿 | 素材管理 - 上传图文消息图片 |
| 新增草稿 | 创建图文草稿（标题、作者、正文 HTML、封面等） | [新增草稿](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html) |
| 更新草稿 | 修改已有草稿 | [更新草稿](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_update.html) |

流程建议：**上传图片（可选）→ 新增草稿 或 更新草稿**。个人号发布需在手机端「公众号助手」操作。

### 三、正文 content 格式与样式（草稿/图文）

草稿 API 的 **content** 字段为正文内容，官方说明与社区反馈总结如下。

#### 官方文档说明（新增草稿 API）

- **格式**：支持 **HTML 标签**。
- **限制**：必须少于 2 万字符、小于 1MB；文档中另写「大小不可超过 2kb」以官方最新文档为准。
- **处理规则**：会**去除 JS**；涉及图片的 URL 必须来自「上传图文消息内的图片获取 URL」接口，**外部图片 URL 会被过滤**。

官方未明确列出支持的 HTML 标签和 CSS 属性清单。

#### 社区反馈（样式与兼容性）

- **基础样式**：部分**行内样式**可能保留，例如 `style="color: red; font-weight: 700;"` 有反馈称文字会变红/加粗，但并非所有样式都生效。
- **易被过滤的样式**：复杂 CSS 如 `position`、`background-color`、`linear-gradient`、`box-sizing` 等上传后常被删除，正文只保留基础效果。
- **系统改写**：后端可能自动插入 `<span leaf>` 或 `&nbsp;`，导致排版与预期不一致。
- **建议**：使用**简单 HTML 结构 + 基础行内样式**（如颜色、加粗、字号）；避免依赖复杂布局和高级 CSS；正文内图片务必使用「上传图文消息内的图片」接口返回的 URL。

#### 小结（写草稿时）

| 项目       | 建议 |
|------------|------|
| 格式       | HTML，标签不宜过复杂 |
| 样式       | 优先简单行内样式（color、font-weight、font-size 等），避免复杂布局与渐变等 |
| 图片       | 仅使用「上传图文消息内的图片」接口返回的 URL，否则会被过滤 |
| 脚本       | 会被去除，不要依赖 JS |
| 预期       | 后端可能插入标签或空格，复杂版式以实际公众号展示为准 |

当前草稿列表/详情接口返回的正文即为上述处理后的 HTML（可能含 `span`、`&nbsp;` 等），前端展示时按 HTML 渲染即可；若需编辑再提交，需注意上述限制。

**草稿正文模板**：项目内提供 GitHub 风格的 HTML 模板，仅使用行内样式，便于在公众号内保留排版。见 [wechat-mp-article-template.html](./wechat-mp-article-template.html)（可浏览器打开预览，复制「正文片段」到草稿 content）。

### 四、不实现（需认证或个人号不可用）

- **发布草稿**、**发布状态查询**：个人主体可能被回收发布能力或仅能手机端发布。
- **数据统计**：用户增减、累计用户、图文阅读/分享等接口均需**已认证**公众号，个人号调用返回 48001。

## 代码与目录结构

```
backend/
├── services/
│   └── wechat_mp_service/
│       ├── __init__.py
│       ├── client.py       # access_token、草稿列表/详情/新增/更新、上传图文图片
│       └── README.md       # 配置说明（appid、secret、IP 白名单）
│
└── core/agent/tools/
    └── builtin/
        └── wechat_mp_tool.py   # Tool 封装（待实现）
```

- **wechat_mp_service**：纯 HTTP 调用微信 API，仅实现个人号可用接口。
- **wechat_mp_tool**：Agent 工具封装，后续按需实现。

## 配置

- `.env`：`WECHAT_MP_APP_ID`、`WECHAT_MP_APP_SECRET`。
- 公众平台 → 开发 → 基本配置 → **IP 白名单**：添加调用方服务器 IP，否则 token 接口返回 40164。

## 后续可扩展（认证号或政策放开时）

- 发布草稿、发布状态查询。
- 数据统计：用户增减、累计用户、图文阅读/分享等。
- 群发、永久素材、留言、用户/标签、客服等。
