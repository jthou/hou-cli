"""模型使用时可选择 - 单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from backend.core.agent.orchestrator import Orchestrator
from backend.services.llm.model_config import get_model_config_manager


class TestResolveUserModel:
    """_resolve_user_model 解析逻辑测试（同步方法，无需 async）"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_resolve_chat_type(self, orchestrator):
        """chat -> get_chat_model()"""
        result = orchestrator._resolve_user_model("chat")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_code_type(self, orchestrator):
        """code -> get_code_model()"""
        result = orchestrator._resolve_user_model("code")
        expected = get_model_config_manager().get_code_model()
        assert result == expected

    def test_resolve_reasoning_type(self, orchestrator):
        """reasoning -> get_reasoning_model()"""
        result = orchestrator._resolve_user_model("reasoning")
        expected = get_model_config_manager().get_reasoning_model()
        assert result == expected

    def test_resolve_case_insensitive(self, orchestrator):
        """Chat、CODE 等大小写应被归一化"""
        result = orchestrator._resolve_user_model("  Chat  ")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_concrete_model_name(self, orchestrator):
        """具体模型名 -> 校验通过后返回规范化名称"""
        with patch("backend.services.llm.model_config.get_model_config_manager") as mock_get:
            mock_config = MagicMock()
            mock_config.model_name = "deepseek-chat"
            mock_manager = MagicMock()
            mock_manager.get_model_config.return_value = mock_config
            mock_get.return_value = mock_manager
            result = orchestrator._resolve_user_model("deepseek-chat")
            assert result == "deepseek-chat"
            mock_manager.get_model_config.assert_called_once_with("deepseek-chat")

    def test_resolve_invalid_raises(self, orchestrator):
        """无效模型类型（无法通过 get_model_config 校验）应抛出 ValueError"""
        with patch("backend.services.llm.model_config.get_model_config_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.get_model_config.side_effect = ValueError("不支持的提供商")
            mock_get.return_value = mock_manager
            with pytest.raises(ValueError):
                orchestrator._resolve_user_model("invalid_type")


class TestSelectModelWithUserOverride:
    """_select_model 在 context 含 model 时的行为"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_user_override_chat(self, orchestrator):
        """context.model=chat 时跳过智能选择"""
        context = {"model": "chat"}
        result = await orchestrator._select_model("分析这段代码", context=context)
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_user_override_reasoning(self, orchestrator):
        """context.model=reasoning 时使用推理模型"""
        context = {"model": "reasoning"}
        result = await orchestrator._select_model("今天天气怎么样", context=context)
        expected = get_model_config_manager().get_reasoning_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_no_override_uses_smart_selection(self, orchestrator):
        """context 无 model 时走智能选择"""
        context = {}
        result = await orchestrator._select_model("你好", context=context)
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_none_context_same_as_empty(self, orchestrator):
        """context=None 与 context={} 行为一致"""
        r1 = await orchestrator._select_model("你好", context=None)
        r2 = await orchestrator._select_model("你好", context={})
        assert r1 == r2
