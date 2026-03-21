"""
将 LLM 调用异常转换为用户可读中文说明。

时间：2026-03-21；理由：技能层/前端直接展示 SDK 原文（如 Error code: 402）用户难以理解；
方法：根据 status_code、异常类型名、以及 str(exc) 中的关键字映射固定中文句。
"""
from __future__ import annotations

from typing import Optional

# LLMService 内部 provider 常量 → 用户可读名（时间：2026-03-21；理由：日志里 deepseek 不等于「哪家网站」）
_PROVIDER_DISPLAY = {
    "deepseek": "DeepSeek（api.deepseek.com）",
    "bailian": "阿里云 DashScope / 百炼",
    "theturbogateway": "TheTurbo.ai 或其它 OpenAI 兼容网关",
}


def insufficient_balance_user_message(provider: str, model: str) -> str:
    """
    402 / Insufficient Balance 时展示：哪条配置线路、哪个模型 id 在欠费。
    方法：使用 LLMService 当前的 self.provider / self.model（即本次请求实际走的线路）。
    """
    p_raw = (provider or "unknown").strip()
    m = (model or "unknown").strip()
    p_show = _PROVIDER_DISPLAY.get(p_raw.lower(), p_raw)
    return (
        f"当前请求所使用的 API 账户余额不足（或欠费）。"
        f"【服务商】{p_show}（配置标识：{p_raw}）"
        f"【模型】{m}。"
        f"请到对应平台充值，或调整环境变量 LLM_PROVIDER、API Key 与 DEEPSEEK_MODEL / BAILIAN_MODEL / TURBOGATEWAY_MODEL 后再试。"
    )


def is_insufficient_balance_error(exc: BaseException) -> bool:
    """是否为 402 或英文余额不足类错误（用于统一包装）。"""
    if exc is None:
        return False
    code = getattr(exc, "status_code", None)
    if code is None:
        resp = getattr(exc, "response", None)
        if resp is not None:
            code = getattr(resp, "status_code", None)
    s = str(exc).lower()
    return bool(
        code == 402
        or "402" in str(exc)
        or "insufficient balance" in s
        or "insufficient_balance" in s
    )


def llm_error_message_for_user(exc: BaseException) -> Optional[str]:
    """
    若可识别为常见计费/鉴权/限流问题，返回中文说明；否则返回 None（由调用方拼接原始信息）。
    """
    if exc is None:
        return None

    code = getattr(exc, "status_code", None)
    if code is None:
        # OpenAI SDK 部分版本用 status_code 在 response 上
        resp = getattr(exc, "response", None)
        if resp is not None:
            code = getattr(resp, "status_code", None)

    s = str(exc)
    low = s.lower()

    # LLMService 已包装过的余额错误（正文为中文，未必含 402 英文字样）
    if "【服务商】" in s and "【模型】" in s:
        return str(exc)

    if code == 402 or "402" in s or "insufficient balance" in low:
        return (
            "当前模型 API 账户余额不足（或欠费），请充值或更换可用的 API Key/提供商后再试。"
        )

    if code == 401 or "401" in s or "invalid api key" in low or "incorrect api key" in low:
        return "API Key 无效或未授权，请检查环境变量或设置中的密钥配置。"

    if code == 403 or "403" in s or "permissiondenied" in low.replace(" ", ""):
        return "API 权限不足（如模型未开通、Key 无该模型权限），请在控制台检查权限或更换模型。"

    if code == 429 or "429" in s or "rate limit" in low:
        return "请求过于频繁被限流，请稍后再试或降低并发。"

    return None
