# LLM 服务配置说明

## 支持的提供商

### 1. OpenAI（通过 TheTurbo.ai 网关）

**环境变量配置：**
```bash
LLM_PROVIDER=openai  # 设置为 openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5  # 可选，默认为 gpt-5
OPENAI_BASE_URL=https://gateway.theturbo.ai/v1  # 可选，默认为 TheTurbo.ai 网关
```

**支持的模型：**

**GPT-4o 系列：**
- `gpt-4o` - GPT-4o 标准版
- `gpt-4o-mini` - GPT-4o 迷你版
- `chatgpt-4o-latest` - ChatGPT 4o 最新版

**O3 系列（支持思考过程）：**
- `o3` - O3 标准版
- `o3-mini` - O3 迷你版

**GPT-4.1 系列：**
- `gpt-4.1` - GPT-4.1 标准版
- `gpt-4.1-mini` - GPT-4.1 迷你版
- `gpt-4.1-nano` - GPT-4.1 纳米版

**O4 系列：**
- `o4-mini` - O4 迷你版

**GPT-5 系列：**
- `gpt-5` - GPT-5 标准版（默认）
- `gpt-5-chat-latest` - GPT-5 聊天最新版
- `gpt-5-mini` - GPT-5 迷你版
- `gpt-5-nano` - GPT-5 纳米版
- `gpt-5-codex` - GPT-5 代码版

**GPT-5.1 系列：**
- `gpt-5.1` - GPT-5.1 标准版
- `gpt-5.1-chat-latest` - GPT-5.1 聊天最新版
- `gpt-5.1-codex` - GPT-5.1 代码版
- `gpt-5.1-codex-mini` - GPT-5.1 代码迷你版
- `gpt-5.1-codex-max` - GPT-5.1 代码最大版

**GPT-5.2 系列：**
- `gpt-5.2` - GPT-5.2 标准版
- `gpt-5.2-chat-latest` - GPT-5.2 聊天最新版

