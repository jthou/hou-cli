"""
任务处理器测试 - 与 docs/design/task-management-and-display.md 及任务管理验证规范一致。

约定：成功时返回 dict 含 "status": "success"、"summary"（一句摘要）、类型相关 "data" 或 "result"。
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from dotenv import load_dotenv

from backend.infrastructure.execution.task_handlers import (
    process_video_download_task,
    process_weather_query_task,
    validate_task_creation,
)

# 加载 .env：与 backend/main.py 一致——用户配置目录、项目根、当前目录
_env_paths = [
    Path.home() / ".config" / "hou-cli" / ".env",
    Path(__file__).resolve().parents[4] / ".env",
    Path.cwd() / ".env",
]
for _env in _env_paths:
    if _env.exists():
        load_dotenv(_env, override=True)
        break
else:
    load_dotenv()


class TestTaskHandlerResultShape:
    """断言 handler 返回结构符合「任务管理与展示」设计"""

    @pytest.mark.asyncio
    async def test_video_download_success_return_shape(self):
        """video_download 成功时返回含 status、summary、data"""
        task_info = {
            "task_id": "t1",
            "task_type": "video_download",
            "task_name": "下载",
            "metadata": {"url": "https://example.com/v", "quality": "best"},
        }
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"output_dir": "/path/to/dir", "title": "视频标题"}
        mock_result.error = None

        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            with patch(
                "backend.infrastructure.execution.task_handlers.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                out = await process_video_download_task(task_info)

        assert out["status"] == "success"
        assert "summary" in out
        assert isinstance(out["summary"], str)
        assert len(out["summary"]) > 0
        assert "data" in out
        assert out["data"]["output_dir"] == "/path/to/dir"
        assert out["data"]["title"] == "视频标题"

    @pytest.mark.asyncio
    async def test_weather_query_success_return_shape(self):
        """weather_query 成功时返回含 status、summary、result"""
        task_info = {
            "task_id": "t1",
            "task_type": "weather_query",
            "task_name": "天气",
            "metadata": {"location": "北京", "query_type": "current"},
        }
        fake_weather = {"temp": 25, "text": "晴"}

        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            with patch(
                "backend.core.agent.tools.builtin.weather_tool.WeatherTool"
            ) as m_weather_tool:
                mock_tool_instance = MagicMock()
                mock_tool_instance.get_current_weather.return_value = fake_weather
                m_weather_tool.return_value = mock_tool_instance
                with patch(
                    "backend.core.agent.tools.auth.jwt_auth.JWTAuth.from_env"
                ) as m_jwt:
                    m_jwt.return_value = MagicMock()
                    out = await process_weather_query_task(task_info)

        assert out["status"] == "success"
        assert "summary" in out
        assert isinstance(out["summary"], str)
        assert "result" in out
        assert "current_weather" in out["result"] or "location" in out


class TestTaskHandlerValidation:
    """Handler 执行时对必填参数的校验（与验证规范一致）"""

    @pytest.mark.asyncio
    async def test_weather_query_missing_location_raises(self):
        """weather_query 缺少 location 时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "weather_query",
            "metadata": {},
        }
        with pytest.raises(ValueError, match="location 参数是必需的"):
            await process_weather_query_task(task_info)

    @pytest.mark.asyncio
    async def test_weather_query_empty_location_raises(self):
        """weather_query location 为空字符串时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "weather_query",
            "metadata": {"location": "   "},
        }
        with pytest.raises(ValueError, match="location 参数是必需的"):
            await process_weather_query_task(task_info)

    @pytest.mark.asyncio
    async def test_video_download_missing_url_raises(self):
        """video_download 缺少 url 时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "video_download",
            "metadata": {},
        }
        with pytest.raises(ValueError, match="url 参数是必需的"):
            await process_video_download_task(task_info)


