"""
任务处理器测试 - 与 docs/design/task-management-and-display.md 及任务管理验证规范一致。

约定：成功时返回 dict 含 "status": "success"、"summary"（一句摘要）、类型相关 "data" 或 "result"。
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from backend.infrastructure.execution.task_handlers import (
    _fix_doubled_pdf_text,
    _validate_input_path_in_home,
    _validate_video_download_url,
    process_video_download_task,
    process_video_extract_audio_task,
    process_weather_query_task,
    process_web_search_task,
    process_speech_to_text_task,
    process_image_generation_task,
    validate_task_creation,
    get_available_task_types,
    get_linkable_upstream_types,
)


class TestFixDoubledPdfText:
    """PDF 提取「每字重复」修复逻辑"""

    def test_doubled_text_even_length(self):
        s = "TThhrroouugghh iinnssiigghhttss"
        assert _fix_doubled_pdf_text(s) == "Through insights"

    def test_doubled_text_with_spaces(self):
        s = "TThhee  qquuiicckk  bbrroowwnn"
        assert _fix_doubled_pdf_text(s) == "The quick brown"

    def test_normal_text_unchanged(self):
        s = "Through insights we gathered"
        assert _fix_doubled_pdf_text(s) == s

    def test_short_text_unchanged(self):
        assert _fix_doubled_pdf_text("") == ""
        assert _fix_doubled_pdf_text("ab") == "ab"
        assert _fix_doubled_pdf_text("abc") == "abc"


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
    async def test_web_search_missing_query_raises(self):
        """web_search 缺少 query 时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "web_search",
            "metadata": {},
        }
        with pytest.raises(ValueError, match="query 参数是必需的"):
            await process_web_search_task(task_info)

    @pytest.mark.asyncio
    async def test_web_search_empty_query_raises(self):
        """web_search query 为空字符串时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "web_search",
            "metadata": {"query": "   "},
        }
        with pytest.raises(ValueError, match="query 参数是必需的"):
            await process_web_search_task(task_info)

    @pytest.mark.asyncio
    async def test_web_search_success_return_shape(self):
        """web_search 成功时返回 status、summary、result.results"""
        from backend.services.google_search_service.models import (
            GoogleSearchResponse,
            GoogleSearchResult,
        )
        task_info = {
            "task_id": "t1",
            "task_type": "web_search",
            "metadata": {"query": "python", "num_results": 2},
        }
        mock_response = GoogleSearchResponse(
            results=[
                GoogleSearchResult(
                    title="Python", link="https://python.org", snippet="...", display_link="python.org"
                ),
            ],
            total_results=None,
            search_time=0.5,
            query="python",
        )
        with patch(
            "backend.services.google_search_service.unified_search.web_search",
            return_value=mock_response,
        ):
            out = await process_web_search_task(task_info)
        assert out.get("status") == "success"
        assert "summary" in out
        assert "result" in out
        assert "results" in out["result"]
        assert len(out["result"]["results"]) == 1
        assert out["result"]["results"][0]["title"] == "Python"

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

    @pytest.mark.asyncio
    async def test_video_download_invalid_url_raises(self):
        """video_download 使用禁止的 URL（内网/非 http(s)）时应抛出 ValueError"""
        task_info = {
            "task_id": "t1",
            "task_type": "video_download",
            "metadata": {"url": "http://127.0.0.1/video"},
        }
        with pytest.raises(ValueError, match="不允许"):
            await process_video_download_task(task_info)


class TestVideoDownloadUrlValidation:
    """视频下载 URL 校验（SSRF 防护）"""

    def test_valid_https(self):
        ok, err = _validate_video_download_url("https://www.bilibili.com/video/BV123")
        assert ok is True
        assert err is None

    def test_valid_http(self):
        ok, err = _validate_video_download_url("http://example.com/path")
        assert ok is True
        assert err is None

    def test_empty_fails(self):
        ok, err = _validate_video_download_url("")
        assert ok is False
        assert "不能为空" in err

    def test_no_scheme_video_domain_auto_prepend(self):
        """常见视频域名（如 b23.tv）缺少协议时自动补全 https://"""
        ok, err = _validate_video_download_url("b23.tv/xxx")
        assert ok is True
        assert err is None

    def test_no_scheme_unknown_domain_fails(self):
        """非视频域名且过短（如 x.y）不补全"""
        ok, err = _validate_video_download_url("x.y")
        assert ok is False
        assert "http" in err or "https" in err

    def test_file_scheme_fails(self):
        ok, err = _validate_video_download_url("file:///etc/passwd")
        assert ok is False
        assert "http" in err or "https" in err

    def test_localhost_fails(self):
        ok, err = _validate_video_download_url("http://localhost/v")
        assert ok is False
        assert "本地" in err or "不允许" in err

    def test_127_loopback_fails(self):
        ok, err = _validate_video_download_url("http://127.0.0.1/v")
        assert ok is False
        assert "内网" in err or "保留" in err or "不允许" in err

    def test_private_ip_fails(self):
        ok, err = _validate_video_download_url("http://192.168.1.1/v")
        assert ok is False
        assert "内网" in err or "保留" in err or "不允许" in err


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

    def test_valid_weather_query_multi_select(self):
        ok, err = validate_task_creation(
            "weather_query", {"location": "北京", "fetch_current": True, "fetch_forecast": True}
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

    def test_web_search_missing_query(self):
        ok, err = validate_task_creation("web_search", {})
        assert ok is False
        assert "query" in (err or "").lower() or "关键词" in (err or "")

    def test_web_search_valid(self):
        ok, err = validate_task_creation("web_search", {"query": "测试"})
        assert ok is True
        assert err is None

    def test_web_search_compare_valid(self):
        ok, err = validate_task_creation("web_search_compare", {"query": "测试"})
        assert ok is True
        assert err is None

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

    def test_weather_query_no_fetch_type_selected(self):
        """多选模式下全部不勾选时应报错"""
        ok, err = validate_task_creation(
            "weather_query",
            {"location": "北京", "fetch_current": False, "fetch_forecast": False, "fetch_warning": False, "fetch_air_quality": False},
        )
        assert ok is False
        assert "至少勾选" in err or "查询类型" in err

    def test_metadata_not_dict_treated_as_empty(self):
        """非 dict 的 metadata 按空 dict 处理，weather_query 必填 location 仍报错"""
        ok, err = validate_task_creation("weather_query", None)
        assert ok is False
        assert "location" in err

    def test_speech_to_text_missing_input_file(self):
        ok, err = validate_task_creation("speech_to_text", {})
        assert ok is False
        assert "input_file" in err

    def test_speech_to_text_valid_metadata(self):
        ok, err = validate_task_creation("speech_to_text", {"input_file": "/tmp/audio.mp3"})
        assert ok is True
        assert err is None

    def test_video_extract_audio_missing_input_file(self):
        ok, err = validate_task_creation("video_extract_audio", {})
        assert ok is False
        assert "input_file" in err

    def test_video_extract_audio_valid_metadata(self):
        ok, err = validate_task_creation("video_extract_audio", {"input_file": "/tmp/video.mp4"})
        assert ok is True
        assert err is None

    def test_speech_to_text_invalid_model_enum(self):
        ok, err = validate_task_creation(
            "speech_to_text", {"input_file": "/tmp/a.mp3", "model": "invalid"}
        )
        assert ok is False
        assert "model" in err and "取值无效" in err

    def test_video_extract_audio_invalid_audio_format_enum(self):
        ok, err = validate_task_creation(
            "video_extract_audio", {"input_file": "/tmp/v.mp4", "audio_format": "invalid"}
        )
        assert ok is False
        assert "audio_format" in err and "取值无效" in err

    def test_image_generation_missing_prompt(self):
        ok, err = validate_task_creation("image_generation", {})
        assert ok is False
        assert "prompt" in err

    def test_image_generation_valid_metadata(self):
        ok, err = validate_task_creation(
            "image_generation", {"prompt": "一只橘猫在阳光下打盹"}
        )
        assert ok is True
        assert err is None


class TestImageGenerationHandler:
    """图片生成任务处理器"""

    @pytest.mark.asyncio
    async def test_image_generation_missing_prompt_returns_error_struct(self):
        """缺 prompt 时返回统一错误结构"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_image_generation_task({
                "task_id": "t1", "task_type": "image_generation", "metadata": {},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "PROMPT_REQUIRED"

    @pytest.mark.asyncio
    async def test_image_generation_success_return_shape(self):
        """mock ImageGenService 成功时返回 status/summary/data"""
        mock_result = {
            "images": ["data:image/png;base64,xxx"],
            "output_file": str(Path.home() / "hou-cli" / "outputs" / "images" / "gen_0.png"),
            "output_dir": str(Path.home() / "hou-cli" / "outputs" / "images"),
            "prompt": "一只猫",
        }
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            with patch(
                "backend.services.llm.image_gen_service.ImageGenService"
            ) as MockSvc:
                mock_svc = MagicMock()
                mock_svc.generate = AsyncMock(return_value=mock_result)
                MockSvc.return_value = mock_svc
                out = await process_image_generation_task({
                    "task_id": "t1", "task_type": "image_generation",
                    "metadata": {"prompt": "一只猫"},
                })
        assert out["status"] == "success"
        assert "summary" in out
        assert "data" in out
        assert out["data"]["output_file"] == mock_result["output_file"]
        assert out["data"]["prompt"] == "一只猫"

    @pytest.mark.asyncio
    async def test_image_generation_api_failure_returns_error_struct(self):
        """ImageGenService 抛出异常时返回 IMAGE_GEN_FAILED"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            with patch(
                "backend.services.llm.image_gen_service.ImageGenService"
            ) as MockSvc:
                mock_svc = MagicMock()
                mock_svc.generate = AsyncMock(side_effect=RuntimeError("API 超时"))
                MockSvc.return_value = mock_svc
                out = await process_image_generation_task({
                    "task_id": "t1", "task_type": "image_generation",
                    "metadata": {"prompt": "一只猫"},
                })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "IMAGE_GEN_FAILED"

    @pytest.mark.asyncio
    async def test_image_generation_output_dir_outside_home_returns_error(self):
        """output_dir 在主目录外时返回 OUTPUT_PATH_DENIED"""
        # /etc 等系统路径不在用户主目录下（Unix/Linux/macOS）
        outside_home = "/etc"
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_image_generation_task({
                "task_id": "t1", "task_type": "image_generation",
                "metadata": {"prompt": "一只猫", "output_dir": outside_home},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "OUTPUT_PATH_DENIED"


class TestPipelineLinkableUpstreams:
    """管道可链接性：pipeline_outputs / pipeline_accept 与 get_linkable_upstream_types"""

    def test_get_available_task_types_includes_pipeline_outputs(self):
        types = get_available_task_types()
        st = next((t for t in types if t["type"] == "speech_to_text"), None)
        assert st is not None
        assert "pipeline_outputs" in st
        assert isinstance(st.get("pipeline_outputs"), list)
        vea = next((t for t in types if t["type"] == "video_extract_audio"), None)
        assert vea is not None
        assert "pipeline_outputs" in vea
        assert any(o.get("path") == "result.data.output_file" and o.get("format") == "audio" for o in (vea.get("pipeline_outputs") or []))

    def test_speech_to_text_input_file_has_pipeline_accept(self):
        types = get_available_task_types()
        st = next((t for t in types if t["type"] == "speech_to_text"), None)
        assert st is not None
        input_file = (st.get("metadata_schema") or {}).get("input_file")
        assert isinstance(input_file, dict)
        assert input_file.get("pipeline_accept", {}).get("type") == "file"
        assert "audio" in (input_file.get("pipeline_accept") or {}).get("formats") or []

    def test_get_linkable_upstream_types_speech_to_text(self):
        out = get_linkable_upstream_types("speech_to_text")
        assert "video_extract_audio" in out["linkable_task_types"]
        assert "video_extract_audio" in out["suggested_bindings"]
        bindings = out["suggested_bindings"]["video_extract_audio"]
        assert any(b.get("downstream_field") == "input_file" and b.get("upstream_path") == "result.data.output_file" for b in bindings)

    def test_get_linkable_upstream_types_video_extract_audio_empty(self):
        out = get_linkable_upstream_types("video_extract_audio")
        assert isinstance(out["linkable_task_types"], list)
        assert isinstance(out["suggested_bindings"], dict)
        assert out["linkable_task_types"] == [] or "video_extract_audio" not in out["linkable_task_types"]

    def test_get_linkable_upstream_types_unknown_returns_empty(self):
        out = get_linkable_upstream_types("unknown_type")
        assert out["linkable_task_types"] == []
        assert out["suggested_bindings"] == {}

    def test_image_generation_has_pipeline_outputs(self):
        """image_generation 任务类型包含 pipeline_outputs，可作为管道上游"""
        types = get_available_task_types()
        ig = next((t for t in types if t["type"] == "image_generation"), None)
        assert ig is not None
        outputs = ig.get("pipeline_outputs") or []
        assert len(outputs) >= 1
        out = outputs[0]
        assert out.get("path") == "result.data.output_file"
        assert out.get("format") == "image"


class TestValidateInputPathInHome:
    """路径校验 _validate_input_path_in_home 允许/禁止路径"""

    def test_nonexistent_path_fails(self):
        ok, msg = _validate_input_path_in_home(Path("/nonexistent_file_12345_abc"))
        assert ok is False
        assert "不存在" in (msg or "")

    def test_path_under_home_and_exists_succeeds(self):
        under_home = Path.home() / ".cache" / "hou-cli-test-path-ok"
        under_home.parent.mkdir(parents=True, exist_ok=True)
        under_home.write_text("x")
        try:
            ok, msg = _validate_input_path_in_home(under_home.resolve())
            assert ok is True
            assert msg is None
        finally:
            if under_home.exists():
                under_home.unlink()

    def test_path_outside_home_fails(self):
        # /etc/hosts 存在且为文件，但不在主目录下（在 Linux/macOS 上）
        outside = Path("/etc/hosts")
        if not outside.exists() or not outside.is_file():
            pytest.skip("需要 /etc/hosts 存在")
        ok, msg = _validate_input_path_in_home(outside.resolve())
        assert ok is False
        assert "主目录" in (msg or "")


class TestSpeechToTextAndVideoExtractAudioHandlers:
    """语音转文字、视频提音频 handler 返回结构与错误码"""

    @pytest.mark.asyncio
    async def test_speech_to_text_missing_input_returns_error_struct(self):
        """缺 input_file 时返回统一错误结构，不抛异常"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_speech_to_text_task({
                "task_id": "t1", "task_type": "speech_to_text", "metadata": {},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "INPUT_FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_speech_to_text_success_return_shape(self):
        """mock WhisperTool 成功时返回 status/summary/data（使用用户主目录下临时文件）"""
        tmp = Path.home() / ".cache" / "hou-cli-test"
        tmp.mkdir(parents=True, exist_ok=True)
        audio_file = tmp / "test_speech_input.mp3"
        audio_file.write_bytes(b"fake")
        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"output_file": str(audio_file.with_suffix(".srt")), "segments_count": 10, "text": "hello"}
            mock_result.error = None
            with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
                m_worker.return_value.update_task_progress = MagicMock()
                with patch("backend.infrastructure.execution.task_handlers.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
                    out = await process_speech_to_text_task({
                        "task_id": "t1", "task_type": "speech_to_text",
                        "metadata": {"input_file": str(audio_file)},
                    })
            assert out["status"] == "success"
            assert "summary" in out and "data" in out
        finally:
            if audio_file.exists():
                audio_file.unlink()

    @pytest.mark.asyncio
    async def test_video_extract_audio_missing_input_returns_error_struct(self):
        """缺 input_file 时返回统一错误结构"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_video_extract_audio_task({
                "task_id": "t1", "task_type": "video_extract_audio", "metadata": {},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "INPUT_FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_video_extract_audio_success_return_shape(self):
        """mock FFmpegTool 成功时返回 status/summary/data（使用用户主目录下临时文件）"""
        tmp = Path.home() / ".cache" / "hou-cli-test"
        tmp.mkdir(parents=True, exist_ok=True)
        video_file = tmp / "test_video_input.mp4"
        video_file.write_bytes(b"fake")
        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"output_file": str(video_file.with_suffix(".mp3")), "format": "mp3"}
            mock_result.error = None
            with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
                m_worker.return_value.update_task_progress = MagicMock()
                with patch("backend.infrastructure.execution.task_handlers.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
                    out = await process_video_extract_audio_task({
                        "task_id": "t1", "task_type": "video_extract_audio",
                        "metadata": {"input_file": str(video_file)},
                    })
            assert out["status"] == "success"
            assert "summary" in out and "data" in out
        finally:
            if video_file.exists():
                video_file.unlink()

    @pytest.mark.asyncio
    async def test_speech_to_text_input_file_not_found_returns_error_struct(self):
        """input_file 指向不存在路径时返回 INPUT_FILE_NOT_FOUND"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_speech_to_text_task({
                "task_id": "t1", "task_type": "speech_to_text",
                "metadata": {"input_file": str(Path.home() / "nonexistent_audio_xyz_123.mp3")},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "INPUT_FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_speech_to_text_input_path_outside_home_returns_error_struct(self):
        """input_file 为主目录外路径时返回 INPUT_PATH_OUTSIDE_HOME"""
        outside = Path("/etc/hosts")
        if not outside.exists() or not outside.is_file():
            pytest.skip("需要 /etc/hosts 存在")
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_speech_to_text_task({
                "task_id": "t1", "task_type": "speech_to_text",
                "metadata": {"input_file": str(outside)},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "INPUT_PATH_OUTSIDE_HOME"

    @pytest.mark.asyncio
    async def test_video_extract_audio_input_file_not_found_returns_error_struct(self):
        """input_file 指向不存在路径时返回 INPUT_FILE_NOT_FOUND"""
        with patch("backend.infrastructure.execution.task_handlers.get_task_worker") as m_worker:
            m_worker.return_value.update_task_progress = MagicMock()
            out = await process_video_extract_audio_task({
                "task_id": "t1", "task_type": "video_extract_audio",
                "metadata": {"input_file": str(Path.home() / "nonexistent_video_xyz_123.mp4")},
            })
        assert out["status"] == "error"
        assert out.get("error", {}).get("code") == "INPUT_FILE_NOT_FOUND"


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
