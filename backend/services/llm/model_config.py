"""模型配置管理器 - 管理不同用途的模型配置（对话、编码、推理）"""
import os
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置信息"""
    model_name: str  # 模型名称（支持 "平台-模型" 格式）
    provider: str  # 提供商名称
    api_key_env: str  # API Key 环境变量名
    base_url_env: Optional[str] = None  # Base URL 环境变量名（可选）
    default_base_url: Optional[str] = None  # 默认 Base URL（可选）


class ModelConfigManager:
    """模型配置管理器 - 管理不同用途的模型配置"""
    
    # TheTurbo.ai 网关默认 Base URL
    TURBOGATEWAY_DEFAULT_BASE_URL = "https://gateway.theturbo.ai/v1"
    
    # 提供商配置表：提供商 -> (API Key 环境变量, Base URL 环境变量, 默认 Base URL)
    PROVIDER_CONFIGS: Dict[str, Tuple[str, Optional[str], Optional[str]]] = {
        "deepseek": (
            "DEEPSEEK_API_KEY",
            None,  # DeepSeek 不使用 Base URL 环境变量
            "https://api.deepseek.com"
        ),
        "bailian": (
            "BAILIAN_API_KEY",
            "BAILIAN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        "theturbogateway": (
            "TURBOGATEWAY_API_KEY",  # 统一的 API Key
            "TURBOGATEWAY_BASE_URL",  # 可选的环境变量
            TURBOGATEWAY_DEFAULT_BASE_URL
        ),
    }
    
    def __init__(self):
        """初始化模型配置管理器"""
        self._model_registry = None
        self._load_model_registry()
    
    def _load_model_registry(self):
        """延迟加载模型注册表"""
        if self._model_registry is None:
            from backend.services.llm.model_registry import ModelRegistry
            self._model_registry = ModelRegistry
    
    def get_model_config(self, model_name: str) -> ModelConfig:
        """
        获取模型配置信息
        
        Args:
            model_name: 模型名称（支持 "平台-模型" 格式）
            
        Returns:
            ModelConfig 对象，包含模型、提供商、API Key 和 Base URL 配置信息
            
        Raises:
            ValueError: 如果模型名称无效或提供商配置不存在
        """
        # 解析模型名称（支持 "平台-模型" 格式）
        provider, actual_model = self._model_registry.parse_model_name(model_name)
        
        # 检查是否是 TheTurbo.ai 网关服务
        # 使用 ModelRegistry 的方法，统一服务类型检测逻辑
        turbogateway_service = self._model_registry.detect_turbogateway_service(actual_model)
        if turbogateway_service:
            # 统一使用 theturbogateway 作为 provider
            provider = "theturbogateway"
        
        # 获取提供商配置
        if provider not in self.PROVIDER_CONFIGS:
            raise ValueError(f"不支持的提供商: {provider}")
        
        api_key_env, base_url_env, default_base_url = self.PROVIDER_CONFIGS[provider]
        
        # 规范化模型名称
        normalized_model = self._model_registry.normalize_model_name(actual_model, provider)
        
        return ModelConfig(
            model_name=normalized_model,
            provider=provider,
            api_key_env=api_key_env,
            base_url_env=base_url_env,
            default_base_url=default_base_url
        )
    
    def get_api_key(self, model_name: str) -> str:
        """
        获取模型的 API Key
        
        Args:
            model_name: 模型名称
            
        Returns:
            API Key 字符串
            
        Raises:
            ValueError: 如果 API Key 未设置或无效
        """
        config = self.get_model_config(model_name)
        api_key = os.environ.get(config.api_key_env)
        
        if api_key is None:
            raise ValueError(f"{config.api_key_env} 环境变量未设置（模型: {model_name}, 提供商: {config.provider}）")
        
        api_key = api_key.strip()
        if not api_key or len(api_key) < 10:
            raise ValueError(f"{config.api_key_env} 格式无效：长度不足或为空（模型: {model_name}, 提供商: {config.provider}）")
        
        return api_key
    
    def get_base_url(self, model_name: str) -> str:
        """
        获取模型的 Base URL
        
        Args:
            model_name: 模型名称
            
        Returns:
            Base URL 字符串
        """
        config = self.get_model_config(model_name)
        
        # TheTurbo.ai 网关：优先使用统一的 TURBOGATEWAY_BASE_URL
        if config.provider == "theturbogateway":
            turbogateway_base_url = os.environ.get("TURBOGATEWAY_BASE_URL")
            if turbogateway_base_url:
                return turbogateway_base_url.strip()
        
        # 优先使用环境变量中的 Base URL
        if config.base_url_env:
            base_url = os.environ.get(config.base_url_env)
            if base_url:
                return base_url.strip()
        
        # 使用默认 Base URL
        if config.default_base_url:
            return config.default_base_url
        
        # 如果没有配置，返回空字符串（某些提供商可能不需要 Base URL）
        return ""
    
    def get_chat_model(self) -> str:
        """
        获取对话模型配置
        
        Returns:
            对话模型名称
        """
        return os.getenv("CHAT_MODEL", "deepseek-chat")
    
    def get_code_model(self) -> str:
        """
        获取编码模型配置
        
        Returns:
            编码模型名称
        """
        return os.getenv("CODE_MODEL", "deepseek-coder")
    
    def get_reasoning_model(self) -> str:
        """
        获取推理模型配置
        
        Returns:
            推理模型名称
        """
        return os.getenv("REASONING_MODEL", "deepseek-reasoner")
    
    def get_model_config_by_type(self, model_type: str) -> ModelConfig:
        """
        根据模型类型获取模型配置
        
        Args:
            model_type: 模型类型（"chat", "code", "reasoning"）
            
        Returns:
            ModelConfig 对象
            
        Raises:
            ValueError: 如果模型类型无效
        """
        model_type = model_type.lower()
        
        if model_type == "chat":
            model_name = self.get_chat_model()
        elif model_type == "code":
            model_name = self.get_code_model()
        elif model_type == "reasoning":
            model_name = self.get_reasoning_model()
        else:
            raise ValueError(f"无效的模型类型: {model_type}，支持的类型: chat, code, reasoning")
        
        return self.get_model_config(model_name)
    
    def validate_config(self) -> Dict[str, bool]:
        """
        验证所有配置的模型是否有效
        
        Returns:
            字典，键为模型类型，值为是否有效
        """
        result = {}
        
        for model_type in ["chat", "code", "reasoning"]:
            try:
                config = self.get_model_config_by_type(model_type)
                # 检查 API Key 是否存在
                api_key = os.environ.get(config.api_key_env)
                result[model_type] = api_key is not None and len(api_key.strip()) >= 10
            except Exception as e:
                logger.warning(f"模型类型 {model_type} 配置验证失败: {e}")
                result[model_type] = False
        
        return result
    
    def get_max_iterations_stream(self) -> int:
        """
        获取流式处理的最大迭代次数
        
        Returns:
            最大迭代次数，默认 100
        """
        return int(os.getenv("MAX_TOOL_ITERATIONS_STREAM", "100"))
    
    def get_max_iterations_non_stream(self) -> int:
        """
        获取非流式处理的最大迭代次数
        
        Returns:
            最大迭代次数，默认 5
        """
        return int(os.getenv("MAX_TOOL_ITERATIONS_NON_STREAM", "5"))
    
    def is_smart_model_selection_enabled(self) -> bool:
        """
        检查是否启用智能模型选择
        
        Returns:
            是否启用，默认 True
        """
        return os.getenv("ENABLE_SMART_MODEL_SELECTION", "true").lower() == "true"
    
    def is_task_decomposition_enabled(self) -> bool:
        """
        检查是否启用任务分解
        
        Returns:
            是否启用，默认 False（分阶段启用）
        """
        return os.getenv("ENABLE_TASK_DECOMPOSITION", "false").lower() == "true"
    
    def is_parallel_execution_enabled(self) -> bool:
        """
        检查是否启用并行执行
        
        Returns:
            是否启用，默认 False（分阶段启用）
        """
        return os.getenv("ENABLE_PARALLEL_EXECUTION", "false").lower() == "true"


# 全局单例
_model_config_manager = None


def get_model_config_manager() -> ModelConfigManager:
    """获取模型配置管理器单例"""
    global _model_config_manager
    if _model_config_manager is None:
        _model_config_manager = ModelConfigManager()
    return _model_config_manager

