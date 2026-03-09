"""Preflight 测试"""
import pytest
from pathlib import Path

from backend.infrastructure.execution.preflight import (
    validate_code_for_shell_bleed,
    validate_script_for_shell_bleed,
)


class TestValidateCodeForShellBleed:
    """validate_code_for_shell_bleed 测试"""

    def test_safe_python_code(self):
        """安全 Python 代码不应报错"""
        validate_code_for_shell_bleed("print('hello')", "python")
        validate_code_for_shell_bleed("x = os.environ.get('PATH')", "python")

    def test_python_with_shell_var_raises(self):
        """Python 代码中的 $PATH 应 raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_code_for_shell_bleed("path = $PATH", "python")
        assert "$PATH" in str(exc_info.value) or "PATH" in str(exc_info.value)
        assert "os.environ" in str(exc_info.value)

    def test_zsh_with_var_allowed(self):
        """zsh 中的 $VAR 是合法的，不应报错"""
        validate_code_for_shell_bleed("echo $HOME", "zsh")

    def test_non_python_ignored(self):
        """非 Python 语言不检查"""
        validate_code_for_shell_bleed("echo $PATH", "zsh")
        validate_code_for_shell_bleed("echo $PATH", "bash")

    def test_empty_code(self):
        """空代码不应报错"""
        validate_code_for_shell_bleed("", "python")
        validate_code_for_shell_bleed("  ", "python")
