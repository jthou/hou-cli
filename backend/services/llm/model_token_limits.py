"""
模型 Token 限制配置

参考：https://github.com/taylorwilsdon/llm-context-limits
各模型的最大上下文、最大输出 token 数，用于限制请求与提示用户。
"""
from typing import Optional, Tuple

# 模型 -> (max_context, max_output)
# 支持前缀匹配，如 "deepseek-chat" 匹配 "bailian-deepseek-chat"
MODEL_TOKEN_LIMITS: dict[str, Tuple[int, int]] = {
    # DeepSeek 官方
    "deepseek-chat": (64_000, 8_000),
    "deepseek-coder": (64_000, 8_000),
    "deepseek-reasoner": (64_000, 8_000),
    "deepseek-r1": (64_000, 8_000),
    "deepseek-v2": (64_000, 8_000),
    "deepseek-v2.5": (64_000, 8_000),
    "deepseek-v3": (64_000, 8_000),
    "deepseek-v3.2": (64_000, 8_000),
    # OpenAI / TheTurbo 网关
    "gpt-5": (400_000, 128_000),
    "gpt-5-mini": (400_000, 128_000),
    "gpt-5-nano": (400_000, 128_000),
    "gpt-5.1": (400_000, 128_000),
    "gpt-5.2": (400_000, 128_000),
    "gpt-4.1": (1_047_576, 32_768),
    "gpt-4o": (128_000, 16_384),
    "gpt-4o-mini": (128_000, 16_384),
    "o3": (200_000, 100_000),
    "o3-mini": (200_000, 100_000),
    "o4-mini": (200_000, 100_000),
    # Anthropic Claude
    "claude-opus-4": (200_000, 64_000),
    "claude-sonnet-4": (200_000, 64_000),
    "claude-sonnet-4-5": (200_000, 64_000),
    "claude-3-7-sonnet": (200_000, 8_000),
    "claude-3-5-sonnet": (200_000, 8_000),
    "claude-3-5-haiku": (200_000, 8_000),
    # Google Gemini
    "gemini-2.5-pro": (1_048_000, 64_000),
    "gemini-2.5-flash": (1_048_000, 8_000),
    "gemini-2.0-flash": (1_048_000, 8_000),
    "gemini-3-pro": (1_000_000, 64_000),
    # 百炼 Qwen
    "qwen-turbo": (32_000, 8_000),
    "qwen-plus": (32_000, 8_000),
    "qwen-max": (32_000, 8_000),
    "qwen3-max": (32_000, 8_000),
    "qwen-flash": (32_000, 8_000),
    "qwen3-coder-plus": (32_000, 8_000),
    "qwen3-vl-plus": (32_000, 8_000),
    "qwen-vl-max": (32_000, 8_000),
    # Perplexity
    "sonar": (32_000, 4_000),
    "sonar-pro": (32_000, 4_000),
}

# 默认值（未知模型）
DEFAULT_MAX_CONTEXT = 64_000
DEFAULT_MAX_OUTPUT = 8_000


def get_model_limits(model_name: str) -> Tuple[int, int]:
    """获取模型的最大上下文和最大输出 token 数。支持 'bailian-deepseek-chat' 等前缀格式。"""
    if not model_name:
        return (DEFAULT_MAX_CONTEXT, DEFAULT_MAX_OUTPUT)
    if model_name in MODEL_TOKEN_LIMITS:
        return MODEL_TOKEN_LIMITS[model_name]
    # 后缀匹配：bailian-deepseek-chat -> deepseek-chat
    for key, limits in sorted(MODEL_TOKEN_LIMITS.items(), key=lambda x: -len(x[0])):
        if model_name == key or model_name.endswith("-" + key) or model_name.endswith("_" + key):
            return limits
    return (DEFAULT_MAX_CONTEXT, DEFAULT_MAX_OUTPUT)


def get_effective_max_tokens(model_name: str, requested: int) -> int:
    """取 min(用户请求, 模型上限)"""
    _, max_out = get_model_limits(model_name)
    return min(max(1, requested), max_out)


def estimate_tokens(text: str) -> int:
    """粗略估计 token 数：英文约 4 字符/token，中文约 2 字符/token"""
    if not text:
        return 0
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u303f")
    other = len(text) - cjk
    return (cjk + 1) // 2 + (other + 3) // 4


def estimate_messages_tokens(messages: list) -> int:
    """估计 messages 列表的总 token 数"""
    total = 0
    for m in messages:
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if isinstance(content, str):
            total += estimate_tokens(content) + 4  # role 等开销
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += estimate_tokens(part["text"]) + 4
    return total


TRUNCATION_WARNING = "\n\n⚠️ 输出因达到 token 上限而截断，建议在 .env 中提高 LLM_MAX_TOKENS 或分批提问。"
