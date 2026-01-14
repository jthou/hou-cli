# 多模型支持与模型切换技术实现

## 概述

本项目实现了一套完整的多模型支持与动态切换机制，支持 7 个主流 LLM 提供商，涵盖 200+ 个模型，并提供了智能的模型识别、推荐和切换功能。本文档详细介绍了该系统的设计思路、核心组件和实现细节。

## 架构设计

### 核心组件

系统主要由两个核心组件构成：

1. **ModelRegistry（模型注册表）**：负责模型识别、提供商检测和模型信息管理
2. **LLMService（LLM 服务）**：负责客户端初始化、模型切换和 API 调用

### 支持的提供商

系统目前支持以下 7 个 LLM 提供商：

| 提供商 | 平台类型 | 模型数量 | 主要特点 |
|--------|---------|---------|---------|
| DeepSeek | 官方平台 | 7+ | 代码生成、推理能力强 |
| 百炼平台（阿里云） | 官方平台 | 100+ | 多模态、全场景覆盖 |
| OpenAI | 网关（TheTurbo.ai） | 20+ | GPT-5、O3 系列 |
| Anthropic | 网关（TheTurbo.ai） | 10+ | Claude 系列、推理能力 |
| Google | 网关（TheTurbo.ai） | 8+ | Gemini 系列、多模态 |
| xAI | 网关（TheTurbo.ai） | 4+ | Grok 系列 |
| Perplexity | 网关（TheTurbo.ai） | 3+ | Sonar 搜索引擎 |

## 核心功能实现

### 1. 模型注册表（ModelRegistry）

#### 1.1 模型分类管理

`ModelRegistry` 使用集合和模式匹配两种方式管理模型：

```python
# 精确匹配集合
DEEPSEEK_MODELS = {
    "deepseek-chat",
    "deepseek-coder",
    "deepseek-reasoner",
    # ...
}

# 模式匹配规则
BAILIAN_MODEL_PATTERNS = [
    r"^qwen",      # 通义千问系列
    r"^deepseek",  # DeepSeek 系列（在百炼平台）
    r"^baichuan",  # 百川系列
    # ...
]
```

#### 1.2 模型名称解析

系统支持两种模型命名格式：

**格式 1：平台-模型（推荐）**
```
bailian-deepseek-chat    # 百炼平台的 deepseek-chat
deepseek-deepseek-chat   # DeepSeek 平台的 deepseek-chat
openai-gpt-5             # OpenAI 平台的 gpt-5
```

**格式 2：传统格式（向后兼容）**
```
deepseek-chat           # 自动检测为 DeepSeek 平台
qwen-max                # 自动检测为百炼平台
gpt-5                   # 自动检测为 OpenAI 平台
```

核心解析逻辑：

```python
@classmethod
def parse_model_name(cls, model_name: str) -> Tuple[str, str]:
    """
    解析模型名称，支持 "平台-模型" 格式
    
    Returns:
        (provider, actual_model_name) 元组
    """
    model_lower = model_name.lower().strip()
    
    # 检查是否是 "平台-模型" 格式
    if '-' in model_lower:
        parts = model_lower.split('-', 1)
        prefix = parts[0]
        actual_model = parts[1]
        
        # 验证前缀是否为已知提供商
        if prefix in ["bailian", "deepseek", "openai", ...]:
            return prefix, actual_model
    
    # 如果不是 "平台-模型" 格式，使用自动检测
    provider = cls.detect_provider(model_name)
    return provider, model_name
```

#### 1.3 提供商自动检测

系统通过以下策略自动检测提供商：

1. **精确匹配**：检查模型名称是否在已知模型集合中
2. **模式匹配**：使用正则表达式匹配模型名称模式
3. **版本号判断**：对于同名模型（如 `deepseek-chat`），根据版本号判断平台

```python
@classmethod
def detect_provider(cls, model_name: str) -> str:
    """根据模型名称自动检测提供商"""
    model_lower = model_name.lower().strip()
    
    # 1. 精确匹配
    if model_lower in cls.BAILIAN_MODELS:
        # 特殊处理：deepseek 模型可能在两个平台都存在
        if "deepseek" in model_lower:
            if any(pattern in model_lower for pattern in ["v3.2", "3.2", "v3.1"]):
                return "bailian"  # 百炼平台
            return "deepseek"  # DeepSeek 平台
        return "bailian"
    
    # 2. 模式匹配
    for pattern in cls.BAILIAN_MODEL_PATTERNS:
        if re.match(pattern, model_lower):
            return "bailian"
    
    # 3. 其他提供商检测...
    
    # 默认返回 deepseek
    return "deepseek"
```

