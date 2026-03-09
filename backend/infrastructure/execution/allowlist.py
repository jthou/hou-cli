"""Allowlist 评估器

借鉴 OpenClaw：命中 allowlist 的命令可免审直接执行。
"""
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class AllowlistResult:
    """Allowlist 评估结果"""
    satisfied: bool
    matched_pattern: Optional[str] = None
    description: Optional[str] = None


# 默认 allowlist 模式（按优先级，先匹配先返回）
# 对于 execute_code，command 为代码内容；对于 exec，command 为 shell 命令
_DEFAULT_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern_id, description, regex)
    ("ls", "列出目录", r"^\s*ls(\s+[\w./\-]+)*\s*$"),
    ("cat", "读取文件", r"^\s*cat\s+[\w./\-]+\s*$"),
    ("pwd", "当前目录", r"^\s*pwd\s*$"),
    ("echo", "输出", r"^\s*echo\s+.*$"),
    ("whoami", "当前用户", r"^\s*whoami\s*$"),
    ("date", "日期", r"^\s*date\s*(\s+[\w\-]+)*\s*$"),
    ("rm-single", "删除单文件（非 -rf）", r"^\s*rm\s+[\w./\-]+\s*$"),
    ("rm-tmp", "删除 /tmp 下", r"^\s*rm\s+-rf\s+/tmp/[\w./\-]+\s*$"),
    ("rm-rel", "删除当前目录下", r"^\s*rm\s+-rf\s+\./[\w./\-]*\s*$"),
    ("rm-rel-no-slash", "删除相对路径", r"^\s*rm\s+-rf\s+[\w./\-]+\s*$"),  # rm -rf build（/ 已在 _is_dangerous 排除）
    ("mkdir", "创建目录", r"^\s*mkdir\s+[\w./\-]+\s*$"),
    ("touch", "创建文件", r"^\s*touch\s+[\w./\-]+\s*$"),
    ("cp", "复制", r"^\s*cp\s+[\w./\-]+\s+[\w./\-]+\s*$"),
    ("mv", "移动", r"^\s*mv\s+[\w./\-]+\s+[\w./\-]+\s*$"),
]


class AllowlistEvaluator:
    """Allowlist 评估器

    评估命令/代码是否命中 allowlist，命中则免审执行。
    """

    def __init__(self, patterns: Optional[List[Tuple[str, str, str]]] = None):
        """
        Args:
            patterns: 可选，自定义模式 [(pattern_id, description, regex), ...]
        """
        self.patterns = patterns or _DEFAULT_PATTERNS

    def evaluate(
        self,
        command: str,
        workdir: str = "",
        language: str = "zsh"
    ) -> AllowlistResult:
        """
        评估命令是否命中 allowlist。

        Args:
            command: 命令或代码内容（对 execute_code 为代码，对 exec 为 shell 命令）
            workdir: 工作目录（可选）
            language: 语言

        Returns:
            AllowlistResult(satisfied=True 若命中)
        """
        if not command or not command.strip():
            return AllowlistResult(satisfied=False)

        # 取首行作为主命令（多行脚本时）
        first_line = command.strip().split("\n")[0].strip()
        # 去掉行尾注释
        if "#" in first_line:
            first_line = first_line.split("#")[0].strip()
        if not first_line:
            return AllowlistResult(satisfied=False)

        # 排除危险模式：即使有宽松的 allowlist，这些也不允许
        if self._is_dangerous(first_line):
            return AllowlistResult(satisfied=False)

        for pattern_id, description, regex_str in self.patterns:
            try:
                if re.match(regex_str, first_line, re.IGNORECASE):
                    return AllowlistResult(
                        satisfied=True,
                        matched_pattern=pattern_id,
                        description=description
                    )
            except re.error:
                continue

        return AllowlistResult(satisfied=False)

    # 受限路径（与 SecureExecutor 一致）
    RESTRICTED_PATHS = [
        "/etc", "/sys", "/proc", "/dev", "/root",
        "C:\\Windows\\System32", "C:\\Windows\\SysWOW64"
    ]

    def _is_dangerous(self, line: str) -> bool:
        """排除明显危险模式"""
        line_lower = line.lower()
        for rp in self.RESTRICTED_PATHS:
            if rp.lower() in line_lower:
                return True
        dangerous = [
            r"rm\s+-rf\s+/\s*$",       # rm -rf / 仅根
            r"rm\s+-rf\s+/etc",
            r"rm\s+-rf\s+/sys",
            r"rm\s+-rf\s+/proc",
            r"rm\s+-rf\s+/dev",
            r"rm\s+-rf\s+/root",
            r"dd\s+if=",
            r"format\s+",
            r"mkfs\s+",
            r"fdisk\s+",
            r":\s*\{\s*:\s*\|",        # fork bomb
        ]
        for p in dangerous:
            if re.search(p, line_lower):
                return True
        return False


# 单例，供全局使用
_default_evaluator: Optional[AllowlistEvaluator] = None


def get_allowlist_evaluator() -> AllowlistEvaluator:
    """获取默认 AllowlistEvaluator 实例"""
    global _default_evaluator
    if _default_evaluator is None:
        _default_evaluator = AllowlistEvaluator()
    return _default_evaluator
