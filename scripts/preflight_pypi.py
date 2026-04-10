#!/usr/bin/env python3
# 时间：2026-04-10；理由：HTTPS SSLEOF 时不应挡死 make；方法：触发索引选择（含自动 HTTP 回退）；仅 STRICT_PYPI_CHECK=1 时探测失败才 exit 1
"""install-deps 第 3 步前：解析 pip 索引（与 pip_install_with_mirror 一致）。"""
from __future__ import annotations

import os
import ssl
import sys
import urllib.request
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from hou_pip_mirror import pip_install_prefix, preflight_fastapi_url  # noqa: E402


def _probe(url: str, timeout: float = 12.0) -> bool:
    use_tls = url.startswith("https://")
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "hou-cli-preflight/1.0"})
        kw: dict = {"timeout": timeout}
        if use_tls:
            kw["context"] = ssl.create_default_context()
        with urllib.request.urlopen(req, **kw) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> int:
    if os.environ.get("SKIP_PYPI_CHECK", "").strip() == "1":
        print("SKIP_PYPI_CHECK=1，跳过 preflight。", file=sys.stderr)
        return 0
    if os.environ.get("WHEELHOUSE", "").strip():
        print("已设置 WHEELHOUSE，跳过 preflight。", file=sys.stderr)
        return 0

    pip_install_prefix()
    url = preflight_fastapi_url()
    print(f"hou-cli preflight: 将使用索引页 {url}", file=sys.stderr)

    if os.environ.get("STRICT_PYPI_CHECK", "").strip() == "1":
        if not _probe(url):
            print(f"[hou-cli] STRICT_PYPI_CHECK=1：索引不可达 {url}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
