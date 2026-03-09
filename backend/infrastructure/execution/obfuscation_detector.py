"""混淆检测

借鉴 OpenClaw：检测 base64|eval|xxd|printf 等混淆模式，防止绕过黑名单。
"""
import re
from dataclasses import dataclass
from typing import List


@dataclass
class ObfuscationResult:
    """混淆检测结果"""
    detected: bool
    reasons: List[str]
    matched_patterns: List[str]


# Shell 混淆模式（zsh/bash 等）
_SHELL_PATTERNS = [
    ("base64-pipe-exec", "Base64 解码后管道到 shell", r"base64\s+(?:-d|--decode)\b.*\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b"),
    ("hex-pipe-exec", "xxd 解码后管道到 shell", r"xxd\s+-r\b.*\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b"),
    ("printf-pipe-exec", "printf 转义序列管道到 shell", r"printf\s+.*\\x[0-9a-f]{2}.*\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b"),
    ("eval-decode", "eval 与 base64/xxd/decode 组合", r"eval\s+.*(?:base64|xxd|printf|decode)"),
    ("base64-decode-to-shell", "管道 base64 解码到 shell", r"\|\s*base64\s+(?:-d|--decode)\b.*\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b"),
    ("pipe-to-shell", "内容直接管道到 shell", r"\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b(?:\s+[^|;\n\r]+)?\s*$"),
    ("command-substitution-decode", "Shell -c 与命令替换解码", r"(?:sh|bash|zsh|dash|ksh|fish)\s+-c\s+[\"'][^\"']*\$\([^)]*(?:base64\s+(?:-d|--decode)|xxd\s+-r|printf\s+.*\\x[0-9a-f]{2})[^)]*\)[^\"']*[\"']"),
    ("curl-pipe-shell", "curl/wget 管道到 shell", r"(?:curl|wget)\s+.*\|\s*(?:sh|bash|zsh|dash|ksh|fish)\b"),
    ("source-curl", "source 远程内容", r"(?:^|[;&\s])(?:source|\.)\s+<\(\s*(?:curl|wget)\b"),
    ("octal-escape", "Bash 八进制转义", r"\$'(?:[^']*\\[0-7]{3}){2,}"),
    ("hex-escape", "Bash 十六进制转义", r"\$'(?:[^']*\\x[0-9a-fA-F]{2}){2,}"),
]

# Python 混淆模式
_PYTHON_PATTERNS = [
    ("python-eval-b64", "eval(base64.b64decode", r"eval\s*\(\s*.*(?:base64\.b64decode|b64decode)"),
    ("python-exec-b64", "exec(base64", r"exec\s*\(\s*.*(?:base64\.b64decode|b64decode)"),
    ("python-os-system-b64", "os.system 含 base64", r"os\.system\s*\(\s*[^)]*(?:base64|b64decode)"),
    ("python-subprocess-b64", "subprocess 含 base64", r"subprocess\.(?:call|run|Popen|check_output)\s*\([^)]*(?:base64|b64decode)"),
    ("python-compile-exec", "compile+exec 动态执行", r"(?:compile|__import__)\s*\([^)]*\)\s*.*\bexec\b"),
]

# 误报抑制：常见合法安装脚本
_FALSE_POSITIVE_SUPPRESSIONS = [
    (r"curl\s+.*https?://(?:raw\.githubusercontent\.com/Homebrew|brew\.sh)\b", ["curl-pipe-shell"]),
    (r"curl\s+.*https?://(?:raw\.githubusercontent\.com/nvm-sh/nvm|sh\.rustup\.rs|get\.docker\.com)\b", ["curl-pipe-shell"]),
    (r"curl\s+.*https?://(?:get\.pnpm\.io|bun\.sh/install)\b", ["curl-pipe-shell"]),
]


class ObfuscationDetector:
    """混淆检测器"""

    def detect(self, code: str, language: str) -> ObfuscationResult:
        """
        检测代码中的混淆模式。

        Args:
            code: 代码内容
            language: 语言（python, zsh, shell 等）

        Returns:
            ObfuscationResult
        """
        if not code or not code.strip():
            return ObfuscationResult(detected=False, reasons=[], matched_patterns=[])

        reasons: List[str] = []
        matched: List[str] = []
        lang_lower = (language or "").strip().lower()

        # 选择模式集
        if lang_lower in ("python", "py"):
            patterns = _PYTHON_PATTERNS
        else:
            # zsh, shell, bash, sh 等
            patterns = _SHELL_PATTERNS

        for pattern_id, description, regex_str in patterns:
            try:
                if re.search(regex_str, code, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                    # 误报抑制
                    if self._is_suppressed(code, pattern_id):
                        continue
                    matched.append(pattern_id)
                    reasons.append(description)
            except re.error:
                continue

        return ObfuscationResult(
            detected=len(matched) > 0,
            reasons=reasons,
            matched_patterns=matched,
        )

    def _is_suppressed(self, code: str, pattern_id: str) -> bool:
        """检查是否被误报抑制规则排除"""
        for supp_regex, supp_ids in _FALSE_POSITIVE_SUPPRESSIONS:
            if pattern_id not in supp_ids:
                continue
            if re.search(supp_regex, code, re.IGNORECASE):
                return True
        return False
