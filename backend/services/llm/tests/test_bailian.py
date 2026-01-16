"""百炼平台 LLM 测试"""
import pytest
import os
import asyncio
from backend.services.llm.llm_service import LLMService


class TestBailian:
    """百炼平台 LLM 测试类"""
    
    @pytest.fixture
    def llm_service(self):
        """创建百炼平台 LLM 服务实例"""
        # 检查是否有 API Key
        api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            pytest.skip("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 未设置，跳过测试")
        
        return LLMService(provider="bailian", model="qwen-turbo")
    
    @pytest.mark.asyncio
    async def test_bailian_chat_non_streaming(self, llm_service):
        """测试百炼平台非流式聊天"""
        user_prompt = "hello，你是什么模型？"
        
        response = await llm_service.chat(user_prompt=user_prompt)
        
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"✅ 百炼平台非流式响应: {response[:100]}...")
    
    @pytest.mark.asyncio
    async def test_bailian_chat_streaming(self, llm_service):
        """测试百炼平台流式聊天"""
        user_prompt = "hello，你是什么模型？"
        
        chunks = []
        async for chunk in llm_service.stream_chat(user_prompt=user_prompt):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0
        print(f"✅ 百炼平台流式响应 ({len(chunks)} 个块): {full_response[:100]}...")

