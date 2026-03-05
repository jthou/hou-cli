"""视频下载工具测试"""
import builtins
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from backend.core.agent.tools.builtin.video_downloader_tool import (
    VideoDownloaderTool,
    DownloaderAdapter,
    DownloadResult,
    YouGetDownloader,
    YtDlpDownloader,
    _detect_platform,
    _select_downloader,
)


class TestPlatformDetection:
    """测试平台检测功能"""
    
    def test_detect_bilibili(self):
        """测试检测 Bilibili 平台"""
        assert _detect_platform("https://www.bilibili.com/video/BV1234567890") == "bilibili"
        assert _detect_platform("https://b23.tv/abc123") == "bilibili"
        assert _detect_platform("http://bilibili.com/video/BV123") == "bilibili"
    
    def test_detect_youtube(self):
        """测试检测 YouTube 平台"""
        assert _detect_platform("https://www.youtube.com/watch?v=xxx") == "youtube"
        assert _detect_platform("https://youtu.be/xxx") == "youtube"
    
    def test_detect_other_platforms(self):
        """测试检测其他平台"""
        assert _detect_platform("https://www.youku.com/video/xxx") == "youku"
        assert _detect_platform("https://www.iqiyi.com/video/xxx") == "iqiyi"
        assert _detect_platform("https://twitter.com/xxx/status/123") == "twitter"
        assert _detect_platform("https://www.facebook.com/video/xxx") == "facebook"
    
    def test_detect_unknown(self):
        """测试检测未知平台"""
        assert _detect_platform("https://example.com/video") == "unknown"


