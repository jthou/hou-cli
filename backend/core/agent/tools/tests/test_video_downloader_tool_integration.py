"""视频下载工具 LLM 集成测试"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.base import ToolResult


class TestVideoDownloaderToolIntegration:
    """视频下载工具 LLM 集成测试"""
    
    @pytest.fixture
    def tool(self):
        """创建工具实例"""
        return VideoDownloaderTool()
    
    @pytest.fixture
    def registry(self):
        """创建工具注册表"""
        registry = ToolRegistry()
        registry.clear()
        tool = VideoDownloaderTool()
        registry.register(tool)
        return registry
    
    def test_tool_registration(self, registry):
        """测试工具注册"""
        tool = registry.get_tool("video_downloader")
        assert tool is not None
        assert tool.name == "video_downloader"
        assert isinstance(tool, VideoDownloaderTool)
    
    def test_tool_for_llm(self, registry):
        """测试工具转换为 LLM 格式"""
        tools = registry.get_tools_for_llm()
        video_tool = next((t for t in tools if t['function']['name'] == 'video_downloader'), None)
        
        assert video_tool is not None
        assert video_tool['type'] == 'function'
        assert video_tool['function']['name'] == 'video_downloader'
        assert 'parameters' in video_tool['function']
        assert 'properties' in video_tool['function']['parameters']
        assert 'url' in video_tool['function']['parameters']['properties']
    
    def test_llm_function_calling_schema(self, tool):
        """测试 LLM Function Calling Schema"""
        tool_dict = tool.to_dict()
        
        # 验证基本结构
        assert tool_dict['type'] == 'function'
        assert tool_dict['function']['name'] == 'video_downloader'
        
        # 验证参数定义
        params = tool_dict['function']['parameters']
        assert params['type'] == 'object'
        assert 'properties' in params
        assert 'required' in params
        
        # 验证必需参数
        assert 'url' in params['required']
        
        # 验证可选参数
        props = params['properties']
        assert 'output_dir' in props
        assert 'quality' in props
        assert 'format' in props
        assert 'download_subtitle' in props
        assert 'download_subtitle_only' in props
        assert 'extract_audio_only' in props
        assert 'preferred_tool' in props
        
        # 验证枚举值（如果存在）
        if 'enum' in props.get('quality', {}):
            assert props['quality']['enum'] == ["best", "worst", "1080p", "720p", "480p", "360p", "240p"]
        if 'enum' in props.get('preferred_tool', {}):
            assert props['preferred_tool']['enum'] == ["auto", "yt-dlp", "you-get"]
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_registry_execute_success(self, mock_normalize, mock_select, registry):
        """测试通过注册表执行工具"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = MagicMock(
            success=True,
            data={'tool': 'yt-dlp', 'output_dir': '/tmp/output'}
        )
        mock_select.return_value = mock_downloader
        
        result = registry.execute(
            "video_downloader",
            url="https://www.youtube.com/watch?v=xxx"
        )
        
        assert result.success is True
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_llm_call_scenario_1_download_video(self, mock_normalize, mock_select, tool):
        """测试 LLM 调用场景 1: 下载视频"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = MagicMock(
            success=True,
            data={'tool': 'yt-dlp', 'output_dir': '/tmp/output', 'title': 'Test Video'}
        )
        mock_select.return_value = mock_downloader
        
        # 模拟 LLM 调用
        result = tool.execute(
            url="https://www.youtube.com/watch?v=xxx",
            quality="720p"
        )
        
        assert result.success is True
        assert result.data['tool'] == 'yt-dlp'
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_llm_call_scenario_2_download_subtitle_only(self, mock_normalize, mock_select, tool):
        """测试 LLM 调用场景 2: 只下载字幕"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = MagicMock(
            success=True,
            data={
                'tool': 'yt-dlp',
                'output_dir': '/tmp/output',
                'subtitle_files': ['/tmp/output/video.en.srt', '/tmp/output/video.zh.srt']
            }
        )
        mock_select.return_value = mock_downloader
        
        # 模拟 LLM 调用
        result = tool.execute(
            url="https://www.youtube.com/watch?v=xxx",
            download_subtitle_only=True,
            subtitle_languages=["en", "zh"]
        )
        
        assert result.success is True
        assert result.data['tool'] == 'yt-dlp'
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_llm_call_scenario_3_extract_audio_only(self, mock_normalize, mock_select, tool):
        """测试 LLM 调用场景 3: 只提取音频"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = MagicMock(
            success=True,
            data={
                'tool': 'yt-dlp',
                'output_dir': '/tmp/output',
                'audio_path': '/tmp/output/video.mp3',
                'audio_format': 'mp3',
                'audio_quality': '192k'
            }
        )
        mock_select.return_value = mock_downloader
        
        # 模拟 LLM 调用
        result = tool.execute(
            url="https://www.youtube.com/watch?v=xxx",
            extract_audio_only=True,
            audio_format="mp3",
            audio_quality="192k"
        )
        
        assert result.success is True
        assert result.data['tool'] == 'yt-dlp'
        assert result.data['audio_format'] == 'mp3'
    
    @patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader')
    @patch('backend.core.agent.tools.builtin.video_downloader_tool.normalize_output_dir')
    def test_llm_call_scenario_4_bilibili_video(self, mock_normalize, mock_select, tool):
        """测试 LLM 调用场景 4: Bilibili 视频下载"""
        mock_normalize.return_value = Path("/tmp/output")
        mock_downloader = MagicMock()
        mock_downloader.is_available.return_value = True
        mock_downloader.download.return_value = MagicMock(
            success=True,
            data={
                'tool': 'you-get',
                'output_dir': '/tmp/output',
                'platform': 'bilibili'
            }
        )
        mock_select.return_value = mock_downloader
        
        # 模拟 LLM 调用
        result = tool.execute(
            url="https://www.bilibili.com/video/BV1234567890",
            download_danmaku=True,
            download_subtitle=True
        )
        
        assert result.success is True
    
    def test_llm_call_parameter_validation(self, tool):
        """测试 LLM 调用参数验证"""
        # 缺少必需参数
        error = tool.validate_parameters()
        assert error is not None
        
        # 无效的质量参数
        error = tool.validate_parameters(
            url="https://www.youtube.com/watch?v=xxx",
            quality="invalid_quality"
        )
        assert error is not None
        
        # 无效的工具选择
        error = tool.validate_parameters(
            url="https://www.youtube.com/watch?v=xxx",
            preferred_tool="invalid_tool"
        )
        assert error is not None
        
        # 有效参数
        error = tool.validate_parameters(
            url="https://www.youtube.com/watch?v=xxx",
            quality="720p",
            preferred_tool="yt-dlp"
        )
        assert error is None
    
    def test_llm_call_error_handling(self, tool):
        """测试 LLM 调用错误处理"""
        # 缺少 URL
        result = tool.execute()
        assert result.success is False
        assert "URL is required" in result.error
        
        # 无效参数 - 参数验证应该在 execute 之前进行
        # 这里只测试 execute 方法本身不会因为无效参数而崩溃
        with patch('backend.core.agent.tools.builtin.video_downloader_tool._select_downloader') as mock_select:
            mock_downloader = MagicMock()
            mock_downloader.is_available.return_value = False
            mock_select.return_value = mock_downloader
            
            result = tool.execute(
                url="https://www.youtube.com/watch?v=xxx",
                quality="invalid"
            )
            # 即使参数无效，execute 也应该返回一个结果
            assert result is not None

