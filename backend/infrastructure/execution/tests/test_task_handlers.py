"""
任务处理器测试 - 与 docs/design/task-management-and-display.md 约定一致。

约定：成功时返回 dict 含 "status": "success"、"summary"（一句摘要）、类型相关 "data" 或 "result"。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.infrastructure.execution.task_handlers import (
    process_video_download_task,
    process_weather_query_task,
)


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
                "backend.core.agent.tools.builtin.weather_tool.get_weather_tool"
            ) as m_tool:
                mock_tool_instance = MagicMock()
                mock_tool_instance.get_current_weather.return_value = fake_weather
                m_tool.return_value = mock_tool_instance
                with patch(
                    "backend.core.agent.tools.auth.jwt_auth.JWTAuth"
                ) as m_jwt:
                    m_jwt.return_value = MagicMock()
                    out = await process_weather_query_task(task_info)

        assert out["status"] == "success"
        assert "summary" in out
        assert isinstance(out["summary"], str)
        assert "result" in out
        assert "current_weather" in out["result"] or "location" in out
