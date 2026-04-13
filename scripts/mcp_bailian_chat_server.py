#!/usr/bin/env python3
# 时间：2026-04-04；理由：Cursor Agent 按需走百炼单步（总结/翻译/长提示等），与主对话模型解耦；方法：FastMCP stdio + LLMService.chat(provider=bailian)
# 时间：2026-04-04；理由：与 hou_article_writing 编排区分；方法：本服务仅单次 chat，无 Orchestrator
# 时间：2026-04-05；理由：百炼还有文生图/文生视频/TTS/短音频 ASR；方法：ImageGenService + bailian_*_service + LLMService(messages+input_audio)
"""
百炼「单步对话」MCP（stdio）：封装 `LLMService.chat`，供 Cursor Agent 通过工具调用。

依赖：仓库根 `.env` 中 `BAILIAN_API_KEY` 或 `DASHSCOPE_API_KEY`；已安装 `mcp`（见 requirements.txt）。

Cursor 配置示例（`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）：

  {
    "mcpServers": {
      "hou-bailian-chat": {
        "command": "python3",
        "args": ["/ABS/PATH/TO/hou-cli/scripts/mcp_bailian_chat_server.py"],
        "cwd": "/ABS/PATH/TO/hou-cli"
      }
    }
  }

工具：
- `hou_bailian_complete`：纯文本单次 chat；**换模型**靠参数 `model`（如 `qwen3.6-plus`、`kimi-k2-thinking`），id 以 `hou_bailian_list_models` / 仓库 `model_registry` 为准。
- `hou_bailian_complete_vision`：多模态：若干 **http(s) 图链** 或 **data:image/*;base64,...** + 文本问句；须用 VL 类模型 id（默认 `qwen3-vl-plus-2025-12-19`）。
- `hou_bailian_list_models`：列出百炼模型 id（可 `filter_prefix` / `max_items` 截断）。
- `hou_bailian_ping`：`live=false` 仅检查密钥与 base_url；`live=true` 发极小请求验证链路。
- `hou_bailian_text_to_image`：文生图（`ImageGenService`，默认 `wan2.6-t2i`，输出在 `~/hou-cli/outputs/bailian_mcp_image/`）。
- `hou_bailian_text_to_video`：文生视频（异步轮询，默认 `wan2.6-t2v`，输出 `~/hou-cli/outputs/bailian_mcp_video/`；超时返回 `task_id`）。
- `hou_bailian_tts`：语音合成（Qwen3-TTS HTTP，输出 `~/hou-cli/outputs/bailian_mcp_tts/*.wav`）。
- `hou_bailian_speech_to_text`：短音频识别（兼容模式 `chat/completions` + `input_audio`，宜公网 `audio_url` 或 `data:audio/*;base64,...`）。

长文成稿请仍用 `hou-bailian-article` 的 `hou_article_writing`。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 与写作 MCP 一致，避免子进程被技能预匹配干扰（若上游读取该变量）
os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")

from shared.load_env import load_env

load_env(ROOT)


def _bailian_key_status() -> tuple[bool, str | None]:
    if os.environ.get("BAILIAN_API_KEY", "").strip():
        return True, "BAILIAN_API_KEY"
    if os.environ.get("DASHSCOPE_API_KEY", "").strip():
        return True, "DASHSCOPE_API_KEY"
    return False, None


def _require_bailian_model(model: str) -> None:
    from backend.services.llm.model_registry import ModelRegistry

    raw = (model or "").strip()
    if not raw:
        raise ValueError("model 不能为空")
    prov, _ = ModelRegistry.parse_model_name(raw)
    if prov != "bailian":
        raise ValueError(
            f"hou_bailian_chat 仅支持百炼线路；当前模型解析为 provider={prov}。"
            "请使用百炼模型 id（如 qwen3-max）或 bailian-<model>。"
        )


# 时间：2026-04-05；理由：VL 工具需统一校验输入，避免把任意字符串送进 image_url；方法：仅允许 https? 与 data:image/*;base64
def _parse_vision_image_urls(raw: list[str] | None, *, max_n: int = 8) -> list[str]:
    if not raw:
        raise ValueError("image_urls 不能为空")
    cleaned = [(s or "").strip() for s in raw if (s or "").strip()]
    if not cleaned:
        raise ValueError("image_urls 至少一条非空 URL 或 data URL")
    if len(cleaned) > max_n:
        raise ValueError(f"图像条数超过上限 {max_n}")
    out: list[str] = []
    for t in cleaned:
        low = t.lower()
        if low.startswith("https://") or low.startswith("http://"):
            out.append(t)
        elif low.startswith("data:image/") and ";base64," in low:
            out.append(t)
        else:
            raise ValueError(
                "每条须为 http(s) 图片地址，或 data:image/<mime>;base64,<payload>；"
                f"非法项前缀: {t[:64]!r}"
            )
    return out


def _build_mcp() -> "FastMCP":
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "hou_bailian_chat",
        instructions=(
            "阿里云百炼单步工具：文本 hou_bailian_complete；图+文 hou_bailian_complete_vision；"
            "文生图 hou_bailian_text_to_image；文生视频 hou_bailian_text_to_video；朗读 hou_bailian_tts；"
            "短音频转写 hou_bailian_speech_to_text。枚举模型 hou_bailian_list_models。公众号长文用 hou_article_writing（另一 MCP）。"
        ),
    )

    @mcp.tool()
    async def hou_bailian_ping(live: bool = False) -> str:
        """检查百炼配置；live=true 时发起一次极短 API 调用验证网络与密钥。"""
        ok, src = _bailian_key_status()
        base = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        payload: dict = {
            "configured": ok,
            "key_source": src,
            "base_url": base,
            "live": live,
        }
        if not ok:
            payload["hint"] = "在仓库根 .env 设置 BAILIAN_API_KEY（或 DASHSCOPE_API_KEY）后重试"
            return json.dumps(payload, ensure_ascii=False)
        if not live:
            return json.dumps(payload, ensure_ascii=False)
        try:
            from backend.services.llm.llm_service import LLMService

            svc = LLMService(temperature=0.0, max_tokens=16, provider="bailian", model="qwen3-max")
            text = await svc.chat(system_prompt="只输出一个词：OK", user_prompt="ping")
            if not isinstance(text, str):
                payload["live_ok"] = False
                payload["live_error"] = "模型返回了 tool_calls，本 MCP 不支持"
            else:
                payload["live_ok"] = True
                payload["sample"] = (text or "")[:120]
        except Exception as e:
            payload["live_ok"] = False
            payload["live_error"] = str(e)
        return json.dumps(payload, ensure_ascii=False)

    @mcp.tool()
    async def hou_bailian_list_models(filter_prefix: str = "", max_items: int = 200) -> str:
        """返回百炼模型 id 列表（来自 ModelRegistry.BAILIAN_MODELS，可能截断）。"""
        from backend.services.llm.model_registry import ModelRegistry

        cap = max(1, min(int(max_items), 2000))
        names = sorted(ModelRegistry.BAILIAN_MODELS)
        fp = (filter_prefix or "").strip().lower()
        if fp:
            names = [n for n in names if fp in n.lower()]
        total = len(names)
        truncated = total > cap
        names = names[:cap]
        return json.dumps(
            {"total_matched": total, "truncated": truncated, "models": names},
            ensure_ascii=False,
        )

    @mcp.tool()
    async def hou_bailian_complete(
        user_prompt: str,
        system_prompt: str = "",
        model: str = "qwen3-max",
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """单次百炼纯文本 chat。换模型：传 model（如 qwen3.6-plus、kimi-k2-thinking、deepseek-v3.2）；枚举用 hou_bailian_list_models。"""
        from backend.services.llm.llm_service import LLMService

        up = (user_prompt or "").strip()
        if not up:
            return json.dumps({"error": "user_prompt 不能为空"}, ensure_ascii=False)
        m = (model or "").strip() or "qwen3-max"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        sp = (system_prompt or "").strip()
        temp = float(temperature)
        temp = max(0.0, min(2.0, temp))
        mt = int(max_tokens) if max_tokens is not None else None
        svc = LLMService(temperature=temp, max_tokens=mt, provider="bailian", model=m)
        try:
            out = await svc.chat(system_prompt=sp, user_prompt=up)
        except Exception as e:
            return json.dumps({"error": str(e), "model": getattr(svc, "model", m)}, ensure_ascii=False)
        if not isinstance(out, str):
            return json.dumps(
                {
                    "error": "模型返回 tool_calls 或非文本，本工具未传入 tools；请改写 prompt 或换模型",
                    "model": getattr(svc, "model", m),
                },
                ensure_ascii=False,
            )
        return out

    @mcp.tool()
    async def hou_bailian_complete_vision(
        user_prompt: str,
        image_urls: list[str],
        system_prompt: str = "",
        model: str = "qwen3-vl-plus-2025-12-19",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        max_images: int = 8,
    ) -> str:
        """百炼多模态：image_urls 为公网 http(s) 图链或 data:image/*;base64,...；user_prompt 为对图的问句/指令。须使用 VL 模型 id。"""
        from backend.services.llm.llm_service import LLMService

        up = (user_prompt or "").strip()
        if not up:
            return json.dumps({"error": "user_prompt 不能为空"}, ensure_ascii=False)
        cap = max(1, min(int(max_images), 16))
        try:
            imgs = _parse_vision_image_urls(image_urls, max_n=cap)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        m = (model or "").strip() or "qwen3-vl-plus-2025-12-19"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        sp = (system_prompt or "").strip()
        temp = max(0.0, min(2.0, float(temperature)))
        mt = int(max_tokens) if max_tokens is not None else None
        svc = LLMService(temperature=temp, max_tokens=mt, provider="bailian", model=m)
        parts: list[dict] = []
        for url in imgs:
            parts.append({"type": "image_url", "image_url": {"url": url}})
        parts.append({"type": "text", "text": up})
        messages: list[dict] = [{"role": "user", "content": parts}]
        if sp:
            messages.insert(0, {"role": "system", "content": sp})
        try:
            out = await svc.chat(messages=messages)
        except Exception as e:
            return json.dumps({"error": str(e), "model": getattr(svc, "model", m)}, ensure_ascii=False)
        if not isinstance(out, str):
            return json.dumps(
                {
                    "error": "模型返回非纯文本；请改写 prompt 或换模型",
                    "model": getattr(svc, "model", m),
                },
                ensure_ascii=False,
            )
        return out

    @mcp.tool()
    async def hou_bailian_text_to_image(
        prompt: str,
        model: str = "wan2.6-t2i",
        size: str = "1024*1024",
        reference_image_urls: list[str] | None = None,
    ) -> str:
        """百炼文生图；可选 reference_image_urls（http(s) 或 data:image;base64），仅部分模型支持读图。"""
        from shared.platform_utils import get_task_output_dir

        from backend.services.llm.image_gen_service import ImageGenService

        p = (prompt or "").strip()
        if not p:
            return json.dumps({"error": "prompt 不能为空"}, ensure_ascii=False)
        m = (model or "").strip() or "wan2.6-t2i"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        out_dir = str(get_task_output_dir("bailian_mcp_image", None))
        try:
            svc = ImageGenService(model=m)
            result = await svc.generate(
                prompt=p,
                model=m,
                size=(size or "1024*1024").strip(),
                n=1,
                output_dir=out_dir,
                reference_image_urls=reference_image_urls,
            )
        except Exception as e:
            return json.dumps({"error": str(e), "model": m}, ensure_ascii=False)
        return json.dumps(
            {
                "output_file": result.get("output_file") or "",
                "output_dir": result.get("output_dir") or out_dir,
                "prompt": p,
                "model": m,
            },
            ensure_ascii=False,
        )

    @mcp.tool()
    async def hou_bailian_text_to_video(
        prompt: str,
        model: str = "wan2.6-t2v",
        size: str = "1280*720",
        duration: int = 5,
        prompt_extend: bool = True,
        watermark: bool = False,
        shot_type: str | None = None,
        max_wait_sec: float = 600.0,
    ) -> str:
        """百炼万相文生视频（异步轮询，可能数分钟）。超时则返回 task_id 便于自助查询。"""
        from shared.platform_utils import get_task_output_dir

        from backend.services.llm.bailian_video_gen_service import text_to_video_and_download

        p = (prompt or "").strip()
        if not p:
            return json.dumps({"error": "prompt 不能为空"}, ensure_ascii=False)
        m = (model or "").strip() or "wan2.6-t2v"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        out_dir = get_task_output_dir("bailian_mcp_video", None)
        out_path = out_dir / f"gen_{int(time.time() * 1000)}.mp4"
        try:
            result = await text_to_video_and_download(
                prompt=p,
                output_path=out_path,
                model=m,
                size=(size or "1280*720").strip(),
                duration=int(duration),
                prompt_extend=bool(prompt_extend),
                watermark=bool(watermark),
                shot_type=(shot_type or "").strip() or None,
                max_wait_sec=float(max(60.0, min(float(max_wait_sec), 1200.0))),
            )
        except Exception as e:
            return json.dumps({"error": str(e), "model": m}, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    async def hou_bailian_tts(
        text: str,
        voice: str = "Cherry",
        language_type: str = "Auto",
        model: str = "qwen3-tts-flash-2025-11-27",
        instructions: str | None = None,
    ) -> str:
        """百炼 Qwen3-TTS：文本转语音，保存为 wav（见返回路径）。"""
        from shared.platform_utils import get_task_output_dir

        from backend.services.llm.bailian_tts_service import synthesize_to_file

        t = (text or "").strip()
        if not t:
            return json.dumps({"error": "text 不能为空"}, ensure_ascii=False)
        m = (model or "").strip() or "qwen3-tts-flash-2025-11-27"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        out_dir = get_task_output_dir("bailian_mcp_tts", None)
        out_path = out_dir / f"tts_{int(time.time() * 1000)}.wav"
        try:
            meta = await synthesize_to_file(
                text=t,
                voice=voice,
                language_type=language_type,
                model=m,
                output_path=out_path,
                instructions=(instructions or "").strip() or None,
                optimize_instructions=False,
            )
        except Exception as e:
            return json.dumps({"error": str(e), "model": m}, ensure_ascii=False)
        meta["model"] = m
        return json.dumps(meta, ensure_ascii=False)

    @mcp.tool()
    async def hou_bailian_speech_to_text(
        audio_url: str = "",
        audio_data_uri: str = "",
        system_context: str = "",
        model: str = "qwen3-asr-flash-2025-09-08",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """百炼短音频 ASR（兼容 chat）：`audio_url` 与 `audio_data_uri` 二选一；data 须 `data:audio/...;base64,...`。"""
        from backend.services.llm.llm_service import LLMService

        au = (audio_url or "").strip()
        ad = (audio_data_uri or "").strip()
        if bool(au) == bool(ad):
            return json.dumps(
                {"error": "请只填 audio_url 或 audio_data_uri 其中之一"},
                ensure_ascii=False,
            )
        data = ad if ad else au
        if ad:
            low = ad.lower()
            if not (low.startswith("data:audio/") and ";base64," in low):
                return json.dumps(
                    {"error": "audio_data_uri 须为 data:audio/<mime>;base64,<payload>"},
                    ensure_ascii=False,
                )
            if len(ad) > 11 * 1024 * 1024:
                return json.dumps({"error": "audio_data_uri 过长（>11MiB），请改用公网 audio_url"}, ensure_ascii=False)
        m = (model or "").strip() or "qwen3-asr-flash-2025-09-08"
        try:
            _require_bailian_model(m)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        messages: list[dict] = []
        sc = (system_context or "").strip()
        if sc:
            messages.append({"role": "system", "content": sc})
        messages.append(
            {
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": data}}],
            }
        )
        temp = max(0.0, min(2.0, float(temperature)))
        mt = max(256, min(int(max_tokens), 32_000))
        svc = LLMService(temperature=temp, max_tokens=mt, provider="bailian", model=m)
        try:
            out = await svc.chat(messages=messages)
        except Exception as e:
            return json.dumps({"error": str(e), "model": getattr(svc, "model", m)}, ensure_ascii=False)
        if not isinstance(out, str):
            return json.dumps({"error": "非文本响应", "model": getattr(svc, "model", m)}, ensure_ascii=False)
        return out

    return mcp


def main() -> None:
    mcp = _build_mcp()
    mcp.run()


if __name__ == "__main__":
    main()
