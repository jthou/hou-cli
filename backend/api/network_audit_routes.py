"""网络状况审计 API - 按 docs/design/network-audit-design.md 实现"""
import asyncio
import logging
import os
import re
import socket
import time
from urllib.request import getproxies
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter

from backend.config.network_audit_targets import get_audit_targets

router = APIRouter()
logger = logging.getLogger(__name__)

TIMEOUT = 6
MAX_HISTORY = 5
_audit_history: deque = deque(maxlen=MAX_HISTORY)

# 部分服务（如 ip.skk.moe）会拒绝无 User-Agent 的请求
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _get_local_ips() -> List[str]:
    """获取本机 IP 列表（含回环、局域网等）"""
    ips = []
    try:
        hostname = socket.gethostname()
        ips.append(socket.gethostbyname(hostname))
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip not in ips:
            ips.append(ip)
    except Exception:
        pass
    return list(dict.fromkeys(ips)) if ips else []


def _get_proxy_settings() -> Dict[str, Any]:
    """获取代理配置：优先环境变量，否则从系统设置获取"""
    from_env = {}
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
        "NO_PROXY", "no_proxy", "ALL_PROXY", "all_proxy",
    ):
        val = os.environ.get(key, "").strip()
        if val:
            from_env[key] = val
    if from_env:
        return {"source": "env", "proxies": from_env}
    try:
        sys_proxies = getproxies()
        if sys_proxies:
            return {"source": "system", "proxies": sys_proxies}
    except Exception:
        pass
    return {"source": "none", "proxies": {}}


def _fetch_ip_geo(ip: str) -> Optional[Dict[str, str]]:
    """根据 IP 查询地理位置（国家、地区），使用 ip-api.com 免费接口"""
    if not ip or not re.match(r"^[\d.a-fA-F:]+$", ip):
        return None
    try:
        url = (
            f"http://ip-api.com/json/{ip}"
            "?fields=status,country,countryCode,regionName,city&lang=zh-CN"
        )
        r = requests.get(url, timeout=4, headers=DEFAULT_HEADERS)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "success":
            return None
        country = data.get("country") or ""
        region = data.get("regionName") or data.get("city") or ""
        return {"country": country, "region": region}
    except Exception:
        return None


def _parse_ip_from_response(r: requests.Response) -> Optional[str]:
    """从响应解析 IP"""
    try:
        data = r.json()
        if isinstance(data, dict):
            return data.get("ip") or None
    except Exception:
        pass
    raw = (r.text or "").strip()
    line = raw.splitlines()[0].strip() if raw else ""
    return line if re.match(r"^[\d.]+\Z", line) else None


def _probe_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """探测单个 URL，返回 status、latency_ms、error。
    status: ok=2xx, reachable=4xx(网络可达但需认证/正确路径), fail=超时/连接失败/5xx
    """
    start = time.perf_counter()
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        if method.upper() == "GET":
            r = requests.get(
                url, timeout=TIMEOUT, headers=hdrs, params=params
            )
        else:
            r = requests.post(
                url, data={}, timeout=TIMEOUT, headers=hdrs, params=params
            )
        latency_ms = int((time.perf_counter() - start) * 1000)
        if 200 <= r.status_code < 300:
            return {"status": "ok", "latency_ms": latency_ms}
        if 400 <= r.status_code < 500:
            return {
                "status": "reachable",
                "latency_ms": latency_ms,
                "error": f"{r.status_code} {r.reason}",
            }
        return {
            "status": "fail",
            "latency_ms": latency_ms,
            "error": f"{r.status_code} {r.reason}",
        }
    except requests.exceptions.Timeout as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"status": "fail", "latency_ms": latency_ms, "error": f"超时: {e}"}
    except requests.exceptions.SSLError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"status": "fail", "latency_ms": latency_ms, "error": f"SSL: {e}"}
    except requests.exceptions.RequestException as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"status": "fail", "latency_ms": latency_ms, "error": str(e)}
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"status": "fail", "latency_ms": latency_ms, "error": str(e)}


