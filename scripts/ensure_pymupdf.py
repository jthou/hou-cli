#!/usr/bin/env python3
# 时间：2026-04-10；理由：PyPI SSL 失败时 requirements 整段不应因 pymupdf 挂死；方法：独立检测 fitz / pip / 打印唯一 apt 提示
"""确保当前 Python 环境中有 PyMuPDF（import fitz），且主版本 >= 1.24。"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from hou_pip_mirror import pip_install_prefix  # noqa: E402

MIN_MAJOR, MIN_MINOR = 1, 24


def _version_ok() -> bool:
    spec = importlib.util.find_spec("fitz")
    if spec is None:
        return False
    try:
        import fitz  # noqa: F401
    except Exception:
        return False
    import fitz as fitz_mod

    v = getattr(fitz_mod, "version", None)
    if not isinstance(v, tuple) or len(v) < 2:
        return False
    try:
        major, minor = int(v[0]), int(v[1])
    except (TypeError, ValueError):
        return False
    return (major, minor) >= (MIN_MAJOR, MIN_MINOR)


def _verify_subprocess() -> bool:
    code = (
        "import fitz; v=fitz.version; "
        "assert isinstance(v,tuple) and len(v)>=2 and (int(v[0]),int(v[1]))>=(1,24)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    if _version_ok():
        print(f"PyMuPDF 已可用（fitz >= {MIN_MAJOR}.{MIN_MINOR}），跳过安装。", file=sys.stderr)
        return 0

    cmd = [sys.executable, "-m", "pip", "install"] + pip_install_prefix()
    wh = os.environ.get("WHEELHOUSE", "").strip()
    if wh:
        cmd.extend(["--no-index", f"--find-links={wh}"])
    cmd.append("pymupdf>=1.24.0")

    print("正在 pip 安装 pymupdf…", file=sys.stderr)
    r = subprocess.run(cmd)
    if r.returncode == 0 and _verify_subprocess():
        print("pymupdf 已通过 pip 安装。", file=sys.stderr)
        return 0

    print(
        "pip 无法安装 pymupdf（常见于 PyPI HTTPS 的 SSLEOF / 证书问题）。\n"
        "Debian/Ubuntu 请使用系统包（需本机 sudo，Agent 无法代输密码）：\n"
        "  sudo apt-get update && sudo apt-get install -y python3-fitz\n"
        "若项目 venv 为隔离环境，安装系统包后需重建 venv 并带上系统 site-packages，例如：\n"
        "  rm -rf venv && python3 -m venv venv --system-site-packages && make install-deps\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
