"""PPT 助手 API：与 CLI 共用 backend.services.ppt_assistant。"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ppt_assistant.markdown import slide_deck_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ppt-assistant", tags=["ppt-assistant"])


def _ppt_llm_service(*, temperature: float, model: Optional[str] = None):
    """与写作助手一致：可选 model 为 /api/models/selectable 返回的 value。"""
    from backend.services.llm.llm_service import LLMService

    m = (model or "").strip()
    if m:
        return LLMService(temperature=temperature, model=m)
    return LLMService(temperature=temperature)


class PptMeta(BaseModel):
    source_hint: str = ""
    audience: str = ""
    constraints_note: str = ""
    max_slides_hint: str = ""
    user_requirements: str = Field(
        "",
        description="用户意见与补充需求，抽取与合并时会一并送给模型",
    )


class ExtractRequest(BaseModel):
    article: str = Field(..., description="长文章正文")
    meta: Optional[PptMeta] = None
    chunk_chars: int = Field(10_000, ge=2000, le=100_000)
    overlap: int = Field(400, ge=0, le=5000)
    model: Optional[str] = Field(
        None,
        description="可选；与 GET /api/models/selectable 中 models[].value 一致，空则环境默认",
    )


class DeckRequest(BaseModel):
    ppt_elements: Dict[str, Any] = Field(..., description="功能一产出的 JSON 对象")
    constraints: str = ""
    user_requirements: str = ""
    single_slide: bool = Field(
        True,
        description="True：一张幻灯片汇总关键要点；False：多页分页",
    )
    model: Optional[str] = Field(
        None,
        description="可选；与 GET /api/models/selectable 中 models[].value 一致，空则环境默认",
    )


class RunRequest(BaseModel):
    article: str
    meta: Optional[PptMeta] = None
    deck_constraints: str = ""
    chunk_chars: int = Field(10_000, ge=2000, le=100_000)
    overlap: int = Field(400, ge=0, le=5000)
    elements_only: bool = False
    single_slide: bool = Field(
        True,
        description="默认单页；False 时生成多页 slide_deck",
    )
    model: Optional[str] = Field(
        None,
        description="可选；全流程（抽取+生成）使用同一模型；空则环境默认",
    )


def _meta_dict(m: Optional[PptMeta]) -> Dict[str, Any]:
    if m is None:
        return {}
    return m.model_dump()


@router.post("/extract")
async def ppt_extract(req: ExtractRequest):
    body = (req.article or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="article 不能为空")
    try:
        from backend.services.ppt_assistant import extract_ppt_elements

        llm = _ppt_llm_service(temperature=0.35, model=req.model)
        data = await extract_ppt_elements(
            body,
            meta=_meta_dict(req.meta),
            llm=llm,
            chunk_chars=req.chunk_chars,
            overlap=req.overlap,
        )
        return {"ppt_elements": data}
    except ValueError as e:
        logger.warning("ppt extract parse error: %s", e)
        raise HTTPException(status_code=502, detail=f"模型输出无法解析为 JSON: {e}") from e
    except Exception as e:
        logger.exception("ppt extract failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/deck")
async def ppt_deck(req: DeckRequest):
    if not req.ppt_elements:
        raise HTTPException(status_code=400, detail="ppt_elements 不能为空")
    try:
        from backend.services.ppt_assistant import generate_slide_deck

        llm = _ppt_llm_service(temperature=0.45, model=req.model)
        deck = await generate_slide_deck(
            req.ppt_elements,
            constraints=req.constraints or "",
            llm=llm,
            single_slide=req.single_slide,
            user_requirements=(req.user_requirements or "").strip() or None,
        )
        return {
            "slide_deck": deck,
            "slide_deck_markdown": slide_deck_to_markdown(deck),
        }
    except ValueError as e:
        logger.warning("ppt deck parse error: %s", e)
        raise HTTPException(status_code=502, detail=f"模型输出无法解析为 JSON: {e}") from e
    except Exception as e:
        logger.exception("ppt deck failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/run")
async def ppt_run(req: RunRequest):
    body = (req.article or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="article 不能为空")
    try:
        from backend.services.ppt_assistant import run_ppt_pipeline

        llm = _ppt_llm_service(temperature=0.4, model=req.model)
        result = await run_ppt_pipeline(
            body,
            meta=_meta_dict(req.meta),
            deck_constraints=req.deck_constraints,
            llm=llm,
            chunk_chars=req.chunk_chars,
            overlap=req.overlap,
            elements_only=req.elements_only,
            single_slide=req.single_slide,
        )
        out: Dict[str, Any] = {"ppt_elements": result["ppt_elements"]}
        deck = result.get("slide_deck")
        if deck is not None:
            out["slide_deck"] = deck
            out["slide_deck_markdown"] = slide_deck_to_markdown(deck)
        else:
            out["slide_deck"] = None
            out["slide_deck_markdown"] = ""
        return out
    except ValueError as e:
        logger.warning("ppt run parse error: %s", e)
        raise HTTPException(status_code=502, detail=f"模型输出无法解析为 JSON: {e}") from e
    except Exception as e:
        logger.exception("ppt run failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
