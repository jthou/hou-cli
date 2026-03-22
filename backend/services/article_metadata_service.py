"""
公众号文章元数据生成服务
根据正文内容生成：标题、摘要（120字内）、作者、封面图（由内容提炼提示词后文生图并上传）
"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

GENERATE_METADATA_SYSTEM = """你是公众号文章编辑。根据用户提供的文章正文，生成以下字段（JSON 格式，不要其他解释）：

1. title: 文章标题，吸引读者点击（微信草稿标题限制 32 字，超限由 API 报错）
2. digest: 文章摘要，不超过 120 字，概括核心内容
3. author: 作者名，不超过 16 字，可留空

只输出 JSON，格式：{"title": "...", "digest": "...", "author": "..."}"""


def _parse_metadata_json(text: str) -> Dict[str, str]:
    """解析 LLM 返回的 JSON 元数据。"""
    import json

    text = (text or "").strip()
    start = text.find("{")
    if start < 0:
        return {}
    depth = 0
    for i, c in enumerate(text[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(text[start : i + 1])
                    return {
                        "title": (data.get("title") or "").strip(),
                        "digest": (data.get("digest") or "")[:120],
                        "author": (data.get("author") or "")[:16],
                    }
                except Exception:
                    pass
                break
    return {}


async def generate_article_metadata(
    content: str, fields: Optional[list] = None
) -> Dict[str, Any]:
    """
    根据文章正文生成标题、摘要、作者。
    fields: 可选，["title","digest","author"] 的子集，仅生成指定字段；None 表示全部。
    返回 {"title": str, "digest": str, "author": str}，失败时返回空字符串。
    """
    content = (content or "").strip()
    if not content:
        return {"title": "", "digest": "", "author": ""}

    try:
        from backend.services.llm.llm_service import LLMService

        llm = LLMService()
        response = await llm.chat(
            system_prompt=GENERATE_METADATA_SYSTEM,
            user_prompt=f"文章正文：\n\n{content[:8000]}",
        )
        parsed = _parse_metadata_json(response or "")
        if not parsed:
            return {"title": "", "digest": "", "author": "", "error": "LLM 返回的 JSON 解析失败"}
        if fields:
            return {k: parsed.get(k, "") for k in ["title", "digest", "author"] if k in fields}
        return parsed
    except Exception as e:
        err = (str(e) or type(e).__name__ or "未知错误").strip()
        logger.warning("生成文章元数据失败: %s", e)
        return {"title": "", "digest": "", "author": "", "error": "生成文章元数据失败：" + (err or "未知错误")}


async def generate_cover_prompt_from_content(content: str) -> Dict[str, Any]:
    """
    第一步：根据文章内容生成封面图提示词。
    时间：2025-03-17；理由：封面生成拆分为三步，用户可编辑提示词；方法：调用 TextToImagePromptTool。
    返回 {"prompt": str} 成功；失败时 {"prompt": "", "error": str}。
    """
    content = (content or "").strip()
    if not content:
        return {"prompt": "", "error": "文章内容为空"}
    try:
        from backend.core.agent.tools.builtin.text_to_image_prompt_tool import TextToImagePromptTool
        tool = TextToImagePromptTool()
        result = await tool._execute_async(text=content[:3000])
        if not result.success or not result.data or not result.data.get("prompt"):
            err = (result.error if hasattr(result, "error") and result.error else "") or "提炼封面提示词失败"
            return {"prompt": "", "error": err}
        return {"prompt": result.data["prompt"]}
    except Exception as e:
        return {"prompt": "", "error": str(e) or "未知错误"}


async def generate_cover_images_from_prompt(
    prompt: str, n: int = 4
) -> Dict[str, Any]:
    """
    第二步：根据提示词生成多张封面图供选择。
    时间：2025-03-17；理由：用户可多选一；方法：调用 ImageGenService.generate(n=4)。
    返回 {"images": List[str]}，每项为 data:image/png;base64,... 或 URL；失败时 {"images": [], "error": str}。
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return {"images": [], "error": "提示词为空"}
    n = max(1, min(n, 4))
    try:
        from backend.services.llm.image_gen_service import ImageGenService
        service = ImageGenService()
        out = await service.generate(prompt=prompt, size="1024*1024", n=n)
        images = out.get("images") or []
        return {"images": images}
    except Exception as e:
        return {"images": [], "error": str(e) or "未知错误"}


