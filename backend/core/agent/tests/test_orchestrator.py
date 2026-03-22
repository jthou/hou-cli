"""Orchestrator 测试"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.agent.orchestrator import Orchestrator
from backend.core.context.models import MessageRole


def _content_chunks(chunks):
    """从流式输出中提取纯内容块（排除 __DEBUG__、__TOOL__、__STATUS__、__EVALUATION__ 等）"""
    skip_prefixes = ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__", "__ORCH_TRACE__")
    return [c for c in chunks if not any(c.startswith(p) for p in skip_prefixes)]


class TestOrchestrator:
    """Orchestrator 测试类"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_process_dynamic(self, orchestrator):
        """测试动态编排处理"""
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "测试响应"
            result = await orchestrator.process_dynamic("测试任务")
            assert result == "测试响应"
            assert mock_chat.call_count >= 1
            # process_dynamic 使用 _chat_with_tools，内部调用 chat(messages=..., tools=...)
            last_call = mock_chat.call_args
            if last_call.kwargs.get("messages"):
                msgs = last_call.kwargs["messages"]
                user_msgs = [m for m in msgs if m.get("role") == "user"]
                assert any("测试任务" in (m.get("content") or "") for m in user_msgs)
    
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
        """测试流式处理：验证输出包含 LLM 返回的内容块"""
        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        with patch.object(orchestrator.llm_service, 'stream_chat', return_value=mock_stream()):
            chunks = []
            async for chunk in orchestrator.stream_process("测试任务"):
                chunks.append(chunk)
            content = "".join(_content_chunks(chunks))
            assert "chunk1" in content and "chunk2" in content and "chunk3" in content
            assert content == "chunk1chunk2chunk3"
    
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
        """测试 Orchestrator 的上下文管理：历史消息被正确保存和传递"""
        session_id = "test_session_ctx_mgmt"
        with patch.object(orchestrator.skill_registry, 'match', new_callable=AsyncMock, return_value=None):
            # 第一轮对话
            with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = "你好！我是智能助手。"
                response1 = await orchestrator.process("你好", context={"session_id": session_id})
                assert response1 == "你好！我是智能助手。"
                history = orchestrator.context_manager.get_messages(session_id, compressed=False)
                assert len(history) >= 2
                assert history[0].content == "你好"
                assert history[1].content == "你好！我是智能助手。"
            
            # 第二轮对话：验证 user_prompt/messages 包含历史
            with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
                def check_history(*args, **kwargs):
                    msgs = kwargs.get('messages', [])
                    combined = " ".join(m.get("content", "") or "" for m in msgs)
                    assert "你好" in combined or "智能助手" in combined, f"历史未注入: {combined[:100]}"
                    return "我刚才说我是智能助手。"
                mock_chat.side_effect = check_history
                response2 = await orchestrator.process("我刚才说了什么？", context={"session_id": session_id})
                assert response2 == "我刚才说我是智能助手。"
                history = orchestrator.context_manager.get_messages(session_id, compressed=False)
                assert len(history) >= 4
    
    @pytest.mark.asyncio
    async def test_stream_with_context(self, orchestrator):
        """测试流式响应的上下文管理"""
        session_id = "test_stream_ctx_123"
        async def mock_stream():
            yield "流式"
            yield "回复"
            yield "内容"
        
        with patch.object(orchestrator.llm_service, 'stream_chat', return_value=mock_stream()):
            chunks = []
            async for chunk in orchestrator.stream_process("测试", context={"session_id": session_id}):
                chunks.append(chunk)
            content = "".join(_content_chunks(chunks))
            assert content == "流式回复内容"
            history = orchestrator.context_manager.get_messages(session_id, compressed=False)
            assert len(history) >= 2  # user + assistant
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, orchestrator):
        """测试多轮对话的上下文连贯性"""
        session_id = "multi_turn_test_123"
        
        user_msg1 = "你好，我的名字是张三"
        with patch.object(orchestrator.skill_registry, 'match', new_callable=AsyncMock, return_value=None):
            # 第一轮
            with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = "你好张三！很高兴认识你。"
                response1 = await orchestrator.process(user_msg1, context={"session_id": session_id})
                assert response1 == "你好张三！很高兴认识你。"
                history = orchestrator.context_manager.get_messages(session_id, compressed=False)
                assert len(history) >= 2
                assert history[0].content == user_msg1
                assert history[1].content == response1
            
            # 第二轮：验证包含第一轮历史
            with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
                def check_context(*args, **kwargs):
                    msgs = kwargs.get('messages', [])
                    combined = " ".join(m.get("content", "") or "" for m in msgs)
                    assert "张三" in combined or "名字" in combined
                    return "当然记得！你的名字是张三。"
                mock_chat.side_effect = check_context
                response2 = await orchestrator.process("你还记得我的名字吗？", context={"session_id": session_id})
                assert response2 == "当然记得！你的名字是张三。"
                history = orchestrator.context_manager.get_messages(session_id, compressed=False)
                assert len(history) >= 4
            
            # 第三轮：验证历史较长
            with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
                def check_context_again(*args, **kwargs):
                    msgs = kwargs.get('messages', [])
                    combined = " ".join(m.get("content", "") or "" for m in msgs)
                    assert len(combined) > 50
                    return "不客气！有什么其他问题吗？"
                mock_chat.side_effect = check_context_again
                response3 = await orchestrator.process("很好，谢谢", context={"session_id": session_id})
                assert response3 == "不客气！有什么其他问题吗？"
            
            history = orchestrator.context_manager.get_messages(session_id, compressed=False)
            assert len(history) >= 6
            assert history[0].role == MessageRole.USER
            assert history[0].content == user_msg1
            assert history[-1].role == MessageRole.ASSISTANT

