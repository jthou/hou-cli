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

1. title: 文章标题，不超过 32 字，吸引读者点击
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
                        "title": (data.get("title") or "")[:32],
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


async def generate_cover_image_from_content(content: str) -> Dict[str, Any]:
    """
    根据文章内容生成封面图并上传到公众号。
    返回 {"thumb_media_id": str, "prompt": str} 成功；失败时 {"thumb_media_id": "", "prompt": "", "error": str}。
    """
    content = (content or "").strip()
    if not content:
        return {"thumb_media_id": "", "prompt": "", "error": "文章内容为空"}

    try:
        from backend.core.agent.tools.builtin.text_to_image_prompt_tool import (
            TextToImagePromptTool,
        )
        from backend.services.llm.image_gen_service import ImageGenService
        from backend.services.wechat_mp_service.client import (
            WeChatMPClient,
            WeChatMPClientError,
        )

        # 1. 提炼图片提示词
        tool = TextToImagePromptTool()
        result = await tool._execute_async(text=content[:3000])
        if not result.success or not result.data or not result.data.get("prompt"):
            err = (result.error if hasattr(result, "error") and result.error else "") or "提炼封面提示词失败"
            logger.warning("提炼封面提示词失败: %s", err)
            return {"thumb_media_id": "", "prompt": "", "error": err}
        prompt = result.data["prompt"]

        # 2. 文生图
        service = ImageGenService()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = await service.generate(
                prompt=prompt,
                size="1024*1024",
                output_dir=tmpdir,
            )
            output_file = out.get("output_file")
            if not output_file or not Path(output_file).exists():
                err = out.get("error") or "图片生成未保存到文件"
                logger.warning("图片生成未保存到文件: %s", err)
                return {"thumb_media_id": "", "prompt": prompt, "error": err}

            img_bytes = Path(output_file).read_bytes()
            if len(img_bytes) > 2 * 1024 * 1024:
                logger.warning("封面图超过 2MB，尝试压缩或跳过")
                return {"thumb_media_id": "", "prompt": prompt, "error": "封面图超过 2MB，公众号仅支持 ≤2MB"}

            # 3. 上传到公众号
            client = WeChatMPClient()
            data = client.upload_image_permanent(img_bytes, filename="cover.png")
            media_id = data.get("media_id") or ""
            if not media_id:
                return {"thumb_media_id": "", "prompt": prompt, "error": "上传到公众号失败，未返回 media_id"}

            # 4. 保存到 ~/hou-cli/outputs/cover/ 便于用户查找
            try:
                from shared.platform_utils import get_default_output_dir
                import time
                cover_dir = get_default_output_dir() / "cover"
                cover_dir.mkdir(parents=True, exist_ok=True)
                ts = int(time.time())
                save_path = cover_dir / f"cover_{ts}.png"
                save_path.write_bytes(img_bytes)
                logger.info("封面已保存到 %s", save_path)
            except Exception as e:
                logger.debug("保存封面到本地失败（不影响上传）: %s", e)

            return {"thumb_media_id": media_id, "prompt": prompt}
    except WeChatMPClientError as e:
        err_msg = str(e) or "上传失败"
        logger.warning("上传封面到公众号失败: %s", e)
        return {"thumb_media_id": "", "prompt": "", "error": f"上传到公众号失败：{err_msg}"}
    except Exception as e:
        err_msg = str(e) or "未知错误"
        logger.exception("生成封面图失败: %s", e)
        return {"thumb_media_id": "", "prompt": "", "error": f"生成封面图失败：{err_msg}"}