async def upload_cover_to_wechat(image_data: str) -> Dict[str, Any]:
    """
    第三步：将选中的图片上传到公众号永久素材。
    时间：2025-03-17；理由：用户选择后再上传；方法：解码 base64 或下载 URL 后调用 WeChatMPClient。
    image_data: data:image/png;base64,xxx 或 https://... 或 纯 base64 字符串
    返回 {"thumb_media_id": str} 成功；失败时 {"thumb_media_id": "", "error": str}。
    """
    if not (image_data or "").strip():
        return {"thumb_media_id": "", "error": "图片数据为空"}
    try:
        import base64
        import httpx
        from backend.services.wechat_mp_service.client import WeChatMPClient, WeChatMPClientError

        raw = (image_data or "").strip()
        img_bytes = None

        if raw.startswith("data:"):
            # data:image/png;base64,xxx
            idx = raw.find(",")
            if idx >= 0:
                b64 = raw[idx + 1 :].strip()
                img_bytes = base64.b64decode(b64)
        elif raw.startswith("http://") or raw.startswith("https://"):
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(raw)
                r.raise_for_status()
                img_bytes = r.content
        else:
            img_bytes = base64.b64decode(raw)

        if not img_bytes:
            return {"thumb_media_id": "", "error": "图片无效或为空"}

        # 时间：2026-03-13；理由：URL/base64 大图与上传接口一致；方法：fit_wechat_cover_image
        try:
            from backend.services.wechat_mp_service.cover_image_fit import fit_wechat_cover_image

            img_bytes, cover_name = fit_wechat_cover_image(img_bytes, "cover.png")
        except ValueError as e:
            return {"thumb_media_id": "", "error": str(e) or "封面图无法压缩到微信限制内"}

        client = WeChatMPClient()
        data = client.upload_image_permanent(img_bytes, filename=cover_name)
        media_id = data.get("media_id") or ""
        if not media_id:
            return {"thumb_media_id": "", "error": "上传失败，未返回 media_id"}
        return {"thumb_media_id": media_id}
    except WeChatMPClientError as e:
        return {"thumb_media_id": "", "error": str(e) or "上传失败"}
    except Exception as e:
        return {"thumb_media_id": "", "error": str(e) or "未知错误"}


async def generate_cover_image_from_content(content: str) -> Dict[str, Any]:
    """
    根据文章内容生成封面图并上传到公众号（一步完成，兼容旧逻辑）。
    返回 {"thumb_media_id": str, "prompt": str} 成功；失败时 {"thumb_media_id": "", "prompt": "", "error": str}。
    """
    content = (content or "").strip()
    if not content:
        return {"thumb_media_id": "", "prompt": "", "error": "文章内容为空"}

    try:
        from backend.core.agent.tools.builtin.text_to_image_prompt_tool import TextToImagePromptTool
        from backend.services.llm.image_gen_service import ImageGenService
        from backend.services.wechat_mp_service.client import WeChatMPClient, WeChatMPClientError

        tool = TextToImagePromptTool()
        result = await tool._execute_async(text=content[:3000])
        if not result.success or not result.data or not result.data.get("prompt"):
            err = (result.error if hasattr(result, "error") and result.error else "") or "提炼封面提示词失败"
            return {"thumb_media_id": "", "prompt": "", "error": err}
        prompt = result.data["prompt"]

        service = ImageGenService()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = await service.generate(prompt=prompt, size="1024*1024", output_dir=tmpdir)
            output_file = out.get("output_file")
            if not output_file or not Path(output_file).exists():
                err = out.get("error") or "图片生成未保存到文件"
                return {"thumb_media_id": "", "prompt": prompt, "error": err}

            img_bytes = Path(output_file).read_bytes()
            try:
                from backend.services.wechat_mp_service.cover_image_fit import fit_wechat_cover_image

                img_bytes, cover_name = fit_wechat_cover_image(img_bytes, "cover.png")
            except ValueError as e:
                return {"thumb_media_id": "", "prompt": prompt, "error": str(e) or "封面图无法压缩到微信限制内"}

            client = WeChatMPClient()
            data = client.upload_image_permanent(img_bytes, filename=cover_name)
            media_id = data.get("media_id") or ""
            if not media_id:
                return {"thumb_media_id": "", "prompt": prompt, "error": "上传到公众号失败，未返回 media_id"}

            try:
                from shared.platform_utils import get_default_output_dir
                import time
                cover_dir = get_default_output_dir() / "cover"
                cover_dir.mkdir(parents=True, exist_ok=True)
                save_path = cover_dir / f"cover_{int(time.time())}.png"
                save_path.write_bytes(img_bytes)
                logger.info("封面已保存到 %s", save_path)
            except Exception:
                pass

            return {"thumb_media_id": media_id, "prompt": prompt}
    except WeChatMPClientError as e:
        return {"thumb_media_id": "", "prompt": "", "error": f"上传到公众号失败：{e}"}
    except Exception as e:
        return {"thumb_media_id": "", "prompt": "", "error": f"生成封面图失败：{e}"}
