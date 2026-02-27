"""FFmpegTool 测试"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool, _get_ffmpeg_path, _get_ffprobe_path
from backend.core.agent.tools.base import ToolResult


class TestFFmpegTool:
    """FFmpegTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 FFmpegTool 实例"""
        return FFmpegTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "ffmpeg"
        assert tool.description is not None
        assert len(tool.parameters) >= 1

        param_names = [p.name for p in tool.parameters]
        assert "operation" in param_names

    def test_missing_operation(self, tool):
        """测试缺少 operation 参数"""
        result = tool.execute()
        assert result.success is False
        assert "operation" in result.error.lower() or "必需" in result.error

    def test_invalid_operation(self, tool):
        """测试无效的操作类型"""
        result = tool.execute(operation="invalid_operation")
        assert result.success is False
        assert "未知操作" in result.error or "invalid" in result.error.lower()

    def test_ffmpeg_path_detection(self):
        """测试 FFmpeg 路径检测（系统 PATH 或占位名）"""
        ffmpeg_path = _get_ffmpeg_path()
        assert isinstance(ffmpeg_path, Path)
        assert "ffmpeg" in str(ffmpeg_path).lower()

    def test_ffprobe_path_detection(self):
        """测试 FFprobe 路径检测（系统 PATH 或占位名）"""
        ffprobe_path = _get_ffprobe_path()
        assert isinstance(ffprobe_path, Path)
        assert "ffprobe" in str(ffprobe_path).lower()

    def test_probe_operation_missing_file(self, tool):
        """测试 probe 操作缺少文件"""
        result = tool.execute(operation="probe")
        # probe 操作可能需要 input_file，或者有默认行为
        # 根据实际实现调整断言

    def test_extract_audio_missing_files(self, tool):
        """测试 extract_audio 操作缺少文件"""
        result = tool.execute(operation="extract_audio")
        assert result.success is False
        # 应该提示缺少 input_file 或 output_file

    def test_cut_operation_missing_files(self, tool):
        """测试 cut 操作缺少文件"""
        result = tool.execute(operation="cut")
        assert result.success is False
        # 应该提示缺少必需参数

    def test_convert_operation_missing_files(self, tool):
        """测试 convert 操作缺少文件"""
        result = tool.execute(operation="convert")
        assert result.success is False
        # 应该提示缺少必需参数

    def test_merge_operation_missing_files(self, tool):
        """测试 merge 操作缺少文件"""
        result = tool.execute(operation="merge")
        assert result.success is False
        # 应该提示缺少 input_files 或 output_file

    @pytest.mark.skipif(
        not os.getenv("FFMPEG_TEST_VIDEO_FILE"),
        reason="需要设置 FFMPEG_TEST_VIDEO_FILE 环境变量"
    )
    def test_probe_operation(self, tool):
        """测试 probe 操作（需要真实的视频文件）"""
        video_file = os.getenv("FFMPEG_TEST_VIDEO_FILE")
        if not Path(video_file).exists():
            pytest.skip(f"测试视频文件不存在: {video_file}")

        result = tool.execute(
            operation="probe",
            input_file=video_file
        )

        if result.success:
            assert "format" in result.data or "streams" in result.data
        else:
            # 检查是否是 FFmpeg 未找到
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"FFmpeg 未找到: {result.error}")

    def test_ffmpeg_not_found_error(self, tool):
        """测试 FFmpeg 未找到的错误处理"""
        with patch('backend.core.agent.tools.builtin.ffmpeg_tool._find_ffmpeg_binary') as mock_find:
            mock_find.return_value = None
            
            result = tool.execute(operation="probe", input_file="/dummy/file.mp4")
            assert result.success is False
            assert "未找到" in result.error or "not found" in result.error.lower()


class TestFFmpegToolIntegration:
    """FFmpegTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 FFmpegTool 实例"""
        return FFmpegTool()

    @pytest.mark.skipif(
        not os.getenv("FFMPEG_TEST_VIDEO_FILE"),
        reason="需要设置 FFMPEG_TEST_VIDEO_FILE 环境变量"
    )
    @pytest.mark.integration
    def test_full_probe_workflow(self, tool):
        """测试完整的 probe 工作流"""
        video_file = os.getenv("FFMPEG_TEST_VIDEO_FILE")
        if not Path(video_file).exists():
            pytest.skip(f"测试视频文件不存在: {video_file}")

        result = tool.execute(
            operation="probe",
            input_file=video_file
        )

        if result.success:
            assert "format" in result.data
            format_info = result.data["format"]
            assert "duration" in format_info or "size" in format_info
        else:
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"FFmpeg 未找到: {result.error}")

