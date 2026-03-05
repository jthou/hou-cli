"""TextToImagePromptTool 单元测试"""
import pytest
from unittest.mock import AsyncMock, patch

from backend.core.agent.tools.builtin.text_to_image_prompt_tool import (
    TextToImagePromptTool,
    TEXT_TO_PROMPT_SYSTEM,
)


class TestTextToImagePromptTool:
    """TextToImagePromptTool 单元测试"""

    @pytest.fixture
    def tool(self):
        return TextToImagePromptTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "text_to_image_prompt"
        assert tool.description is not None
        assert len(tool.parameters) >= 3

        param_names = [p.name for p in tool.parameters]
        assert "text" in param_names
        assert "max_length" in param_names
        assert "style_hint" in param_names

    def test_system_prompt_defined(self):
        """测试系统提示已定义"""
        assert TEXT_TO_PROMPT_SYSTEM is not None
        assert "图片提示词专家" in TEXT_TO_PROMPT_SYSTEM
        assert "50" in TEXT_TO_PROMPT_SYSTEM

    def test_missing_text(self, tool):
        """测试缺少 text 参数"""
        result = tool.execute()
        assert result.success is False
        assert "text" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_empty_text(self, tool):
        """测试空 text"""
        result = await tool._execute_async(text="")
        assert result.success is False
        assert "text" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_success_with_llm_response(self, tool):
        """测试 LLM 提炼成功"""
        refined_prompt = "一只橘猫在阳光下打盹，写实风格，温暖色调"

        with patch.object(
            tool.llm_service, "chat", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = refined_prompt

            result = await tool._execute_async(
                text="这是一篇关于猫咪的文章，内容很长..."
            )

        assert result.success is True
        assert result.data["prompt"] == refined_prompt
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs.get("system_prompt") == TEXT_TO_PROMPT_SYSTEM
        user_prompt = call_kwargs.kwargs.get("user_prompt", "")
        assert "这是一篇关于猫咪的文章" in user_prompt

    @pytest.mark.asyncio
    async def test_with_style_hint(self, tool):
        """测试带 style_hint 参数"""
        refined_prompt = "水彩风格，一只橘猫"

        with patch.object(
            tool.llm_service, "chat", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = refined_prompt

            result = await tool._execute_async(
                text="一只橘猫",
                style_hint="水彩",
            )

        assert result.success is True
        assert result.data["prompt"] == refined_prompt
        call_kwargs = mock_chat.call_args
        assert "风格要求" in call_kwargs.kwargs.get("user_prompt", "")
        assert "水彩" in call_kwargs.kwargs.get("user_prompt", "")

    @pytest.mark.asyncio
    async def test_llm_returns_empty(self, tool):
        """测试 LLM 返回空"""
        with patch.object(
            tool.llm_service, "chat", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = ""

            result = await tool._execute_async(text="一些长文本")

        assert result.success is False
        assert "未返回有效提示词" in result.error

    @pytest.mark.asyncio
    async def test_llm_raises_exception(self, tool):
        """测试 LLM 抛出异常"""
        with patch.object(
            tool.llm_service, "chat", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = RuntimeError("LLM 连接失败")

            result = await tool._execute_async(text="一些长文本")

        assert result.success is False
        assert "LLM 连接失败" in result.error
