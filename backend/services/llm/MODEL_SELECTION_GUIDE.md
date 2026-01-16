# 模型选择和切换指南

## 目录

1. [快速开始](#快速开始)
2. [模型推荐功能](#模型推荐功能)
3. [按任务类型选择模型](#按任务类型选择模型)
4. [动态切换模型](#动态切换模型)
5. [查看可用模型](#查看可用模型)
6. [最佳实践](#最佳实践)

## 快速开始

### 1. 初始化并选择模型

```python
from backend.services.llm.llm_service import LLMService

# 方式 1：初始化时指定模型（推荐）
llm_service = LLMService(model="gpt-5")  # 自动识别为 theturbogateway

# 方式 2：使用默认模型，然后切换
llm_service = LLMService()
llm_service.set_model("gpt-5")  # 自动识别为 theturbogateway
```

### 2. 使用推荐功能选择模型

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 获取代码生成任务的推荐模型
code_models = llm_service.recommend_models("code")
print("代码生成推荐模型:")
for model in code_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")

# 选择第一个推荐模型
if code_models:
    best_model = code_models[0]
    model_name = f"{best_model['provider']}-{best_model['model']}"
    llm_service.set_model(model_name)
    print(f"已切换到: {model_name}")
```

## 模型推荐功能

### 基本用法

```python
# 根据任务类型推荐模型
recommendations = llm_service.recommend_models("code")

# 指定提供商推荐
recommendations = llm_service.recommend_models("reasoning", provider="theturbogateway")

# 获取所有推荐（不指定任务类型）
all_recommendations = llm_service.recommend_models()
```

### 支持的任务类型

- `"text"` / `"chat"` / `"writing"` - 文本生成
- `"code"` / `"programming"` - 代码生成
- `"reasoning"` / `"thinking"` / `"analysis"` - 推理分析
- `"vision"` / `"image"` / `"visual"` - 视觉理解
- `"image_generation"` / `"image_gen"` - 图像生成
- `"video"` / `"video_generation"` - 视频生成
- `"asr"` / `"speech_recognition"` - 语音识别
- `"tts"` / `"speech_synthesis"` - 语音合成
- `"search"` / `"web_search"` - 搜索

## 按任务类型选择模型

### 文本生成任务

**推荐模型：**
- `gpt-5` - OpenAI GPT-5（通过 TheTurbo.ai 网关），强大的文本生成能力
- `bailian-qwen3-max` - 通义千问3 Max，适配复杂智能体场景
- `bailian-qwen-plus-2025-12-01` - 通义千问 Plus，支持思考模式融合
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet（通过 TheTurbo.ai 网关）

```python
llm_service.set_model("gpt-5")  # 自动识别为 theturbogateway
# 或
llm_service.set_model("bailian-qwen3-max")
```

### 代码生成任务

**推荐模型：**
- `deepseek-deepseek-coder` - DeepSeek Coder，专为代码生成优化
- `bailian-qwen3-coder-plus-2025-09-23` - 通义千问3 Coder Plus
- `bailian-qwen3-coder-flash` - 通义千问3 Coder Flash

```python
llm_service.set_model("deepseek-deepseek-coder")
# 或
llm_service.set_model("bailian-qwen3-coder-plus-2025-09-23")
```

### 推理分析任务

**推荐模型：**
- `deepseek-deepseek-r1` - DeepSeek R1，支持思考过程
- `o3` - OpenAI O3（通过 TheTurbo.ai 网关），支持思考过程
- `bailian-deepseek-v3.2` - DeepSeek V3.2，支持深度思考
- `bailian-qwq-plus` - 通义千问 QwQ Plus

```python
llm_service.set_model("deepseek-deepseek-r1")
# 或
llm_service.set_model("o3")  # 自动识别为 theturbogateway
```

### 视觉理解任务

**推荐模型：**
- `bailian-qwen3-vl-plus-2025-12-19` - 通义千问3 VL Plus
- `bailian-qwen-vl-max-2025-08-13` - 通义千问 VL Max
- `gemini-2.5-pro` - Gemini 2.5 Pro（通过 TheTurbo.ai 网关）

```python
llm_service.set_model("bailian-qwen3-vl-plus-2025-12-19")
```

### 图像生成任务

**推荐模型：**
- `bailian-qwen-image-max-2025-12-30` - 通义千问 Image Max
- `bailian-wan2.6-t2i` - 通义万相 文生图

```python
llm_service.set_model("bailian-qwen-image-max-2025-12-30")
```

### 视频生成任务

**推荐模型：**
- `bailian-wan2.6-t2v` - 通义万相 文生视频
- `bailian-wan2.6-i2v` - 通义万相 图生视频
- `bailian-wan2.6-r2v` - 通义万相 参考生视频

```python
llm_service.set_model("bailian-wan2.6-t2v")
```

### 搜索任务

**推荐模型：**
- `sonar-pro` - Perplexity Sonar Pro（通过 TheTurbo.ai 网关）
- `gemini-2.5-pro` - Gemini 2.5 Pro（通过 TheTurbo.ai 网关，支持 Google Search）

```python
llm_service.set_model("sonar-pro")  # 自动识别为 theturbogateway
```

## 动态切换模型

### 方式 1：直接切换（推荐）

```python
from backend.services.llm.llm_service import LLMService

llm_service = LLMService()

# 切换到不同的模型（自动切换提供商）
llm_service.set_model("gpt-5")  # 切换到 TheTurbo.ai 网关的 GPT-5
response1 = await llm_service.chat(user_prompt="写一篇文章")

llm_service.set_model("deepseek-deepseek-coder")  # 切换到 DeepSeek Coder
response2 = await llm_service.chat(user_prompt="写一个 Python 函数")

llm_service.set_model("bailian-qwen3-max")  # 切换到通义千问3 Max
response3 = await llm_service.chat(user_prompt="分析这个复杂问题")
```

### 方式 2：根据任务类型智能切换

```python
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

# 使用示例
switch_model_for_task(llm_service, "code")      # 代码任务
switch_model_for_task(llm_service, "reasoning") # 推理任务
switch_model_for_task(llm_service, "vision")     # 视觉任务
```

### 方式 3：在同一会话中切换

```python
# 开始使用文本生成模型
llm_service.set_model("gpt-5")  # 自动识别为 theturbogateway
response1 = await llm_service.chat(user_prompt="写一篇文章")

# 切换到代码生成模型
llm_service.set_model("deepseek-deepseek-coder")
response2 = await llm_service.chat(user_prompt="写一个 Python 函数")

# 切换到推理模型
llm_service.set_model("deepseek-deepseek-r1")
response3 = await llm_service.chat(user_prompt="分析这个复杂问题")
```

## 查看可用模型

### 查看当前提供商的模型

```python
# 查看当前提供商的可用模型
current_models = llm_service.get_available_models()
print(f"当前提供商 ({llm_service.provider}) 的模型:")
for model in current_models[:10]:  # 显示前10个
    print(f"  - {model}")
```

### 查看所有提供商的模型

```python
# 查看所有提供商的模型
all_models = llm_service.list_all_models()
for provider, models in all_models.items():
    print(f"\n{provider.upper()} ({len(models)} 个模型):")
    print(f"  {', '.join(models[:10])}...")  # 显示前10个
```

### 查看当前模型信息

```python
# 查看当前模型信息
model_info = llm_service.get_model_info()
print(f"当前模型: {model_info['original_name']}")
print(f"提供商: {model_info['provider']}")
print(f"规范化名称: {model_info['normalized_name']}")
print(f"是否可用: {model_info['is_available']}")
```

## 最佳实践

### 1. 明确任务类型

根据任务类型选择合适的模型：

```python
# ✅ 好：明确指定任务类型
if task == "代码生成":
    llm_service.set_model("deepseek-deepseek-coder")
elif task == "推理分析":
    llm_service.set_model("deepseek-deepseek-r1")
elif task == "视觉理解":
    llm_service.set_model("bailian-qwen3-vl-plus-2025-12-19")

# ❌ 不好：总是使用同一个模型
llm_service.set_model("deepseek-deepseek-chat")  # 不适合所有任务
```

### 2. 使用推荐功能

利用系统提供的推荐功能：

```python
# ✅ 好：使用推荐功能
recommendations = llm_service.recommend_models("code")
if recommendations:
    best_model = recommendations[0]
    llm_service.set_model(f"{best_model['provider']}-{best_model['model']}")

# ❌ 不好：硬编码模型名称
llm_service.set_model("deepseek-deepseek-coder")  # 可能不是最佳选择
```

### 3. 优先使用 "平台-模型" 格式

避免同名模型混淆：

```python
# ✅ 好：明确指定平台
llm_service.set_model("bailian-deepseek-chat")   # 百炼平台
llm_service.set_model("deepseek-deepseek-chat")  # DeepSeek 平台

# ❌ 不好：可能混淆
llm_service.set_model("deepseek-chat")  # 不确定是哪个平台
```

### 4. 考虑成本和性能

不同模型的成本和性能不同：

```python
# 低成本模型（适合简单任务）
llm_service.set_model("bailian-qwen-turbo")
llm_service.set_model("gemini-2.5-flash")  # 自动识别为 theturbogateway

# 高性能模型（适合复杂任务）
llm_service.set_model("openai-gpt-5")
llm_service.set_model("bailian-qwen3-max")
llm_service.set_model("claude-opus-4-20250514")  # 自动识别为 theturbogateway
```

### 5. 测试不同模型

对于重要任务，可以尝试多个模型：

```python
async def try_multiple_models(task: str):
    """尝试多个模型，选择最佳结果"""
    models_to_try = [
        "gpt-5",
        "bailian-qwen3-max",
        "claude-3-5-sonnet-20241022",
    ]
    
    results = []
    for model_name in models_to_try:
        llm_service.set_model(model_name)
        response = await llm_service.chat(user_prompt=task)
        results.append({
            "model": model_name,
            "response": response
        })
    
    # 选择最佳结果
    return results
```

## 快速参考表

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

## 常见问题

### Q: 如何知道应该使用哪个模型？

A: 使用 `recommend_models()` 方法，根据任务类型获取推荐：

```python
recommendations = llm_service.recommend_models("code")
```

### Q: 切换模型会影响之前的对话吗？

A: 不会。每次调用 `set_model()` 只是切换模型，不会清除对话历史。如果需要新的对话，需要重新初始化 `LLMService` 或使用新的 `messages` 列表。

### Q: 可以在同一个任务中使用多个模型吗？

A: 可以。你可以在不同的步骤中使用不同的模型：

```python
# 步骤1：使用文本生成模型
llm_service.set_model("openai-gpt-5")
outline = await llm_service.chat(user_prompt="生成文章大纲")

# 步骤2：使用代码生成模型
llm_service.set_model("deepseek-deepseek-coder")
code = await llm_service.chat(user_prompt="生成示例代码")
```

### Q: 如何查看所有可用的模型？

A: 使用 `list_all_models()` 方法：

```python
all_models = llm_service.list_all_models()
for provider, models in all_models.items():
    print(f"{provider}: {len(models)} 个模型")
```



