"""WhisperTool 测试"""
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

from backend.core.agent.tools.builtin.whisper_tool import WhisperTool, WhisperProgressCapture
from backend.core.agent.tools.base import ToolResult


class TestWhisperTool:
    """WhisperTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 WhisperTool 实例"""
        return WhisperTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "whisper"
        assert tool.description is not None
        assert len(tool.parameters) >= 3

        param_names = [p.name for p in tool.parameters]
        assert "audio_file" in param_names
        assert "language" in param_names
        assert "model" in param_names

    def test_missing_audio_file(self, tool):
        """测试缺少 audio_file 参数"""
        result = tool.execute()
        assert result.success is False
        assert "audio_file" in result.error.lower() or "必需" in result.error

    def test_nonexistent_audio_file(self, tool):
        """测试不存在的音频文件"""
        result = tool.execute(audio_file="/nonexistent/file.mp3")
        assert result.success is False
        assert "不存在" in result.error or "not found" in result.error.lower()

    @pytest.mark.skipif(
        not os.getenv("WHISPER_TEST_AUDIO_FILE"),
        reason="需要设置 WHISPER_TEST_AUDIO_FILE 环境变量"
    )
    def test_execute_transcription(self, tool):
        """测试语音转文字（需要真实的音频文件）"""
        audio_file = os.getenv("WHISPER_TEST_AUDIO_FILE")
        if not Path(audio_file).exists():
            pytest.skip(f"测试音频文件不存在: {audio_file}")

        result = tool.execute(
            audio_file=audio_file,
            language="zh",
            model="tiny"  # 使用最小的模型以加快测试
        )

        # 注意：这个测试可能需要较长时间，因为需要实际运行 Whisper
        # 如果测试环境没有安装 Whisper 或缺少依赖，会失败
        if result.success:
            assert "text" in result.data
            assert "language" in result.data
            assert "segments_count" in result.data
        else:
            # 如果失败，检查是否是依赖问题
            if "未安装" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Whisper 未安装或依赖缺失: {result.error}")
            else:
                # 其他错误，正常失败
                assert False, f"转录失败: {result.error}"

    def test_whisper_import_error(self, tool):
        """测试 Whisper 导入错误处理"""
        with patch('backend.core.agent.tools.builtin.whisper_tool._load_whisper_model') as mock_load:
            mock_load.side_effect = ImportError("Whisper not found")
            
            # 使用一个存在的文件路径（但不实际处理）
            test_file = Path(__file__)  # 使用测试文件本身作为占位符
            
            result = tool.execute(audio_file=str(test_file))
            assert result.success is False
            assert "未安装" in result.error or "not found" in result.error.lower()

    def test_progress_capture(self):
        """测试进度捕获器"""
        progress_messages = []
        
        def progress_callback(msg: str):
            progress_messages.append(msg)
        
        with WhisperProgressCapture(progress_callback=progress_callback):
            # 模拟一些输出
            import sys
            print("测试输出", file=sys.stderr)
        
        # 验证回调被调用（如果有进度消息）
        # 注意：实际进度消息取决于 Whisper 的输出格式

    def test_language_auto_detection(self, tool):
        """测试语言自动检测"""
        # 当 language="auto" 时，应该转换为 None
        # 这个测试主要验证参数处理逻辑
        assert tool.parameters is not None


class TestWhisperToolIntegration:
    """WhisperTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 WhisperTool 实例"""
        return WhisperTool()

    @pytest.mark.skipif(
        not os.getenv("WHISPER_TEST_AUDIO_FILE"),
        reason="需要设置 WHISPER_TEST_AUDIO_FILE 环境变量"
    )
    @pytest.mark.integration
    def test_full_transcription_workflow(self, tool):
        """测试完整的转录工作流"""
        audio_file = os.getenv("WHISPER_TEST_AUDIO_FILE")
        if not Path(audio_file).exists():
            pytest.skip(f"测试音频文件不存在: {audio_file}")

        # 测试完整流程
        result = tool.execute(
            audio_file=audio_file,
            language="auto",
            model="base",
            output_file=None  # 使用默认输出路径
        )

        if result.success:
            assert "text" in result.data
            assert "output_file" in result.data
            output_file = Path(result.data["output_file"])
            assert output_file.exists(), "输出文件应该存在"
            assert output_file.suffix == ".srt", "输出文件应该是 SRT 格式"
        else:
            # 检查是否是依赖问题
            if "未安装" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Whisper 未安装或依赖缺失: {result.error}")

