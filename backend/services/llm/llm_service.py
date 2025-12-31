"""LLM 服务"""
import os
from typing import AsyncIterator
from openai import AsyncOpenAI

class LLMService:
    """LLM 服务"""
    
    def __init__(self):
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        else:
            self.client = None
    
    async def chat(self, system_prompt: str = "", user_prompt: str = "") -> str:
        """聊天（非流式）"""
        if not self.client:
            return "LLM 服务未配置"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        response = await self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, system_prompt: str = "", user_prompt: str = "") -> AsyncIterator[str]:
        """流式聊天"""
        if not self.client:
            yield "LLM 服务未配置"
            return
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        stream = await self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

