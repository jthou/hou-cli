"""LLM 服务"""
import os
import asyncio
import logging
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
import httpx

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
        
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 参数配置：验证和设置参数
        self.temperature = max(0.0, min(2.0, temperature))
        self.max_tokens = max(1, max_tokens)
    
    async def chat(self, system_prompt: str = "", user_prompt: str = "") -> str:
        """
        聊天（非流式）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            
        Returns:
            LLM 生成的回复
            
        Raises:
            httpx.HTTPStatusError: API 错误
            httpx.RequestError: 网络错误
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        # 错误处理：重试机制
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=False,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
                
            except httpx.HTTPStatusError as e:
                # 401 错误（认证失败）：不重试
                if e.response.status_code == 401:
                    logger.error(f"API 认证失败: {e}")
                    raise
                
                # 429 错误（限流）：等待 2 秒后重试
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning(f"API 限流，等待 2 秒后重试 (尝试 {attempt + 1}/{max_retries})")
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error(f"API 限流，重试次数耗尽: {e}")
                        raise
                
                # 其他 HTTP 错误：重试
                if attempt < max_retries - 1:
                    logger.warning(f"API 错误 {e.response.status_code}，1 秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"API 错误，重试次数耗尽: {e}")
                    raise
                    
            except httpx.RequestError as e:
                # 网络错误：重试
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"网络错误，1 秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"网络错误，重试次数耗尽: {e}")
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
        
        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="deepseek-chat",
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
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except KeyboardInterrupt:
                # 优雅处理中断
                logger.info("流式响应被用户中断")
                return
            except Exception as e:
                logger.error(f"流式响应处理错误: {e}")
                raise
                
        except asyncio.TimeoutError:
            logger.error(f"流式响应超时（{timeout} 秒）")
            raise
        except httpx.HTTPStatusError as e:
            # 401 错误（认证失败）：不重试
            if e.response.status_code == 401:
                logger.error(f"API 认证失败: {e}")
                raise
            # 429 错误（限流）：等待后重试（流式响应暂不支持重试，直接抛出）
            if e.response.status_code == 429:
                logger.error(f"API 限流: {e}")
                raise
            logger.error(f"API 错误: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"网络错误: {e}")
            raise

