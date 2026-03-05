"""ImageGenerationTool 单元测试"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from backend.core.agent.tools.builtin.image_generation_tool import ImageGenerationTool
from backend.core.agent.tools.base import ToolResult


class TestImageGenerationTool:
    """ImageGenerationTool 单元测试"""

    @pytest.fixture
    def tool(self):
        return ImageGenerationTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "image_generation"
        assert tool.description is not None
        assert len(tool.parameters) >= 4

        param_names = [p.name for p in tool.parameters]
        assert "prompt" in param_names
        assert "model" in param_names
        assert "size" in param_names
        assert "output_dir" in param_names

    def test_missing_prompt(self, tool):
        """测试缺少 prompt 参数"""
        result = tool.execute()
        assert result.success is False
        assert "prompt" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_empty_prompt(self, tool):
        """测试空 prompt"""
        result = await tool._execute_async(prompt="")
        assert result.success is False
        assert "prompt" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_success_with_base64_chat_mode(self, tool):
        """测试 Chat 场景：API 返回 base64，工具返回 image_base64"""
        mock_result = {
            "images": ["data:image/png;base64,iVBORw0KGgo="],
            "output_file": "",
            "output_dir": "",
            "prompt": "一只猫",
        }

        with patch(
            "backend.services.llm.image_gen_service.ImageGenService"
        ) as MockSvc:
            mock_svc = MagicMock()
            mock_svc.generate = AsyncMock(return_value=mock_result)
            MockSvc.return_value = mock_svc

            result = await tool._execute_async(prompt="一只猫")

        assert result.success is True
        assert result.data["prompt"] == "一只猫"
        assert result.data["image_base64"] == "data:image/png;base64,iVBORw0KGgo="

    @pytest.mark.asyncio
    async def test_success_with_output_dir(self, tool):
        """测试任务型场景：指定 output_dir，返回 output_file"""
        mock_result = {
            "images": ["data:image/png;base64,iVBORw0KGgo="],
            "output_file": "/home/user/hou-cli/outputs/images/gen_123_0.png",
            "output_dir": "/home/user/hou-cli/outputs/images",
            "prompt": "一只猫",
        }

        with patch(
            "backend.services.llm.image_gen_service.ImageGenService"
        ) as MockSvc:
            mock_svc = MagicMock()
            mock_svc.generate = AsyncMock(return_value=mock_result)
            MockSvc.return_value = mock_svc

            result = await tool._execute_async(
                prompt="一只猫",
                output_dir="/home/user/hou-cli/outputs/images",
            )

        assert result.success is True
        assert result.data["output_file"] == mock_result["output_file"]
        assert result.data["output_dir"] == mock_result["output_dir"]
        assert "image_base64" not in result.data

    @pytest.mark.asyncio
    async def test_api_returns_url_downloads_to_base64(self, tool):
        """测试 API 返回 URL 时，工具下载并转为 base64"""
        mock_result = {
            "images": ["https://example.com/image.png"],
            "output_file": "",
            "output_dir": "",
            "prompt": "一只猫",
        }

        with patch(
            "backend.services.llm.image_gen_service.ImageGenService"
        ) as MockSvc:
            mock_svc = MagicMock()
            mock_svc.generate = AsyncMock(return_value=mock_result)
            MockSvc.return_value = mock_svc

            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = MagicMock()
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.content = b"\x89PNG"
                mock_resp.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await tool._execute_async(prompt="一只猫")

        assert result.success is True
        assert "image_base64" in result.data
        assert result.data["image_base64"].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_api_returns_no_images(self, tool):
        """测试 API 未返回图片"""
        mock_result = {
            "images": [],
            "output_file": "",
            "output_dir": "",
            "prompt": "一只猫",
        }

        with patch(
            "backend.services.llm.image_gen_service.ImageGenService"
        ) as MockSvc:
            mock_svc = MagicMock()
            mock_svc.generate = AsyncMock(return_value=mock_result)
            MockSvc.return_value = mock_svc

            result = await tool._execute_async(prompt="一只猫")

        assert result.success is False
        assert "未生成图片" in result.error

    @pytest.mark.asyncio
    async def test_api_raises_exception(self, tool):
        """测试 API 抛出异常"""
        with patch(
            "backend.services.llm.image_gen_service.ImageGenService"
        ) as MockSvc:
            mock_svc = MagicMock()
            mock_svc.generate = AsyncMock(side_effect=RuntimeError("API 错误"))
            MockSvc.return_value = mock_svc

            result = await tool._execute_async(prompt="一只猫")

        assert result.success is False
        assert "API 错误" in result.error
