"""Orchestrator 测试"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.agent.orchestrator import Orchestrator


class TestOrchestrator:
    """Orchestrator 测试类"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_process_dynamic(self, orchestrator):
        """测试动态编排处理"""
        # [MOCK] 使用 Mock 数据模拟 llm_service.chat 方法
        print("[MOCK] 测试使用 Mock 数据: llm_service.chat 返回 '测试响应'")
        with patch.object(orchestrator.llm_service, 'chat') as mock_chat:
            mock_chat.return_value = "测试响应"
            print(f"[MOCK] Mock llm_service.chat 已设置，返回值: '测试响应'")
            
            result = await orchestrator.process_dynamic("测试任务")
            
            assert result == "测试响应"
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            print(f"[MOCK] Mock chat 被调用，user_prompt: {call_args[1]['user_prompt']}")
            assert call_args[1]["user_prompt"] == "测试任务"
    
    @pytest.mark.asyncio
    async def test_process(self, orchestrator):
        """测试处理任务（调用 process_dynamic）"""
        # [MOCK] 使用 Mock 数据模拟 process_dynamic 方法
        print("[MOCK] 测试使用 Mock 数据: process_dynamic 返回 '测试响应'")
        with patch.object(orchestrator, 'process_dynamic') as mock_process:
            mock_process.return_value = "测试响应"
            print(f"[MOCK] Mock process_dynamic 已设置，返回值: '测试响应'")
            
            result = await orchestrator.process("测试任务")
            
            assert result == "测试响应"
            mock_process.assert_called_once_with("测试任务", None)
            print(f"[MOCK] Mock process_dynamic 被调用，参数: ('测试任务', None)")
    
    @pytest.mark.asyncio
    async def test_stream_process(self, orchestrator):
        """测试流式处理"""
        # [MOCK] 使用 Mock 数据模拟 llm_service.stream_chat 流式响应
        print("[MOCK] 测试使用 Mock 数据: llm_service.stream_chat 返回流式数据 ['chunk1', 'chunk2', 'chunk3']")
        async def mock_stream():
            print("[MOCK] Mock stream 生成器开始生成数据")
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        with patch.object(orchestrator.llm_service, 'stream_chat') as mock_stream_chat:
            mock_stream_chat.return_value = mock_stream()
            print("[MOCK] Mock llm_service.stream_chat 已设置为流式响应")
            
            chunks = []
            async for chunk in orchestrator.stream_process("测试任务"):
                chunks.append(chunk)
                print(f"[MOCK] 接收到流式数据块: {chunk}")
            
            assert chunks == ["chunk1", "chunk2", "chunk3"]
            mock_stream_chat.assert_called_once()
            print(f"[MOCK] Mock stream_chat 被调用一次")
    
    @pytest.mark.asyncio
    async def test_process_with_context(self, orchestrator):
        """测试带上下文的处理"""
        # [MOCK] 使用 Mock 数据模拟 process_dynamic 方法（带上下文）
        context = {"key": "value"}
        print(f"[MOCK] 测试使用 Mock 数据: process_dynamic 返回 '测试响应'，上下文: {context}")
        with patch.object(orchestrator, 'process_dynamic') as mock_process:
            mock_process.return_value = "测试响应"
            print(f"[MOCK] Mock process_dynamic 已设置，返回值: '测试响应'")
            
            result = await orchestrator.process("测试任务", context=context)
            
            assert result == "测试响应"
            mock_process.assert_called_once_with("测试任务", context)
            print(f"[MOCK] Mock process_dynamic 被调用，参数: ('测试任务', {context})")