class TestValidateTaskCreation:
    """通用任务创建校验 validate_task_creation（任务管理验证规范）"""

    def test_valid_weather_query(self):
        ok, err = validate_task_creation("weather_query", {"location": "北京"})
        assert ok is True
        assert err is None

    def test_valid_weather_query_with_enum(self):
        ok, err = validate_task_creation(
            "weather_query", {"location": "上海", "query_type": "forecast"}
        )
        assert ok is True
        assert err is None

    def test_valid_weather_query_warning(self):
        ok, err = validate_task_creation(
            "weather_query", {"location": "北京", "query_type": "warning"}
        )
        assert ok is True
        assert err is None

    def test_valid_weather_query_air_quality(self):
        ok, err = validate_task_creation(
            "weather_query", {"location": "深圳", "query_type": "air_quality"}
        )
        assert ok is True
        assert err is None

    def test_invalid_task_type(self):
        ok, err = validate_task_creation("unknown_type", {})
        assert ok is False
        assert "无效的任务类型" in err
        assert "unknown_type" in err

    def test_weather_query_missing_location(self):
        ok, err = validate_task_creation("weather_query", {})
        assert ok is False
        assert "缺少必填参数" in err
        assert "location" in err

    def test_weather_query_empty_location(self):
        ok, err = validate_task_creation("weather_query", {"location": "   "})
        assert ok is False
        assert "必填参数不能为空" in err
        assert "location" in err

    def test_video_download_missing_url(self):
        ok, err = validate_task_creation("video_download", {})
        assert ok is False
        assert "缺少必填参数" in err
        assert "url" in err

    def test_weather_query_invalid_query_type_enum(self):
        ok, err = validate_task_creation(
            "weather_query", {"location": "北京", "query_type": "invalid"}
        )
        assert ok is False
        assert "query_type" in err
        assert "取值无效" in err

    def test_metadata_not_dict_treated_as_empty(self):
        """非 dict 的 metadata 按空 dict 处理，weather_query 必填 location 仍报错"""
        ok, err = validate_task_creation("weather_query", None)
        assert ok is False
        assert "location" in err


class TestWeatherQueryLiveEnv:
    """使用 .env 配置的真实天气任务处理（未配置时跳过）"""

    def _skip_if_no_weather_env(self):
        if not os.getenv("WEATHER_JWT_PRIVATE_KEY") or not os.getenv("QWEATHER_API_HOST"):
            pytest.skip(
                "需要 .env 中配置 WEATHER_JWT_PRIVATE_KEY、QWEATHER_CREDENTIAL_ID、"
                "QWEATHER_PROJECT_ID、QWEATHER_API_HOST"
            )

    @pytest.mark.asyncio
    async def test_process_weather_query_task_live_current(self):
        """使用 .env 执行天气查询任务（实时），校验返回 status/summary/result"""
        self._skip_if_no_weather_env()
        task_info = {
            "task_id": "live-1",
            "task_type": "weather_query",
            "task_name": "天气",
            "metadata": {"location": "北京", "query_type": "current"},
        }
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            try:
                out = await process_weather_query_task(task_info)
            except Exception as e:
                if "401" in str(e):
                    pytest.skip(f"和风 API 返回 401，请检查 .env 中 JWT 配置: {e}")
                raise
        assert out["status"] == "success"
        assert isinstance(out.get("summary"), str)
        assert "result" in out
        assert "current_weather" in out["result"] or "summary" in str(out)

    @pytest.mark.asyncio
    async def test_process_weather_query_task_live_forecast(self):
        """使用 .env 执行天气查询任务（预报），校验返回含 forecast"""
        self._skip_if_no_weather_env()
        task_info = {
            "task_id": "live-2",
            "task_type": "weather_query",
            "task_name": "天气",
            "metadata": {"location": "上海", "query_type": "forecast"},
        }
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            try:
                out = await process_weather_query_task(task_info)
            except Exception as e:
                if "401" in str(e):
                    pytest.skip(f"和风 API 返回 401，请检查 .env 中 JWT 配置: {e}")
                raise
        assert out["status"] == "success"
        assert "result" in out
        assert "daily" in out["result"] and isinstance(out["result"].get("daily"), list)
