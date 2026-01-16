"""百炼平台视觉模型 LLM 测试"""
import pytest
import os
import asyncio
from backend.services.llm.llm_service import LLMService


class TestBailianVision:
    """百炼平台视觉模型 LLM 测试类"""
    
    @pytest.fixture
    def llm_service(self):
        """创建百炼平台 LLM 服务实例"""
        # 检查是否有 API Key
        api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            pytest.skip("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 未设置，跳过测试")
        
        return LLMService(provider="bailian", model="qwen-vl-max-2025-08-13")
    
    @pytest.mark.asyncio
    async def test_vision_model_chat_non_streaming(self, llm_service):
        """测试视觉模型非流式聊天（文本）"""
        user_prompt = "hello，你是什么模型？你能处理图像吗？"
        
        response = await llm_service.chat(user_prompt=user_prompt)
        
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"✅ 视觉模型非流式响应: {response[:100]}...")
    
    @pytest.mark.asyncio
    async def test_vision_model_chat_streaming(self, llm_service):
        """测试视觉模型流式聊天（文本）"""
        user_prompt = "hello，你是什么模型？你能处理图像吗？"
        
        chunks = []
        async for chunk in llm_service.stream_chat(user_prompt=user_prompt):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0
        print(f"✅ 视觉模型流式响应 ({len(chunks)} 个块): {full_response[:100]}...")
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", [
        "qwen-vl-max-2025-08-13",
        "qwen3-vl-plus-2025-12-19",
        "qwen3-vl-flash-2025-10-15",
        "qwen-vl-plus-latest",
    ])
    async def test_vision_models(self, model):
        """测试所有视觉模型"""
        api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            pytest.skip("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 未设置，跳过测试")
        
        llm_service = LLMService(provider="bailian", model=model)
        
        user_prompt = f"你好，我是 {model} 模型，请简单介绍一下你自己。"
        response = await llm_service.chat(user_prompt=user_prompt)
        
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"✅ {model} 测试通过: {response[:100]}...")