**API Key 获取：**
1. 访问 [TheTurbo.ai](https://theturbo.ai/)
2. 注册/登录账户
3. 在控制台获取 API Key

**注意事项：**
- 平台为保障并发资源量，后端为多账号负载
- 如需提高缓存命中率，多轮对话模式可携带 HTTP 请求头 `X-Conversation-Id` 加随机字符串请求
- 平台会优先路由到后端同一账号上

### 2. Anthropic Claude（通过 TheTurbo.ai 网关）

**环境变量配置：**
```bash
LLM_PROVIDER=anthropic  # 设置为 anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-20241022  # 可选，默认为 claude-3-5-haiku-20241022
ANTHROPIC_BASE_URL=https://gateway.theturbo.ai/v1  # 可选，默认为 TheTurbo.ai 网关
```

**支持的模型：**

**Claude 3.5 系列：**
- `claude-3-5-haiku-20241022` - Claude 3.5 Haiku（默认）
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet

**Claude 3.7 系列（支持 reasoning_effort 参数）：**
- `claude-3-7-sonnet-20250219` - Claude 3.7 Sonnet

**Claude Opus 4 系列（支持 reasoning_effort 参数）：**
- `claude-opus-4-20250514` - Claude Opus 4
- `claude-opus-4-1-20250805` - Claude Opus 4.1
- `claude-opus-4-5-20251101` - Claude Opus 4.5

**Claude Sonnet 4 系列（支持 reasoning_effort 参数）：**
- `claude-sonnet-4-20250514` - Claude Sonnet 4
- `claude-sonnet-4-5-20250929` - Claude Sonnet 4.5

**Claude Haiku 4 系列（支持 reasoning_effort 参数）：**
- `claude-haiku-4-5-20251001` - Claude Haiku 4.5

**API Key 获取：**
1. 访问 [TheTurbo.ai](https://theturbo.ai/)
2. 注册/登录账户
3. 在控制台获取 API Key

**注意事项：**
- Claude 支持 OpenAI 协议（通过 `/v1/chat/completions` 端点）
- 某些模型支持 `reasoning_effort` 参数（low, medium, high, none），用于控制推理任务的"计算精力"
- 平台为保障并发资源量，后端为多账号负载
- 如需提高缓存命中率，多轮对话模式可携带 HTTP 请求头 `X-Conversation-Id` 加随机字符串请求
- 平台会优先路由到后端同一账号上

### 3. Google Gemini（通过 TheTurbo.ai 网关）

**环境变量配置：**
```bash
LLM_PROVIDER=google  # 设置为 google
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL=gemini-2.5-flash  # 可选，默认为 gemini-2.5-flash
GOOGLE_BASE_URL=https://gateway.theturbo.ai/v1  # 可选，默认为 TheTurbo.ai 网关
```

**支持的模型：**

**Gemini 2.0 系列：**
- `gemini-2.0-flash` - Gemini 2.0 Flash

**Gemini 2.5 系列：**
- `gemini-2.5-flash` - Gemini 2.5 Flash（默认）
- `gemini-2.5-pro` - Gemini 2.5 Pro
- `gemini-2.5-flash-lite` - Gemini 2.5 Flash Lite
- `gemini-2.5-flash-lite-preview-06-17` - Gemini 2.5 Flash Lite 预览版
- `gemini-2.5-flash-thinking` - Gemini 2.5 Flash Thinking（输出思考过程）
- `gemini-2.5-pro-thinking` - Gemini 2.5 Pro Thinking（输出思考过程）

**Gemini 3 系列：**
- `gemini-3-pro-preview` - Gemini 3 Pro 预览版
- `gemini-3-flash-preview` - Gemini 3 Flash 预览版

**API Key 获取：**
1. 访问 [TheTurbo.ai](https://theturbo.ai/)
2. 注册/登录账户
3. 在控制台获取 API Key

**注意事项：**
- Gemini 支持 OpenAI 协议（通过 `/v1/chat/completions` 端点）
- 某些模型支持思考过程（`thinking` 系列）
- 某些模型支持 `reasoning_effort` 参数（控制推理任务的"计算精力"）
- 某些模型支持 `web_search_options`（Google Search 功能，仅 `gemini-2.5-pro` 和 `gemini-2.5-flash` 系列）
- 支持多模态理解（文档、图像、音频、视频），仅支持 base64 格式上传
- 模型名称包含 `exp` 的为实验性模型，不太稳定，建议只用来进行实验性测试
- 平台为保障并发资源量，后端为多账号负载
- 如需提高缓存命中率，多轮对话模式可携带 HTTP 请求头 `X-Conversation-Id` 加随机字符串请求
- 平台会优先路由到后端同一账号上

### 4. xAI Grok（通过 TheTurbo.ai 网关）

**环境变量配置：**
```bash
LLM_PROVIDER=xai  # 设置为 xai
XAI_API_KEY=your_xai_api_key
XAI_MODEL=grok-4  # 可选，默认为 grok-4
XAI_BASE_URL=https://gateway.theturbo.ai/v1  # 可选，默认为 TheTurbo.ai 网关
```

**支持的模型：**

**Grok 3 系列：**
- `grok-3` - Grok 3

**Grok 4 系列：**
- `grok-4` - Grok 4（默认）
- `grok-4-fast-non-reasoning` - Grok 4 快速非推理版本
- `grok-4-fast-reasoning` - Grok 4 快速推理版本（支持推理）

**API Key 获取：**
1. 访问 [TheTurbo.ai](https://theturbo.ai/)
2. 注册/登录账户
3. 在控制台获取 API Key

**注意事项：**
- Grok 支持 OpenAI 协议（通过 `/v1/chat/completions` 端点）
- `grok-4-fast-reasoning` 支持推理功能
- 平台为保障并发资源量，后端为多账号负载
- 如需提高缓存命中率，多轮对话模式可携带 HTTP 请求头 `X-Conversation-Id` 加随机字符串请求
- 平台会优先路由到后端同一账号上

### 5. Perplexity Sonar（通过 TheTurbo.ai 网关）

**环境变量配置：**
```bash
LLM_PROVIDER=perplexity  # 设置为 perplexity
PERPLEXITY_API_KEY=your_perplexity_api_key
PERPLEXITY_MODEL=sonar  # 可选，默认为 sonar
PERPLEXITY_BASE_URL=https://gateway.theturbo.ai/v1  # 可选，默认为 TheTurbo.ai 网关
```

**支持的模型：**

**Sonar 系列：**
- `sonar` - Sonar 标准版（默认）
- `sonar-pro` - Sonar Pro 版本
- `sonar-reasoning-pro` - Sonar Reasoning Pro（支持推理）

**API Key 获取：**
1. 访问 [TheTurbo.ai](https://theturbo.ai/)
2. 注册/登录账户
3. 在控制台获取 API Key

**注意事项：**
- Perplexity Sonar 支持 OpenAI 协议（通过 `/v1/chat/completions` 端点）
- `sonar-reasoning-pro` 支持推理功能
- 支持 `search_recency_filter` 参数（搜索时间过滤：`month`、`week`、`day`、`hour`）
- 响应中包含 `citations` 字段（引用来源链接）
- 平台为保障并发资源量，后端为多账号负载
- 如需提高缓存命中率，多轮对话模式可携带 HTTP 请求头 `X-Conversation-Id` 加随机字符串请求
- 平台会优先路由到后端同一账号上

### 6. DeepSeek（默认）

**环境变量配置：**
```bash
LLM_PROVIDER=deepseek  # 可选，默认为 deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat  # 可选，默认为 deepseek-chat
```

**支持的模型：**
- `deepseek-chat` - 默认聊天模型
- `deepseek-coder` - 编程专用模型
- `deepseek-reasoner` - 推理模型
- `deepseek-r1` - 支持思考过程的模型
- `deepseek-v2`, `deepseek-v2.5`, `deepseek-v3` - 版本化模型

### 7. 阿里云百炼平台

**环境变量配置：**
```bash
LLM_PROVIDER=bailian  # 设置为 bailian
BAILIAN_API_KEY=your_bailian_api_key  # 或使用 DASHSCOPE_API_KEY
BAILIAN_MODEL=qwen-turbo  # 可选，默认为 qwen-turbo
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 可选
```

**支持的模型：**

**通义千问3 系列（文本生成）：**
- `qwen3-max` - 通义千问3 Max（最新版本，适配复杂智能体场景）
- `qwen-plus-2025-12-01` - 通义千问 Plus（支持思考模式和非思考模式融合）
- `qwen-flash` - 通义千问 Flash（支持1M上下文长度）
- `qwen-max-2025-01-25` - 通义千问 Max（千亿级别超大规模模型）
- `qwen-turbo-latest` - 通义千问 Turbo（最新版本）
- `qwen-deep-research` - 通义千问深入研究（面向复杂研究任务）

**通义千问3 代码系列：**
- `qwen3-coder-plus-2025-09-23` - 通义千问3 Coder Plus（强大的 Coding Agent 能力）
- `qwen3-coder-flash` - 通义千问3 Coder Flash（优化仓库级别理解能力）
- `qwen3-coder-480b-a35b-instruct` - 通义千问3 Coder 480B（代码能力达到开源模型 SOTA）
- `qwen3-coder-30b-a3b-instruct` - 通义千问3 Coder 30B（同尺寸规模模型 SOTA）

**通义千问3 视觉理解系列：**
- `qwen3-vl-plus-2025-12-19` - 通义千问3 VL Plus（视觉智能体业界领先，支持深度思考）
- `qwen3-vl-flash-2025-10-15` - 通义千问3 VL Flash（支持长视频长文档等超长上下文）
- `qwen3-vl-32b-thinking` - 通义千问3 VL 32B Thinking（开源模型，支持深度思考）

**通义千问 VL 系列：**
- `qwen-vl-max-2025-08-13` - 通义千问 VL Max（超大规模视觉语言模型）
- `qwen-vl-plus-latest` - 通义千问 VL Plus（支持超百万像素分辨率）

**通义千问3 全模态系列：**
- `qwen3-omni-flash-2025-12-01` - 通义千问3 Omni Flash（支持文本、图像、音频、视频理解与语音生成）
- `qwen3-omni-flash-realtime-2025-12-01` - 通义千问3 Omni Flash 实时版
- `qwen3-omni-30b-a3b-captioner` - 通义千问3 Omni 30B Captioner（音频细粒度分析）

**通义千问 Omni 系列：**
- `qwen-omni-turbo-2025-03-26` - 通义千问 Omni Turbo（多模态理解生成大模型）
- `qwen-omni-turbo-realtime-2025-05-08` - 通义千问 Omni Turbo 实时版

**通义千问3 语音识别系列：**
- `qwen3-asr-flash-2025-09-08` - 通义千问3 ASR Flash（多语种语音识别）
- `qwen3-asr-flash-realtime-2025-10-27` - 通义千问3 ASR Flash 实时版
- `qwen3-asr-flash-filetrans-2025-11-17` - 通义千问3 ASR Flash 大文件转录版

**通义千问3 语音合成系列：**
- `qwen3-tts-flash-2025-11-27` - 通义千问3 TTS Flash（17种高表现力拟人音色）
- `qwen3-tts-flash-realtime-2025-11-27` - 通义千问3 TTS Flash 实时版
- `qwen3-tts-vc-realtime-2025-11-27` - 通义千问3 TTS VC 实时版（声音复刻）
- `qwen3-tts-vd-realtime-2025-12-16` - 通义千问3 TTS VD 实时版（声音设计）

**通义千问 TTS 系列：**
- `qwen-tts-2025-05-22` - 通义千问 TTS（首个语音合成模型）
- `qwen-tts-realtime-2025-07-15` - 通义千问 TTS 实时版
- `qwen-voice-enrollment` - 通义千问声音复刻（仅需5s以上音频即可复刻声音）

**通义千问3 翻译系列：**
- `qwen3-livetranslate-flash` - 通义千问3 LiveTranslate Flash（多语言实时音视频同传）
- `qwen3-livetranslate-flash-realtime` - 通义千问3 LiveTranslate Flash 实时版

**通义千问 MT 系列：**
- `qwen-mt-plus` - 通义千问 MT Plus（旗舰级翻译大模型，支持92个语种）
- `qwen-mt-flash` - 通义千问 MT Flash（轻量级文本翻译大模型）
- `qwen-mt-turbo` - 通义千问 MT Turbo（轻量级文本翻译大模型）
- `qwen-mt-lite` - 通义千问 MT Lite（基础级文本翻译大模型，支持32个语种）
- `qwen-mt-image` - 通义千问 MT Image（图片翻译，支持11个语言）

**通义千问 图像生成系列：**
- `qwen-image-max-2025-12-30` - 通义千问 Image Max（图像生成模型 Max 系列）
- `qwen-image-plus-2026-01-09` - 通义千问 Image Plus（卓越的文本渲染能力）
- `qwen-image-edit-plus-2025-12-15` - 通义千问 Image Edit Plus（图像编辑 Plus 模型）

**通义万相系列（视频/图像生成）：**
- `wan2.6-t2v` - 通义万相 文生视频（文字生成视频内容，最高15秒）
- `wan2.6-i2v` - 通义万相 图生视频（图片生成视频内容）
- `wan2.6-r2v` - 通义万相 参考生视频（参考视频中的人或物）
- `wan2.6-t2i` - 通义万相 文生图（文字生成图片）
- `wan2.6-image` - 通义万相 图像生成（指令编辑图片内容）

**通义千问 推理系列：**
- `qwq-plus` - 通义千问 QwQ Plus（推理模型增强版，达到 DeepSeek-R1 满血版水平）
- `qvq-max-latest` - 通义千问 QVQ Max（视觉推理模型，支持视觉输入及思维链输出）
- `qvq-plus-latest` - 通义千问 QVQ Plus（视觉推理模型增强版）

**通义千问2.5 开源系列：**
- `qwen2.5-omni-7b` - 通义千问2.5 Omni 7B（开源多模态模型）

**通义千问 传统系列（向后兼容）：**
- `qwen-turbo` - 通义千问 Turbo（默认）
- `qwen-plus` - 通义千问 Plus
- `qwen-max` - 通义千问 Max
- `qwen-max-longcontext` - 长上下文版本
- `qwen-7b-chat`, `qwen-14b-chat`, `qwen-72b-chat`, `qwen-1.8b-chat`, `qwen-32b-chat` 等

**DeepSeek 系列（在百炼平台）：**
- `deepseek-v3.2` - DeepSeek V3.2（最新版本，支持深度思考）
- `deepseek-chat` - DeepSeek 聊天模型
- `deepseek-coder` - DeepSeek 编程模型
- `deepseek-reasoner` - DeepSeek 推理模型
- `deepseek-r1` - DeepSeek 思考模型
- `deepseek-v3.2-exp` - DeepSeek V3.2 实验版
- `deepseek-v3.1` - DeepSeek V3.1
- `deepseek-v3`, `deepseek-v2.5`, `deepseek-v2` - 版本化模型
- `deepseek3.2` - 简化名称（自动映射到 deepseek-v3.2）
- `deepseek-3.2` - 带连字符版本（自动映射到 deepseek-v3.2）

**GLM 系列：**
- `glm-4.7` - GLM 4.7（智谱提供的开源模型）

**Kimi 系列：**
- `kimi-k2-thinking` - Kimi K2 Thinking（月之暗面提供的开源模型，具有卓越的编码和工具调用能力）

**Fun-ASR 系列：**
- `fun-asr` - Fun-ASR 语音识别（新一代端到端语音识别大模型）
- `fun-asr-realtime-2025-11-07` - Fun-ASR 实时语音识别

**其他模型：**
- `z-image-turbo` - Z-Image Turbo（文生图开源模型世界第一）
- `tongyi-embedding-vision-flash` - 通义多模态向量（支持文本、图像、视频3种模态）
- `cosyvoice-v3-flash` - CosyVoice 大模型（新一代生成式语音大模型）
- `aitryon-plus` - AI试衣 Plus版（虚拟试衣图片生成模型）
- `baichuan2-turbo`, `baichuan2-13b-chat` - 百川系列
- `chatglm3-6b`, `chatglm3-32k` - ChatGLM 系列
- `llama2-7b-chat`, `llama2-13b-chat`, `llama2-70b-chat` - LLaMA 系列

**API Key 获取：**
1. 访问 [阿里云百炼平台](https://www.bailian.online/)
2. 注册/登录阿里云账户
3. 在控制台获取 API Key（DashScope API Key）

## 模型命名格式和识别

### 推荐格式：平台-模型

为了避免不同平台同名模型的混淆，**强烈建议使用 `平台-模型` 格式**：

```python
from backend.services.llm.llm_service import LLMService

# 方式 1：使用 "平台-模型" 格式（推荐）
llm_service = LLMService(model="openai-gpt-5")  # OpenAI 平台的 gpt-5
llm_service = LLMService(model="anthropic-claude-3-5-haiku-20241022")  # Anthropic 平台的 Claude
llm_service = LLMService(model="google-gemini-2.5-flash")  # Google 平台的 Gemini
llm_service = LLMService(model="xai-grok-4")  # xAI 平台的 Grok
llm_service = LLMService(model="perplexity-sonar")  # Perplexity 平台的 Sonar
llm_service = LLMService(model="bailian-deepseek-chat")  # 百炼平台的 deepseek-chat
llm_service = LLMService(model="deepseek-deepseek-chat")  # DeepSeek 平台的 deepseek-chat
llm_service = LLMService(model="bailian-deepseek3.2")  # 百炼平台的 deepseek3.2
llm_service = LLMService(model="bailian-qwen-max")  # 百炼平台的 qwen-max

# 方式 2：动态切换（使用 "平台-模型" 格式）
llm_service = LLMService()
llm_service.set_model("openai-gpt-5")  # 切换到 OpenAI 平台的 gpt-5
llm_service.set_model("openai-o3")  # 切换到 OpenAI 平台的 o3（支持思考过程）
llm_service.set_model("anthropic-claude-3-5-haiku-20241022")  # 切换到 Anthropic 平台的 Claude
llm_service.set_model("anthropic-claude-opus-4-20250514")  # 切换到 Anthropic 平台的 Claude Opus 4
llm_service.set_model("google-gemini-2.5-flash")  # 切换到 Google 平台的 Gemini
llm_service.set_model("google-gemini-2.5-flash-thinking")  # 切换到 Google 平台的 Gemini Thinking
llm_service.set_model("xai-grok-4")  # 切换到 xAI 平台的 Grok
llm_service.set_model("xai-grok-4-fast-reasoning")  # 切换到 xAI 平台的 Grok 推理版本
llm_service.set_model("perplexity-sonar")  # 切换到 Perplexity 平台的 Sonar
llm_service.set_model("perplexity-sonar-reasoning-pro")  # 切换到 Perplexity 平台的 Sonar 推理版本
llm_service.set_model("bailian-deepseek-chat")  # 切换到百炼平台的 deepseek-chat
llm_service.set_model("deepseek-deepseek-coder")  # 切换到 DeepSeek 平台的 deepseek-coder
llm_service.set_model("bailian-qwen-max")  # 切换到百炼平台的 qwen-max
```

### 支持的格式

**1. "平台-模型" 格式（推荐）：**
- `openai-gpt-5` - OpenAI 平台的 gpt-5
- `openai-o3` - OpenAI 平台的 o3
- `anthropic-claude-3-5-haiku-20241022` - Anthropic 平台的 Claude 3.5 Haiku
- `anthropic-claude-opus-4-20250514` - Anthropic 平台的 Claude Opus 4
- `google-gemini-2.5-flash` - Google 平台的 Gemini 2.5 Flash
- `google-gemini-2.5-pro` - Google 平台的 Gemini 2.5 Pro
- `xai-grok-4` - xAI 平台的 Grok 4
- `xai-grok-4-fast-reasoning` - xAI 平台的 Grok 4 推理版本
- `perplexity-sonar` - Perplexity 平台的 Sonar
- `perplexity-sonar-pro` - Perplexity 平台的 Sonar Pro
- `bailian-deepseek-chat` - 百炼平台的 deepseek-chat
- `deepseek-deepseek-chat` - DeepSeek 平台的 deepseek-chat
- `bailian-deepseek3.2` - 百炼平台的 deepseek3.2
- `bailian-qwen-max` - 百炼平台的 qwen-max

**2. 传统格式（向后兼容，但可能混淆）：**
- `gpt-5` - 自动检测（OpenAI 平台）
- `o3` - 自动检测（OpenAI 平台）
- `claude-3-5-haiku-20241022` - 自动检测（Anthropic 平台）
- `claude-opus-4-20250514` - 自动检测（Anthropic 平台）
- `gemini-2.5-flash` - 自动检测（Google 平台）
- `gemini-2.5-pro` - 自动检测（Google 平台）
- `grok-4` - 自动检测（xAI 平台）
- `grok-4-fast-reasoning` - 自动检测（xAI 平台）
- `sonar` - 自动检测（Perplexity 平台）
- `sonar-pro` - 自动检测（Perplexity 平台）
- `deepseek-chat` - 自动检测（默认 DeepSeek 平台）
- `qwen-max` - 自动检测（百炼平台）

**3. 通过参数指定提供商：**
```python
# 明确指定提供商（覆盖自动检测）
llm_service.set_model("deepseek-chat", provider="bailian")  # 百炼平台
llm_service.set_model("deepseek-chat", provider="deepseek")  # DeepSeek 平台
```

### 模型名称映射

百炼平台上的某些模型名称会被自动映射：

- `deepseek3.2` → `deepseek-v3.2`
- `deepseek-3.2` → `deepseek-v3.2`

### 为什么推荐 "平台-模型" 格式？

1. **明确性**：避免同名模型在不同平台的混淆
   - `deepseek-chat` 在 DeepSeek 平台和百炼平台都存在
   - 使用 `deepseek-deepseek-chat` 明确指定 DeepSeek 平台
   - 使用 `bailian-deepseek-chat` 明确指定百炼平台
2. **可读性**：一眼就能看出使用的是哪个平台的哪个模型
3. **可维护性**：代码更清晰，减少错误

### 同名模型区分示例

当同一个模型名称在多个平台存在时，使用 `平台-模型` 格式可以明确区分：

```python
# ❌ 不推荐：可能混淆
llm_service.set_model("deepseek-chat")  # 不确定是哪个平台的

# ✅ 推荐：明确指定平台
llm_service.set_model("deepseek-deepseek-chat")  # DeepSeek 平台的 deepseek-chat
llm_service.set_model("bailian-deepseek-chat")   # 百炼平台的 deepseek-chat

# ✅ 或者通过参数指定
llm_service.set_model("deepseek-chat", provider="deepseek")  # DeepSeek 平台
llm_service.set_model("deepseek-chat", provider="bailian")  # 百炼平台
```

## 使用示例

### 代码中使用

```python
from backend.services.llm.llm_service import LLMService

# 方式 1：使用默认配置
llm_service = LLMService()

# 方式 2：指定初始模型（自动检测提供商）
llm_service = LLMService(model="openai-gpt-5")  # 自动使用 OpenAI 平台
llm_service = LLMService(model="anthropic-claude-3-5-haiku-20241022")  # 自动使用 Anthropic 平台
llm_service = LLMService(model="google-gemini-2.5-flash")  # 自动使用 Google 平台
llm_service = LLMService(model="xai-grok-4")  # 自动使用 xAI 平台
llm_service = LLMService(model="perplexity-sonar")  # 自动使用 Perplexity 平台
llm_service = LLMService(model="deepseek3.2")  # 自动使用百炼平台

# 方式 3：明确指定提供商
llm_service = LLMService(provider="openai")
llm_service = LLMService(provider="anthropic")
llm_service = LLMService(provider="google")
llm_service = LLMService(provider="xai")
llm_service = LLMService(provider="perplexity")
llm_service = LLMService(provider="bailian")

# 动态切换模型（自动切换提供商）
llm_service.set_model("openai-gpt-5")  # 切换到 OpenAI 平台的 gpt-5
llm_service.set_model("openai-o3")  # 切换到 OpenAI 平台的 o3
llm_service.set_model("anthropic-claude-3-5-haiku-20241022")  # 切换到 Anthropic 平台的 Claude
llm_service.set_model("anthropic-claude-opus-4-20250514")  # 切换到 Anthropic 平台的 Claude Opus 4
llm_service.set_model("google-gemini-2.5-flash")  # 切换到 Google 平台的 Gemini
llm_service.set_model("google-gemini-2.5-flash-thinking")  # 切换到 Google 平台的 Gemini Thinking
llm_service.set_model("xai-grok-4")  # 切换到 xAI 平台的 Grok
llm_service.set_model("xai-grok-4-fast-reasoning")  # 切换到 xAI 平台的 Grok 推理版本
llm_service.set_model("perplexity-sonar")  # 切换到 Perplexity 平台的 Sonar
llm_service.set_model("perplexity-sonar-reasoning-pro")  # 切换到 Perplexity 平台的 Sonar 推理版本
llm_service.set_model("deepseek3.2")  # 切换到百炼平台的 deepseek3.2
llm_service.set_model("qwen-max")  # 继续使用百炼平台
llm_service.set_model("deepseek-coder")  # 切换到 DeepSeek 平台

# 查看可用模型
available_models = llm_service.get_available_models()  # 当前提供商的模型列表
all_models = llm_service.list_all_models()  # 所有提供商的模型

# 查看模型信息
model_info = llm_service.get_model_info()  # 当前模型信息
```

### 环境变量配置

在 `.env` 文件中：

```bash
# 选择提供商（可选，如果不设置会根据模型名称自动检测）
LLM_PROVIDER=openai  # 或 anthropic, google, xai, perplexity, bailian, deepseek

# OpenAI 配置（通过 TheTurbo.ai 网关）
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-5  # 或 o3, gpt-4o 等
OPENAI_BASE_URL=https://gateway.theturbo.ai/v1  # 可选

# Anthropic Claude 配置（通过 TheTurbo.ai 网关）
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_MODEL=claude-3-5-haiku-20241022  # 或 claude-opus-4-20250514 等
ANTHROPIC_BASE_URL=https://gateway.theturbo.ai/v1  # 可选

# Google Gemini 配置（通过 TheTurbo.ai 网关）
GOOGLE_API_KEY=sk-xxx
GOOGLE_MODEL=gemini-2.5-flash  # 或 gemini-2.5-pro, gemini-2.5-flash-thinking 等
GOOGLE_BASE_URL=https://gateway.theturbo.ai/v1  # 可选

# xAI Grok 配置（通过 TheTurbo.ai 网关）
XAI_API_KEY=sk-xxx
XAI_MODEL=grok-4  # 或 grok-3, grok-4-fast-reasoning 等
XAI_BASE_URL=https://gateway.theturbo.ai/v1  # 可选

# Perplexity Sonar 配置（通过 TheTurbo.ai 网关）
PERPLEXITY_API_KEY=sk-xxx
PERPLEXITY_MODEL=sonar  # 或 sonar-pro, sonar-reasoning-pro 等
PERPLEXITY_BASE_URL=https://gateway.theturbo.ai/v1  # 可选

# 百炼平台配置
BAILIAN_API_KEY=sk-xxx
BAILIAN_MODEL=deepseek3.2  # 或 qwen-max

# DeepSeek 配置（如果使用 DeepSeek 平台）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
```

## 模型识别规则

### OpenAI 模型识别

以下模型会被识别为 OpenAI 平台：
- 所有以 `gpt-` 开头的模型（如 `gpt-4o`, `gpt-5`, `gpt-5.1` 等）
- 所有以 `o` 开头后跟数字的模型（如 `o3`, `o3-mini`, `o4-mini`）
- 所有以 `chatgpt-` 开头的模型

### Anthropic Claude 模型识别

以下模型会被识别为 Anthropic 平台：
- 所有以 `claude-` 开头的模型（如 `claude-3-5-haiku-20241022`, `claude-opus-4-20250514` 等）

### Google Gemini 模型识别

以下模型会被识别为 Google 平台：
- 所有以 `gemini-` 开头的模型（如 `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-3-pro-preview` 等）

### xAI Grok 模型识别

以下模型会被识别为 xAI 平台：
- 所有以 `grok-` 开头的模型（如 `grok-3`, `grok-4`, `grok-4-fast-reasoning` 等）

### Perplexity Sonar 模型识别

以下模型会被识别为 Perplexity 平台：
- 所有以 `sonar` 开头的模型（如 `sonar`, `sonar-pro`, `sonar-reasoning-pro` 等）

### 百炼平台模型识别

以下模型会被识别为百炼平台：
- 所有以 `qwen` 开头的模型
- 所有以 `deepseek` 开头且包含版本号的模型（如 `deepseek3.2`, `deepseek-v3.2`）
- `baichuan`, `chatglm`, `llama` 系列模型

### DeepSeek 平台模型识别

以下模型会被识别为 DeepSeek 平台：
- `deepseek-chat`, `deepseek-coder`, `deepseek-reasoner`, `deepseek-r1`
- `deepseek-v2`, `deepseek-v2.5`, `deepseek-v3`（不带具体版本号）

## 注意事项

1. **API Key 格式**：
   - OpenAI 通过 TheTurbo.ai 网关，API Key 格式通常为 `sk-xxx`
   - Anthropic Claude 通过 TheTurbo.ai 网关，API Key 格式通常为 `sk-xxx`
   - Google Gemini 通过 TheTurbo.ai 网关，API Key 格式通常为 `sk-xxx`
   - xAI Grok 通过 TheTurbo.ai 网关，API Key 格式通常为 `sk-xxx`
   - Perplexity Sonar 通过 TheTurbo.ai 网关，API Key 格式通常为 `sk-xxx`
   - 百炼平台使用 DashScope API Key，格式通常为 `sk-xxx`
   - DeepSeek 使用 DeepSeek API Key，格式通常为 `sk-xxx`
2. **兼容性**：
   - OpenAI、Anthropic Claude、Google Gemini、xAI Grok、Perplexity Sonar 和百炼平台都通过 OpenAI 兼容模式提供 API，使用相同的接口
   - DeepSeek 也使用 OpenAI 兼容 API
3. **模型名称**：系统会自动识别和映射模型名称，但建议使用标准名称
4. **工具调用**：所有平台都支持 Function Calling（工具调用）
5. **思考过程/推理能力**：以下模型支持思考过程或推理参数：
   - OpenAI: `o3`, `o3-mini`, `o4-mini`（支持思考过程）
   - Anthropic: `claude-3-7-sonnet-20250219`, `claude-opus-4-*`, `claude-sonnet-4-*`, `claude-haiku-4-*`（支持 `reasoning_effort` 参数）
   - Google: `gemini-2.5-flash-thinking`, `gemini-2.5-pro-thinking`（输出思考过程）
   - xAI: `grok-4-fast-reasoning`（支持推理）
   - Perplexity: `sonar-reasoning-pro`（支持推理）
   - DeepSeek: `deepseek-r1`（支持思考过程）
   - 百炼平台: `deepseek-v3.2`, `deepseek-v3.2-exp`, `deepseek-v3.1`（支持思考过程）
6. **特殊功能**：
   - Google Gemini: 支持多模态理解（文档、图像、音频、视频），支持 `web_search_options`（Google Search，仅 `gemini-2.5-pro` 和 `gemini-2.5-flash` 系列）
   - Perplexity Sonar: 支持 `search_recency_filter` 参数（搜索时间过滤：`month`、`week`、`day`、`hour`），响应中包含 `citations` 字段（引用来源）
7. **自动切换**：切换模型时，如果检测到属于不同提供商，会自动切换提供商和客户端
8. **模型映射**：某些简化名称（如 `deepseek3.2`）会自动映射到完整名称（`deepseek-v3.2`）
9. **多轮对话**：OpenAI、Anthropic、Google、xAI 和 Perplexity 平台支持通过 HTTP 请求头 `X-Conversation-Id` 提高缓存命中率

## 模型选择和切换指南

> 📖 **详细指南**：查看 [MODEL_SELECTION_GUIDE.md](./MODEL_SELECTION_GUIDE.md) 获取完整的模型选择和切换指南。

### 如何选择合适的模型？

系统提供了智能推荐功能，可以根据任务类型自动推荐合适的模型：

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 1. 根据任务类型推荐模型
# 文本生成任务
text_models = llm_service.recommend_models("text")
print("文本生成推荐模型:")
for model in text_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")

# 代码生成任务
code_models = llm_service.recommend_models("code")
print("\n代码生成推荐模型:")
for model in code_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")

# 推理任务
reasoning_models = llm_service.recommend_models("reasoning")
print("\n推理任务推荐模型:")
for model in reasoning_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")

# 视觉理解任务
vision_models = llm_service.recommend_models("vision")
print("\n视觉理解推荐模型:")
for model in vision_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")
```

### 任务类型和模型选择建议

#### 1. **文本生成 / 对话任务**
**推荐模型：**
- `openai-gpt-5` - OpenAI GPT-5，强大的文本生成能力
- `bailian-qwen3-max` - 通义千问3 Max，适配复杂智能体场景
- `bailian-qwen-plus-2025-12-01` - 通义千问 Plus，支持思考模式融合
- `anthropic-claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet，强大的对话和写作能力
- `google-gemini-2.5-pro` - Gemini 2.5 Pro，多模态理解生成

**使用示例：**
```python
llm_service = LLMService(model="openai-gpt-5")
# 或
llm_service = LLMService(model="bailian-qwen3-max")
```

#### 2. **代码生成 / 编程任务**
**推荐模型：**
- `deepseek-deepseek-coder` - DeepSeek Coder，专为代码生成优化
- `bailian-qwen3-coder-plus-2025-09-23` - 通义千问3 Coder Plus，强大的 Coding Agent 能力
- `bailian-qwen3-coder-flash` - 通义千问3 Coder Flash，优化仓库级别理解
- `openai-gpt-5-codex` - GPT-5 Codex，代码生成专用

**使用示例：**
```python
llm_service = LLMService(model="deepseek-deepseek-coder")
# 或
llm_service = LLMService(model="bailian-qwen3-coder-plus-2025-09-23")
```

#### 3. **推理 / 分析任务**
**推荐模型：**
- `deepseek-deepseek-r1` - DeepSeek R1，支持思考过程
- `openai-o3` - OpenAI O3，支持思考过程
- `bailian-deepseek-v3.2` - DeepSeek V3.2，支持深度思考
- `bailian-qwq-plus` - 通义千问 QwQ Plus，达到 DeepSeek-R1 满血版水平
- `anthropic-claude-3-7-sonnet-20250219` - Claude 3.7 Sonnet，支持 reasoning_effort
- `google-gemini-2.5-flash-thinking` - Gemini 2.5 Flash Thinking，输出思考过程
- `xai-grok-4-fast-reasoning` - Grok 4 Fast Reasoning，支持推理
- `perplexity-sonar-reasoning-pro` - Sonar Reasoning Pro，支持推理

**使用示例：**
```python
llm_service = LLMService(model="deepseek-deepseek-r1")
# 或
llm_service = LLMService(model="openai-o3")
```

#### 4. **视觉理解任务**
**推荐模型：**
- `bailian-qwen3-vl-plus-2025-12-19` - 通义千问3 VL Plus，视觉智能体业界领先
- `bailian-qwen-vl-max-2025-08-13` - 通义千问 VL Max，超大规模视觉语言模型
- `google-gemini-2.5-pro` - Gemini 2.5 Pro，支持多模态理解
- `anthropic-claude-opus-4-20250514` - Claude Opus 4，支持图片理解

**使用示例：**
```python
llm_service = LLMService(model="bailian-qwen3-vl-plus-2025-12-19")
```

#### 5. **图像生成任务**
**推荐模型：**
- `bailian-qwen-image-max-2025-12-30` - 通义千问 Image Max
- `bailian-wan2.6-t2i` - 通义万相 文生图

**使用示例：**
```python
llm_service = LLMService(model="bailian-qwen-image-max-2025-12-30")
```

#### 6. **视频生成任务**
**推荐模型：**
- `bailian-wan2.6-t2v` - 通义万相 文生视频（最高15秒）
- `bailian-wan2.6-i2v` - 通义万相 图生视频
- `bailian-wan2.6-r2v` - 通义万相 参考生视频

**使用示例：**
```python
llm_service = LLMService(model="bailian-wan2.6-t2v")
```

#### 7. **搜索任务**
**推荐模型：**
- `perplexity-sonar-pro` - Perplexity Sonar Pro，对话式搜索引擎
- `google-gemini-2.5-pro` - Gemini 2.5 Pro，支持 Google Search

**使用示例：**
```python
llm_service = LLMService(model="perplexity-sonar-pro")
```

### 如何动态切换模型？

#### 方式 1：使用 `set_model` 方法（推荐）

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 切换到不同的模型（自动切换提供商）
llm_service.set_model("openai-gpt-5")  # 切换到 OpenAI GPT-5
llm_service.set_model("deepseek-deepseek-coder")  # 切换到 DeepSeek Coder
llm_service.set_model("bailian-qwen3-max")  # 切换到通义千问3 Max
llm_service.set_model("anthropic-claude-3-5-sonnet-20241022")  # 切换到 Claude

# 系统会自动检测模型所属的提供商并切换客户端
```

#### 方式 2：根据任务类型智能切换

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 根据任务类型推荐并切换模型
def switch_model_for_task(llm_service, task_type: str):
    """根据任务类型切换模型"""
    recommendations = llm_service.recommend_models(task_type)
    if recommendations:
        # 选择第一个推荐模型
        best_model = recommendations[0]
        model_name = f"{best_model['provider']}-{best_model['model']}"
        llm_service.set_model(model_name)
        print(f"已切换到: {model_name} - {best_model['description']}")
        return model_name
    return None

# 代码任务
switch_model_for_task(llm_service, "code")
# 输出: 已切换到: deepseek-deepseek-coder - DeepSeek Coder，专为代码生成优化

# 推理任务
switch_model_for_task(llm_service, "reasoning")
# 输出: 已切换到: deepseek-deepseek-r1 - DeepSeek R1，支持思考过程

# 视觉任务
switch_model_for_task(llm_service, "vision")
# 输出: 已切换到: bailian-qwen3-vl-plus-2025-12-19 - 通义千问3 VL Plus...
```

#### 方式 3：在同一个会话中切换模型

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 开始使用文本生成模型
llm_service.set_model("openai-gpt-5")
response1 = await llm_service.chat(user_prompt="写一篇文章")

# 切换到代码生成模型
llm_service.set_model("deepseek-deepseek-coder")
response2 = await llm_service.chat(user_prompt="写一个 Python 函数")

# 切换到推理模型
llm_service.set_model("deepseek-deepseek-r1")
response3 = await llm_service.chat(user_prompt="分析这个复杂问题")
```

### 查看可用模型

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 查看当前提供商的可用模型
current_models = llm_service.get_available_models()
print(f"当前提供商 ({llm_service.provider}) 的模型: {current_models}")

# 查看所有提供商的模型
all_models = llm_service.list_all_models()
for provider, models in all_models.items():
    print(f"\n{provider.upper()} ({len(models)} 个模型):")
    print(f"  {', '.join(models[:10])}...")  # 显示前10个

# 查看当前模型信息
model_info = llm_service.get_model_info()
print(f"\n当前模型信息: {model_info}")
```

### 模型选择最佳实践

1. **明确任务类型**：根据任务类型（文本、代码、视觉、推理等）选择合适的模型
2. **使用推荐功能**：使用 `recommend_models()` 方法获取推荐
3. **优先使用 "平台-模型" 格式**：避免同名模型混淆
4. **考虑成本**：不同模型的成本不同，根据需求选择
5. **测试不同模型**：对于重要任务，可以尝试多个模型比较效果

### 快速参考表

| 任务类型 | 推荐模型（按优先级） | 提供商 |
|---------|-------------------|--------|
| 文本生成 | `qwen3-max`, `gpt-5`, `claude-3-5-sonnet-20241022` | 百炼/OpenAI/Anthropic |
| 代码生成 | `deepseek-coder`, `qwen3-coder-plus-2025-09-23` | DeepSeek/百炼 |
| 推理分析 | `deepseek-r1`, `o3`, `deepseek-v3.2` | DeepSeek/OpenAI/百炼 |
| 视觉理解 | `qwen3-vl-plus-2025-12-19`, `qwen-vl-max-2025-08-13` | 百炼 |
| 图像生成 | `qwen-image-max-2025-12-30`, `wan2.6-t2i` | 百炼 |
| 视频生成 | `wan2.6-t2v`, `wan2.6-i2v` | 百炼 |
| 语音识别 | `qwen3-asr-flash-2025-09-08`, `fun-asr` | 百炼 |
| 语音合成 | `qwen3-tts-flash-2025-11-27`, `cosyvoice-v3-flash` | 百炼 |
| 搜索 | `sonar-pro`, `gemini-2.5-pro` | Perplexity/Google |