class TestYouGetDownloader:
    """测试 YouGetDownloader 适配器（现用 pip you-get，通过 subprocess python -m you_get）"""

    @patch('backend.core.agent.tools.builtin.video_downloader_tool.subprocess.run')
    def test_is_available_true(self, mock_run):
        """测试 is_available 返回 True"""
        mock_run.return_value = MagicMock(returncode=0)
        downloader = YouGetDownloader()
        assert downloader.is_available() is True

    @patch('backend.core.agent.tools.builtin.video_downloader_tool.subprocess.run')
    def test_is_available_false(self, mock_run):
        """测试 is_available 返回 False"""
        mock_run.side_effect = FileNotFoundError()
        downloader = YouGetDownloader()
        assert downloader.is_available() is False

    def test_supports_platform(self):
        """测试 supports_platform"""
        downloader = YouGetDownloader()
        assert downloader.supports_platform("https://www.youtube.com/watch?v=xxx") is True
        assert downloader.supports_platform("https://www.bilibili.com/video/BV123") is True
        assert downloader.supports_platform("https://example.com/video") is False

    @patch('backend.core.agent.tools.builtin.video_downloader_tool.subprocess.run')
    def test_download_success(self, mock_run):
        """测试下载成功"""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        downloader = YouGetDownloader()
        result = downloader.download(
            "https://www.youtube.com/watch?v=xxx",
            Path("/tmp/output"),
            quality="720p"
        )
        assert result.success is True
        assert result.data['tool'] == 'you-get'

    @patch('backend.core.agent.tools.builtin.video_downloader_tool.subprocess.run')
    def test_download_failure(self, mock_run):
        """测试下载失败"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message", stdout="")
        downloader = YouGetDownloader()
        result = downloader.download(
            "https://www.youtube.com/watch?v=xxx",
            Path("/tmp/output")
        )
        assert result.success is False
        error_lower = result.error.lower()
        assert "you-get" in error_lower and ("failed" in error_lower or "失败" in error_lower or "下载失败" in result.error)


class TestYtDlpDownloader:
    """测试 YtDlpDownloader 适配器（现用 pip yt-dlp，直接 import yt_dlp）"""

    def test_is_available_true(self):
        """测试 is_available 返回 True（mock 已安装 yt_dlp）"""
        import sys
        try:
            sys.modules['yt_dlp'] = MagicMock()
            downloader = YtDlpDownloader()
            assert downloader.is_available() is True
        finally:
            sys.modules.pop('yt_dlp', None)

    def test_is_available_false(self):
        """测试 is_available 返回 False（import yt_dlp 失败）"""
        real_import = builtins.__import__
        def fake_import(name, *a, **k):
            if name == 'yt_dlp':
                raise ImportError("No module named 'yt_dlp'")
            return real_import(name, *a, **k)
        with patch('builtins.__import__', side_effect=fake_import):
            downloader = YtDlpDownloader()
            assert downloader.is_available() is False

    def test_supports_platform(self):
        """测试 supports_platform"""
        downloader = YtDlpDownloader()
        assert downloader.supports_platform("https://www.youtube.com/watch?v=xxx") is True
        assert downloader.supports_platform("https://www.bilibili.com/video/BV123") is True
        assert downloader.supports_platform("https://example.com/video") is False

    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
    def test_download_subtitle_only(self, mock_ffmpeg_dir):
        """测试只下载字幕"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            result = downloader.download(
                "https://www.youtube.com/watch?v=xxx",
                Path("/tmp/output"),
                download_subtitle_only=True,
                subtitle_languages=["en", "zh"]
            )
            assert result.success is True
            mock_ydl.extract_info.assert_called_once()
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)

    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
    def test_extract_audio_only(self, mock_ffmpeg_dir):
        """测试只提取音频"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            result = downloader.download(
                "https://www.youtube.com/watch?v=xxx",
                Path("/tmp/output"),
                extract_audio_only=True,
                audio_format="mp3",
                audio_quality="192k"
            )
            assert result.success is True
            mock_ydl.extract_info.assert_called_once()
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)

    def test_convert_quality_to_yt_dlp_format(self):
        """测试质量参数转换（带 /best 回退避免 Requested format is not available）"""
        downloader = YtDlpDownloader()
        assert downloader._convert_quality_to_yt_dlp_format("best") == "best"
        assert downloader._convert_quality_to_yt_dlp_format("1080p") == "best[height<=1080]/best"
        assert downloader._convert_quality_to_yt_dlp_format("720p") == "best[height<=720]/best"
        assert downloader._convert_quality_to_yt_dlp_format("unknown") == "best"

    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
    def test_quality_auto_does_not_set_format_in_opts(self, mock_ffmpeg_dir):
        """quality=auto（或 best）时不设 format，让 yt-dlp 用默认逻辑"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        captured_opts = []

        def capture_opts(ydl_opts):
            captured_opts.append(ydl_opts.copy())
            return _make_ydl_cm()

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = capture_opts
        mock_yt_dlp.utils.DownloadError = type('DownloadError', (Exception,), {})
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            downloader.download(
                "https://www.youtube.com/watch?v=xxx",
                Path("/tmp/out"),
                quality="auto",
            )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert len(captured_opts) >= 1
        assert 'format' not in captured_opts[0]

    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
    def test_quality_1080p_sets_format_in_opts(self, mock_ffmpeg_dir):
        """quality=1080p 时 ydl_opts 含 format=best[height<=1080]/best"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        captured_opts = []

        def capture_opts(ydl_opts):
            captured_opts.append(ydl_opts.copy())
            return _make_ydl_cm()

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = capture_opts
        mock_yt_dlp.utils.DownloadError = type('DownloadError', (Exception,), {})
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            downloader.download(
                "https://www.youtube.com/watch?v=xxx",
                Path("/tmp/out"),
                quality="1080p",
            )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert len(captured_opts) >= 1
        # 参考 yt-dlp#11295：分辨率质量改用 format_sort 以支持回退
        opts = captured_opts[0]
        assert opts.get('format_sort') == ['res:1080', 'ext'] and opts.get('format_sort_force') is True

    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
    def test_requested_format_not_available_retries_without_format_and_succeeds(self, mock_ffmpeg_dir):
        """Requested format is not available 时去掉 format 重试，成功则返回 success"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        DownloadError = type('DownloadError', (Exception,), {})

        cm_first = MagicMock()
        cm_first.__enter__.return_value.extract_info.side_effect = DownloadError(
            "Requested format is not available"
        )
        cm_first.__exit__.return_value = None
        cm_retry = _make_ydl_cm({
            'title': 'YouTube Video',
            'uploader': '',
            'upload_date': '',
            'view_count': None,
            'description': '',
        })

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = [cm_first, cm_retry]
        mock_yt_dlp.utils.DownloadError = DownloadError
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            result = downloader.download(
                "https://www.youtube.com/watch?v=xxx",
                Path("/tmp/out"),
                quality="1080p",
            )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert result.success is True
        assert result.data.get('title') == 'YouTube Video'


