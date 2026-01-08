"""LLM 服务"""
import os
import asyncio
import logging
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
import httpx
from shared.debug_utils import DebugOutput

logger = logging.getLogger(__name__)

class LLMService:
    """LLM 服务"""
    
    def __init__(self, temperature: float = 0.7, max_tokens: int = 2000):
        """
        初始化 LLM 服务
        
        Args:
            temperature: 温度参数，控制输出的随机性 (0.0-2.0)，默认 0.7
            max_tokens: 最大 token 数，默认 2000
        """
        # 配置管理：读取和验证 API Key
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if api_key is None:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        
        # 配置验证：API Key 格式验证
        api_key = api_key.strip()
        if not api_key or len(api_key) < 10:
            raise ValueError("API Key 格式无效：长度不足或为空")
        
        # 配置 httpx 客户端，跳过代理以避免连接超时
        # 如果系统配置了代理但代理不可用，会导致连接超时
        # 通过设置 trust_env=False 可以跳过环境变量中的代理配置
        import httpx
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),  # 连接超时 10 秒，总超时 60 秒
            trust_env=False  # 跳过环境变量中的代理配置，直接连接
        )
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            http_client=http_client
        )
        
        # 参数配置：验证和设置参数
        self.temperature = max(0.0, min(2.0, temperature))
        self.max_tokens = max(1, max_tokens)
        
        # 调试输出
        self.debug = DebugOutput()
        self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 默认模型
        self.model = self.default_model  # 当前使用的模型
    
    def set_model(self, model: str):
        """动态设置使用的模型"""
        self.model = model
        logger.info(f"模型已切换为: {model}")
    
    def reset_model(self):
        """重置为默认模型"""
        self.model = self.default_model
        logger.info(f"模型已重置为默认: {self.default_model}")
    
    @property
    def supports_thinking(self) -> bool:
        """检测模型是否支持思考过程"""
        # DeepSeek R1 模型支持思考过程
        return "r1" in self.model.lower() or "reasoning" in self.model.lower()
    
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

