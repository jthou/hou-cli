"""混淆检测器测试"""
import pytest
from backend.infrastructure.execution.obfuscation_detector import ObfuscationDetector


class TestObfuscationDetector:
    """ObfuscationDetector 测试"""

    @pytest.fixture
    def detector(self):
        return ObfuscationDetector()

    def test_safe_python_code(self, detector):
        """安全 Python 代码不应被检测"""
        result = detector.detect("print('hello')", "python")
        assert result.detected is False
        assert len(result.reasons) == 0

    def test_safe_zsh_code(self, detector):
        """安全 zsh 代码不应被检测"""
        result = detector.detect("echo hello", "zsh")
        assert result.detected is False

    def test_python_eval_b64_detected(self, detector):
        """Python eval(base64) 应被检测"""
        code = "eval(base64.b64decode('aGVsbG8='))"
        result = detector.detect(code, "python")
        assert result.detected is True
        assert any("eval" in r or "base64" in r for r in result.reasons)

    def test_shell_base64_pipe_detected(self, detector):
        """Shell base64|sh 应被检测"""
        code = "echo aGVsbG8= | base64 -d | sh"
        result = detector.detect(code, "zsh")
        assert result.detected is True

    def test_empty_code(self, detector):
        """空代码不应被检测"""
        result = detector.detect("", "python")
        assert result.detected is False
        result = detector.detect("   \n  ", "zsh")
        assert result.detected is False
