"""图像生成服务 - 封装百炼 multimodal-generation API"""
import base64
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from shared.httpx_defaults import httpx_default_network_kwargs

from shared.platform_utils import get_default_output_dir, normalize_output_dir

logger = logging.getLogger(__name__)

# 百炼图像生成 API 路径（与 chat 的 base_url 不同）
BAILIAN_IMAGE_API_PATH = "/api/v1/services/aigc/multimodal-generation/generation"

# 已知可在 messages 中附带参考图做风格迁移的模型（纯 t2i 勿混用 image 块，避免 400）
_STYLE_REF_IMAGE_MODEL_MARKERS = ("wan2.6-image", "wan2.5-image", "wan2.2-image", "qwen-image")


def _normalize_reference_image_urls(raw: Optional[List[str]], *, max_n: int = 3) -> List[str]:
    out: List[str] = []
    for x in raw or []:
        s = (x or "").strip()
        if not s or s in out:
            continue
        if s.startswith("data:image/") and ";base64," in s:
            out.append(s)
        elif s.startswith("https://") or s.startswith("http://"):
            out.append(s)
        else:
            logger.warning("跳过无效参考图地址（仅支持 http(s) 或 data:image;base64）: %s", s[:80])
        if len(out) >= max_n:
            break
    return out


def _model_supports_reference_images(api_model: str) -> bool:
    m = (api_model or "").lower().strip()
    if "t2i" in m and "image" not in m.replace("t2i", ""):
        return False
    for marker in _STYLE_REF_IMAGE_MODEL_MARKERS:
        if marker in m:
            return True
    return "image" in m and "t2i" not in m


