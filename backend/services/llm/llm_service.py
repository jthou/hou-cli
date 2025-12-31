"""LLM 服务"""
import os
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
        """聊天"""
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