class TestDownloaderSelection:
    """测试下载器选择逻辑"""
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YtDlpDownloader')
    def test_select_for_subtitle_only(self, mock_yt_dlp_class):
        """测试只下载字幕时选择 yt-dlp"""
        mock_yt_dlp = MagicMock()
        mock_yt_dlp.is_available.return_value = True
        mock_yt_dlp_class.return_value = mock_yt_dlp
        
        downloader = _select_downloader(
            "https://www.youtube.com/watch?v=xxx",
            preferred="auto",
            download_subtitle_only=True
        )
        
        assert downloader == mock_yt_dlp
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YtDlpDownloader')
    def test_select_for_audio_only(self, mock_yt_dlp_class):
        """测试只提取音频时选择 yt-dlp"""
        mock_yt_dlp = MagicMock()
        mock_yt_dlp.is_available.return_value = True
        mock_yt_dlp_class.return_value = mock_yt_dlp
        
        downloader = _select_downloader(
            "https://www.youtube.com/watch?v=xxx",
            preferred="auto",
            extract_audio_only=True
        )
        
        assert downloader == mock_yt_dlp
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YouGetDownloader')
    def test_select_bilibili_auto(self, mock_you_get_class):
        """测试 Bilibili 平台自动选择（优先 you-get）"""
        mock_you_get = MagicMock()
        mock_you_get.is_available.return_value = True
        mock_you_get_class.return_value = mock_you_get
        
        downloader = _select_downloader(
            "https://www.bilibili.com/video/BV123",
            preferred="auto"
        )
        
        assert downloader == mock_you_get
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YtDlpDownloader')
    def test_select_youtube_auto(self, mock_yt_dlp_class):
        """测试 YouTube 平台自动选择"""
        mock_yt_dlp = MagicMock()
        mock_yt_dlp.is_available.return_value = True
        mock_yt_dlp_class.return_value = mock_yt_dlp
        
        downloader = _select_downloader(
            "https://www.youtube.com/watch?v=xxx",
            preferred="auto"
        )
        
        assert downloader == mock_yt_dlp
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YouGetDownloader')
    def test_select_preferred_tool(self, mock_you_get_class):
        """测试指定首选工具"""
        mock_you_get = MagicMock()
        mock_you_get.is_available.return_value = True
        mock_you_get_class.return_value = mock_you_get
        
        downloader = _select_downloader(
            "https://www.youtube.com/watch?v=xxx",
            preferred="you-get"
        )
        
        assert downloader == mock_you_get