class ImageGenService:
    """封装百炼/网关图像生成 API"""

    def __init__(self, model: Optional[str] = None):
        """model 支持 provider-model 格式，如 bailian-wan2.6-t2i"""
        self._default_model = model or "wan2.6-t2i"

    def _get_api_config(self, model: Optional[str] = None) -> Dict[str, str]:
        """获取 API 配置：api_key, base_url, actual_model"""
        from backend.services.llm.model_config import get_model_config_manager
        from backend.services.llm.model_registry import ModelRegistry

        model_name = model or self._default_model
        registry = ModelRegistry
        config_manager = get_model_config_manager()

        provider, actual_model = registry.parse_model_name(model_name)
        if provider != "bailian":
            logger.warning(f"图像生成目前仅支持百炼，model={model_name} 将尝试使用百炼")
            actual_model = actual_model or "wan2.6-t2i"
            provider = "bailian"

        api_key = config_manager.get_api_key(f"{provider}-{actual_model}")
        base_url = config_manager.get_base_url(f"{provider}-{actual_model}")
        if not base_url:
            base_url = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        # 图像 API 的 base 为域名，不含 /compatible-mode/v1
        if "dashscope.aliyuncs.com" in base_url:
            api_base = "https://dashscope.aliyuncs.com"
        elif "dashscope-intl.aliyuncs.com" in base_url:
            api_base = "https://dashscope-intl.aliyuncs.com"
        elif "dashscope-us.aliyuncs.com" in base_url:
            api_base = "https://dashscope-us.aliyuncs.com"
        else:
            api_base = base_url.rstrip("/").rsplit("/", 1)[0] if "/" in base_url else base_url

        # 时间：2025-03；理由：百炼 API 报 Model not exist；方法：API 要求小写模型 ID，如 qwen-image-2.0
        api_model = actual_model.lower() if isinstance(actual_model, str) else actual_model
        return {
            "api_key": api_key,
            "api_url": f"{api_base}{BAILIAN_IMAGE_API_PATH}",
            "model": api_model,
        }

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024*1024",
        n: int = 1,
        output_dir: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        调用百炼图像生成 API，返回图片信息。

        Args:
            prompt: 图片描述
            model: 模型名，默认 wan2.6-t2i
            size: 尺寸，如 1024*1024
            n: 生成数量，首期固定 1
            output_dir: 保存目录，若指定则下载并保存到本地
            reference_image_urls: 风格参考图 URL（https）或 data:image/*;base64,…；
                在支持多模态输入的模型（如 wan2.6-image）下插入 content；否则仅将链接写入文生图 prompt。

        Returns:
            {
                "images": List[str],      # URL 或 base64 列表
                "output_file": str,       # 保存后的首图路径（若指定 output_dir）
                "output_dir": str,
                "prompt": str,
            }
        """
        n = max(1, min(n, 4))
        config = self._get_api_config(model)
        api_url = config["api_url"]
        api_key = config["api_key"]
        actual_model = config["model"]

        refs = _normalize_reference_image_urls(reference_image_urls)
        use_refs = bool(refs) and _model_supports_reference_images(actual_model)
        prompt_stripped = (prompt or "").strip() or "一只可爱的猫"

        if use_refs:
            style_prefix = (
                "【风格迁移】请严格参考上方参考图的整体配色、质感、留白与版式气质，"
                "生成一张**新的**宽屏幻灯片画面；不要复制参考图上的文字，仅学习视觉风格。"
                "具体画面内容与结构要求：\n"
            )
            user_text = style_prefix + prompt_stripped
            content: List[Dict[str, Any]] = []
            for r in refs:
                content.append({"type": "image", "image": r})
            content.append({"type": "text", "text": user_text})
        else:
            prefix = ""
            if refs:
                prefix = (
                    "【风格说明】（当前模型为纯文生图，无法读图；以下为参考图链接供你联想相近风格）"
                    + " ".join(refs[:2])
                    + "\n\n"
                )
            content = [{"type": "text", "text": prefix + prompt_stripped}]

        body = {
            "model": actual_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            },
            "parameters": {
                "size": size,
                "n": n,
                "watermark": False,
                "stream": True,  # 时间：2025-03；理由：百炼 API 报 stream=False is not supported；方法：显式传 stream=True
            },
        }
        if use_refs or actual_model == "wan2.6-image":
            body["parameters"]["enable_interleave"] = True

        async with httpx.AsyncClient(timeout=120.0, **httpx_default_network_kwargs()) as client:
            resp = await client.post(
                api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=body,
            )

        if resp.status_code != 200:
            err_text = resp.text[:500] if resp.text else ""
            logger.error(f"图像生成 API 失败: status={resp.status_code}, body={err_text}")
            raise RuntimeError(f"图像生成失败: HTTP {resp.status_code} - {err_text}")

        data = resp.json()
        if "code" in data and data["code"]:
            raise RuntimeError(f"图像生成失败: {data.get('message', data.get('code', 'Unknown'))}")

        images: List[str] = []
        choices = (data.get("output") or {}).get("choices") or []
        for choice in choices:
            msg = choice.get("message") or {}
            content = msg.get("content") or []
            for item in content:
                if isinstance(item, dict):
                    if "image" in item:
                        images.append(item["image"])
                    elif item.get("type") == "image" and "image" in item:
                        images.append(item["image"])

        if not images:
            raise RuntimeError("图像生成 API 未返回图片")

        result: Dict[str, Any] = {
            "images": images,
            "output_file": "",
            "output_dir": "",
            "prompt": prompt,
        }

        if output_dir:
            out_path = normalize_output_dir(output_dir, restrict_to_home=True)
            out_path.mkdir(parents=True, exist_ok=True)

            import time
            ts = int(time.time() * 1000)
            first_saved = None
            last_error = None
            for i, img_src in enumerate(images[:n]):
                ext = ".png"
                fname = f"gen_{ts}_{i}{ext}"
                fp = out_path / fname
                try:
                    if img_src.startswith("data:"):
                        # base64
                        m = re.match(r"data:image/(\w+);base64,(.+)", img_src)
                        if m:
                            raw = base64.b64decode(m.group(2))
                            fp.write_bytes(raw)
                    elif img_src.startswith(("http://", "https://")):
                        async with httpx.AsyncClient(timeout=60.0, **httpx_default_network_kwargs()) as client:
                            r = await client.get(img_src)
                            r.raise_for_status()
                            fp.write_bytes(r.content)
                    else:
                        last_error = f"图片格式不支持: {type(img_src)}, 需 data: 或 http(s)://"
                        continue
                    if first_saved is None:
                        first_saved = str(fp.resolve())
                except Exception as e:
                    last_error = str(e) or type(e).__name__
                    logger.warning(f"保存图片失败 {fp}: {e}")
                    continue

            result["output_dir"] = str(out_path.resolve())
            if first_saved:
                result["output_file"] = first_saved
            elif last_error:
                result["error"] = f"保存图片失败: {last_error}"

        return result
