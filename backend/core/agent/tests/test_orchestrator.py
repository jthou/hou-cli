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
        context = {"session_id": "test_session_123"}
        print(f"[MOCK] 测试使用 Mock 数据: process_dynamic 返回 '测试响应'，上下文: {context}")
        with patch.object(orchestrator, 'process_dynamic') as mock_process:
            mock_process.return_value = "测试响应"
            print(f"[MOCK] Mock process_dynamic 已设置，返回值: '测试响应'")
            
            result = await orchestrator.process("测试任务", context=context)
            
            assert result == "测试响应"
            mock_process.assert_called_once_with("测试任务", context)
            print(f"[MOCK] Mock process_dynamic 被调用，参数: ('测试任务', {context})")
    
    @pytest.mark.asyncio
    async def test_orchestrator_context_management(self, orchestrator):
        """测试 Orchestrator 的上下文管理"""
        # [MOCK] 使用 Mock 数据模拟 LLM Service
        print("[MOCK] 测试使用 Mock 数据: Orchestrator 上下文管理")
        session_id = "test_session_123"
        
        # 第一轮对话
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "你好！我是智能助手。"
            print("[MOCK] Mock chat 返回: '你好！我是智能助手。'")
            
            response1 = await orchestrator.process("你好", context={"session_id": session_id})
            assert response1 == "你好！我是智能助手。"
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 2  # user + assistant
            print(f"[MOCK] 第一轮历史消息数: {len(history)}")
        
        # 第二轮对话（应该包含历史）
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 验证 user_prompt 包含历史
            def check_history_in_prompt(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                assert "你好" in user_prompt or "智能助手" in user_prompt
                print(f"[MOCK] user_prompt 包含历史: {len(user_prompt) > 10}")
                return "我刚才说我是智能助手。"
            
            mock_chat.side_effect = check_history_in_prompt
            
            response2 = await orchestrator.process("我刚才说了什么？", context={"session_id": session_id})
            assert response2 == "我刚才说我是智能助手。"
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 4  # 2轮对话，每轮2条消息
            print(f"[MOCK] 第二轮历史消息数: {len(history)}")
    
    @pytest.mark.asyncio
    async def test_stream_with_context(self, orchestrator):
        """测试流式响应的上下文管理"""
        # [MOCK] 使用 Mock 数据模拟流式响应
        print("[MOCK] 测试使用 Mock 数据: 流式响应上下文管理")
        session_id = "test_stream_123"
        
        async def mock_stream():
            yield "流式"
            yield "回复"
            yield "内容"
        
        with patch.object(orchestrator.llm_service, 'stream_chat', return_value=mock_stream()):
            chunks = []
            async for chunk in orchestrator.stream_process("测试", context={"session_id": session_id}):
                chunks.append(chunk)
            
            assert chunks == ["流式", "回复", "内容"]
            print(f"[MOCK] 流式响应: {''.join(chunks)}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 2  # user + assistant
            print(f"[MOCK] 流式响应历史消息数: {len(history)}")
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, orchestrator):
        """测试多轮对话的上下文连贯性"""
        # [MOCK] 使用 Mock 数据模拟多轮对话
        print("[MOCK] 测试使用 Mock 数据: 多轮对话上下文连贯性")
        session_id = "multi_turn_test_123"
        
        # 第一轮：自我介绍
        user_msg1 = "你好，我的名字是张三"
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "你好张三！很高兴认识你。"
            print(f"[MOCK] 第一轮: 用户: {user_msg1}")
            
            response1 = await orchestrator.process(user_msg1, context={"session_id": session_id})
            assert response1 == "你好张三！很高兴认识你。"
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 2
            assert history[0]["content"] == user_msg1
            assert history[1]["content"] == response1
        
        # 第二轮：询问名字（应该记住）
        user_msg2 = "你还记得我的名字吗？"
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 验证 user_prompt 包含第一轮的历史
            def check_context(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                # 验证包含历史
                assert "张三" in user_prompt or "名字" in user_prompt
                print(f"[MOCK] user_prompt 包含'张三': {'张三' in user_prompt}")
                return "当然记得！你的名字是张三。"
            
            mock_chat.side_effect = check_context
            print(f"[MOCK] 第二轮: 用户: {user_msg2}")
            
            response2 = await orchestrator.process(user_msg2, context={"session_id": session_id})
            assert response2 == "当然记得！你的名字是张三。"
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 4
        
        # 第三轮：继续对话
        user_msg3 = "很好，谢谢"
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            def check_context_again(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                # 应该包含前两轮的历史
                assert len(user_prompt) > 50  # 包含历史，应该比较长
                print(f"[MOCK] user_prompt 长度: {len(user_prompt)} (包含历史)")
                return "不客气！有什么其他问题吗？"
            
            mock_chat.side_effect = check_context_again
            print(f"[MOCK] 第三轮: 用户: {user_msg3}")
            
            response3 = await orchestrator.process(user_msg3, context={"session_id": session_id})
            assert response3 == "不客气！有什么其他问题吗？"
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            assert len(history) == 6
        
        # 验证历史内容
        history = orchestrator.context_manager.get_history(session_id)
        assert history[0]["role"] == "user"
        assert history[0]["content"] == user_msg1
        assert history[-1]["role"] == "assistant"
        print(f"[MOCK] 多轮对话测试通过，总历史消息数: {len(history)}")

