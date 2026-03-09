"""Preflight 检查

借鉴 OpenClaw：检测 Python/Node 脚本中的 shell 变量注入（如 $PATH）。
"""
import re
from pathlib import Path

# 匹配 $VAR 形式（全大写+下划线，常见 shell 变量）
_SHELL_VAR_REGEX = re.compile(r"\$[A-Z_][A-Z0-9_]{1,}", re.MULTILINE)

# 解析 command 中的 python file.py / node file.js
_PYTHON_CMD = re.compile(r"^\s*(?:python3?|python)\s+(?:-[^\s]+\s+)*([^\s]+\.py)\b", re.IGNORECASE)
_NODE_CMD = re.compile(r"^\s*(?:node)\s+(?:--[^\s]+\s+)*([^\s]+\.js)\b", re.IGNORECASE)

_MAX_FILE_SIZE = 512 * 1024  # 512KB
_MAX_LINES_SCAN = 50


def validate_code_for_shell_bleed(code: str, language: str) -> None:
    """
    当 language 为 python 时，检测代码中的 $VAR（常见错误：把 shell 变量写进 Python）。

    Args:
        code: 代码内容
        language: 语言

    Raises:
        ValueError: 检测到可能的 shell 变量注入
    """
    if not code or (language or "").strip().lower() != "python":
        return
    m = _SHELL_VAR_REGEX.search(code)
    if m:
        var = m.group(0)
        raise ValueError(
            f"exec preflight: detected likely shell variable injection ({var}) in Python code. "
            f"In Python, use os.environ.get({var[1:]!r}) instead of raw {var}. "
            "(If inside a string literal on purpose, escape or restructure.)"
        )


def validate_script_for_shell_bleed(command: str, workdir: Path) -> None:
    """
    解析 command 中的 python file.py / node file.js，
    读取文件内容，检测 $VAR 模式，若存在则 raise ValueError。

    Args:
        command: 要执行的命令
        workdir: 工作目录（用于解析相对路径）

    Raises:
        ValueError: 检测到可能的 shell 变量注入
    """
    if not command or not command.strip():
        return

    target = _extract_script_target(command)
    if not target:
        return

    abs_path = (target.path if Path(target.path).is_absolute()
                else (workdir / target.path)).resolve()

    if not abs_path.exists():
        return

    try:
        stat = abs_path.stat()
        if not stat.is_file() or stat.size > _MAX_FILE_SIZE:
            return
    except OSError:
        return

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    lines = content.splitlines()[: _MAX_LINES_SCAN]
    for i, line in enumerate(lines, 1):
        m = _SHELL_VAR_REGEX.search(line)
        if m:
            var = m.group(0)
            hint = (
                f"In Python, use os.environ.get({var[1:]!r}) instead of raw {var}."
                if target.kind == "python"
                else f"In Node.js, use process.env[{var[1:]!r}] instead of raw {var}."
            )
            raise ValueError(
                f"exec preflight: detected likely shell variable injection ({var}) "
                f"in {target.kind} script: {abs_path.name}:{i}. {hint} "
                "(If inside a string literal on purpose, escape or restructure.)"
            )

    # Node 额外检查：首行是否为 shell 语法
    if target.kind == "node":
        first = next((l.strip() for l in lines if l.strip()), "")
        if first and re.match(r"^NODE\b", first, re.IGNORECASE):
            raise ValueError(
                f"exec preflight: JS file starts with shell syntax ({first[:50]}). "
                "This looks like a shell command, not JavaScript."
            )


def _extract_script_target(command: str) -> "ScriptTarget | None":
    """从命令中解析脚本文件路径"""
    raw = command.strip()
    if not raw:
        return None

    m = _PYTHON_CMD.match(raw)
    if m:
        return _ScriptTarget("python", m.group(1))

    m = _NODE_CMD.match(raw)
    if m:
        return _ScriptTarget("node", m.group(1))

    return None


class _ScriptTarget:
    def __init__(self, kind: str, path: str):
        self.kind = kind
        self.path = path
