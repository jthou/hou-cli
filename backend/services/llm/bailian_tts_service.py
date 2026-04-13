# 时间：2026-04-05；理由：百炼 Qwen3-TTS 与文生图不同 body（无 messages），不宜塞进 ImageGenService；方法：独立 httpx POST multimodal-generation + 解析 output.audio
"""百炼语音合成（Qwen-TTS / Qwen3-TTS）HTTP 调用，与 ImageGenService 共用 DashScope 域名推导。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from shared.httpx_defaults import httpx_default_network_kwargs

logger = logging.getLogger(__name__)

BAILIAN_MULTIMODAL_GEN_PATH = "/api/v1/services/aigc/multimodal-generation/generation"


def _dashscope_origin() -> str:
    base = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
    if "dashscope.aliyuncs.com" in base:
        return "https://dashscope.aliyuncs.com"
    if "dashscope-intl.aliyuncs.com" in base:
        return "https://dashscope-intl.aliyuncs.com"
    if "dashscope-us.aliyuncs.com" in base:
        return "https://dashscope-us.aliyuncs.com"
    if "dashscope-cn-hongkong.aliyuncs.com" in base:
        return "https://dashscope-cn-hongkong.aliyuncs.com"
    return "https://dashscope.aliyuncs.com"


def _get_bailian_api_key() -> str:
    key = (os.environ.get("BAILIAN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not key:
        raise ValueError("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 未设置")
    return key


async def synthesize_to_file(
    *,
    text: str,
    voice: str = "Cherry",
    language_type: str = "Auto",
    model: str = "qwen3-tts-flash-2025-11-27",
    output_path: Path,
    instructions: Optional[str] = None,
    optimize_instructions: bool = False,
) -> Dict[str, Any]:
    """
    非流式 TTS：请求百炼 multimodal-generation，下载 wav 到 output_path。

    Returns:
        {"output_file": str, "audio_url": str|None, "request_id": str|None}
    """
    from backend.services.llm.model_registry import ModelRegistry

    prov, _ = ModelRegistry.parse_model_name((model or "").strip())
    if prov != "bailian":
        raise ValueError("TTS 当前仅支持百炼模型 id")

    api_key = _get_bailian_api_key()
    origin = _dashscope_origin()
    api_url = f"{origin}{BAILIAN_MULTIMODAL_GEN_PATH}"

    body: Dict[str, Any] = {
        "model": (model or "").strip().lower(),
        "input": {
            "text": (text or "").strip(),
            "voice": (voice or "Cherry").strip(),
            "language_type": (language_type or "Auto").strip(),
        },
    }
    if instructions:
        body["parameters"] = {
            "instructions": instructions.strip(),
            "optimize_instructions": bool(optimize_instructions),
        }

    async with httpx.AsyncClient(timeout=120.0, **httpx_default_network_kwargs()) as client:
        resp = await client.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"TTS HTTP {resp.status_code}: {(resp.text or '')[:500]}")
    data = resp.json()
    if data.get("code"):
        raise RuntimeError(f"TTS 失败: {data.get('message', data.get('code'))}")

    out = (data.get("output") or {}) if isinstance(data.get("output"), dict) else {}
    audio = out.get("audio") or {}
    url = (audio.get("url") or "").strip() if isinstance(audio, dict) else ""
    if not url:
        raise RuntimeError("TTS 响应中无 output.audio.url")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=120.0, **httpx_default_network_kwargs()) as client:
        r = await client.get(url)
        r.raise_for_status()
        output_path.write_bytes(r.content)

    return {
        "output_file": str(output_path.resolve()),
        "audio_url": url,
        "request_id": data.get("request_id"),
    }
