"""model_selector 模块单元测试"""
import pytest
from unittest.mock import MagicMock, patch
from backend.core.agent.planning.model_selector import resolve_user_model, select_model
from backend.services.llm.model_config import get_model_config_manager


class TestResolveUserModel:
    """resolve_user_model 测试"""

    def test_resolve_chat_type(self):
        result = resolve_user_model("chat")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_code_type(self):
        result = resolve_user_model("code")
        expected = get_model_config_manager().get_code_model()
        assert result == expected

    def test_resolve_reasoning_type(self):
        result = resolve_user_model("reasoning")
        expected = get_model_config_manager().get_reasoning_model()
        assert result == expected

    def test_resolve_case_insensitive(self):
        result = resolve_user_model("  Chat  ")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_invalid_raises(self):
        """无效模型类型应抛出异常（通过 mock 模拟）"""
        with patch("backend.services.llm.model_config.get_model_config_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.get_model_config.side_effect = ValueError("不支持的提供商")
            mock_get.return_value = mock_manager
            with pytest.raises(ValueError):
                resolve_user_model("invalid_type")


class TestSelectModel:
    """select_model 测试"""

    @pytest.mark.asyncio
    async def test_user_override_from_context(self):
        mock_llm = MagicMock()
        result = await select_model(
            "分析这段代码",
            context={"model": "chat"},
            llm_service=mock_llm,
            complexity_analyzer=None,
        )
        expected = get_model_config_manager().get_chat_model()
        assert result == expected
        mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_code_keyword_selects_code_model(self):
        mock_llm = MagicMock()
        result = await select_model(
            "执行 ls 命令看看",
            context={},
            llm_service=mock_llm,
            complexity_analyzer=None,
        )
        expected = get_model_config_manager().get_code_model()
        assert result == expected
