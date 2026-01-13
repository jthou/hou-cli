"""LLM 服务"""
import os
import asyncio
import logging
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
import httpx
from shared.debug_utils import DebugOutput

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
    """LLM 服务 - 支持多提供商（DeepSeek、百炼平台等）"""
    
    # 支持的提供商
    PROVIDER_DEEPSEEK = "deepseek"
    PROVIDER_BAILIAN = "bailian"
    PROVIDER_OPENAI = "openai"
    PROVIDER_ANTHROPIC = "anthropic"
    PROVIDER_GOOGLE = "google"
    PROVIDER_XAI = "xai"
    PROVIDER_PERPLEXITY = "perplexity"
    
    def __init__(self, temperature: float = 0.7, max_tokens: int = 2000, provider: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 LLM 服务
        
        Args:
            temperature: 温度参数，控制输出的随机性 (0.0-2.0)，默认 0.7
            max_tokens: 最大 token 数，默认 2000
            provider: 提供商名称（"deepseek" 或 "bailian"），如果为 None 则从环境变量或模型名称自动检测
            model: 初始模型名称，如果提供则自动检测提供商
        """
        # 如果提供了模型名称，优先根据模型名称检测提供商（支持 "平台-模型" 格式）
        if model and provider is None:
            registry = get_model_registry()
            provider, actual_model = registry.parse_model_name(model)
            logger.info(f"根据模型名称 {model} 解析提供商: {provider}, 实际模型: {actual_model}")
        
        # 确定使用的提供商
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", self.PROVIDER_DEEPSEEK).lower()
        
        self.provider = provider
        logger.info(f"初始化 LLM 服务，提供商: {self.provider}")
        
        # 根据提供商初始化客户端
        if self.provider == self.PROVIDER_BAILIAN:
            self._init_bailian_client()
        elif self.provider == self.PROVIDER_OPENAI:
            self._init_openai_client()
        elif self.provider == self.PROVIDER_ANTHROPIC:
            self._init_anthropic_client()
        elif self.provider == self.PROVIDER_GOOGLE:
            self._init_google_client()
        elif self.provider == self.PROVIDER_XAI:
            self._init_xai_client()
        elif self.provider == self.PROVIDER_PERPLEXITY:
            self._init_perplexity_client()
        else:
            # 默认使用 DeepSeek
            self._init_deepseek_client()
        
        # 参数配置：验证和设置参数
        self.temperature = max(0.0, min(2.0, temperature))
        self.max_tokens = max(1, max_tokens)
        
        # 调试输出
        self.debug = DebugOutput()
        
        # 设置默认模型（根据提供商）
        if self.provider == self.PROVIDER_BAILIAN:
            self.default_model = os.getenv("BAILIAN_MODEL", "qwen-turbo")  # 百炼平台默认模型
        elif self.provider == self.PROVIDER_OPENAI:
            self.default_model = os.getenv("OPENAI_MODEL", "gpt-5")  # OpenAI 默认模型
        elif self.provider == self.PROVIDER_ANTHROPIC:
            self.default_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")  # Anthropic 默认模型
        elif self.provider == self.PROVIDER_GOOGLE:
            self.default_model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")  # Google 默认模型
        elif self.provider == self.PROVIDER_XAI:
            self.default_model = os.getenv("XAI_MODEL", "grok-4")  # xAI 默认模型
        elif self.provider == self.PROVIDER_PERPLEXITY:
            self.default_model = os.getenv("PERPLEXITY_MODEL", "sonar")  # Perplexity 默认模型
        else:
            self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # DeepSeek 默认模型
        
        # 如果提供了初始模型，使用它（并规范化）
        if model:
            registry = get_model_registry()
            # 解析模型名称（可能包含平台前缀）
            _, actual_model = registry.parse_model_name(model)
            normalized_model = registry.normalize_model_name(actual_model, self.provider)
            self.model = normalized_model
            logger.info(f"使用指定的初始模型: {normalized_model} (原始名称: {model})")
        else:
            self.model = self.default_model  # 当前使用的模型
            logger.info(f"使用默认模型: {self.model}")
    
    def _init_deepseek_client(self):
        """初始化 DeepSeek 客户端"""
        # 配置管理：读取和验证 API Key
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if api_key is None:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        
        # 配置验证：API Key 格式验证
        api_key = api_key.strip()
        if not api_key or len(api_key) < 10:
            raise ValueError("DeepSeek API Key 格式无效：长度不足或为空")
        
        # 配置 httpx 客户端
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0),
            trust_env=False
        )
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            http_client=http_client
        )
        logger.info("DeepSeek 客户端已初始化")
    
    def _init_bailian_client(self):
        """初始化百炼平台客户端"""
        try:
            from backend.services.llm.bailian_client import BailianClient
        except ImportError:
            # 如果导入失败，使用内联实现
            api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
            if api_key is None:
                raise ValueError("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 环境变量未设置")
            
            api_key = api_key.strip()
            if not api_key or len(api_key) < 10:
                raise ValueError("百炼平台 API Key 格式无效：长度不足或为空")
            
            # 百炼平台 API 地址（使用 dashscope 兼容模式）
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
            logger.info(f"百炼平台客户端已初始化，base_url: {base_url}")
        else:
            # 使用独立的 BailianClient
            api_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
            if api_key is None:
                raise ValueError("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 环境变量未设置")
            
            bailian_client = BailianClient(api_key=api_key)
            self.client = bailian_client.client
    
    def _init_openai_client(self):
        """初始化 OpenAI 客户端"""
        try:
            from backend.services.llm.openai_client import OpenAIClient
        except ImportError:
            # 如果导入失败，使用内联实现
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key is None:
                raise ValueError("OPENAI_API_KEY 环境变量未设置")
            
            api_key = api_key.strip()
            if not api_key or len(api_key) < 10:
                raise ValueError("OpenAI API Key 格式无效：长度不足或为空")
            
            # TheTurbo.ai 网关 API 地址
            base_url = os.getenv(
                "OPENAI_BASE_URL",
                "https://gateway.theturbo.ai/v1"
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
            logger.info(f"OpenAI 客户端已初始化，base_url: {base_url}")
        else:
            # 使用独立的 OpenAIClient
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key is None:
                raise ValueError("OPENAI_API_KEY 环境变量未设置")
            
            openai_client = OpenAIClient(api_key=api_key)
            self.client = openai_client.client
    
    def set_model(self, model: str, provider: Optional[str] = None):
        """
        动态设置使用的模型（支持 "平台-模型" 格式）
        
        Args:
            model: 模型名称（支持 "平台-模型" 格式，如 "bailian-deepseek-chat" 或 "deepseek-deepseek-chat"）
            provider: 提供商名称（可选，如果不提供则从模型名称解析或自动检测）
        
        示例：
            llm_service.set_model("bailian-deepseek-chat")  # 明确指定百炼平台的 deepseek-chat
            llm_service.set_model("deepseek-deepseek-chat")  # 明确指定 DeepSeek 平台的 deepseek-chat
            llm_service.set_model("deepseek-chat", provider="bailian")  # 通过参数指定
        """
        registry = get_model_registry()
        
        # 解析模型名称（支持 "平台-模型" 格式）
        if provider:
            # 如果明确提供了提供商，使用提供的提供商
            target_provider = provider.lower()
            actual_model = model
        else:
            # 解析模型名称（可能包含平台前缀）
            target_provider, actual_model = registry.parse_model_name(model)
        
        # 如果检测到的提供商与当前提供商不同，需要切换提供商
        if target_provider != self.provider:
            logger.info(f"检测到模型 {model} 属于 {target_provider} 提供商，当前为 {self.provider}，正在切换...")
            self._switch_provider(target_provider)
        
        # 规范化模型名称
        normalized_model = registry.normalize_model_name(actual_model, self.provider)
        
        self.model = normalized_model
        logger.info(f"模型已切换为: {normalized_model} (提供商: {self.provider}, 原始名称: {model})")
    
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
            # 更新默认模型
            self.default_model = os.getenv("BAILIAN_MODEL", "qwen-turbo")
        elif self.provider == self.PROVIDER_OPENAI:
            self._init_openai_client()
            # 更新默认模型
            self.default_model = os.getenv("OPENAI_MODEL", "gpt-5")
        elif self.provider == self.PROVIDER_ANTHROPIC:
            self._init_anthropic_client()
            # 更新默认模型
            self.default_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        elif self.provider == self.PROVIDER_GOOGLE:
            self._init_google_client()
            # 更新默认模型
            self.default_model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        elif self.provider == self.PROVIDER_XAI:
            self._init_xai_client()
            # 更新默认模型
            self.default_model = os.getenv("XAI_MODEL", "grok-4")
        elif self.provider == self.PROVIDER_PERPLEXITY:
            self._init_perplexity_client()
            # 更新默认模型
            self.default_model = os.getenv("PERPLEXITY_MODEL", "sonar")
        else:
            self._init_deepseek_client()
            # 更新默认模型
            self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        # 恢复模型名称（如果可能）
        if current_model:
            self.model = current_model
        else:
            self.model = self.default_model
        
        logger.info(f"提供商切换完成，当前模型: {self.model}")
    
    def reset_model(self):
        """重置为默认模型"""
        self.model = self.default_model
        logger.info(f"模型已重置为默认: {self.default_model} (提供商: {self.provider})")
    
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
            
        示例:
            # 推荐代码生成模型
            models = llm_service.recommend_models("code")
            
            # 推荐推理模型（仅百炼平台）
            models = llm_service.recommend_models("reasoning", provider="bailian")
            
            # 推荐低成本文本生成模型
            models = llm_service.recommend_models("text", cost_level="low")
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
        # OpenAI O3 系列支持思考过程
        if self.provider == self.PROVIDER_OPENAI:
            if model_lower.startswith("o3") or model_lower.startswith("o4"):
                return True
        # Anthropic Claude 某些模型支持 reasoning_effort 参数（类似思考过程）
        if self.provider == self.PROVIDER_ANTHROPIC:
            # Claude 3.7 和 Claude 4 系列支持 reasoning_effort
            if "3-7" in model_lower or "opus-4" in model_lower or "sonnet-4" in model_lower or "haiku-4" in model_lower:
                return True
        # Google Gemini 某些模型支持思考过程
        if self.provider == self.PROVIDER_GOOGLE:
            # Gemini thinking 系列模型支持思考过程
            if "thinking" in model_lower:
                return True
        # xAI Grok 某些模型支持推理
        if self.provider == self.PROVIDER_XAI:
            # Grok fast-reasoning 模型支持推理
            if "reasoning" in model_lower:
                return True
        # Perplexity Sonar 某些模型支持推理
        if self.provider == self.PROVIDER_PERPLEXITY:
            # Sonar reasoning-pro 模型支持推理
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
            
            except Exception as e:
                # 处理 OpenAI SDK 的 APITimeoutError 和其他超时异常
                error_str = str(e)
                error_type = type(e).__name__
                
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
                    # 处理思考过程（DeepSeek R1 格式）
                    if self.supports_thinking:
                        if hasattr(chunk.choices[0].delta, 'reasoning_content'):
                            thinking_chunk = chunk.choices[0].delta.reasoning_content
                            if thinking_chunk:
                                thinking_chunks.append(thinking_chunk)
                    
                    # 处理内容
                    if chunk.choices[0].delta.content:
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
            # 429 错误（限流）：流式响应暂不支持重试，直接抛出
            if e.response.status_code == 429:
                logger.error(f"API 限流 (429): {e}", exc_info=True)
                raise
            logger.error(f"API 错误 {e.response.status_code}: {e}", exc_info=True)
            raise
        except httpx.RequestError as e:
            logger.error(f"网络错误: {e}", exc_info=True)
            raise

