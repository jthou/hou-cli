# 写作画像（Writing Profile）

写文章 Agent 会根据**写作画像**记住你的喜好、表述习惯和范文，在生成文章时尽量贴合你的风格。

## 配置文件位置

- 环境变量 **`WRITING_PROFILE_PATH`** 指定 JSON 文件路径（优先）
- 否则依次查找：项目下的 `config/writing_profile.json`、项目根目录的 `writing_profile.json`
- 若不存在，可复制 `config/writing_profile.example.json` 为 `config/writing_profile.json` 并编辑

## 配置说明

| 字段 | 说明 |
|------|------|
| **preferences** | 用户喜好列表，每条一句话。例如：少用「的」、偏好短句、技术文要贴代码 |
| **style_notes** | 习惯的表述方式：一段文字描述你平时的语气、用词、结构习惯 |
| **sample_articles** | 范文列表。每项可填 **title** + **content**（正文），或 **title** + **path**（本地文件路径，如 .md /.txt） |
| **extra** | 预留扩展字段，可忽略 |

## 范文（sample_articles）

- **content**：直接写范文正文，Agent 会截取前约 3500 字参与风格参考。
- **path**：本地文件路径（支持 `~`），Agent 会读取该文件内容作为范文。适合放你过去写好的文章路径。

多篇范文会一起注入提示，模型会模仿其风格与表述。

## 使用方式

- **前端入口**：侧边栏 **工具 → 写文章**，进入多轮对话页，与 Agent 对话完成定主题、改大纲、逐节写、润色等；由 **blog_writing** 技能 / **ArticleWritingAgent** 在对话中加载上述画像并在生成时注入。
- 修改 `config/writing_profile.json` 后，下次调用即生效，无需重启。