class TestVideoDownloaderTool:
    """测试 VideoDownloaderTool 主工具类"""
    
    def test_init(self):
        """测试初始化"""
        tool = VideoDownloaderTool()
        assert tool.name == "video_downloader"
        assert len(tool.parameters) > 0
        assert any(p.name == "url" for p in tool.parameters)
        assert any(p.name == "output_dir" for p in tool.parameters)
    
    def test_validate_parameters_missing_url(self):
        """测试参数验证 - 缺少 URL"""
        tool = VideoDownloaderTool()
        error = tool.validate_parameters()
        assert error is not None
        assert "url" in error.lower()
    
    def test_validate_parameters_valid(self):
        """测试参数验证 - 有效参数"""
        tool = VideoDownloaderTool()
        error = tool.validate_parameters(url="https://www.youtube.com/watch?v=xxx")
        assert error is None
    
    def test_validate_parameters_invalid_quality(self):
        """测试参数验证 - 无效质量"""
        tool = VideoDownloaderTool()
        error = tool.validate_parameters(
            url="https://www.youtube.com/watch?v=xxx",
            quality="invalid_quality"
        )
        assert error is not None
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_execute_success(self, mock_normalize, mock_select):
        """测试执行成功"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = DownloadResult(
            success=True,
            data={'tool': 'yt-dlp', 'output_dir': '/tmp/output'}
        )
        mock_select.return_value = mock_downloader
        
        tool = VideoDownloaderTool()
        result = tool.execute(url="https://www.youtube.com/watch?v=xxx")
        
        assert result.success is True
        assert result.data['tool'] == 'yt-dlp'
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_execute_missing_url(self, mock_normalize, mock_select):
        """测试执行 - 缺少 URL"""
        tool = VideoDownloaderTool()
        result = tool.execute()
        
        assert result.success is False
        assert "URL is required" in result.error
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YouGetDownloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.YtDlpDownloader')
    def test_execute_with_fallback(self, mock_yt_dlp_class, mock_you_get_class, mock_normalize, mock_select):
        """测试执行 - 带降级策略"""
        mock_normalize.return_value = Path("/tmp/output")
        
        # 首选下载器失败
        mock_primary = MagicMock()
        mock_primary.is_available.return_value = True
        mock_primary.download.return_value = DownloadResult(
            success=False,
            error="Primary downloader failed"
        )
        mock_select.return_value = mock_primary
        
        # 降级下载器成功
        mock_fallback = MagicMock()
        mock_fallback.is_available.return_value = True
        mock_fallback.download.return_value = DownloadResult(
            success=True,
            data={'tool': 'you-get', 'output_dir': '/tmp/output'}
        )
        mock_you_get_class.return_value = mock_fallback
        
        tool = VideoDownloaderTool()
        result = tool.execute(url="https://www.youtube.com/watch?v=xxx")
        
        assert result.success is True
        assert result.data['tool'] == 'you-get'
    
    def test_to_dict(self):
        """测试转换为字典（用于 LLM Function Calling）"""
        tool = VideoDownloaderTool()
        tool_dict = tool.to_dict()
        
        assert tool_dict['type'] == 'function'
        assert tool_dict['function']['name'] == 'video_downloader'
        assert 'parameters' in tool_dict['function']
        assert 'properties' in tool_dict['function']['parameters']
        assert 'url' in tool_dict['function']['parameters']['properties']


# =============================================================================
# 能力测试：反爬虫（headers、cookies、412 重试、登录错误文案）
# =============================================================================

def _make_ydl_cm(extract_info_return=None):
    """构造 YtDlpDownloader 用的 YoutubeDL 上下文管理器 mock"""
    if extract_info_return is None:
        extract_info_return = {
            'title': 'Test', 'uploader': '', 'upload_date': '',
            'view_count': None, 'description': ''
        }
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = extract_info_return
    cm = MagicMock()
    cm.__enter__.return_value = mock_ydl
    cm.__exit__.return_value = None
    return cm


def _patch_import_yt_dlp(mock_yt_dlp):
    """仅 mock 对 yt_dlp 的 import，其余用真实 import"""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == 'yt_dlp':
            return mock_yt_dlp
        return real_import(name, *args, **kwargs)

    return patch('builtins.__import__', side_effect=fake_import)


@patch('backend.core.agent.tools.builtin.video_downloader_tool._get_ffmpeg_bin_dir')
class TestYtDlpAntiScrapingCapability:
    """能力测试：YtDlp 反爬虫能力（headers、cookies、412、错误文案）"""

    def test_bilibili_url_receives_http_headers(self, mock_ffmpeg_dir):
        """B 站 URL 时传入 yt-dlp 的 opts 含 http_headers（User-Agent、Referer）"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        captured_opts = []

        def capture_opts(ydl_opts):
            captured_opts.append(ydl_opts)
            return _make_ydl_cm()

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = capture_opts
        mock_yt_dlp.utils.DownloadError = type('DownloadError', (Exception,), {})

        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            downloader.download(
                "https://www.bilibili.com/video/BV123",
                Path("/tmp/out"),
            )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert len(captured_opts) >= 1
        opts = captured_opts[0]
        assert 'http_headers' in opts
        assert opts['http_headers'].get('User-Agent', '').startswith('Mozilla/')
        assert 'bilibili.com' in opts['http_headers'].get('Referer', '')

    def test_cookies_file_sets_cookiefile_in_opts(self, mock_ffmpeg_dir):
        """cookies_file 有效时 ydl_opts 含 cookiefile"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        captured_opts = []

        def capture_opts(ydl_opts):
            captured_opts.append(ydl_opts)
            return _make_ydl_cm()

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = capture_opts
        mock_yt_dlp.utils.DownloadError = type('DownloadError', (Exception,), {})
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            with patch('backend.core.agent.tools.builtin.video_downloader_tool._load_cookies_from_file') as m_load:
                m_load.return_value = "/tmp/cookies.txt"
                downloader = YtDlpDownloader()
                # Bilibili 立即使用 cookies；YouTube 会延后，首轮无 cookiefile
                downloader.download(
                    "https://www.bilibili.com/video/BV123",
                    Path("/tmp/out"),
                    cookies_file="/tmp/cookies.txt",
                )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert len(captured_opts) >= 1
        assert captured_opts[0].get('cookiefile') == "/tmp/cookies.txt"

    def test_cookies_from_browser_sets_cookiefile_in_opts(self, mock_ffmpeg_dir):
        """cookies_from_browser 指定时尝试提取并设置 cookiefile"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        captured_opts = []

        def capture_opts(ydl_opts):
            captured_opts.append(ydl_opts)
            return _make_ydl_cm()

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = capture_opts
        mock_yt_dlp.utils.DownloadError = type('DownloadError', (Exception,), {})
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            with patch('backend.core.agent.tools.builtin.video_downloader_tool._extract_cookies_from_browser') as m_extract:
                m_extract.return_value = "/tmp/browser_cookies.txt"
                downloader = YtDlpDownloader()
                downloader.download(
                    "https://www.bilibili.com/video/BV123",
                    Path("/tmp/out"),
                    cookies_from_browser="chrome",
                )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert len(captured_opts) >= 1
        assert captured_opts[0].get('cookiefile') == "/tmp/browser_cookies.txt"

    def test_412_tries_browser_cookies_and_retry_succeeds(self, mock_ffmpeg_dir):
        """412 错误时尝试从浏览器提取 cookie 并重试，第二次成功则返回 success"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        DownloadError = type('DownloadError', (Exception,), {})

        cm_first = MagicMock()
        cm_first.__enter__.return_value.extract_info.side_effect = DownloadError("HTTP Error 412: Precondition Failed")
        cm_first.__exit__.return_value = None
        cm_retry = _make_ydl_cm({'title': 'B站视频', 'uploader': '', 'upload_date': '', 'view_count': None, 'description': ''})

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = [cm_first, cm_retry]
        mock_yt_dlp.utils.DownloadError = DownloadError
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            with patch('backend.core.agent.tools.builtin.video_downloader_tool._extract_cookies_from_browser') as m_extract:
                m_extract.return_value = "/tmp/auto_cookies.txt"
                downloader = YtDlpDownloader()
                result = downloader.download(
                    "https://www.bilibili.com/video/BV123",
                    Path("/tmp/out"),
                )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert result.success is True
        assert result.data.get('title') == 'B站视频'
        assert result.data.get('cookies_auto_extracted') is True
        assert result.data.get('cookies_source') in ('chrome', 'firefox', 'safari', 'edge')

    def test_youtube_requested_format_tries_browser_cookies_and_succeeds(self, mock_ffmpeg_dir):
        """YouTube Requested format 错误时自动从浏览器提取 cookies 重试，成功则返回 success"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        DownloadError = type('DownloadError', (Exception,), {})

        cm_prefetch = MagicMock()
        cm_prefetch.__enter__.return_value.extract_info.side_effect = DownloadError(
            "Requested format is not available. Use --list-formats"
        )
        cm_prefetch.__exit__.return_value = None
        cm_first = MagicMock()
        cm_first.__enter__.return_value.extract_info.side_effect = DownloadError(
            "Requested format is not available. Use --list-formats"
        )
        cm_first.__exit__.return_value = None
        cm_format_retry = MagicMock()
        cm_format_retry.__enter__.return_value.extract_info.side_effect = DownloadError(
            "Requested format is not available"
        )
        cm_format_retry.__exit__.return_value = None
        cm_cookie_retry = _make_ydl_cm({
            'title': 'YouTube Video',
            'uploader': '',
            'upload_date': '',
            'view_count': None,
            'description': '',
        })

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.side_effect = [cm_prefetch, cm_first, cm_format_retry, cm_cookie_retry]
        mock_yt_dlp.utils.DownloadError = DownloadError
        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            with patch('backend.core.agent.tools.builtin.video_downloader_tool._extract_cookies_from_browser') as m_extract:
                m_extract.return_value = "/tmp/yt_cookies.txt"
                downloader = YtDlpDownloader()
                result = downloader.download(
                    "https://www.youtube.com/watch?v=aAPpQC-3EyE",
                    Path("/tmp/out"),
                )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert result.success is True
        assert result.data.get('title') == 'YouTube Video'
        assert result.data.get('cookies_auto_extracted') is True
        assert result.data.get('cookies_source') in ('chrome', 'firefox', 'safari', 'edge')

    def test_login_required_error_includes_cookie_suggestion(self, mock_ffmpeg_dir):
        """登录/机器人错误时返回文案含 cookie 使用建议"""
        mock_ffmpeg_dir.return_value = MagicMock(exists=MagicMock(return_value=True))
        DownloadError = type('DownloadError', (Exception,), {})

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = DownloadError("LOGIN_REQUIRED: 请登录后重试")

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl
        mock_yt_dlp.YoutubeDL.return_value.__exit__.return_value = None
        mock_yt_dlp.utils.DownloadError = DownloadError

        import sys
        old_yt_dlp = sys.modules.get('yt_dlp')
        sys.modules['yt_dlp'] = mock_yt_dlp
        try:
            downloader = YtDlpDownloader()
            result = downloader.download(
                "https://www.bilibili.com/video/BV123",
                Path("/tmp/out"),
            )
        finally:
            if old_yt_dlp is not None:
                sys.modules['yt_dlp'] = old_yt_dlp
            else:
                sys.modules.pop('yt_dlp', None)
        assert result.success is False
        assert result.error
        err_lower = result.error.lower()
        assert 'cookie' in err_lower or 'cookies' in err_lower
        assert 'cookies_from_browser' in result.error or 'cookies_file' in result.error

