"""模型注册表 - 管理不同提供商的模型"""
import logging
import re
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class ModelRegistry:
    """模型注册表，用于识别模型所属的提供商"""
    
    # DeepSeek 平台模型（在 DeepSeek 官方平台）
    DEEPSEEK_MODELS = {
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-reasoner",
        "deepseek-r1",
        "deepseek-v2",
        "deepseek-v2.5",
        "deepseek-v3",
    }
    
    # OpenAI 模型（通过 TheTurbo.ai 网关）
    OPENAI_MODELS = {
        # GPT-4o 系列
        "gpt-4o",
        "gpt-4o-mini",
        "chatgpt-4o-latest",
        # O1 系列
        "o1-preview",  # 预览版，支持链式思考
        # O3 系列
        "o3",
        "o3-mini",
        "o3-mini-2025-01-31",  # 日期快照版本
        # GPT-4.1 系列
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # O4 系列
        "o4-mini",
        # GPT-5 系列
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5-codex",
        # GPT-5.1 系列
        "gpt-5.1",
        "gpt-5.1-chat-latest",
        "gpt-5.1-codex",
        "gpt-5.1-codex-mini",
        "gpt-5.1-codex-max",
        # GPT-5.2 系列
        "gpt-5.2",
    }
    
    # Anthropic Claude 模型（通过 TheTurbo.ai 网关）
    ANTHROPIC_MODELS = {
        # Claude 3.5 系列
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022",
        # Claude 3.7 系列
        "claude-3-7-sonnet-20250219",  # 支持 reasoning_effort 参数
        # Claude Opus 4 系列
        "claude-opus-4-20250514",  # 支持 reasoning_effort 参数
        "claude-opus-4-1-20250805",  # 支持 reasoning_effort 参数
        "claude-opus-4-5-20251101",  # 支持 reasoning_effort 参数
        # Claude Sonnet 4 系列
        "claude-sonnet-4-20250514",  # 支持 reasoning_effort 参数
        "claude-sonnet-4-5-20250929",  # 支持 reasoning_effort 参数
        # Claude Haiku 4 系列
        "claude-haiku-4-5-20251001",  # 支持 reasoning_effort 参数
    }
    
    # Google Gemini 模型（通过 TheTurbo.ai 网关）
    GOOGLE_MODELS = {
        # Gemini 2.0 系列
        "gemini-2.0-flash",
        # Gemini 2.5 系列
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-image",  # 多模态图像模型（高速轻量）
        "gemini-2.5-flash-thinking",  # 输出思考过程
        "gemini-2.5-pro-thinking",  # 输出思考过程
        # Gemini 3 系列
        "gemini-3-pro-preview",
        "gemini-3-pro-image-preview",  # 多模态图像模型（高精度细节）
    }
    
    # Perplexity Sonar 模型（通过 TheTurbo.ai 网关）
    PERPLEXITY_MODELS = {
        # Sonar 系列
        "sonar",
        "sonar-pro",
        "sonar-reasoning-pro",  # 支持推理
    }
    
    # 百炼平台模型（包括 DeepSeek 系列在百炼平台上的版本）
    BAILIAN_MODELS = {
        # 通义千问3 系列（文本生成）
        "qwen3-max",
        "qwen-plus-2025-12-01",
        "qwen-flash",
        "qwen-max-2025-01-25",
        "qwen-turbo-latest",
        "qwen-deep-research",
        # 通义千问3 代码系列
        "qwen3-coder-plus-2025-09-23",
        "qwen3-coder-flash",
        "qwen3-coder-480b-a35b-instruct",
        "qwen3-coder-30b-a3b-instruct",
        # 通义千问3 视觉理解系列
        "qwen3-vl-plus-2025-12-19",
        "qwen3-vl-flash-2025-10-15",
        "qwen3-vl-32b-thinking",
        # 通义千问 VL 系列
        "qwen-vl-max-2025-08-13",
        "qwen-vl-plus-latest",
        # 通义千问3 全模态系列
        "qwen3-omni-flash-2025-12-01",
        "qwen3-omni-flash-realtime-2025-12-01",
        "qwen3-omni-30b-a3b-captioner",
        # 通义千问 Omni 系列
        "qwen-omni-turbo-2025-03-26",
        "qwen-omni-turbo-realtime-2025-05-08",
        # 通义千问3 语音识别系列
        "qwen3-asr-flash-2025-09-08",
        "qwen3-asr-flash-realtime-2025-10-27",
        "qwen3-asr-flash-filetrans-2025-11-17",
        # 通义千问3 语音合成系列
        "qwen3-tts-flash-2025-11-27",
        "qwen3-tts-flash-realtime-2025-11-27",
        "qwen3-tts-vc-realtime-2025-11-27",
        "qwen3-tts-vd-realtime-2025-12-16",
        # 通义千问 TTS 系列
        "qwen-tts-2025-05-22",
        "qwen-tts-realtime-2025-07-15",
        "qwen-voice-enrollment",
        # 通义千问3 翻译系列
        "qwen3-livetranslate-flash",
        "qwen3-livetranslate-flash-realtime",
        # 通义千问 MT 系列
        "qwen-mt-plus",
        "qwen-mt-flash",
        "qwen-mt-turbo",
        "qwen-mt-lite",
        "qwen-mt-image",
        # 通义千问 图像生成系列（官方模型列表，时间：2025-03）
        "qwen-image-2.0",
        "qwen-image-2.0-pro",
        "qwen-image-max",
        "qwen-image-plus",
        "qwen-image-edit-max",
        "qwen-image-edit-plus",
        "qwen-image-max-2025-12-30",
        "qwen-image-plus-2026-01-09",
        "qwen-image-edit-plus-2025-12-15",
        # 通义万相 / 其他图像模型
        "z-image-turbo",
        "wan-t2i",
        "ai试衣-plus版",  # AI试衣-Plus版
        "ai试衣-基础版",  # AI试衣-基础版
        "flux-schnell",
        "flux-dev",
        "flux-merged",
        # 通义万相系列
        "wan2.6-t2v",  # 文生视频
        "wan2.6-i2v",  # 图生视频
        "wan2.6-r2v",  # 参考生视频
        "wan2.6-t2i",  # 文生图
        "wan2.6-image",  # 图像生成
        # 通义千问 推理系列
        "qwq-plus",
        "qvq-max-latest",
        "qvq-plus-latest",
        # 通义千问2.5 开源系列
        "qwen2.5-omni-7b",
        # 通义千问 传统系列（向后兼容）
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        "qwen-max-longcontext",
        "qwen-max-0403",
        "qwen-max-0107",
        "qwen-max-1201",
        "qwen-7b-chat",
        "qwen-14b-chat",
        "qwen-72b-chat",
        "qwen-1.8b-chat",
        "qwen-32b-chat",
        # DeepSeek 系列（在百炼平台上）
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-reasoner",
        "deepseek-r1",
        "deepseek-v2",
        "deepseek-v2.5",
        "deepseek-v3",
        "deepseek-v3.2",
        "deepseek-v3.2-exp",
        "deepseek-v3.1",
        "deepseek3.2",  # 简化名称
        "deepseek-3.2",  # 带连字符
        # GLM 系列
        "glm-4.7",
        # Kimi 系列
        "kimi-k2-thinking",
        # 其他百炼平台模型
        "baichuan2-turbo",
        "baichuan2-13b-chat",
        "chatglm3-6b",
        "chatglm3-32k",
        "llama2-7b-chat",
        "llama2-13b-chat",
        "llama2-70b-chat",
        # Fun-ASR 系列
        "fun-asr",
        "fun-asr-realtime-2025-11-07",
        # 其他模型
        "z-image-turbo",
        "tongyi-embedding-vision-flash",
        "cosyvoice-v3-flash",
        "aitryon-plus",
    }
    
    # 模型名称模式匹配（用于识别模型）
    BAILIAN_MODEL_PATTERNS = [
        r"^qwen",  # 通义千问系列（包括 qwen-turbo, qwen-plus 等）
        r"^deepseek",  # DeepSeek 系列（在百炼平台，包括 deepseek3.2）
        r"^baichuan",  # 百川系列
        r"^chatglm",  # ChatGLM 系列
        r"^llama",  # LLaMA 系列
    ]
    
    # OpenAI 模型名称模式匹配
    OPENAI_MODEL_PATTERNS = [
        r"^gpt-",  # GPT 系列（包括 gpt-4o, gpt-5 等）
        r"^o\d",  # O 系列（包括 o3, o3-mini, o4-mini 等）
        r"^chatgpt-",  # ChatGPT 系列
    ]
    
    # Anthropic Claude 模型名称模式匹配
    ANTHROPIC_MODEL_PATTERNS = [
        r"^claude-",  # Claude 系列（包括 claude-3-5-haiku, claude-opus-4 等）
    ]
    
    # Google Gemini 模型名称模式匹配
    GOOGLE_MODEL_PATTERNS = [
        r"^gemini-",  # Gemini 系列（包括 gemini-2.5-flash, gemini-3-pro 等）
    ]
    
    # Perplexity Sonar 模型名称模式匹配
    PERPLEXITY_MODEL_PATTERNS = [
        r"^sonar",  # Sonar 系列（包括 sonar, sonar-pro, sonar-reasoning-pro）
    ]
    
    # 百炼平台 DeepSeek 模型映射（用户友好名称 -> 实际 API 使用的名称）
    # 注意：根据实际百炼平台 API 文档调整
    BAILIAN_DEEPSEEK_MODEL_MAP = {
        "deepseek3.2": "deepseek-v3.2",  # 简化名称映射到完整名称
        "deepseek-3.2": "deepseek-v3.2",
        "deepseek-v3.2-exp": "deepseek-v3.2-exp",  # 实验版本保持原样
    }
    
    @classmethod
    def parse_model_name(cls, model_name: str) -> Tuple[str, str]:
        """
        解析模型名称，支持 "平台-模型" 格式
        
        Args:
            model_name: 模型名称（支持 "平台-模型" 格式，如 "bailian-deepseek-chat"）
            
        Returns:
            (provider, actual_model_name) 元组
            
        示例:
            parse_model_name("bailian-deepseek-chat") -> ("bailian", "deepseek-chat")
            parse_model_name("deepseek-deepseek-chat") -> ("deepseek", "deepseek-chat")
            parse_model_name("deepseek-chat") -> ("deepseek", "deepseek-chat")  # 自动检测
        """
        model_lower = model_name.lower().strip()
        
        # 检查是否是 "平台-模型" 格式
        # 格式：平台名称必须是 "bailian" 或 "deepseek"，且后面必须跟着一个有效的模型名称
        if '-' in model_lower:
            parts = model_lower.split('-', 1)
            prefix = parts[0]
            actual_model = parts[1]
            
            # 检查前缀是否是已知的提供商
            if prefix in ["bailian", "deepseek", "openai", "anthropic", "google", "perplexity", "theturbogateway"]:
                # 进一步验证：剩余部分应该看起来像一个模型名称
                # 如果剩余部分太短（少于3个字符）或只是单个单词，可能不是 "平台-模型" 格式
                # 例如："deepseek-chat" 不应该被解析为 ("deepseek", "chat")
                # 但 "bailian-deepseek-chat" 应该被解析为 ("bailian", "deepseek-chat")
                
                # 如果前缀是 "bailian" 或 "theturbogateway"，总是认为是 "平台-模型" 格式
                if prefix in ["bailian", "theturbogateway"]:
                    logger.info(f"解析模型名称: {model_name} -> 提供商: {prefix}, 模型: {actual_model}")
                    return prefix, actual_model
                
                # 如果前缀是 "openai"、"anthropic"、"google"、"perplexity"，统一映射为 "theturbogateway"
                if prefix in ["openai", "anthropic", "google", "perplexity"]:
                    logger.info(f"解析模型名称: {model_name} -> 提供商: theturbogateway (原服务: {prefix}), 模型: {actual_model}")
                    return "theturbogateway", actual_model
                
                # 如果前缀是 "deepseek"，需要更谨慎
                # 只有当剩余部分看起来像是一个完整的模型名称时才认为是 "平台-模型" 格式
                # 例如："deepseek-deepseek-chat" -> ("deepseek", "deepseek-chat")
                # 但 "deepseek-chat" -> 自动检测（不是 "平台-模型" 格式）
                if prefix == "deepseek":
                    # 如果剩余部分以 "deepseek" 开头，认为是 "平台-模型" 格式
                    # 例如："deepseek-deepseek-chat"
                    if actual_model.startswith("deepseek") or actual_model.startswith("qwen") or \
                       actual_model.startswith("baichuan") or actual_model.startswith("chatglm") or \
                       actual_model.startswith("llama") or actual_model.startswith("gpt") or \
                       actual_model.startswith("o") or actual_model.startswith("chatgpt") or \
                       actual_model.startswith("claude") or actual_model.startswith("gemini") or \
                       actual_model.startswith("sonar"):
                        logger.info(f"解析模型名称: {model_name} -> 提供商: {prefix}, 模型: {actual_model}")
                        return prefix, actual_model
        
        # 如果不是 "平台-模型" 格式，使用自动检测（向后兼容）
        provider = cls.detect_provider(model_name)
        return provider, model_name
    
    @classmethod
    def detect_provider(cls, model_name: str) -> str:
        """
        根据模型名称自动检测提供商（向后兼容，用于非 "平台-模型" 格式）
        
        Args:
            model_name: 模型名称
            
        Returns:
            提供商名称 ("deepseek", "bailian", 或 "theturbogateway")
        """
        model_lower = model_name.lower().strip()
        
        # 检查是否是明确的百炼平台模型
        if model_lower in cls.BAILIAN_MODELS:
            # 特殊处理：deepseek 模型可能在两个平台都存在
            # DeepSeek 平台仅有无版本号模型（chat/coder/reasoner）
            # 带版本号的（r1, v2, v2.5, v3, v3.2 等）均为百炼平台
            if "deepseek" in model_lower:
                if any(
                    pattern in model_lower
                    for pattern in ["-r1", "-v2", "-v2.5", "-v3", "v3.2", "3.2", "v3.1", "3.1", "-exp"]
                ):
                    return "bailian"
                # deepseek-chat, deepseek-coder, deepseek-reasoner 无版本号 -> DeepSeek 平台
                return "deepseek"
            return "bailian"
        
        # 使用模式匹配
        for pattern in cls.BAILIAN_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "bailian"
        
        # 检查是否是 TheTurbo.ai 网关服务模型（统一返回 theturbogateway）
        # OpenAI 模型
        if model_lower in cls.OPENAI_MODELS:
            return "theturbogateway"
        
        # 使用 OpenAI 模型模式匹配
        for pattern in cls.OPENAI_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "theturbogateway"
        
        # Anthropic Claude 模型
        if model_lower in cls.ANTHROPIC_MODELS:
            return "theturbogateway"
        
        # 使用 Anthropic Claude 模型模式匹配
        for pattern in cls.ANTHROPIC_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "theturbogateway"
        
        # Google Gemini 模型
        if model_lower in cls.GOOGLE_MODELS:
            return "theturbogateway"
        
        # 使用 Google Gemini 模型模式匹配
        for pattern in cls.GOOGLE_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "theturbogateway"
        
        # Perplexity Sonar 模型
        if model_lower in cls.PERPLEXITY_MODELS:
            return "theturbogateway"
        
        # 使用 Perplexity Sonar 模型模式匹配
        for pattern in cls.PERPLEXITY_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "theturbogateway"
        
        # 检查是否是 DeepSeek 模型（在 DeepSeek 平台上）
        if model_lower in cls.DEEPSEEK_MODELS:
            return "deepseek"
        
        # 时间：2026-03-21；理由：默认栈为百炼 Qwen；方法：未知模型名时走 bailian（须为有效 dashscope 模型名）
        logger.warning(f"无法识别模型 {model_name} 的提供商，默认使用 bailian")
        return "bailian"
    
    @classmethod
    def detect_turbogateway_service(cls, model_name: str) -> Optional[str]:
        """
        检测模型是否属于 TheTurbo.ai 网关，并返回服务类型
        
        Args:
            model_name: 模型名称
            
        Returns:
            服务类型（"openai"/"anthropic"/"google"/"perplexity"）或 None
            如果模型不属于 TheTurbo.ai 网关，返回 None
        """
        model_lower = model_name.lower().strip()
        
        # 检查是否是 OpenAI 模型
        if model_lower in cls.OPENAI_MODELS:
            return "openai"
        
        for pattern in cls.OPENAI_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "openai"
        
        # 检查是否是 Anthropic 模型
        if model_lower in cls.ANTHROPIC_MODELS:
            return "anthropic"
        
        for pattern in cls.ANTHROPIC_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "anthropic"
        
        # 检查是否是 Google 模型
        if model_lower in cls.GOOGLE_MODELS:
            return "google"
        
        for pattern in cls.GOOGLE_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "google"
        
        # 检查是否是 Perplexity 模型
        if model_lower in cls.PERPLEXITY_MODELS:
            return "perplexity"
        
        for pattern in cls.PERPLEXITY_MODEL_PATTERNS:
            if re.match(pattern, model_lower):
                return "perplexity"
        
        return None
    
    @classmethod
    def normalize_model_name(cls, model_name: str, provider: str) -> str:
        """
        规范化模型名称（根据提供商）
        
        Args:
            model_name: 原始模型名称
            provider: 提供商名称
            
        Returns:
            规范化后的模型名称
        """
        model_lower = model_name.lower().strip()
        
        if provider == "bailian":
            # 百炼平台的模型名称规范化
            # 检查是否有映射
            if model_lower in cls.BAILIAN_DEEPSEEK_MODEL_MAP:
                mapped_name = cls.BAILIAN_DEEPSEEK_MODEL_MAP[model_lower]
                logger.info(f"模型名称映射: {model_name} -> {mapped_name} (百炼平台)")
                return mapped_name
            
            # 特殊处理：百炼平台上可能没有某些基础模型名称，需要映射到实际可用的版本
            # deepseek-chat 在百炼平台上可能不存在，使用 deepseek-v3.2 作为替代
            if model_lower == "deepseek-chat":
                logger.warning("百炼平台上可能没有 deepseek-chat 模型，映射到 deepseek-v3.2")
                return "deepseek-v3.2"
            
            # 如果没有映射，直接返回原名称（百炼平台通常直接使用模型名称）
            return model_name
        
        if provider == "theturbogateway":
            # TheTurbo.ai 网关：保持原名称
            return model_name
        
        # DeepSeek 平台：保持原名称
        return model_name
    
    @classmethod
    def get_available_models(cls, provider: str) -> List[str]:
        """
        获取指定提供商可用的模型列表
        
        Args:
            provider: 提供商名称
            
        Returns:
            模型名称列表
        """
        if provider == "bailian":
            return sorted(list(cls.BAILIAN_MODELS))
        elif provider == "deepseek":
            return sorted(list(cls.DEEPSEEK_MODELS))
        elif provider == "theturbogateway":
            # TheTurbo.ai 网关包含所有服务类型的模型
            all_models = set()
            all_models.update(cls.OPENAI_MODELS)
            all_models.update(cls.ANTHROPIC_MODELS)
            all_models.update(cls.GOOGLE_MODELS)
            all_models.update(cls.PERPLEXITY_MODELS)
            return sorted(list(all_models))
        else:
            return []
    
    @classmethod
    def list_all_models(cls) -> Dict[str, List[str]]:
        """
        列出所有提供商的所有模型
        
        Returns:
            字典，键为提供商名称，值为模型列表
        """
        return {
            "deepseek": cls.get_available_models("deepseek"),
            "bailian": cls.get_available_models("bailian"),
            "theturbogateway": cls.get_available_models("theturbogateway"),
        }
    
    # 模型成本等级（相对成本，用于成本感知推荐）
    # 成本等级：low（低成本）, medium（中等成本）, high（高成本）
    MODEL_COST_LEVELS = {
        # DeepSeek 平台（通常成本较低）
        "deepseek-chat": "low",
        "deepseek-coder": "low",
        "deepseek-reasoner": "medium",
        "deepseek-r1": "medium",
        "deepseek-v2": "low",
        "deepseek-v2.5": "low",
        "deepseek-v3": "low",
        # OpenAI 平台（成本较高）
        "gpt-4o": "medium",
        "gpt-4o-mini": "low",
        "gpt-5": "high",
        "gpt-5-mini": "medium",
        "gpt-5-nano": "low",
        "o3": "high",
        "o3-mini": "medium",
        # Anthropic 平台（成本较高）
        "claude-3-5-haiku-20241022": "low",
        "claude-3-5-sonnet-20241022": "medium",
        "claude-3-7-sonnet-20250219": "high",
        "claude-opus-4-20250514": "high",
        "claude-sonnet-4-20250514": "high",
        # Google 平台（成本中等）
        "gemini-2.0-flash": "low",
        "gemini-2.5-flash": "low",
        "gemini-2.5-pro": "medium",
        "gemini-2.5-flash-thinking": "medium",
        "gemini-2.5-pro-thinking": "high",
        # Perplexity 平台（成本中等）
        "sonar": "low",
        "sonar-pro": "medium",
        "sonar-reasoning-pro": "high",
        # 百炼平台（成本差异较大）
        "qwen-turbo": "low",
        "qwen-turbo-latest": "low",
        "qwen-flash": "low",
        "qwen-plus": "medium",
        "qwen-plus-2025-12-01": "medium",
        "qwen-max": "high",
        "qwen-max-2025-01-25": "high",
        "qwen3-max": "high",
        "qwen3-coder-flash": "low",
        "qwen3-coder-plus-2025-09-23": "medium",
        "qwen3-vl-flash-2025-10-15": "medium",
        "qwen3-vl-plus-2025-12-19": "high",
        "qwen-vl-max-2025-08-13": "high",
        "deepseek-v3.2": "medium",
        "qwq-plus": "high",
        "qwen-image-max-2025-12-30": "high",
        "qwen-image-plus-2026-01-09": "medium",
        "wan2.6-t2v": "high",
        "wan2.6-i2v": "high",
        "wan2.6-t2i": "medium",
    }
    
    @classmethod
    def get_model_cost_level(cls, provider: str, model: str) -> str:
        """
        获取模型的成本等级
        
        Args:
            provider: 提供商名称
            model: 模型名称
            
        Returns:
            成本等级：'low', 'medium', 'high'，如果未知则返回 'medium'
        """
        # 尝试直接匹配
        if model in cls.MODEL_COST_LEVELS:
            return cls.MODEL_COST_LEVELS[model]
        
        # 根据模型名称模式推断
        model_lower = model.lower()
        
        # 低成本模型特征
        if any(keyword in model_lower for keyword in ["turbo", "flash", "mini", "nano", "lite", "haiku"]):
            return "low"
        
        # 高成本模型特征
        if any(keyword in model_lower for keyword in ["max", "opus", "pro-thinking", "reasoning-pro", "o3", "gpt-5"]):
            return "high"
        
        # 中等成本模型特征
        if any(keyword in model_lower for keyword in ["plus", "sonnet", "pro", "coder-plus"]):
            return "medium"
        
        # 默认返回中等成本
        return "medium"
    
    @classmethod
    def recommend_models(cls, task_type: str = None, provider: Optional[str] = None, cost_level: Optional[str] = None) -> List[Dict[str, str]]:
        """
        根据任务类型推荐合适的模型（支持成本过滤）
        
        Args:
            task_type: 任务类型（"text", "code", "vision", "audio", "video", "reasoning", "search"）
            provider: 指定提供商（可选）
            cost_level: 成本等级过滤（"low", "medium", "high"），可选
            
        Returns:
            推荐的模型列表，每个模型包含 provider, model, description, cost_level
        """
        recommendations = []
        
        # 文本生成任务
        if task_type in [None, "text", "chat", "writing"]:
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gpt-5",
                    "description": "OpenAI GPT-5，强大的文本生成能力（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gpt-5")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gpt-4o-mini",
                    "description": "OpenAI GPT-4o Mini，低成本文本生成（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gpt-4o-mini")
                })
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-max",
                    "description": "通义千问3 Max，适配复杂智能体场景",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-max")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen-plus-2025-12-01",
                    "description": "通义千问 Plus，支持思考模式和非思考模式融合",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen-plus-2025-12-01")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen-turbo-latest",
                    "description": "通义千问 Turbo，低成本文本生成",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen-turbo-latest")
                })
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "claude-3-5-sonnet-20241022",
                    "description": "Claude 3.5 Sonnet，强大的对话和写作能力（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "claude-3-5-sonnet-20241022")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "claude-3-5-haiku-20241022",
                    "description": "Claude 3.5 Haiku，低成本文本生成（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "claude-3-5-haiku-20241022")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gemini-2.5-pro",
                    "description": "Gemini 2.5 Pro，多模态理解生成（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gemini-2.5-pro")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gemini-2.5-flash",
                    "description": "Gemini 2.5 Flash，低成本多模态理解（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gemini-2.5-flash")
                })
        
        # 代码生成任务
        if task_type in [None, "code", "programming"]:
            if not provider or provider == "deepseek":
                recommendations.append({
                    "provider": "deepseek",
                    "model": "deepseek-coder",
                    "description": "DeepSeek Coder，专为代码生成优化",
                    "cost_level": cls.get_model_cost_level("deepseek", "deepseek-coder")
                })
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-coder-plus-2025-09-23",
                    "description": "通义千问3 Coder Plus，强大的 Coding Agent 能力",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-coder-plus-2025-09-23")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-coder-flash",
                    "description": "通义千问3 Coder Flash，优化仓库级别理解（低成本）",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-coder-flash")
                })
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gpt-5-codex",
                    "description": "GPT-5 Codex，代码生成专用（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gpt-5-codex")
                })
        
        # 推理任务
        if task_type in [None, "reasoning", "thinking", "analysis"]:
            if not provider or provider == "deepseek":
                recommendations.append({
                    "provider": "deepseek",
                    "model": "deepseek-r1",
                    "description": "DeepSeek R1，支持思考过程",
                    "cost_level": cls.get_model_cost_level("deepseek", "deepseek-r1")
                })
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "o3",
                    "description": "OpenAI O3，支持思考过程（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "o3")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "o3-mini",
                    "description": "OpenAI O3 Mini，支持思考过程（中等成本，通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "o3-mini")
                })
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "deepseek-v3.2",
                    "description": "DeepSeek V3.2，支持深度思考",
                    "cost_level": cls.get_model_cost_level("bailian", "deepseek-v3.2")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwq-plus",
                    "description": "通义千问 QwQ Plus，达到 DeepSeek-R1 满血版水平",
                    "cost_level": cls.get_model_cost_level("bailian", "qwq-plus")
                })
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "claude-3-7-sonnet-20250219",
                    "description": "Claude 3.7 Sonnet，支持 reasoning_effort 参数（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "claude-3-7-sonnet-20250219")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gemini-2.5-flash-thinking",
                    "description": "Gemini 2.5 Flash Thinking，输出思考过程（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gemini-2.5-flash-thinking")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "sonar-reasoning-pro",
                    "description": "Sonar Reasoning Pro，支持推理（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "sonar-reasoning-pro")
                })
        
        # 视觉理解任务
        if task_type in [None, "vision", "image", "visual"]:
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-vl-plus-2025-12-19",
                    "description": "通义千问3 VL Plus，视觉智能体业界领先，支持深度思考",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-vl-plus-2025-12-19")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen-vl-max-2025-08-13",
                    "description": "通义千问 VL Max，超大规模视觉语言模型",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen-vl-max-2025-08-13")
                })
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gemini-2.5-pro",
                    "description": "Gemini 2.5 Pro，支持多模态理解（图像、视频，通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gemini-2.5-pro")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "claude-opus-4-20250514",
                    "description": "Claude Opus 4，支持图片理解（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "claude-opus-4-20250514")
                })
        
        # 图像生成任务
        if task_type in [None, "image_generation", "image_gen"]:
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen-image-max-2025-12-30",
                    "description": "通义千问 Image Max，图像生成模型 Max 系列",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen-image-max-2025-12-30")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "wan2.6-t2i",
                    "description": "通义万相 文生图，文字生成图片",
                    "cost_level": cls.get_model_cost_level("bailian", "wan2.6-t2i")
                })
        
        # 视频生成任务
        if task_type in [None, "video", "video_generation"]:
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "wan2.6-t2v",
                    "description": "通义万相 文生视频，最高15秒视频生成",
                    "cost_level": cls.get_model_cost_level("bailian", "wan2.6-t2v")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "wan2.6-i2v",
                    "description": "通义万相 图生视频，图片生成视频内容",
                    "cost_level": cls.get_model_cost_level("bailian", "wan2.6-i2v")
                })
        
        # 语音识别任务
        if task_type in [None, "asr", "speech_recognition"]:
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-asr-flash-2025-09-08",
                    "description": "通义千问3 ASR Flash，多语种语音识别",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-asr-flash-2025-09-08")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "fun-asr",
                    "description": "Fun-ASR，新一代端到端语音识别大模型",
                    "cost_level": cls.get_model_cost_level("bailian", "fun-asr")
                })
        
        # 语音合成任务
        if task_type in [None, "tts", "speech_synthesis"]:
            if not provider or provider == "bailian":
                recommendations.append({
                    "provider": "bailian",
                    "model": "qwen3-tts-flash-2025-11-27",
                    "description": "通义千问3 TTS Flash，17种高表现力拟人音色",
                    "cost_level": cls.get_model_cost_level("bailian", "qwen3-tts-flash-2025-11-27")
                })
                recommendations.append({
                    "provider": "bailian",
                    "model": "cosyvoice-v3-flash",
                    "description": "CosyVoice 大模型，新一代生成式语音大模型",
                    "cost_level": cls.get_model_cost_level("bailian", "cosyvoice-v3-flash")
                })
        
        # 搜索任务
        if task_type in [None, "search", "web_search"]:
            if not provider or provider == "theturbogateway":
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "sonar-pro",
                    "description": "Perplexity Sonar Pro，对话式搜索引擎（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "sonar-pro")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "sonar",
                    "description": "Perplexity Sonar，低成本对话式搜索引擎（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "sonar")
                })
                recommendations.append({
                    "provider": "theturbogateway",
                    "model": "gemini-2.5-pro",
                    "description": "Gemini 2.5 Pro，支持 Google Search（通过 TheTurbo.ai 网关）",
                    "cost_level": cls.get_model_cost_level("theturbogateway", "gemini-2.5-pro")
                })
        
        # 为所有推荐添加成本等级（如果还没有）
        for rec in recommendations:
            if "cost_level" not in rec:
                rec["cost_level"] = cls.get_model_cost_level(rec["provider"], rec["model"])
        
        # 成本过滤
        if cost_level:
            cost_level = cost_level.lower()
            if cost_level in ["low", "medium", "high"]:
                recommendations = [rec for rec in recommendations if rec.get("cost_level") == cost_level]
        
        # 如果没有指定任务类型，返回所有推荐
        if task_type is None:
            # 去重
            seen = set()
            unique_recommendations = []
            for rec in recommendations:
                key = (rec["provider"], rec["model"])
                if key not in seen:
                    seen.add(key)
                    unique_recommendations.append(rec)
            return unique_recommendations
        
        return recommendations
    
    @classmethod
    def get_model_info(cls, model_name: str) -> Dict[str, str]:
        """
        获取模型信息（支持 "平台-模型" 格式）
        
        Args:
            model_name: 模型名称（支持 "平台-模型" 格式）
            
        Returns:
            包含模型信息的字典（provider, normalized_name 等）
        """
        # 解析模型名称（支持 "平台-模型" 格式）
        provider, actual_model = cls.parse_model_name(model_name)
        normalized_name = cls.normalize_model_name(actual_model, provider)
        
        return {
            "original_name": model_name,
            "provider": provider,
            "actual_model": actual_model,
            "normalized_name": normalized_name,
            "is_available": (normalized_name in cls.BAILIAN_MODELS or 
                            normalized_name in cls.DEEPSEEK_MODELS or 
                            normalized_name in cls.OPENAI_MODELS or 
                            normalized_name in cls.ANTHROPIC_MODELS or 
                            normalized_name in cls.GOOGLE_MODELS or 
                            normalized_name in cls.PERPLEXITY_MODELS),
            "full_name": f"{provider}-{normalized_name}"  # 完整格式名称
        }