#### 1.4 模型名称规范化

某些模型名称需要映射到实际 API 使用的名称：

```python
# 百炼平台 DeepSeek 模型映射
BAILIAN_DEEPSEEK_MODEL_MAP = {
    "deepseek3.2": "deepseek-v3.2",
    "deepseek-3.2": "deepseek-v3.2",
    "deepseek-v3.2-exp": "deepseek-v3.2-exp",
}
```

#### 1.5 模型推荐系统

系统提供基于任务类型的智能推荐功能：

```python
@classmethod
def recommend_models(cls, task_type: str = None, 
                     provider: Optional[str] = None,
                     cost_level: Optional[str] = None) -> List[Dict[str, str]]:
    """
    根据任务类型推荐合适的模型
    
    Args:
        task_type: 任务类型（"text", "code", "vision", "reasoning" 等）
        provider: 指定提供商（可选）
        cost_level: 成本等级过滤（"low", "medium", "high"）
    """
    # 根据任务类型返回推荐模型列表
    # 每个推荐包含：provider, model, description, cost_level
```

支持的任务类型：
- `text` / `chat` / `writing` - 文本生成
- `code` / `programming` - 代码生成
- `reasoning` / `thinking` / `analysis` - 推理分析
- `vision` / `image` / `visual` - 视觉理解
- `image_generation` - 图像生成
- `video` / `video_generation` - 视频生成
- `asr` / `speech_recognition` - 语音识别
- `tts` / `speech_synthesis` - 语音合成
- `search` / `web_search` - 搜索

### 2. LLM 服务（LLMService）

#### 2.1 初始化机制

`LLMService` 支持多种初始化方式：

```python
# 方式 1：使用默认配置
llm_service = LLMService()

# 方式 2：指定初始模型（自动检测提供商）
llm_service = LLMService(model="openai-gpt-5")

# 方式 3：明确指定提供商
llm_service = LLMService(provider="openai")
```

初始化流程：

```python
def __init__(self, temperature: float = 0.7, 
             max_tokens: int = 2000,
             provider: Optional[str] = None,
             model: Optional[str] = None):
    # 1. 如果提供了模型名称，优先根据模型名称检测提供商
    if model and provider is None:
        registry = get_model_registry()
        provider, actual_model = registry.parse_model_name(model)
    
    # 2. 确定使用的提供商
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", self.PROVIDER_DEEPSEEK).lower()
    
    self.provider = provider
    
    # 3. 根据提供商初始化客户端
    if self.provider == self.PROVIDER_BAILIAN:
        self._init_bailian_client()
    elif self.provider == self.PROVIDER_OPENAI:
        self._init_openai_client()
    # ... 其他提供商
    
    # 4. 设置默认模型
    self.model = self.default_model
```

#### 2.2 客户端初始化

每个提供商都有独立的客户端初始化方法：

```python
def _init_bailian_client(self):
    """初始化百炼平台客户端"""
    api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
    if api_key is None:
        raise ValueError("BAILIAN_API_KEY 环境变量未设置")
    
    base_url = os.getenv(
        "BAILIAN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0),
        trust_env=False
    )
    
    self.client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client
    )
```

#### 2.3 动态模型切换

系统支持运行时动态切换模型，如果检测到模型属于不同提供商，会自动切换提供商和客户端：

```python
def set_model(self, model: str, provider: Optional[str] = None):
    """
    动态设置使用的模型（支持 "平台-模型" 格式）
    
    Args:
        model: 模型名称（支持 "平台-模型" 格式）
        provider: 提供商名称（可选，如果不提供则从模型名称解析）
    """
    registry = get_model_registry()
    
    # 解析模型名称（支持 "平台-模型" 格式）
    if provider:
        target_provider = provider.lower()
        actual_model = model
    else:
        target_provider, actual_model = registry.parse_model_name(model)
    
    # 如果检测到的提供商与当前提供商不同，需要切换提供商
    if target_provider != self.provider:
        logger.info(f"检测到模型 {model} 属于 {target_provider} 提供商，"
                   f"当前为 {self.provider}，正在切换...")
        self._switch_provider(target_provider)
    
    # 规范化模型名称
    normalized_model = registry.normalize_model_name(actual_model, self.provider)
    self.model = normalized_model
```

