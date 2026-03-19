# baoyu-comic 漫画技能配置说明

时间：2025-03-17；理由：hou-cli 集成 baoyu；方法：环境变量与 .baoyu-skills 配置
更新：2025-03-18；TheTurbo.ai、万相图生、模型选择

## 前置条件

- **Node.js** 与 **npx**（用于安装 baoyu-comic）
- **LLM API**：二选一
  - `ANTHROPIC_API_KEY`（Claude 直连）
  - `TURBOGATEWAY_API_KEY`（TheTurbo.ai 网关，推荐）
- **至少一个图生 API key**（供 baoyu-image-gen 生成漫画图片）

## 配置步骤

### 1. 安装 baoyu-comic（可选，skill 会自动执行）

```bash
npx skills add JimLiu/baoyu-skills --skill baoyu-comic -a cursor -y
```

### 2. 配置图生 API（含万相 wanx）

在项目根目录或用户目录创建 `.baoyu-skills/.env`：

```bash
mkdir -p .baoyu-skills
```

编辑 `.baoyu-skills/.env`，添加至少一个：

```env
# 阿里云百炼/万相（推荐，与 hou-cli 百炼一致）
# 万相 wanx 文生图通过 DASHSCOPE 调用
DASHSCOPE_API_KEY=sk-xxx

# 或 OpenAI
OPENAI_API_KEY=sk-xxx

# 或 Google
GOOGLE_API_KEY=xxx

# 或 Replicate
REPLICATE_API_TOKEN=r8_xxx
```

### 3. 配置 LLM API

#### 方式 A：TheTurbo.ai 网关（推荐）

```bash
export TURBOGATEWAY_API_KEY=你的TheTurbo密钥
# 可选，默认为 https://gateway.theturbo.ai/v1
export ANTHROPIC_BASE_URL=https://gateway.theturbo.ai/v1
```

或在 `.env` 中：

```env
TURBOGATEWAY_API_KEY=你的TheTurbo密钥
ANTHROPIC_BASE_URL=https://gateway.theturbo.ai/v1
```

#### 方式 B：Anthropic 直连

```bash
export ANTHROPIC_API_KEY=sk-ant-xxx
```

### 4. 安装 run_baoyu_comic 依赖

```bash
make install-deps
```

`make install-deps` 会安装 `scripts/run_baoyu_comic` 的 npm 依赖（Claude Agent SDK）。

## 模型选择

漫画生成 UI 支持选择 LLM 模型。**默认模型**（留空时使用）优先级：

1. `ANTHROPIC_MODEL` 环境变量
2. `COMIC_DEFAULT_MODEL` 环境变量
3. 固定默认：`claude-3-5-sonnet-20241022`

**可选模型**：

- **TheTurbo.ai**：Claude 3.5 Sonnet / Haiku、Claude Sonnet 4 / Opus 4、Gemini 2.5 Pro / Flash、GPT-4o / GPT-5
- **百炼平台**：Qwen3 Max、Qwen Plus、Qwen Turbo、DeepSeek V3.2、QWQ Plus（需 LiteLLM 代理）

**百炼模型使用步骤**（时间：2025-03-19；理由：用户要求支持百炼；方法：LiteLLM 代理将 Anthropic 请求转发到 DashScope）：

1. 在 `.env` 或 `.baoyu-skills/.env` 中配置 `DASHSCOPE_API_KEY` 或 `BAILIAN_API_KEY`
2. 另开终端执行：`make litellm-comic-proxy`
3. 在漫画 UI 中选择百炼平台及模型（如 Qwen3 Max）

## 使用方式

在 hou-cli Chat 中说：

- 「把这篇文章做成漫画」
- 「用 manga 风格把 source.md 做成知识漫画」
- 「把这段故事做成教育漫画，用 ohmsha 预设」

或在「漫画生成」页面填写源内容、画风、模型等，提交任务。

## 首次运行与 EXTEND.md

baoyu-comic 需要 `EXTEND.md` 配置偏好（水印、画风等）。**hou-cli 会在首次运行时自动创建** `.baoyu-skills/baoyu-comic/EXTEND.md`（最小化默认配置），避免 Agent 卡在首次设置问答。你可后续手动编辑该文件自定义偏好。

## 输出位置

漫画默认输出到项目根目录下的 `comic/{topic-slug}/`；若通过 hou-cli 指定了输出目录，生成完成后会自动复制到该目录。包含：

- `storyboard.md` - 分镜
- `prompts/` - 每格提示词
- `*.png` - 生成的图片
- `{slug}.pdf` - 合并后的 PDF

## 验证：真实 API 测试

```bash
# 需配置：ANTHROPIC/TURBOGATEWAY + DASHSCOPE（或 .baoyu-skills/.env）
# 模型不可用时：COMIC_DEFAULT_MODEL=gemini-2.5-flash make test-task-comic
make test-task-comic
```

## 故障排查

| 错误 | 处理 |
|------|------|
| 未生成任何 PDF / Agent 未找到 baoyu-comic | 1. 执行 `npx skills add JimLiu/baoyu-skills --skill baoyu-comic -a cursor -y`；2. 确保 `.baoyu-skills/baoyu-comic/EXTEND.md` 存在（hou-cli 会自动创建，或手动创建最小配置）；3. 执行 `make install-deps` |
| 模型不可用或无权访问 | 设置 `COMIC_DEFAULT_MODEL=gemini-2.5-flash` 或你账户支持的模型 |
| 百炼模型连接失败 / Connection refused | 另开终端执行 `make litellm-comic-proxy`，确保 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY 已配置 |
| 未找到 npx | 安装 Node.js |
| 未设置 ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY | 在环境变量或 .env 中配置其一 |
| npx skills add 失败 | 检查网络，或手动执行安装命令 |
| 图生失败 | 检查 .baoyu-skills/.env 中的 API key 是否有效（万相用 DASHSCOPE_API_KEY） |
