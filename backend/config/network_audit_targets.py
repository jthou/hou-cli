"""网络审计目标配置 - 按 docs/design/network-audit-design.md 实现"""
import os
from typing import Any, Dict, List, Optional


def _resolve_url(target: Dict[str, Any]) -> Optional[str]:
    """解析目标 URL：固定 URL 或从环境变量读取"""
    if "url" in target:
        return target["url"]
    url_from_env = target.get("url_from_env")
    if not url_from_env:
        return None
    base = os.getenv(url_from_env) or target.get("default", "")
    if not base:
        return None
    base = base.rstrip("/")
    # 若 base 无协议（如 QWEATHER_API_HOST），补上 https://
    if base and not base.startswith("http://") and not base.startswith("https://"):
        base = f"https://{base}"
    path = target.get("path", "")
    suffix = target.get("suffix", "")
    if path:
        return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
    if suffix:
        return f"{base}{suffix}" if suffix.startswith("/") else f"{base}/{suffix}"
    return base


def _is_configured(target: Dict[str, Any]) -> bool:
    """检查目标是否已配置（env_required 存在时需满足）"""
    env_required = target.get("env_required")
    if not env_required:
        return True
    for key in env_required:
        if not (os.getenv(key) or "").strip():
            return False
    return True


def get_audit_targets() -> List[Dict[str, Any]]:
    """返回审计目标列表，含解析后的 URL 和配置状态"""
    raw = [
        {
            "id": "duckduckgo",
            "name": "网页搜索 (DuckDuckGo)",
            "url": "https://html.duckduckgo.com/html/",
            "method": "GET",
            "required": True,
        },
        {
            "id": "outbound_ip",
            "name": "出口 IP",
            "url": "https://ip.skk.moe/",
            "method": "GET",
            "required": True,
            "sources": [
                "https://ip.skk.moe/",
                "https://api.ipify.org?format=json",
                "https://ifconfig.me/ip",
                "https://icanhazip.com",
            ],
        },
        {
            "id": "wechat_mp",
            "name": "微信公众号 API",
            "url": "https://api.weixin.qq.com/cgi-bin/token",
            "method": "GET",
            "required": False,
            "env_required": ["WECHAT_MP_APP_ID", "WECHAT_MP_APP_SECRET"],
            "auth_type": "wechat",
        },
        {
            "id": "deepseek",
            "name": "DeepSeek API",
            "url_from_env": "DEEPSEEK_BASE_URL",
            "default": "https://api.deepseek.com",
            "path": "/v1/models",
            "method": "GET",
            "required": False,
            "auth_type": "bearer",
            "api_key_env": "DEEPSEEK_API_KEY",
        },
        {
            "id": "bailian",
            "name": "百炼 API",
            "url_from_env": "BAILIAN_BASE_URL",
            "default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "path": "/models",
            "method": "GET",
            "required": False,
            "auth_type": "bearer",
            "api_key_env": "BAILIAN_API_KEY",
            "api_key_env_alt": "DASHSCOPE_API_KEY",
        },
        {
            "id": "turbogateway",
            "name": "TheTurbo 网关",
            "url_from_env": "TURBOGATEWAY_BASE_URL",
            "default": "https://gateway.theturbo.ai/v1",
            "path": "/models",
            "method": "GET",
            "required": False,
            "auth_type": "bearer",
            "api_key_env": "TURBOGATEWAY_API_KEY",
        },
        {
            "id": "qweather",
            "name": "和风天气",
            "url_from_env": "QWEATHER_API_HOST",
            "suffix": "/geo/v2/city/lookup?location=北京",
            "method": "GET",
            "required": False,
            "auth_type": "jwt",
            "env_required": [
                "WEATHER_JWT_PRIVATE_KEY",
                "QWEATHER_CREDENTIAL_ID",
                "QWEATHER_PROJECT_ID",
                "QWEATHER_API_HOST",
            ],
        },
        {
            "id": "mediawiki",
            "name": "MediaWiki",
            "url_from_env": "MEDIAWIKI_URL",
            "default": "http://www.jthou.com/mediawiki",
            "path": "/api.php",
            "method": "GET",
            "required": False,
        },
        {
            "id": "codecogs",
            "name": "LaTeX 渲染 (CodeCogs)",
            "url": "https://latex.codecogs.com/png.latex?%5CLaTeX",
            "method": "GET",
            "required": False,
        },
    ]

    result = []
    for t in raw:
        url = _resolve_url(t)
        configured = _is_configured(t)
        item = {
            "id": t["id"],
            "name": t["name"],
            "url": url,
            "method": t.get("method", "GET"),
            "required": t.get("required", False),
            "configured": configured,
        }
        if "sources" in t:
            item["sources"] = t["sources"]
        if t.get("auth_type"):
            item["auth_type"] = t["auth_type"]
            if t.get("api_key_env"):
                item["api_key_env"] = t["api_key_env"]
            if t.get("api_key_env_alt"):
                item["api_key_env_alt"] = t["api_key_env_alt"]
            if t.get("env_required"):
                item["env_required"] = t["env_required"]
        result.append(item)
    return result