def _run_single_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """执行单个目标的检测"""
    tid = target["id"]
    name = target["name"]
    method = target.get("method", "GET")

    # 未配置则跳过
    if not target.get("configured", True):
        return {
            "id": tid,
            "name": name,
            "url": target.get("url"),
            "status": "skip",
            "latency_ms": None,
            "error": "未配置（缺少环境变量）",
        }

    # 无 URL 则跳过
    url = target.get("url")
    if not url:
        return {
            "id": tid,
            "name": name,
            "url": None,
            "status": "skip",
            "latency_ms": None,
            "error": "无法解析 URL",
        }

    # 出口 IP：多源任一连通即可，并解析返回的 IP（需 2xx 才能解析）
    if tid == "outbound_ip":
        sources = target.get("sources", [url])
        for src in sources:
            start = time.perf_counter()
            try:
                r = requests.get(src, timeout=TIMEOUT, headers=DEFAULT_HEADERS)
                if 200 <= r.status_code < 300:
                    latency_ms = int((time.perf_counter() - start) * 1000)
                    outbound_ip = _parse_ip_from_response(r)
                    return {
                        "id": tid,
                        "name": name,
                        "url": src,
                        "status": "ok",
                        "latency_ms": latency_ms,
                        "error": None,
                        "outbound_ip": outbound_ip,
                    }
            except Exception:
                continue
        last = _probe_url(sources[-1], method)
        return {
            "id": tid,
            "name": name,
            "url": sources[0],
            "status": "fail",
            "latency_ms": last.get("latency_ms"),
            "error": last.get("error", "所有出口 IP 源均不可达"),
        }

    # 需要 .env 授权的目标：使用配置的 API Key / 凭据发起请求
    auth_type = target.get("auth_type")
    headers = None
    params = None

    if auth_type == "bearer":
        api_key = (
            os.getenv(target.get("api_key_env", ""))
            or os.getenv(target.get("api_key_env_alt", ""))
            or ""
        ).strip()
        if not api_key:
            return {
                "id": tid,
                "name": name,
                "url": url,
                "status": "skip",
                "latency_ms": None,
                "error": "未配置（缺少 API Key）",
            }
        headers = {"Authorization": f"Bearer {api_key}"}
    elif auth_type == "wechat":
        app_id = (os.getenv("WECHAT_MP_APP_ID") or "").strip()
        app_secret = (os.getenv("WECHAT_MP_APP_SECRET") or "").strip()
        if not app_id or not app_secret:
            return {
                "id": tid,
                "name": name,
                "url": url,
                "status": "skip",
                "latency_ms": None,
                "error": "未配置（缺少 WECHAT_MP_APP_ID / WECHAT_MP_APP_SECRET）",
            }
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
    elif auth_type == "jwt":
        try:
            from backend.core.agent.tools.auth.jwt_auth import (
                JWTAuth,
                JWTAuthError,
            )
            jwt_auth = JWTAuth.from_env()
            auth_header = jwt_auth.get_authorization_header()
            headers = {"Authorization": auth_header}
        except (JWTAuthError, Exception) as e:
            return {
                "id": tid,
                "name": name,
                "url": url,
                "status": "skip",
                "latency_ms": None,
                "error": f"未配置或 JWT 加载失败: {e}",
            }

    res = _probe_url(url, method, headers=headers, params=params)
    return {
        "id": tid,
        "name": name,
        "url": url,
        "status": res["status"],
        "latency_ms": res.get("latency_ms"),
        "error": res.get("error"),
    }


async def _run_audit_async() -> List[Dict[str, Any]]:
    """并发执行所有目标检测（线程池中运行 requests）"""
    loop = asyncio.get_event_loop()
    targets = get_audit_targets()
    tasks = [loop.run_in_executor(None, _run_single_target, t) for t in targets]
    return await asyncio.gather(*tasks)


@router.get("/network/audit/targets")
async def get_targets():
    """返回审计目标列表（含是否已配置、当前 URL）"""
    try:
        targets = get_audit_targets()
        return {"success": True, "targets": targets}
    except Exception as e:
        logger.exception("获取审计目标失败")
        return {"success": False, "error": str(e), "targets": []}


def _build_env_info(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构建环境信息：本机 IP、出口 IP、代理设置、网络状况"""
    outbound_ip = None
    for r in results:
        if r.get("id") == "outbound_ip" and r.get("status") == "ok":
            outbound_ip = r.get("outbound_ip")
            break

    outbound_location = None
    if outbound_ip:
        outbound_location = _fetch_ip_geo(outbound_ip)

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    reachable_count = sum(1 for r in results if r.get("status") == "reachable")
    fail_count = sum(1 for r in results if r.get("status") == "fail")
    skip_count = sum(1 for r in results if r.get("status") == "skip")
    total = len(results)
    parts = [f"{ok_count} 正常"]
    if reachable_count:
        parts.append(f"{reachable_count} 可达(4xx)")
    if fail_count:
        parts.append(f"{fail_count} 失败")
    if skip_count:
        parts.append(f"{skip_count} 跳过")
    summary = ", ".join(parts)

    return {
        "local_ips": _get_local_ips(),
        "outbound_ip": outbound_ip,
        "outbound_location": outbound_location,
        "proxy_settings": _get_proxy_settings(),
        "summary": summary,
        "ok_count": ok_count,
        "reachable_count": reachable_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
    }


@router.get("/network/audit/env")
async def get_env():
    """返回本机 IP、代理设置（无需执行检测）"""
    try:
        return {
            "success": True,
            "local_ips": _get_local_ips(),
            "proxy_settings": _get_proxy_settings(),
        }
    except Exception as e:
        logger.exception("获取环境信息失败")
        return {"success": False, "error": str(e)}


@router.post("/network/audit/run")
async def run_audit():
    """触发一次网络检测，返回各目标结果及环境信息"""
    try:
        results = await _run_audit_async()
        created_at = datetime.now(timezone.utc).isoformat()
        env_info = _build_env_info(results)
        entry = {
            "created_at": created_at,
            "results": results,
            "env": env_info,
        }
        _audit_history.append(entry)
        return {
            "success": True,
            "results": results,
            "created_at": created_at,
            "env": env_info,
        }
    except Exception as e:
        logger.exception("执行网络审计失败")
        return {"success": False, "error": str(e), "results": []}


@router.get("/network/audit/history")
async def get_history():
    """返回最近几次检测记录（内存存储，进程重启后清空）"""
    items = []
    for entry in _audit_history:
        e = dict(entry)
        if "env" not in e and "results" in e:
            e["env"] = _build_env_info(e["results"])
        items.append(e)
    return {"success": True, "history": items}
