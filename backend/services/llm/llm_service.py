"""LLM 服务"""
import os
import asyncio
import logging
import time
from pathlib import Path
from typing import AsyncIterator, Optional, Dict, Any, TYPE_CHECKING
from openai import AsyncOpenAI, PermissionDeniedError, APIConnectionError
import httpx
from shared.debug_utils import DebugOutput
from shared.load_env import load_env

if TYPE_CHECKING:
    from browser_use.llm.base import BaseChatModel


logger = logging.getLogger(__name__)

# 延迟导入，避免循环依赖
_model_registry = None

def get_model_registry():
    """获取模型注册表（延迟导入）"""
    global _model_registry
    if _model_registry is None:
        from backend.services.llm.model_registry import ModelRegistry
        _model_registry = ModelRegistry
    return _model_registry


class LLMService:
    """LLM 服务 - 支持多提供商（DeepSeek、百炼平台、TheTurbo.ai 网关等）"""
    
    # 支持的提供商
    PROVIDER_DEEPSEEK = "deepseek"
    PROVIDER_BAILIAN = "bailian"
    PROVIDER_TURBOGATEWAY = "theturbogateway"
    
    def __init__(self, temperature: float = 0.7, max_tokens: Optional[int] = None, provider: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 LLM 服务
        
        Args:
            temperature: 温度参数，控制输出的随机性 (0.0-2.0)，默认 0.7
            max_tokens: 最大 token 数。None 表示不人为截断，使用模型上限；也可显式传入或通过 LLM_MAX_TOKENS 环境变量。
            provider: 提供商名称，如果为 None 则从环境变量或模型名称自动检测
            model: 初始模型名称，如果提供则自动检测提供商
        """
        # 参数配置：验证和设置参数
        self.temperature = max(0.0, min(2.0, temperature))
        # max_tokens=None: 不人为截断，使用模型上限；显式传入: 使用该值（请求时取 min(传入值, 模型上限)）
        self._max_tokens_override = max_tokens
        
        # 调试输出
        self.debug = DebugOutput()
        
        # 确保环境变量已加载（统一管理配置）
        self._ensure_env_loaded()
        
        # 确定初始模型和提供商
        if model:
            # 如果提供了模型名称，优先根据模型名称检测提供商（支持 "平台-模型" 格式）
            registry = get_model_registry()
            if provider is None:
                provider, _ = registry.parse_model_name(model)
                logger.info(f"根据模型名称 {model} 解析提供商: {provider}")
            self.model = model
        else:
            # 如果没有提供模型，确定默认提供商和模型
            if provider is None:
                provider = os.getenv("LLM_PROVIDER", self.PROVIDER_DEEPSEEK).lower()
            
            # 设置默认模型（根据提供商）
            if provider == self.PROVIDER_BAILIAN:
                self.model = os.getenv("BAILIAN_MODEL", "qwen-turbo")
            elif provider == self.PROVIDER_TURBOGATEWAY:
                self.model = os.getenv("TURBOGATEWAY_MODEL", "gpt-5")
            else:
                self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        self.provider = provider
        self.default_model = self.model
        
        logger.info(f"初始化 LLM 服务，提供商: {self.provider}, 模型: {self.model}")
        
        # 获取模型配置并初始化客户端
        config = self._get_model_config(self.model)
        self._init_client(config)
    
    def _get_effective_max_tokens(self) -> int:
        """
        获取本次请求的有效 max_tokens。
        策略：不人为截断，除非超出模型能力。
        - _max_tokens_override 为 None 且未设置 LLM_MAX_TOKENS：使用模型 max_output
        - 设置了 LLM_MAX_TOKENS：取 min(env, 模型 max_output)
        - 显式传入 max_tokens：取 min(传入值, 模型 max_output)
        """
        from backend.services.llm.model_token_limits import get_effective_max_tokens
        requested = self._max_tokens_override
        if requested is None:
            env_val = os.getenv("LLM_MAX_TOKENS")
            requested = int(env_val) if env_val else 999_999  # 未设置时用大数表示取模型上限
        return get_effective_max_tokens(self.model, requested)
    
    def _normalize_messages_for_api(self, messages: list) -> list:
        """
        规范化 messages，确保 content 为数组时每个块含 type 字段。
        时间：2025-03-14；理由：部分 API（如 Claude 代理）要求 content 块有 type；方法：补全缺失的 type。
        """
        out = []
        for m in messages:
            if not isinstance(m, dict):
                out.append(m)
                continue
            role = m.get("role", "user")
            content = m.get("content")
            extra = {k: v for k, v in m.items() if k not in ("role", "content")}
            if isinstance(content, list):
                normalized_parts = []
                for part in content:
                    if isinstance(part, str):
                        normalized_parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict):
                        if "type" not in part:
                            if "text" in part:
                                part = {"type": "text", "text": part["text"]}
                            elif "image_url" in part:
                                part = {"type": "image_url", "image_url": part["image_url"]}
                            else:
                                part = {"type": "text", "text": str(part)}
                        normalized_parts.append(part)
                    else:
                        normalized_parts.append({"type": "text", "text": str(part)})
                content = normalized_parts
            out.append({"role": role, "content": content, **extra})
        return out
    
    def _ensure_env_loaded(self):
        """确保环境变量已加载（统一配置管理）"""
        if not os.environ.get('DEEPSEEK_API_KEY'):
            project_root = Path(__file__).parent.parent.parent.parent
            load_env(project_root)
    
    def _get_model_config(self, model_name: str) -> Dict[str, str]:
        """
        获取模型配置字典
        
        Args:
            model_name: 模型名称（支持 "平台-模型" 格式）
            
        Returns:
            配置字典，包含 model, api_key, base_url, provider
        """
        from backend.services.llm.model_config import get_model_config_manager
        
        registry = get_model_registry()
        config_manager = get_model_config_manager()
        
        # 解析模型名称（支持 "平台-模型" 格式）
        provider, actual_model = registry.parse_model_name(model_name)
        
        # 规范化模型名称
        normalized_model = registry.normalize_model_name(actual_model, provider)
        
        # 获取 API Key 和 Base URL
        try:
            api_key = config_manager.get_api_key(model_name)
            base_url = config_manager.get_base_url(model_name)
        except Exception as e:
            logger.warning(f"使用 ModelConfigManager 获取配置失败，回退到环境变量: {e}")
            # 回退到环境变量（向后兼容）
            if provider == self.PROVIDER_BAILIAN:
                api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
                base_url = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            elif provider == self.PROVIDER_TURBOGATEWAY:
                # 使用统一的 TURBOGATEWAY_API_KEY
                api_key = os.environ.get('TURBOGATEWAY_API_KEY')
                base_url = os.getenv("TURBOGATEWAY_BASE_URL", "https://gateway.theturbo.ai/v1")
            else:
                api_key = os.environ.get('DEEPSEEK_API_KEY')
                base_url = "https://api.deepseek.com"
            
            if api_key is None:
                raise ValueError(f"{provider} API Key 环境变量未设置")
        
        # 验证 API Key
        api_key = api_key.strip()
        if not api_key or len(api_key) < 10:
            raise ValueError(f"{provider} API Key 格式无效：长度不足或为空")
        
        return {
            "model": normalized_model,
            "api_key": api_key,
            "base_url": base_url,
            "provider": provider
        }
    
    def _init_client(self, config: Dict[str, str]):
        """
        统一初始化客户端（使用配置字典）
        
        Args:
            config: 配置字典，包含 model, api_key, base_url, provider
        """
        # 配置 httpx 客户端
        # 超时设置：连接30秒，读取60秒（测试环境），写入30秒
        # 生产环境可以通过环境变量覆盖
        # trust_env=False + proxy=None：强制直连，不使用环境变量或系统代理（避免代理导致 SSL 错误）
        read_timeout = float(os.getenv("LLM_READ_TIMEOUT", "60.0"))
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(read_timeout, connect=30.0, read=read_timeout, write=30.0),
            trust_env=False,
            proxy=None,
        )
        
        # 创建 OpenAI 客户端（所有提供商都使用 OpenAI 兼容接口）
        self.client = AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            http_client=http_client
        )
        
        # 保存当前配置
        self.model = config["model"]
        self.provider = config["provider"]
        self._current_config = config
        
        logger.info(f"客户端已初始化，provider: {self.provider}, model: {self.model}, base_url: {config['base_url']}")
    
    def set_model(self, model: str, provider: Optional[str] = None):
        """
        动态设置使用的模型（支持 "平台-模型" 格式）
        
        Args:
            model: 模型名称（支持 "平台-模型" 格式，如 "bailian-deepseek-chat"）
            provider: 提供商名称（可选，如果不提供则从模型名称解析或自动检测）
        
        示例：
            llm_service.set_model("bailian-deepseek-chat")
            llm_service.set_model("gpt-5")
            llm_service.set_model("deepseek-chat", provider="bailian")
        """
        # 如果明确提供了提供商，临时设置以影响解析
        if provider:
            # 使用 "provider-model" 格式来确保解析正确
            model_with_provider = f"{provider}-{model}" if "-" not in model else model
            config = self._get_model_config(model_with_provider)
        else:
            config = self._get_model_config(model)
        
        # 更新客户端配置
        self._init_client(config)
        
        logger.info(f"模型已切换为: {config['model']} (provider: {config['provider']}, base_url: {config['base_url']})")
    
    def reset_model(self):
        """重置为默认模型"""
        config = self._get_model_config(self.default_model)
        self._init_client(config)
        logger.info(f"模型已重置为默认: {self.default_model} (provider: {self.provider})")
    
    def get_available_models(self) -> list:
        """
        获取当前提供商可用的模型列表
        
        Returns:
            模型名称列表
        """
        registry = get_model_registry()
        return registry.get_available_models(self.provider)
    
    def get_model_info(self) -> dict:
        """
        获取当前模型信息
        
        Returns:
            包含模型信息的字典
        """
        registry = get_model_registry()
        return registry.get_model_info(self.model)
    
    def list_all_models(self) -> dict:
        """
        列出所有提供商的所有模型
        
        Returns:
            字典，键为提供商名称，值为模型列表
        """
        registry = get_model_registry()
        return registry.list_all_models()
    
    def recommend_models(self, task_type: str = None, provider: Optional[str] = None, cost_level: Optional[str] = None) -> list:
        """
        根据任务类型推荐合适的模型（支持成本过滤）
        
        Args:
            task_type: 任务类型，可选值：
                - "text" / "chat" / "writing" - 文本生成
                - "code" / "programming" - 代码生成
                - "reasoning" / "thinking" / "analysis" - 推理分析
                - "vision" / "image" / "visual" - 视觉理解
                - "image_generation" / "image_gen" - 图像生成
                - "video" / "video_generation" - 视频生成
                - "asr" / "speech_recognition" - 语音识别
                - "tts" / "speech_synthesis" - 语音合成
                - "search" / "web_search" - 搜索
            provider: 指定提供商（可选），如果不指定则推荐所有提供商的模型
            cost_level: 成本等级过滤（"low", "medium", "high"），可选
            
        Returns:
            推荐的模型列表，每个模型包含 provider, model, description, cost_level
        """
        registry = get_model_registry()
        return registry.recommend_models(task_type=task_type, provider=provider, cost_level=cost_level)
    
    @property
    def supports_thinking(self) -> bool:
        """检测模型是否支持思考过程"""
        model_lower = self.model.lower()
        # DeepSeek R1 模型支持思考过程
        if "r1" in model_lower or "reasoning" in model_lower:
            return True
        # TheTurbo.ai 网关服务支持思考过程的模型
        if self.provider == self.PROVIDER_TURBOGATEWAY:
            # OpenAI O1 系列支持链式思考
            if model_lower.startswith("o1"):
                return True
            # OpenAI O3 系列支持思考过程
            if model_lower.startswith("o3") or model_lower.startswith("o4"):
                return True
            # Anthropic Claude 某些模型支持 reasoning_effort 参数（类似思考过程）
            if "3-7" in model_lower or "opus-4" in model_lower or "sonnet-4" in model_lower or "haiku-4" in model_lower:
                return True
            # Google Gemini 某些模型支持思考过程
            if "thinking" in model_lower:
                return True
            if "reasoning" in model_lower:
                return True
            # Perplexity Sonar 某些模型支持推理
            if "reasoning" in model_lower:
                return True
        # 百炼平台的思考模型
        if self.provider == self.PROVIDER_BAILIAN:
            # 百炼平台的一些模型支持思考过程（根据实际模型调整）
            return "reasoning" in model_lower or "think" in model_lower
        return False
    
    async def chat(
        self,
        system_prompt: str = "",
        user_prompt: str = "",
        tools: Optional[list] = None,
        messages: Optional[list] = None,
        audit_meta: Optional[Dict[str, Any]] = None,
    ):
        """
        聊天（非流式）

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表（OpenAI Function Calling 格式）
            messages: 消息列表（如果提供，将忽略 system_prompt 和 user_prompt）
            audit_meta: 可选，审计用元数据（如 session_id），会写入 LLM 审计日志

        Returns:
            LLM 生成的回复（字符串）或包含工具调用的响应对象（message 对象）

        Raises:
            httpx.HTTPStatusError: API 错误
            httpx.RequestError: 网络错误
        """
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

        # 审计：记录请求（送入 LLM 的内容），audit_id 关联本次调用的请求与响应
        audit_id = None
        try:
            from backend.services.llm.llm_audit import append_audit, _messages_summary, create_audit_id
            audit_id = create_audit_id()
            append_audit(
                "request",
                self.model,
                _messages_summary(messages),
                meta=dict(audit_meta or {}, has_tools=bool(tools), audit_id=audit_id),
            )
        except Exception as e:
            logger.debug("LLM 审计写入请求记录失败: %s", e)

        # 调试输出：请求信息
        # 为了满足调试需求，记录完整的请求信息
        logger.debug(f"LLM Request Details - Model: {self.model}")
        if system_prompt:
            logger.debug(f"LLM System Prompt: {system_prompt}")
        logger.debug(f"LLM User Prompt: {user_prompt}")
        self.debug.log_llm_request(system_prompt or "", user_prompt or "", self.model)
        
        # 规范化 messages：content 为数组时，每个块需含 type 字段（2025-03-14：修复 missing field type）
        messages = self._normalize_messages_for_api(messages)
        
        # 构建请求参数（不人为截断，使用模型上限）
        request_params = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self._get_effective_max_tokens()
        }
        
        # 如果提供了工具，添加到请求中
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"  # 让 LLM 决定是否调用工具
        
        # 错误处理：重试机制（指数退避）
        max_retries = 3
        base_delay = 1.0  # 基础延迟（秒）
        max_delay = 10.0  # 最大延迟（秒）
        last_error = None

        try:
            for attempt in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(**request_params)

                    # 处理思考过程（如果支持）
                    result = response.choices[0].message
                    content = result.content

                    # 审计：记录 LLM 输出（与请求同 audit_id）
                    try:
                        from backend.services.llm.llm_audit import append_audit, _response_summary
                        meta = dict(audit_meta or {}, audit_id=audit_id)
                        if getattr(response, "usage", None):
                            meta["usage"] = {k: getattr(response.usage, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if hasattr(response.usage, k)}
                        append_audit("response", self.model, _response_summary(result, self.model), meta=meta)
                    except Exception as e:
                        logger.debug("LLM 审计写入响应记录失败: %s", e)

                    # 检查是否有工具调用
                    if hasattr(result, 'tool_calls') and result.tool_calls:
                        # 返回包含工具调用的响应对象
                        return result

                    # 检查是否有思考过程（DeepSeek R1 格式）
                    # 注意：OpenAI SDK 可能不支持 reasoning_content，需要根据实际 API 响应调整
                    if self.supports_thinking and hasattr(result, 'reasoning_content'):
                        thinking = result.reasoning_content
                        if thinking:
                            self.debug.log_llm_thinking(thinking)

                    # 调试输出：响应信息
                    logger.debug(f"LLM Response Details - Model: {self.model}")
                    logger.debug(f"LLM Response Content: {content}")
                    self.debug.log_llm_response(content, self.model)

                    return content

                except httpx.ReadTimeout as e:
                    # 读取超时：可能是响应太长或网络慢，增加延迟后重试
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"请求超时（读取超时），等待 {delay:.1f} 秒后重试 "
                            f"(尝试 {attempt + 1}/{max_retries}): {e}",
                            exc_info=True
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"请求超时，重试次数耗尽: {e}", exc_info=True)
                        raise

                except httpx.HTTPStatusError as e:
                    # 401 错误（认证失败）：不重试
                    if e.response.status_code == 401:
                        logger.error(f"API 认证失败 (401): {e}", exc_info=True)
                        raise

                    # 403 错误（权限不足/模型未启用）：不重试
                    if e.response.status_code == 403:
                        logger.error(f"API 权限不足 (403): 模型可能未启用或权限不足: {e}", exc_info=True)
                        raise

                    # 429 错误（限流）：等待后重试（固定 2 秒，因为限流通常很快恢复）
                    if e.response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = 2.0
                            logger.warning(
                                f"API 限流 (429)，等待 {delay} 秒后重试 "
                                f"(尝试 {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"API 限流 (429)，重试次数耗尽: {e}", exc_info=True)
                            raise

                    # 其他 HTTP 错误：指数退避重试
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"API 错误 {e.response.status_code}，等待 {delay:.1f} 秒后重试 "
                            f"(尝试 {attempt + 1}/{max_retries}): {e}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"API 错误 {e.response.status_code}，重试次数耗尽: {e}",
                            exc_info=True
                        )
                        raise

                except httpx.RequestError as e:
                    # 网络错误：指数退避重试
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"网络错误，等待 {delay:.1f} 秒后重试 "
                            f"(尝试 {attempt + 1}/{max_retries}): {e}",
                            exc_info=True
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"网络错误，重试次数耗尽: {e}", exc_info=True)
                        raise

                except PermissionDeniedError as e:
                    # OpenAI SDK 的权限错误（403）：不重试
                    logger.error(f"API 权限不足 (PermissionDeniedError): 模型可能未启用或权限不足: {e}", exc_info=True)
                    raise
                except APIConnectionError as e:
                    # 连接失败：网络/代理/防火墙问题，可重试
                    last_error = e
                    hint = "请检查：1) 网络连接；2) 代理/VPN 设置；3) 防火墙是否拦截 api.deepseek.com"
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"API 连接失败，等待 {delay:.1f} 秒后重试 "
                            f"(尝试 {attempt + 1}/{max_retries}): {e}。{hint}",
                            exc_info=True
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        cause = getattr(e, "__cause__", None)
                        cause_str = f" 底层原因: {type(cause).__name__}: {cause}" if cause else ""
                        try:
                            from backend.services.llm.llm_audit import append_audit
                            append_audit(
                                "response_error",
                                self.model,
                                {"error": str(e), "error_type": "APIConnectionError", "hint": hint, "cause": str(cause) if cause else None},
                                meta=dict(audit_meta or {}, audit_id=audit_id),
                            )
                        except Exception:
                            pass
                        logger.error(f"API 连接失败，重试次数耗尽: {e}{cause_str}。{hint}", exc_info=True)
                        raise
                except Exception as e:
                    # 处理 OpenAI SDK 的 APITimeoutError 和其他超时异常
                    error_str = str(e)
                    error_type = type(e).__name__

                    # 检查是否是权限错误（403、PermissionDenied等）
                    if ("403" in error_str or
                        "PermissionDenied" in error_type or
                        "permission denied" in error_str.lower() or
                        "not enabled" in error_str.lower() or
                        "do not have access" in error_str.lower()):
                        logger.error(f"API 权限不足: 模型可能未启用或权限不足: {e}", exc_info=True)
                        raise

                    # 检查是否是超时错误
                    if ("timeout" in error_str.lower() or
                        "timed out" in error_str.lower() or
                        "APITimeoutError" in error_type or
                        "ReadTimeout" in error_type):
                        last_error = e
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(
                                f"请求超时，等待 {delay:.1f} 秒后重试 "
                                f"(尝试 {attempt + 1}/{max_retries}): {e}",
                                exc_info=True
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"请求超时，重试次数耗尽: {e}", exc_info=True)
                            raise
                    else:
                        # 其他未知错误，直接抛出
                        logger.error(f"未知错误: {e}", exc_info=True)
                        raise

            # 如果所有重试都失败
            if last_error:
                raise last_error
        except Exception as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit(
                    "response_error",
                    self.model,
                    {"error": str(e), "error_type": type(e).__name__},
                    meta=dict(audit_meta or {}, audit_id=audit_id),
                )
            except Exception:
                pass
            raise

    async def stream_chat(
        self,
        system_prompt: str = "",
        user_prompt: str = "",
        timeout: int = 60,
        audit_meta: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        流式聊天

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            timeout: 超时时间（秒），默认 60 秒
            audit_meta: 可选，审计用元数据（如 session_id）

        Yields:
            流式数据块

        Raises:
            asyncio.TimeoutError: 超时错误
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        audit_id = None
        try:
            from backend.services.llm.llm_audit import append_audit, _messages_summary, create_audit_id
            audit_id = create_audit_id()
            append_audit(
                "request",
                self.model,
                _messages_summary(messages),
                meta=dict(audit_meta or {}, audit_id=audit_id),
            )
        except Exception as e:
            logger.debug("LLM 审计写入请求记录失败: %s", e)

        # 调试输出：请求信息
        self.debug.log_llm_request(system_prompt, user_prompt, self.model)
        
        # 收集思考过程（如果支持）
        thinking_chunks = []
        content_chunks = []
        last_usage = None
        
        try:
            create_params = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "temperature": self.temperature,
                "max_tokens": self._get_effective_max_tokens(),
            }
            try:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(**{**create_params, "stream_options": {"include_usage": True}}),
                    timeout=timeout
                )
            except Exception:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(**create_params),
                    timeout=timeout
                )
            
            # 流式响应中断处理
            try:
                async for chunk in stream:
                    if getattr(chunk, "usage", None):
                        last_usage = {k: getattr(chunk.usage, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if hasattr(chunk.usage, k)}
                    # 检查 chunk 是否有 choices
                    if not hasattr(chunk, 'choices') or not chunk.choices:
                        continue
                    
                    # 处理思考过程（DeepSeek R1 格式）
                    if self.supports_thinking:
                        if hasattr(chunk.choices[0].delta, 'reasoning_content'):
                            thinking_chunk = chunk.choices[0].delta.reasoning_content
                            if thinking_chunk:
                                thinking_chunks.append(thinking_chunk)
                    
                    # 处理内容
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        content_chunks.append(content_chunk)
                        yield content_chunk
            except KeyboardInterrupt:
                # 审计：流式中断时记录已产生的局部响应
                try:
                    from backend.services.llm.llm_audit import append_audit, _response_summary
                    partial = "".join(content_chunks)
                    append_audit(
                        "response",
                        self.model,
                        _response_summary(partial, self.model),
                        meta=dict(audit_meta or {}, audit_id=audit_id, stream_interrupted=True),
                    )
                except Exception:
                    pass
                logger.info("流式响应被用户中断")
                return
            except Exception as e:
                try:
                    from backend.services.llm.llm_audit import append_audit, _response_summary
                    partial = "".join(content_chunks)
                    append_audit(
                        "response_error",
                        self.model,
                        {"error": str(e), "error_type": type(e).__name__, "partial_length": len(partial), "partial_preview": _response_summary(partial, self.model).get("content_preview", "")[:2000]},
                        meta=dict(audit_meta or {}, audit_id=audit_id),
                    )
                except Exception:
                    pass
                logger.error(f"流式响应处理错误: {e}")
                raise

            # 如果有思考过程，输出完整思考过程
            if thinking_chunks:
                thinking = "".join(thinking_chunks)
                self.debug.log_llm_thinking(thinking)

            # 审计：记录流式响应完整内容（含 token 统计）
            full_response = "".join(content_chunks)
            try:
                from backend.services.llm.llm_audit import append_audit, _response_summary
                meta = dict(audit_meta or {}, audit_id=audit_id)
                if last_usage:
                    meta["usage"] = last_usage
                append_audit(
                    "response",
                    self.model,
                    _response_summary(full_response, self.model),
                    meta=meta,
                )
            except Exception as e:
                logger.debug("LLM 审计写入流式响应记录失败: %s", e)

            # 调试输出：响应信息
            self.debug.log_llm_response(full_response, self.model)

        except asyncio.TimeoutError as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit("response_error", self.model, {"error": str(e), "error_type": "TimeoutError"}, meta=dict(audit_meta or {}, audit_id=audit_id))
            except Exception:
                pass
            logger.error(f"流式响应超时（{timeout} 秒）")
            raise
        except httpx.HTTPStatusError as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit("response_error", self.model, {"error": str(e), "error_type": "HTTPStatusError", "status": e.response.status_code}, meta=dict(audit_meta or {}, audit_id=audit_id))
            except Exception:
                pass
            # 401 错误（认证失败）：不重试
            if e.response.status_code == 401:
                logger.error(f"API 认证失败 (401): {e}", exc_info=True)
                raise
            # 403 错误（权限不足/模型未启用）：不重试
            if e.response.status_code == 403:
                logger.error(f"API 权限不足 (403): 模型可能未启用或权限不足: {e}", exc_info=True)
                raise
            # 429 错误（限流）：流式响应暂不支持重试，直接抛出
            if e.response.status_code == 429:
                logger.error(f"API 限流 (429): {e}", exc_info=True)
                raise
            logger.error(f"API 错误 {e.response.status_code}: {e}", exc_info=True)
            raise
        except PermissionDeniedError as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit("response_error", self.model, {"error": str(e), "error_type": "PermissionDeniedError"}, meta=dict(audit_meta or {}, audit_id=audit_id))
            except Exception:
                pass
            logger.error(f"API 权限不足 (PermissionDeniedError): 模型可能未启用或权限不足: {e}", exc_info=True)
            raise
        except httpx.RequestError as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit("response_error", self.model, {"error": str(e), "error_type": "RequestError"}, meta=dict(audit_meta or {}, audit_id=audit_id))
            except Exception:
                pass
            logger.error(f"网络错误: {e}", exc_info=True)
            raise
        except APIConnectionError as e:
            hint = "请检查：1) 网络连接；2) 代理/VPN 设置；3) 防火墙是否拦截 api.deepseek.com；4) 若在中国大陆，确认可访问 DeepSeek API"
            cause = getattr(e, "__cause__", None)
            cause_str = f" 底层原因: {type(cause).__name__}: {cause}" if cause else ""
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit(
                    "response_error",
                    self.model,
                    {"error": str(e), "error_type": "APIConnectionError", "hint": hint, "cause": str(cause) if cause else None},
                    meta=dict(audit_meta or {}, audit_id=audit_id),
                )
            except Exception:
                pass
            logger.error(f"API 连接失败: {e}{cause_str}。{hint}", exc_info=True)
            raise
        except Exception as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit(
                    "response_error",
                    self.model,
                    {"error": str(e), "error_type": type(e).__name__},
                    meta=dict(audit_meta or {}, audit_id=audit_id),
                )
            except Exception:
                pass
            raise

    async def stream_chat_with_tools(
        self,
        messages: list,
        tools: Optional[list] = None,
        timeout: int = 120,
        audit_meta: Optional[Dict[str, Any]] = None,
        out_result: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        带工具调用的流式聊天：content 实时 yield，tool_calls 累积后写入 out_result。

        Args:
            messages: 消息列表
            tools: 工具定义（OpenAI Function Calling 格式）
            timeout: 超时秒数
            audit_meta: 审计元数据
            out_result: 可变的 dict，流结束后写入 {"content": str} 或 {"tool_calls": [...]}

        Yields:
            content 文本块（逐 token）
        """
        out = out_result if out_result is not None else {}
        out.clear()
        content_chunks = []
        tool_calls_acc = {}  # index -> {id, function: {name, arguments}}

        messages = self._normalize_messages_for_api(messages)
        request_params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self._get_effective_max_tokens(),
        }
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        audit_id = None
        try:
            from backend.services.llm.llm_audit import append_audit, _messages_summary, create_audit_id
            audit_id = create_audit_id()
            append_audit("request", self.model, _messages_summary(messages), meta=dict(audit_meta or {}, has_tools=bool(tools), audit_id=audit_id))
        except Exception as e:
            logger.debug("LLM 审计写入请求记录失败: %s", e)

        last_usage = None
        try:
            try:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(**{**request_params, "stream_options": {"include_usage": True}}),
                    timeout=timeout,
                )
            except Exception:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(**request_params),
                    timeout=timeout,
                )
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    last_usage = {k: getattr(chunk.usage, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if hasattr(chunk.usage, k)}
                if not hasattr(chunk, "choices") or not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                finish_reason = getattr(chunk.choices[0], "finish_reason", None)

                if hasattr(delta, "content") and delta.content:
                    content_chunks.append(delta.content)
                    yield delta.content

                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = getattr(tc, "index", 0)
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                        acc = tool_calls_acc[idx]
                        if getattr(tc, "id", None):
                            acc["id"] = tc.id
                        if hasattr(tc, "function") and tc.function:
                            fn = tc.function
                            if getattr(fn, "name", None):
                                acc["function"]["name"] = (acc["function"]["name"] or "") + (fn.name or "")
                            if getattr(fn, "arguments", None):
                                acc["function"]["arguments"] = (acc["function"]["arguments"] or "") + (fn.arguments or "")

                if finish_reason == "tool_calls" and tool_calls_acc:
                    from types import SimpleNamespace
                    tool_calls_list = []
                    for i in sorted(tool_calls_acc.keys()):
                        acc = tool_calls_acc[i]
                        fn = SimpleNamespace(
                            name=acc["function"]["name"] or "",
                            arguments=acc["function"]["arguments"] or "{}",
                        )
                        tc = SimpleNamespace(
                            id=acc["id"] or f"call_{i}",
                            type="function",
                            function=fn,
                        )
                        tool_calls_list.append(tc)
                    out["tool_calls"] = tool_calls_list
                    break
                if finish_reason in ("stop", "end_turn", "length"):
                    break

            full_content = "".join(content_chunks)
            if "tool_calls" not in out:
                out["content"] = full_content

            try:
                from backend.services.llm.llm_audit import append_audit, _response_summary
                meta = dict(audit_meta or {}, audit_id=audit_id)
                if last_usage:
                    meta["usage"] = last_usage
                if "tool_calls" in out:
                    append_audit("response", self.model, {"tool_calls": len(out["tool_calls"])}, meta=meta)
                else:
                    append_audit("response", self.model, _response_summary(full_content, self.model), meta=meta)
            except Exception as e:
                logger.debug("LLM 审计写入流式响应记录失败: %s", e)

        except Exception as e:
            try:
                from backend.services.llm.llm_audit import append_audit
                append_audit("response_error", self.model, {"error": str(e)}, meta=dict(audit_meta or {}, audit_id=audit_id))
            except Exception:
                pass
            raise

    def supports_response_format(self) -> bool:
        """
        检查当前 LLM 是否支持 response_format 参数
        """
        provider = self.provider
        model = self.model
        
        # DeepSeek 不支持 response_format
        if provider == self.PROVIDER_DEEPSEEK:
            return False
        
        # 百炼平台部分模型支持
        if provider == self.PROVIDER_BAILIAN:
            unsupported_models = ["qwen-turbo"]  # 根据实际情况调整
            if model in unsupported_models:
                return False
            return True
        
        # TheTurbo.ai 网关支持大多数模型
        if provider == self.PROVIDER_TURBOGATEWAY:
            return True
        
        # 默认认为支持
        return True
    
    def get_browser_use_llm(self, model: Optional[str] = None):
        """
        获取 browser-use 兼容的 LLM 实例
        
        Args:
            model: 模型名称（可选），如果不提供则使用当前模型
            
        Returns:
            browser-use 兼容的 BaseChatModel 实例
            
        Note:
            这个方法返回的 LLM 实例可以直接用于 browser-use 的 Agent
        """
        return self.get_browser_use_llm_with_adaptation(model)
    
    def get_browser_use_llm_with_adaptation(self, model: Optional[str] = None, disable_response_schema: bool = False):
        """
        获取 browser-use 兼容的 LLM 实例，带适配层支持
        
        Args:
            model: 模型名称（可选），如果不提供则使用当前模型
            disable_response_schema: 是否禁用响应格式模式
            
        Returns:
            browser-use 兼容的 BaseChatModel 实例
        """
        # 延迟导入，避免循环依赖
        try:
            from browser_use.llm.openai.chat import ChatOpenAI
        except ImportError:
            raise ImportError(
                "browser-use 未安装，无法创建 browser-use 兼容的 LLM 实例。"
                "请安装: pip install browser-use"
            )
        
        # 如果指定了模型，临时切换
        original_model = self.model
        if model and model != self.model:
            self.set_model(model)
        
        try:
            # 获取当前配置
            config = self._get_model_config(self.model)
            
            # 检查是否支持 response_format
            supports_response_format = self.supports_response_format()
            
            # 准备参数（browser-use / LangChain 默认会读环境变量代理，需传入 http_client 强制直连）
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=120.0),
                trust_env=False,
                proxy=None,
            )
            llm_kwargs = {
                "model": config["model"],
                "api_key": config["api_key"],
                "base_url": config["base_url"],
                "temperature": self.temperature,
                "max_retries": 5,
                "http_client": _http_client,
            }
            
            # 记录browser-use LLM创建信息
            logger.debug(f"准备创建browser-use LLM实例，模型: {config['model']}, 提供商: {config['provider']}")
            
            # 根据兼容性决定是否添加额外参数
            if disable_response_schema or not supports_response_format:
                # 某些 LLM 不支持 response_format，避免使用可能导致错误的参数
                # 传递 timeout 以避免 browser-use 内部添加不兼容参数
                llm_kwargs["timeout"] = 120
                
                # 确保不会传递任何可能导致 response_format 错误的参数
                # 对于不支持 response_format 的模型，创建一个包装类
                from langchain_openai import ChatOpenAI as LangChainChatOpenAI
                browser_llm = LangChainChatOpenAI(**llm_kwargs)
                
                # 创建一个代理对象来拦截可能导致问题的方法
                class ResponseFormatSafeLLM:
                    def __init__(self, llm, original_config):
                        self.llm = llm
                        self.original_config = original_config  # 保留原始配置信息
                        
                    def __getattr__(self, name):
                        # 特殊处理某些属性，如果底层实例没有，则返回默认值或模拟值
                        if name == 'provider':
                            # browser-use 可能需要 provider 属性
                            return self.original_config.get('provider', 'unknown')
                        elif name == 'model':
                            # browser-use 可能需要 model 属性
                            return self.original_config.get('model', 'unknown-model')
                        elif name == 'model_name':
                            # 有些实现可能使用 model_name
                            return self.original_config.get('model', 'unknown-model')
                        try:
                            return getattr(self.llm, name)
                        except AttributeError:
                            # 如果底层实例没有该属性，返回一个合适的默认值或模拟实现
                            if name == 'bind_tools':
                                return self.bind_tools
                            elif name == 'with_structured_output':
                                return self.with_structured_output
                            else:
                                raise
                    
                    def bind_tools(self, tools, **kwargs):
                        # 过滤掉可能导致 response_format 错误的参数
                        safe_kwargs = {k: v for k, v in kwargs.items() 
                                     if k != "strict" and k != "response_format"}
                        return self.llm.bind_tools(tools, **safe_kwargs)
                    
                    def with_structured_output(self, schema, **kwargs):
                        # 对于不支持 response_format 的模型，返回原始 LLM 的方法
                        # 避免可能导致 'items' 错误的复杂处理
                        try:
                            # 尝试调用原始 LLM 的方法，但过滤掉不支持的参数
                            safe_kwargs = {k: v for k, v in kwargs.items() 
                                         if k != "response_format"}
                            return self.llm.with_structured_output(schema, **safe_kwargs)
                        except Exception:
                            # 如果仍然失败，返回一个模拟的结构化输出处理器
                            # 这样可以避免 'items' 错误
                            # 返回原始 LLM 的方法，但确保不包含问题参数
                            def passthrough_method(*args, **kwargs):
                                # 简单的透传方法，返回输入不变
                                if args:
                                    return args[0]
                                return None
                            return passthrough_method
                
                browser_llm = ResponseFormatSafeLLM(browser_llm, config)
            else:
                # 创建 ChatOpenAI 实例（browser-use 兼容）
                browser_llm = ChatOpenAI(**llm_kwargs)
            
            
            logger.info(
                f"创建 browser-use 兼容的 LLM: "
                f"model={config['model']}, provider={config['provider']}, "
                f"supports_response_format={supports_response_format}, "
                f"disable_response_schema={disable_response_schema}"
            )
            
            # 特别处理 DeepSeek 模型用于 browser-use
            # 为 DeepSeek 模型设置额外参数以提高兼容性
            if config['provider'] == 'deepseek':
                # 设置更长的超时时间以应对 DeepSeek 模型响应较慢的情况
                if hasattr(browser_llm, 'timeout'):
                    browser_llm.timeout = 120  # 2分钟超时
                elif hasattr(browser_llm, '_client') and hasattr(browser_llm._client, 'timeout'):
                    browser_llm._client.timeout = 120
                elif hasattr(browser_llm, '_timeout'):
                    browser_llm._timeout = 120
                
                # 记录 DeepSeek 特殊处理
                logger.info(f"为 DeepSeek 模型 {config['model']} 设置了特殊兼容性参数")
            
            return browser_llm
        finally:
            # 恢复原始模型（如果切换过）
            if model and model != self.model:
                self.set_model(original_model)


async def probe_model(model: str, timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    对指定模型发起简单探测（发送 "hello"），用于模型可用性审计。

    Args:
        model: 模型名称（支持 "平台-模型" 格式）
        timeout_seconds: 超时秒数，默认 15

    Returns:
        {"ok": True, "response": "模型回复", "duration_ms": 123} 或 {"ok": False, "error": "错误信息", "duration_ms": 123}
    """
    t0 = time.perf_counter()
    try:
        service = LLMService(model=model)
        result = await asyncio.wait_for(
            service.chat(user_prompt="hello", audit_meta={"is_probe": True}),
            timeout=timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if result is not None:
            text = result if isinstance(result, str) else getattr(
                result, "content", ""
            ) or ""
            return {"ok": True, "response": text, "duration_ms": duration_ms}
        return {"ok": False, "error": "无响应", "duration_ms": duration_ms}
    except asyncio.TimeoutError:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        return {"ok": False, "error": "请求超时", "duration_ms": duration_ms}
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        return {"ok": False, "error": str(e), "duration_ms": duration_ms}