#### 2.4 提供商切换机制

当需要切换提供商时，系统会重新初始化客户端：

```python
def _switch_provider(self, new_provider: str):
    """
    切换提供商（重新初始化客户端）
    
    Args:
        new_provider: 新的提供商名称
    """
    logger.info(f"切换提供商: {self.provider} -> {new_provider}")
    
    # 保存当前模型名称
    current_model = self.model
    
    # 更新提供商
    self.provider = new_provider
    
    # 重新初始化客户端
    if self.provider == self.PROVIDER_BAILIAN:
        self._init_bailian_client()
        self.default_model = os.getenv("BAILIAN_MODEL", "qwen-turbo")
    elif self.provider == self.PROVIDER_OPENAI:
        self._init_openai_client()
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-5")
    # ... 其他提供商
    
    # 恢复模型名称（如果可能）
    if current_model:
        self.model = current_model
    else:
        self.model = self.default_model
```

#### 2.5 思考过程支持检测

系统可以检测模型是否支持思考过程：

```python
@property
def supports_thinking(self) -> bool:
    """检测模型是否支持思考过程"""
    model_lower = self.model.lower()
    
    # DeepSeek R1 模型支持思考过程
    if "r1" in model_lower or "reasoning" in model_lower:
        return True
    
    # OpenAI O3 系列支持思考过程
    if self.provider == self.PROVIDER_OPENAI:
        if model_lower.startswith("o3") or model_lower.startswith("o4"):
            return True
    
    # Anthropic Claude 某些模型支持 reasoning_effort 参数
    if self.provider == self.PROVIDER_ANTHROPIC:
        if "3-7" in model_lower or "opus-4" in model_lower:
            return True
    
    # ... 其他提供商检测
    
    return False
```

## 使用示例

### 基本使用

```python
from backend.services.llm.llm_service import LLMService

# 初始化服务
llm_service = LLMService(model="openai-gpt-5")

# 调用模型
response = await llm_service.chat(
    system_prompt="你是一个有用的助手",
    user_prompt="写一篇关于 AI 的文章"
)
```

### 动态切换模型

```python
# 切换到不同的模型（自动切换提供商）
llm_service.set_model("openai-gpt-5")  # 切换到 OpenAI GPT-5
response1 = await llm_service.chat(user_prompt="写一篇文章")

llm_service.set_model("deepseek-deepseek-coder")  # 切换到 DeepSeek Coder
response2 = await llm_service.chat(user_prompt="写一个 Python 函数")

llm_service.set_model("bailian-qwen3-max")  # 切换到通义千问3 Max
response3 = await llm_service.chat(user_prompt="分析这个复杂问题")
```

### 使用推荐功能

```python
# 根据任务类型推荐模型
code_models = llm_service.recommend_models("code")
print("代码生成推荐模型:")
for model in code_models:
    print(f"  - {model['provider']}-{model['model']}: {model['description']}")

# 选择第一个推荐模型
if code_models:
    best_model = code_models[0]
    model_name = f"{best_model['provider']}-{best_model['model']}"
    llm_service.set_model(model_name)
```

### 查看可用模型

```python
# 查看当前提供商的可用模型
current_models = llm_service.get_available_models()
print(f"当前提供商 ({llm_service.provider}) 的模型: {current_models}")

# 查看所有提供商的模型
all_models = llm_service.list_all_models()
for provider, models in all_models.items():
    print(f"\n{provider.upper()} ({len(models)} 个模型):")
    print(f"  {', '.join(models[:10])}...")

# 查看当前模型信息
model_info = llm_service.get_model_info()
print(f"\n当前模型信息: {model_info}")
```

## 设计亮点

### 1. 灵活的模型命名格式

系统支持两种命名格式，既保证了向后兼容性，又提供了明确的平台指定能力：

- **"平台-模型"格式**：明确指定平台，避免混淆
- **传统格式**：自动检测，简化使用

### 2. 智能提供商检测

