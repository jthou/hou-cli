"""LLM 服务"""
import os
import asyncio
import logging
from typing import AsyncIterator, Optional, Dict, TYPE_CHECKING
from openai import AsyncOpenAI, PermissionDeniedError
import httpx
from shared.debug_utils import DebugOutput

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
    
    def __init__(self, temperature: float = 0.7, max_tokens: int = 2000, provider: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 LLM 服务
        
        Args:
            temperature: 温度参数，控制输出的随机性 (0.0-2.0)，默认 0.7
            max_tokens: 最大 token 数，默认 2000
            provider: 提供商名称，如果为 None 则从环境变量或模型名称自动检测
            model: 初始模型名称，如果提供则自动检测提供商
        """
        # 参数配置：验证和设置参数
        self.temperature = max(0.0, min(2.0, temperature))
        self.max_tokens = max(1, max_tokens)
        
        # 调试输出
        self.debug = DebugOutput()
        
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
        read_timeout = float(os.getenv("LLM_READ_TIMEOUT", "60.0"))
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(read_timeout, connect=30.0, read=read_timeout, write=30.0),
            trust_env=False
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
    
    async def chat(self, system_prompt: str = "", user_prompt: str = "", tools: Optional[list] = None, messages: Optional[list] = None):
        """
        聊天（非流式）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表（OpenAI Function Calling 格式）
            messages: 消息列表（如果提供，将忽略 system_prompt 和 user_prompt）
            
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
        
        # 调试输出：请求信息
        self.debug.log_llm_request(system_prompt or "", user_prompt or "", self.model)
        
        # 构建请求参数
        request_params = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
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
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(**request_params)
                
                # 处理思考过程（如果支持）
                result = response.choices[0].message
                content = result.content
                
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
                    # 指数退避：delay = base_delay * (2 ^ attempt)，但不超过 max_delay
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
                    # 指数退避：delay = base_delay * (2 ^ attempt)，但不超过 max_delay
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
    
    async def stream_chat(self, system_prompt: str = "", user_prompt: str = "", timeout: int = 60) -> AsyncIterator[str]:
        """
        流式聊天
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            timeout: 超时时间（秒），默认 60 秒
            
        Yields:
            流式数据块
            
        Raises:
            asyncio.TimeoutError: 超时错误
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        # 调试输出：请求信息
        self.debug.log_llm_request(system_prompt, user_prompt, self.model)
        
        # 收集思考过程（如果支持）
        thinking_chunks = []
        content_chunks = []
        
        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                ),
                timeout=timeout
            )
            
            # 流式响应中断处理
            try:
                async for chunk in stream:
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
                # 优雅处理中断
                logger.info("流式响应被用户中断")
                return
            except Exception as e:
                logger.error(f"流式响应处理错误: {e}")
                raise
            
            # 如果有思考过程，输出完整思考过程
            if thinking_chunks:
                thinking = "".join(thinking_chunks)
                self.debug.log_llm_thinking(thinking)
            
            # 调试输出：响应信息
            full_response = "".join(content_chunks)
            self.debug.log_llm_response(full_response, self.model)
                
        except asyncio.TimeoutError:
            logger.error(f"流式响应超时（{timeout} 秒）")
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
            # 429 错误（限流）：流式响应暂不支持重试，直接抛出
            if e.response.status_code == 429:
                logger.error(f"API 限流 (429): {e}", exc_info=True)
                raise
            logger.error(f"API 错误 {e.response.status_code}: {e}", exc_info=True)
            raise
        except PermissionDeniedError as e:
            # OpenAI SDK 的权限错误（403）：不重试
            logger.error(f"API 权限不足 (PermissionDeniedError): 模型可能未启用或权限不足: {e}", exc_info=True)
            raise
        except httpx.RequestError as e:
            logger.error(f"网络错误: {e}", exc_info=True)
            raise
    
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
            
            # 创建 ChatOpenAI 实例（browser-use 兼容）
            browser_llm = ChatOpenAI(
                model=config["model"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                temperature=self.temperature,
                max_retries=5
            )
            
            logger.info(
                f"创建 browser-use 兼容的 LLM: "
                f"model={config['model']}, provider={config['provider']}"
            )
            
            return browser_llm
        finally:
            # 恢复原始模型（如果切换过）
            if model and model != self.model:
                self.set_model(original_model)
