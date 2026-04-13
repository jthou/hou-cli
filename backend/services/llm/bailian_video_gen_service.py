# 时间：2026-04-05；理由：万相文生视频为异步 task（与 ImageGenService 的同步 multimodal 图不同）；方法：POST video-synthesis + X-DashScope-Async + 轮询 /api/v1/tasks
"""百炼万相文生视频：创建异步任务、轮询状态、下载 MP4。"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from shared.httpx_defaults import httpx_default_network_kwargs

logger = logging.getLogger(__name__)

VIDEO_SYNTH_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"


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


def _task_id_from_submit(data: Dict[str, Any]) -> str:
    out = data.get("output")
    if isinstance(out, dict):
        tid = (out.get("task_id") or "").strip()
        if tid:
            return tid
    raise RuntimeError(f"创建视频任务未返回 task_id: {str(data)[:400]}")


def _video_url_from_task(data: Dict[str, Any]) -> tuple[str, str]:
    """返回 (task_status, video_url 或 '')"""
    out = data.get("output") if isinstance(data.get("output"), dict) else {}
    status = (out.get("task_status") or out.get("status") or "").strip()
    url = (out.get("video_url") or "").strip()
    return status, url


async def text_to_video_and_download(
    *,
    prompt: str,
    output_path: Path,
    model: str = "wan2.6-t2v",
    size: str = "1280*720",
    duration: int = 5,
    prompt_extend: bool = True,
    watermark: bool = False,
    shot_type: Optional[str] = None,
    poll_interval_sec: float = 4.0,
    max_wait_sec: float = 600.0,
) -> Dict[str, Any]:
    """
    文生视频：异步提交后轮询 GET /api/v1/tasks/{task_id}，成功后下载视频。

    明确指令（超时）：若在 max_wait_sec 内未完成，返回 JSON 可序列化字段中含 task_id 与
    task_status，便于用户到控制台查任务（方法：不无限轮询）。
    """
    from backend.services.llm.model_registry import ModelRegistry

    prov, _ = ModelRegistry.parse_model_name((model or "").strip())
    if prov != "bailian":
        raise ValueError("文生视频当前仅支持百炼模型 id")

    api_key = _get_bailian_api_key()
    origin = _dashscope_origin()
    submit_url = f"{origin}{VIDEO_SYNTH_PATH}"
    task_base = f"{origin}/api/v1/tasks"

    params: Dict[str, Any] = {
        "size": size,
        "prompt_extend": bool(prompt_extend),
        "watermark": bool(watermark),
        "duration": int(max(2, min(int(duration), 15))),
    }
    if shot_type:
        params["shot_type"] = shot_type.strip()

    body = {
        "model": (model or "").strip(),
        "input": {"prompt": (prompt or "").strip()},
        "parameters": params,
    }

    async with httpx.AsyncClient(timeout=120.0, **httpx_default_network_kwargs()) as client:
        resp = await client.post(
            submit_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json=body,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"创建视频任务 HTTP {resp.status_code}: {(resp.text or '')[:500]}")
    submit_json = resp.json()
    if submit_json.get("code"):
        raise RuntimeError(f"创建视频任务失败: {submit_json.get('message', submit_json.get('code'))}")

    task_id = _task_id_from_submit(submit_json)
    deadline = time.monotonic() + float(max_wait_sec)

    async with httpx.AsyncClient(timeout=120.0, **httpx_default_network_kwargs()) as client:
        while time.monotonic() < deadline:
            await asyncio.sleep(float(poll_interval_sec))
            tr = await client.get(
                f"{task_base}/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if tr.status_code != 200:
                raise RuntimeError(f"查询任务 HTTP {tr.status_code}: {(tr.text or '')[:400]}")
            tj = tr.json()
            if tj.get("code"):
                raise RuntimeError(f"查询任务失败: {tj.get('message', tj.get('code'))}")
            status, vurl = _video_url_from_task(tj)
            stu = status.upper()
            if stu == "FAILED" or (stu == "UNKNOWN" and not vurl):
                raise RuntimeError(f"视频任务失败: status={status}, body={str(tj)[:500]}")
            if stu == "SUCCEEDED" and vurl:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                async with httpx.AsyncClient(timeout=300.0, **httpx_default_network_kwargs()) as dl:
                    r = await dl.get(vurl)
                    r.raise_for_status()
                    output_path.write_bytes(r.content)
                return {
                    "output_file": str(output_path.resolve()),
                    "video_url": vurl,
                    "task_id": task_id,
                    "task_status": status,
                }
            if stu == "SUCCEEDED" and not vurl:
                raise RuntimeError(f"任务显示成功但未返回 video_url: {str(tj)[:500]}")
            # PENDING / RUNNING 等继续轮询
        return {
            "timeout": True,
            "task_id": task_id,
            "hint": f"在 {max_wait_sec}s 内未完成，请稍后 GET {task_base}/{task_id} 或控制台查看",
        }
