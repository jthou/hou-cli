"""ImageGenService 单元测试"""
import base64
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from backend.services.llm.image_gen_service import ImageGenService


class TestImageGenService:
    """ImageGenService 单元测试"""

    def test_init_default_model(self):
        """测试默认模型"""
        svc = ImageGenService()
        assert svc._default_model == "wan2.6-t2i"

    def test_init_custom_model(self):
        """测试自定义模型"""
        svc = ImageGenService(model="qwen-image-max-2025-12-30")
        assert svc._default_model == "qwen-image-max-2025-12-30"

    @pytest.mark.asyncio
    async def test_generate_parses_api_response_base64(self):
        """测试解析 API 返回的 base64 图片"""
        fake_b64 = base64.b64encode(b"\x89PNG").decode()
        api_response = {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "image", "image": f"data:image/png;base64,{fake_b64}"}
                            ]
                        }
                    }
                ]
            }
        }

        with patch(
            "backend.services.llm.image_gen_service.httpx.AsyncClient"
        ) as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = api_response
            mock_post = AsyncMock(return_value=mock_resp)
            mock_client_instance = MagicMock()
            mock_client_instance.post = mock_post
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            svc = ImageGenService()
            with patch.object(svc, "_get_api_config") as mock_config:
                mock_config.return_value = {
                    "api_key": "test-key",
                    "api_url": "https://test.com/api",
                    "model": "wan2.6-t2i",
                }
                result = await svc.generate(prompt="一只猫")

        assert len(result["images"]) == 1
        assert result["images"][0].startswith("data:image/png;base64,")
        assert result["prompt"] == "一只猫"

    @pytest.mark.asyncio
    async def test_generate_saves_to_output_dir(self):
        """测试指定 output_dir 时保存到该目录"""
        tmp_dir = Path.home() / ".cache" / "hou-cli-test-image-gen"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            fake_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
            api_response = {
                "output": {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "image", "image": f"data:image/png;base64,{fake_b64}"}
                                ]
                            }
                        }
                    ]
                }
            }

            with patch(
                "backend.services.llm.image_gen_service.httpx.AsyncClient"
            ) as MockClient:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = api_response
                mock_post = AsyncMock(return_value=mock_resp)
                mock_client_instance = MagicMock()
                mock_client_instance.post = mock_post
                mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                MockClient.return_value = mock_client_instance

                svc = ImageGenService()
                with patch.object(svc, "_get_api_config") as mock_config:
                    mock_config.return_value = {
                        "api_key": "test-key",
                        "api_url": "https://test.com/api",
                        "model": "wan2.6-t2i",
                    }
                    result = await svc.generate(
                        prompt="一只猫",
                        output_dir=str(tmp_dir),
                    )

            assert result["output_file"]
            assert result["output_dir"] == str(tmp_dir.resolve())
            assert Path(result["output_file"]).exists()
            assert Path(result["output_file"]).suffix == ".png"
        finally:
            for f in tmp_dir.glob("gen_*.png"):
                f.unlink()
            if tmp_dir.exists() and not any(tmp_dir.iterdir()):
                tmp_dir.rmdir()

    @pytest.mark.asyncio
    async def test_generate_http_error_raises(self):
        """测试 API 返回非 200 时抛出异常"""
        with patch(
            "backend.services.llm.image_gen_service.httpx.AsyncClient"
        ) as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_post = AsyncMock(return_value=mock_resp)
            mock_client_instance = MagicMock()
            mock_client_instance.post = mock_post
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            svc = ImageGenService()
            with patch.object(svc, "_get_api_config") as mock_config:
                mock_config.return_value = {
                    "api_key": "test-key",
                    "api_url": "https://test.com/api",
                    "model": "wan2.6-t2i",
                }
                with pytest.raises(RuntimeError, match="HTTP 500"):
                    await svc.generate(prompt="一只猫")

    @pytest.mark.asyncio
    async def test_generate_empty_images_raises(self):
        """测试 API 未返回图片时抛出异常"""
        api_response = {"output": {"choices": [{"message": {"content": []}}]}}

        with patch(
            "backend.services.llm.image_gen_service.httpx.AsyncClient"
        ) as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = api_response
            mock_post = AsyncMock(return_value=mock_resp)
            mock_client_instance = MagicMock()
            mock_client_instance.post = mock_post
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            svc = ImageGenService()
            with patch.object(svc, "_get_api_config") as mock_config:
                mock_config.return_value = {
                    "api_key": "test-key",
                    "api_url": "https://test.com/api",
                    "model": "wan2.6-t2i",
                }
                with pytest.raises(RuntimeError, match="未返回图片"):
                    await svc.generate(prompt="一只猫")