通过精确匹配、模式匹配和版本号判断的多层策略，系统能够准确识别模型所属的提供商。

### 3. 自动提供商切换

当切换模型时，如果检测到模型属于不同提供商，系统会自动切换提供商和客户端，用户无需关心底层实现。

### 4. 任务导向的模型推荐

系统提供基于任务类型的智能推荐功能，帮助用户快速选择合适的模型。

### 5. 成本感知

系统维护了模型的成本等级信息，支持根据成本过滤推荐结果。

### 6. 统一的 API 接口

所有提供商都通过统一的 `LLMService` 接口访问，使用方式完全一致，降低了使用复杂度。

## 配置管理

### 环境变量配置

系统通过环境变量管理各提供商的配置：

```bash
# 提供商选择（可选）
LLM_PROVIDER=openai

# DeepSeek 配置
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat

# 百炼平台配置
BAILIAN_API_KEY=sk-xxx
BAILIAN_MODEL=qwen-turbo

# OpenAI 配置（通过 TheTurbo.ai 网关）
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-5
OPENAI_BASE_URL=https://gateway.theturbo.ai/v1

# Anthropic 配置（通过 TheTurbo.ai 网关）
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Google 配置（通过 TheTurbo.ai 网关）
GOOGLE_API_KEY=sk-xxx
GOOGLE_MODEL=gemini-2.5-flash

# xAI 配置（通过 TheTurbo.ai 网关）
XAI_API_KEY=sk-xxx
XAI_MODEL=grok-4

# Perplexity 配置（通过 TheTurbo.ai 网关）
PERPLEXITY_API_KEY=sk-xxx
PERPLEXITY_MODEL=sonar
```

## 扩展性设计

### 添加新提供商

要添加新的提供商，需要：

1. **在 ModelRegistry 中添加模型集合和模式**：
```python
NEW_PROVIDER_MODELS = {
    "model-1",
    "model-2",
    # ...
}

NEW_PROVIDER_MODEL_PATTERNS = [
    r"^model-",
    # ...
]
```

2. **在 LLMService 中添加客户端初始化方法**：
```python
def _init_new_provider_client(self):
    """初始化新提供商客户端"""
    api_key = os.environ.get('NEW_PROVIDER_API_KEY')
    # ... 初始化逻辑
```

3. **更新相关方法**：
   - `detect_provider()` - 添加检测逻辑
   - `_switch_provider()` - 添加切换逻辑
   - `recommend_models()` - 添加推荐逻辑

### 添加新模型

只需在对应的模型集合中添加模型名称即可：

```python
DEEPSEEK_MODELS = {
    "deepseek-chat",
    "deepseek-coder",
    "deepseek-new-model",  # 新模型
}
```

## 最佳实践

### 1. 使用 "平台-模型" 格式

对于可能混淆的模型，建议使用 "平台-模型" 格式：

```python
# ✅ 推荐
llm_service.set_model("bailian-deepseek-chat")
llm_service.set_model("deepseek-deepseek-chat")

# ❌ 不推荐（可能混淆）
llm_service.set_model("deepseek-chat")
```

### 2. 根据任务类型选择模型

使用推荐功能选择合适的模型：

```python
# ✅ 推荐
recommendations = llm_service.recommend_models("code")
if recommendations:
    best_model = recommendations[0]
    llm_service.set_model(f"{best_model['provider']}-{best_model['model']}")

# ❌ 不推荐（硬编码）
llm_service.set_model("deepseek-deepseek-chat")  # 可能不适合代码任务
```

### 3. 考虑成本和性能

根据任务复杂度选择合适的模型：

```python
# 简单任务：使用低成本模型
llm_service.set_model("bailian-qwen-turbo")

# 复杂任务：使用高性能模型
llm_service.set_model("openai-gpt-5")
```

## 总结

本项目实现了一套完整、灵活、易用的多模型支持与切换系统，具有以下特点：

1. **支持 7 个主流提供商，200+ 个模型**
2. **智能的模型识别和提供商检测**
3. **自动的提供商切换机制**
4. **任务导向的模型推荐**
5. **统一的 API 接口**
6. **良好的扩展性**

该系统为项目提供了强大的模型管理能力，使得开发者可以轻松地在不同模型之间切换，根据任务需求选择最合适的模型。

