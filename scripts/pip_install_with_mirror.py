#!/usr/bin/env python3
# 时间：2026-04-10；理由：Makefile 多处 pip install 需同一套默认镜像；方法：封装 pip install + hou_pip_mirror 前缀
"""用法: 与 pip install 相同，额外参数由环境变量 PIP_EXTRA / PIP_USE_OFFICIAL 控制（见 hou_pip_mirror.py）。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from hou_pip_mirror import pip_install_prefix  # noqa: E402


def main() -> int:
    prefix = pip_install_prefix()
    cmd = [sys.executable, "-m", "pip", "install"] + prefix + sys.argv[1:]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
