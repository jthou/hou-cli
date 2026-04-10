# 时间：2026-04-10；理由：pypi.org/镜像 HTTPS SSLEOF 时安装全挂；方法：默认阿里云，HTTPS 探针失败则自动改 HTTP 索引；preflight 默认不挡 make
"""hou-cli Makefile / 脚本共用的 pip 镜像与索引选择。"""
from __future__ import annotations

import os
import shlex
import ssl
import sys
import urllib.request
from typing import List, Optional

DEFAULT_INDEX_BASE = "https://mirrors.aliyun.com/pypi/simple"
DEFAULT_TRUSTED_HOST = "mirrors.aliyun.com"
HTTP_INDEX_BASE = "http://mirrors.aliyun.com/pypi/simple"

_aliyun_resolved: Optional[List[str]] = None


def _probe_get(url: str, *, use_tls: bool, timeout: float = 12.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "hou-cli-pip-probe/1.0"})
        kw: dict = {"timeout": timeout}
        if use_tls:
            kw["context"] = ssl.create_default_context()
        with urllib.request.urlopen(req, **kw) as resp:
            return resp.status == 200
    except Exception:
        return False


def _https_aliyun_prefix() -> List[str]:
    return [
        "-i",
        DEFAULT_INDEX_BASE + "/",
        "--trusted-host",
        DEFAULT_TRUSTED_HOST,
    ]


def _http_aliyun_prefix() -> List[str]:
    return [
        "-i",
        HTTP_INDEX_BASE + "/",
        "--trusted-host",
        DEFAULT_TRUSTED_HOST,
    ]


def _choose_aliyun_prefix() -> List[str]:
    """
    允许回退时：**优先 HTTP 索引**（与 pip 的 TLS 栈一致；urllib 探针 HTTPS 通过但 pip SSLEOF 时仍应走 HTTP）。
    否则仅用 HTTPS。
    """
    global _aliyun_resolved
    if _aliyun_resolved is not None:
        return list(_aliyun_resolved)

    https_p = _https_aliyun_prefix()
    http_p = _http_aliyun_prefix()
    fb = os.environ.get("HOU_PIP_HTTP_FALLBACK", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    if not fb:
        _aliyun_resolved = https_p
        return list(https_p)

    u_http = HTTP_INDEX_BASE.rstrip("/") + "/fastapi/"
    u_https = DEFAULT_INDEX_BASE.rstrip("/") + "/fastapi/"

    if _probe_get(u_http, use_tls=False):
        print(
            "hou-cli: 使用阿里云 PyPI **HTTP** 索引（规避部分环境 pip 访问 HTTPS 镜像的 SSLEOF；"
            "wheel 链接若指向外站 HTTPS 仍可能失败，需代理/证书或 WHEELHOUSE）。",
            file=sys.stderr,
        )
        _aliyun_resolved = http_p
        return list(http_p)

    if _probe_get(u_https, use_tls=True):
        _aliyun_resolved = https_p
        return list(https_p)

    print(
        "hou-cli: 阿里云 HTTP/HTTPS 索引均不可达，仍尝试 HTTPS（pip 可能失败）。",
        file=sys.stderr,
    )
    _aliyun_resolved = https_p
    return list(https_p)


def pip_install_prefix() -> List[str]:
    """
    传给 `pip install` 的前缀参数。
    - PIP_INSECURE_INDEX=1：强制阿里云 HTTP 索引。
    - PIP_USE_OFFICIAL=1：官方行为；仅当 PIP_EXTRA 非空时附加其参数。
    - PIP_EXTRA 非空：解析后作为前缀（与官方/镜像互斥由用户负责）。
    - 否则：阿里云，且可在 HTTPS 失败时自动降为 HTTP（HOU_PIP_HTTP_FALLBACK=0 可关闭）。
    """
    if os.environ.get("PIP_INSECURE_INDEX", "").strip() == "1":
        return _http_aliyun_prefix()

    official = os.environ.get("PIP_USE_OFFICIAL", "").strip() == "1"
    extra = os.environ.get("PIP_EXTRA", "").strip()

    if official:
        return shlex.split(extra) if extra else []

    if extra:
        return shlex.split(extra)

    return _choose_aliyun_prefix()


def preflight_fastapi_url() -> str:
    """与 pip_install_prefix() 当前选择的索引对应的 fastapi 包页 URL。"""
    if os.environ.get("PIP_INDEX_URL", "").strip():
        base = os.environ["PIP_INDEX_URL"].strip().rstrip("/")
        return base + "/fastapi/"

    pre = pip_install_prefix()
    for i, a in enumerate(pre):
        if a in ("-i", "--index-url", "--index") and i + 1 < len(pre):
            base = pre[i + 1].rstrip("/")
            return base + "/fastapi/"

    if not pre:
        return "https://pypi.org/simple/fastapi/"
    return DEFAULT_INDEX_BASE.rstrip("/") + "/fastapi/"
