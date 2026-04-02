"""LaTeX 公式渲染接口：将公式转为图片（供公众号等不支持 LaTeX 的平台使用）"""
import logging
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException

from shared.httpx_defaults import httpx_default_network_kwargs
from fastapi.responses import Response

router = APIRouter()
logger = logging.getLogger(__name__)

# 公众号「上传图文消息内的图片」仅支持 jpg/png，故用 PNG
CODECOGS_PNG_URL = "https://latex.codecogs.com/png.latex"


@router.get("/latex/render")
async def render_latex(formula: str):
    """
    将 LaTeX 公式渲染为 PNG 图片并返回。
    用于公众号正文等场景：前端取图后上传至「上传图文消息内的图片」再插入 HTML。
    """
    if not formula or not formula.strip():
        raise HTTPException(status_code=400, detail="formula 不能为空")
    encoded = quote(formula.strip(), safe="")
    url = f"{CODECOGS_PNG_URL}?{encoded}"
    try:
        async with httpx.AsyncClient(timeout=15.0, **httpx_default_network_kwargs()) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.content
            content_type = r.headers.get("content-type", "image/png")
    except httpx.HTTPStatusError as e:
        logger.warning("CodeCogs LaTeX render failed: %s", e)
        raise HTTPException(status_code=502, detail="公式渲染服务返回错误") from e
    except httpx.RequestError as e:
        logger.warning("CodeCogs LaTeX request failed: %s", e)
        raise HTTPException(status_code=502, detail="公式渲染服务不可用") from e
    if not content:
        raise HTTPException(status_code=502, detail="公式渲染返回为空")
    media_type = content_type or "image/png"
    return Response(content=content, media_type=media_type)
