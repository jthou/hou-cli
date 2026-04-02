"""
Hou CLI 与 httpx 相关的环境处理。

默认与 httpx 一致：trust_env=True（使用 HTTP_PROXY / HTTPS_PROXY / ALL_PROXY）。
同时把本站、本机 host 合并进 NO_PROXY，使代理**跳过**这些目标（避免自家 Wiki、127.0.0.1 被送进 Clash 等导致 502）。

可选：
- HTTPX_NO_PROXY_EXTRA：逗号分隔，追加到 NO_PROXY
- HTTPX_TRUST_ENV=0|false：整块关掉 trust_env（等价于不信任环境变量代理），用于极端排障
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

# 始终建议直连的 host（小写）；与浏览器「绕过代理」常见列表对齐
_DEFAULT_NO_PROXY_HOSTS = (
    "localhost",
    "127.0.0.1",
    "::1",
    "www.jthou.com",
    "jthou.com",
)


def merge_hou_cli_no_proxy_hosts() -> None:
    """
    将本机/本站 host 合并进 NO_PROXY、no_proxy（不改写已有条目，只追加缺失项）。
    在 load_env() 末尾调用，以便能读到 MEDIAWIKI_URL。
    """
    additions: list[str] = list(_DEFAULT_NO_PROXY_HOSTS)
    wiki = (os.getenv("MEDIAWIKI_URL") or "").strip()
    if wiki:
        try:
            h = (urlparse(wiki).hostname or "").strip().lower()
            if h and h not in additions:
                additions.append(h)
        except Exception:
            pass
    extra = (os.getenv("HTTPX_NO_PROXY_EXTRA") or "").strip()
    if extra:
        for p in extra.split(","):
            pl = p.strip().lower()
            if pl and pl not in additions:
                additions.append(pl)

    for key in ("NO_PROXY", "no_proxy"):
        cur = (os.environ.get(key) or "").strip()
        if cur == "*":
            continue
        if not cur:
            os.environ[key] = ",".join(additions)
            continue
        existing = [x.strip() for x in cur.split(",") if x.strip()]
        seen = {x.lower() for x in existing}
        for a in additions:
            al = a.lower()
            if al not in seen:
                seen.add(al)
                existing.append(a)
        os.environ[key] = ",".join(existing)


def httpx_trust_env_disabled() -> bool:
    """HTTPX_TRUST_ENV=0|false|no|off 时，httpx 不再读取环境代理（trust_env=False）。"""
    v = (os.getenv("HTTPX_TRUST_ENV") or "").strip().lower()
    return v in ("0", "false", "no", "off")


def httpx_uses_environment_proxy() -> bool:
    """网络审计用：当前配置下 httpx 是否会读 HTTP_PROXY / NO_PROXY 等（默认 True）。"""
    return not httpx_trust_env_disabled()


def httpx_default_network_kwargs() -> dict[str, Any]:
    """
    用于 httpx.get/post 或 httpx.AsyncClient(...) 的额外关键字参数。
    默认 {}（trust_env=True）；仅当 HTTPX_TRUST_ENV=0… 时强制 trust_env=False。
    """
    if httpx_trust_env_disabled():
        return {"trust_env": False, "proxy": None}
    return {}
