"""视频下载工具测试"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from backend.core.agent.tools.builtin.video_downloader_tool import (
    VideoDownloaderTool,
    DownloaderAdapter,
    DownloadResult,
    YouGetDownloader,
    Bili23Downloader,
    YtDlpDownloader,
    _detect_platform,
    _select_downloader,
    _get_you_get_path,
    _get_bili23_path,
    _get_yt_dlp_path,
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
    """测试 YouGetDownloader 适配器"""
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_you_get_path')
    def test_is_available_true(self, mock_path):
        """测试 is_available 返回 True"""
        mock_path.return_value = Path("/fake/path")
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.path'):
                with patch('builtins.__import__', return_value=MagicMock()):
                    downloader = YouGetDownloader()
                    assert downloader.is_available() is True
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_you_get_path')
    def test_is_available_false(self, mock_path):
        """测试 is_available 返回 False"""
        mock_path.return_value = Path("/fake/path")
        with patch('pathlib.Path.exists', return_value=False):
            downloader = YouGetDownloader()
            assert downloader.is_available() is False
    
    def test_supports_platform(self):
        """测试 supports_platform"""
        downloader = YouGetDownloader()
        assert downloader.supports_platform("https://www.youtube.com/watch?v=xxx") is True
        assert downloader.supports_platform("https://www.bilibili.com/video/BV123") is True
        assert downloader.supports_platform("https://example.com/video") is False
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_you_get_path')
    @patch('subprocess.run')
    def test_download_success(self, mock_run, mock_path):
        """测试下载成功"""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path.return_value = mock_path_obj
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        downloader = YouGetDownloader()
        result = downloader.download(
            "https://www.youtube.com/watch?v=xxx",
            Path("/tmp/output"),
            quality="720p"
        )
        
        assert result.success is True
        assert result.data['tool'] == 'you-get'
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_you_get_path')
    @patch('subprocess.run')
    def test_download_failure(self, mock_run, mock_path):
        """测试下载失败"""
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path.return_value = mock_path_obj
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message")
        
        downloader = YouGetDownloader()
        result = downloader.download(
            "https://www.youtube.com/watch?v=xxx",
            Path("/tmp/output")
        )
        
        assert result.success is False
        assert "you-get failed" in result.error


class TestYtDlpDownloader:
    """测试 YtDlpDownloader 适配器"""
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_yt_dlp_path')
    def test_is_available_true(self, mock_path):
        """测试 is_available 返回 True"""
        mock_path.return_value = Path("/fake/path")
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.path'):
                with patch('builtins.__import__', return_value=MagicMock()):
                    downloader = YtDlpDownloader()
                    assert downloader.is_available() is True
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_yt_dlp_path')
    def test_is_available_false(self, mock_path):
        """测试 is_available 返回 False"""
        mock_path.return_value = Path("/fake/path")
        with patch('pathlib.Path.exists', return_value=False):
            downloader = YtDlpDownloader()
            assert downloader.is_available() is False
    
    def test_supports_platform(self):
        """测试 supports_platform"""
        downloader = YtDlpDownloader()
        assert downloader.supports_platform("https://www.youtube.com/watch?v=xxx") is True
        assert downloader.supports_platform("https://www.bilibili.com/video/BV123") is True
        assert downloader.supports_platform("https://example.com/video") is False
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_yt_dlp_path')
    def test_download_subtitle_only(self, mock_path):
        """测试只下载字幕"""
        mock_path.return_value = Path("/fake/path")
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.path'):
                with patch('builtins.__import__', return_value=mock_yt_dlp):
                    downloader = YtDlpDownloader()
                    result = downloader.download(
                        "https://www.youtube.com/watch?v=xxx",
                        Path("/tmp/output"),
                        download_subtitle_only=True,
                        subtitle_languages=["en", "zh"]
                    )
                    
                    assert result.success is True
                    mock_ydl.extract_info.assert_called_once()
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_yt_dlp_path')
    def test_extract_audio_only(self, mock_path):
        """测试只提取音频"""
        mock_path.return_value = Path("/fake/path")
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.path'):
                with patch('builtins.__import__', return_value=mock_yt_dlp):
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
    
    def test_convert_quality_to_yt_dlp_format(self):
        """测试质量参数转换"""
        downloader = YtDlpDownloader()
        assert downloader._convert_quality_to_yt_dlp_format("best") == "best"
        assert downloader._convert_quality_to_yt_dlp_format("1080p") == "best[height<=1080]"
        assert downloader._convert_quality_to_yt_dlp_format("720p") == "best[height<=720]"
        assert downloader._convert_quality_to_yt_dlp_format("unknown") == "best"


class TestBili23Downloader:
    """测试 Bili23Downloader 适配器"""
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._get_bili23_path')
    def test_is_available_true(self, mock_path):
        """测试 is_available 返回 True"""
        mock_path.return_value = Path("/fake/path")
        with patch('pathlib.Path.exists', return_value=True):
            downloader = Bili23Downloader()
            assert downloader.is_available() is True
    
    def test_supports_platform(self):
        """测试 supports_platform"""
        downloader = Bili23Downloader()
        assert downloader.supports_platform("https://www.bilibili.com/video/BV123") is True
        assert downloader.supports_platform("https://www.youtube.com/watch?v=xxx") is False


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
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.Bili23Downloader')
    def test_select_bilibili_auto(self, mock_bili23_class):
        """测试 Bilibili 平台自动选择"""
        mock_bili23 = MagicMock()
        mock_bili23.is_available.return_value = True
        mock_bili23_class.return_value = mock_bili23
        
        downloader = _select_downloader(
            "https://www.bilibili.com/video/BV123",
            preferred="auto"
        )
        
        assert downloader == mock_bili23
    
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

