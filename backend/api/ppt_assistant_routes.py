"""PPT 助手 API：与 CLI 共用 backend.services.ppt_assistant。"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, Response, StreamingResponse

from backend.services.ppt_assistant.markdown import slide_deck_to_markdown
from backend.api.stream_sender import SSEFormatter
from backend.services.ppt_assistant.job_store import (
    start_job,
    set_done,
    set_extract_done,
    set_failed,
    set_slide_failed,
    set_slide_ready,
    set_cancelled,
    get_job,
    job_to_public_dict,
)

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
    max_repair_attempts: int = Field(
        2,
        ge=0,
        le=8,
        description="JSON 校验失败时 repair 轮数；0 表示不 repair",
    )
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
    generation_mode: str = Field(
        "sequential",
        description="sequential：顺序；parallel：并行页级生成（仅当单页为 False 时生效）",
    )
    parallelism: int = Field(
        4,
        ge=1,
        le=16,
        description="parallel 模式并发上限（页级）",
    )
    page_inputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="可选；每页素材/约束提示（并行 Draft 时强对齐 pagesources/bullets）。",
    )
    max_repair_attempts: int = Field(2, ge=0, le=8)
    model: Optional[str] = Field(
        None,
        description="可选；与 GET /api/models/selectable 中 models[].value 一致，空则环境默认",
    )


class RunRequest(BaseModel):
    article: str
    meta: Optional[PptMeta] = None
    run_id: Optional[str] = Field(
        None,
        description="可选；与 /run-stream 配合，用于断线恢复（服务端生成则通过 SSE 首事件返回）",
    )
    deck_constraints: str = ""
    chunk_chars: int = Field(10_000, ge=2000, le=100_000)
    overlap: int = Field(400, ge=0, le=5000)
    elements_only: bool = False
    single_slide: bool = Field(
        True,
        description="默认单页；False 时生成多页 slide_deck",
    )
    generation_mode: str = Field(
        "sequential",
        description="sequential：顺序；parallel：并行页级生成（仅当单页为 False 时生效）",
    )
    parallelism: int = Field(
        4,
        ge=1,
        le=16,
        description="parallel 模式并发上限（页级）",
    )
    page_inputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="可选；每页素材/约束提示（并行 Draft 时强对齐）。",
    )
    max_repair_attempts: int = Field(2, ge=0, le=8)
    model: Optional[str] = Field(
        None,
        description="可选；全流程（抽取+生成）使用同一模型；空则环境默认",
    )


class ExportPptxRequest(BaseModel):
    slide_deck: Dict[str, Any] = Field(..., description="slide_deck JSON（与生成结果结构一致）")
    slide_image_job_id: Optional[str] = Field(
        None,
        description="可选；/slide-images/stream 返回的 job_id，导出时在对应页嵌入百炼整页配图",
    )


class SlideImagesStreamRequest(BaseModel):
    slide_deck: Dict[str, Any] = Field(..., description="当前 slide_deck")
    style_note: str = Field(
        "",
        description="附加风格描述（如：深色科技风、阿里云活动主视觉）",
    )
    image_model: Optional[str] = Field(
        None,
        description="百炼图像 model id（如 bailian-wan2.6-t2i）；空则用 ImageGenService 默认",
    )
    job_id: Optional[str] = Field(
        None,
        description="复用已有配图任务（同 slide_image_job_id）；与 only_indexes 配合补跑失败页",
    )
    only_indexes: Optional[List[int]] = Field(
        None,
        description="仅生成这些页 index；空表示全量（仍会写入同一 job 目录）",
    )
    parallelism: int = Field(
        2,
        ge=1,
        le=8,
        description="页级并行调用百炼上限（过大可能触发限流）",
    )
    style_reference_urls: Optional[List[str]] = Field(
        None,
        description="风格参考图 URL（https 或 data:image/*;base64，最多 5 条）；建议 bailian-wan2.6-image 等多模态模型",
    )


class RefineRequest(BaseModel):
    slide_deck: Dict[str, Any] = Field(..., description="当前 slide_deck JSON")
    target_slide_indexes: List[int] = Field(
        ...,
        min_length=1,
        description="要重写的页 index 列表（与 slides[].index 对应）",
    )
    instructions: str = Field(..., min_length=1, description="用户修改要求（自然语言）")
    ppt_elements: Optional[Dict[str, Any]] = Field(
        None,
        description="可选；提供时一并送入 refine 模型作事实上下文",
    )
    locks: Optional[Dict[str, List[str]]] = Field(
        None,
        description='按页锁定字段，键为页 index 的字符串，如 {"1": ["title", "bullets"]}',
    )
    user_requirements: str = ""
    max_repair_attempts: int = Field(2, ge=0, le=8)
    model: Optional[str] = Field(
        None,
        description="可选；与 GET /api/models/selectable 中 models[].value 一致",
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
            max_repair_attempts=req.max_repair_attempts,
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
            generation_mode=req.generation_mode,
            parallelism=req.parallelism,
            page_inputs=req.page_inputs,
            max_repair_attempts=req.max_repair_attempts,
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
            generation_mode=req.generation_mode,
            parallelism=req.parallelism,
            page_inputs=req.page_inputs,
            max_repair_attempts=req.max_repair_attempts,
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


def _locks_str_keys_to_int(
    raw: Optional[Dict[str, List[str]]],
) -> Optional[Dict[int, List[str]]]:
    if not raw:
        return None
    out: Dict[int, List[str]] = {}
    for k, v in raw.items():
        try:
            ik = int(k)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=400, detail=f"locks 键必须为页 index 整数: {k!r}"
            ) from e
        out[ik] = list(v or [])
    return out


@router.get("/slide-images/file/{job_id}/{page_index}")
async def ppt_slide_image_file(job_id: str, page_index: int):
    from backend.services.ppt_assistant.slide_image_store import safe_image_file

    path = safe_image_file(job_id, page_index)
    if path is None:
        raise HTTPException(status_code=404, detail="图片不存在或任务已过期")
    return FileResponse(path, media_type="image/png")


@router.post("/slide-images/stream")
async def ppt_slide_images_stream(req: SlideImagesStreamRequest):
    if not req.slide_deck or not req.slide_deck.get("slides"):
        raise HTTPException(status_code=400, detail="slide_deck.slides 不能为空")

    only: Optional[Set[int]] = None
    if req.only_indexes:
        ox: Set[int] = set()
        for x in req.only_indexes:
            try:
                ox.add(int(x))
            except (TypeError, ValueError):
                pass
        if ox:
            only = ox
    if only:
        from backend.services.ppt_assistant.slide_image_service import (
            valid_slide_indexes_from_deck,
        )

        valid_ix = valid_slide_indexes_from_deck(req.slide_deck)
        bad = only - valid_ix
        if bad:
            raise HTTPException(
                status_code=400,
                detail=f"only_indexes 含无效页 {sorted(bad)}，有效为 {sorted(valid_ix)}",
            )

    from backend.services.llm.image_gen_service import _normalize_reference_image_urls

    style_refs = _normalize_reference_image_urls(req.style_reference_urls, max_n=5)

    formatter = SSEFormatter()

    async def event_stream():
        from backend.services.ppt_assistant.slide_image_store import (
            get_slide_image_job,
            reuse_or_create_slide_image_job,
        )
        from backend.services.ppt_assistant.slide_image_service import generate_slide_images

        queue: asyncio.Queue = asyncio.Queue()
        _done = object()
        job = reuse_or_create_slide_image_job((req.job_id or "").strip() or None)

        yield formatter.format_chunk(
            json.dumps(
                {
                    "event": "slide_images_job",
                    "job_id": job.job_id,
                    "partial": only is not None,
                },
                ensure_ascii=False,
            ),
            "streaming",
        )

        def on_event(name: str, payload: Dict[str, Any]) -> None:
            queue.put_nowait((name, payload))

        async def runner():
            try:
                await generate_slide_images(
                    req.slide_deck,
                    job,
                    style_note=(req.style_note or "").strip(),
                    image_model=(req.image_model or "").strip() or None,
                    style_reference_urls=style_refs or None,
                    on_event=on_event,
                    parallelism=req.parallelism,
                    only_indexes=only,
                )
            except Exception as e:
                logger.exception("slide-images batch failed")
                on_event("slide_images_fatal", {"error": str(e)})
            finally:
                queue.put_nowait(_done)

        task = asyncio.create_task(runner())
        fatal = False
        while True:
            item = await queue.get()
            if item is _done:
                break
            name, payload = item
            if name == "slide_images_fatal":
                fatal = True
                yield formatter.format_chunk(
                    json.dumps({"event": name, **payload}, ensure_ascii=False),
                    "error",
                )
                break
            yield formatter.format_chunk(
                json.dumps({"event": name, **payload}, ensure_ascii=False),
                "streaming",
            )
        await task

        rec = get_slide_image_job(job.job_id)
        images: Dict[str, str] = {}
        errors: Dict[str, str] = {}
        if rec:
            for k in sorted(rec.images.keys()):
                images[str(k)] = (
                    f"/api/ppt-assistant/slide-images/file/{job.job_id}/{k}"
                )
            errors = {str(k): v for k, v in rec.errors.items()}
        yield formatter.format_chunk(
            json.dumps(
                {
                    "event": "slide_images_done",
                    "job_id": job.job_id,
                    "images": images,
                    "errors": errors,
                },
                ensure_ascii=False,
            ),
            "done",
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/export-pptx")
async def ppt_export_pptx(req: ExportPptxRequest):
    if not req.slide_deck:
        raise HTTPException(status_code=400, detail="slide_deck 不能为空")
    try:
        from backend.services.ppt_assistant.pptx_export import slide_deck_to_pptx_bytes
        from backend.services.ppt_assistant.slide_image_store import job_images_for_export

        slide_imgs = None
        jid = (req.slide_image_job_id or "").strip()
        if jid:
            slide_imgs = job_images_for_export(jid)
            if not slide_imgs:
                logger.warning("export-pptx: slide_image_job_id=%s 无可用文件，回退为文案版式", jid)
                slide_imgs = None

        data = slide_deck_to_pptx_bytes(req.slide_deck, slide_images=slide_imgs)
    except ImportError as e:
        logger.warning("export-pptx: %s", e)
        raise HTTPException(
            status_code=503,
            detail="服务端未安装 python-pptx，无法导出 .pptx",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("export-pptx failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": 'attachment; filename="slide_deck.pptx"',
        },
    )


@router.post("/refine")
async def ppt_refine(req: RefineRequest):
    if not req.slide_deck:
        raise HTTPException(status_code=400, detail="slide_deck 不能为空")
    try:
        from backend.services.ppt_assistant import refine_slide_deck

        llm = _ppt_llm_service(temperature=0.45, model=req.model)
        locks = _locks_str_keys_to_int(req.locks)
        deck = await refine_slide_deck(
            req.slide_deck,
            target_slide_indexes=list(req.target_slide_indexes),
            instructions=req.instructions.strip(),
            llm=llm,
            ppt_elements=req.ppt_elements,
            locks=locks,
            user_requirements=(req.user_requirements or "").strip() or None,
            max_repair_attempts=req.max_repair_attempts,
        )
        return {
            "slide_deck": deck,
            "slide_deck_markdown": slide_deck_to_markdown(deck),
        }
    except ValueError as e:
        logger.warning("ppt refine error: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("ppt refine failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/run-stream")
async def ppt_run_stream(req: RunRequest):
    body = (req.article or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="article 不能为空")

    formatter = SSEFormatter()

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        rec = start_job(req.run_id)
        run_id = rec.run_id

        yield formatter.format_chunk(
            json.dumps(
                {
                    "event": "run_started",
                    "run_id": run_id,
                    "generation_mode": req.generation_mode,
                    "parallelism": req.parallelism,
                },
                ensure_ascii=False,
            ),
            "streaming",
        )

        def on_slide_ready(page_index: int, slide: Dict[str, Any]) -> None:
            # callback 可能在并行任务里触发；放入队列给 SSE 协程消费
            set_slide_ready(run_id, page_index, slide)
            queue.put_nowait(
                {
                    "event": "slide_ready",
                    "page_index": page_index,
                    "slide": slide,
                }
            )

        def on_slide_failed(page_index: int, error: str) -> None:
            set_slide_failed(run_id, page_index, error)
            queue.put_nowait(
                {
                    "event": "slide_failed",
                    "page_index": page_index,
                    "error": error,
                }
            )

        llm = _ppt_llm_service(temperature=0.4, model=req.model)
        deck_task: Optional[asyncio.Task] = None
        try:
            from backend.services.ppt_assistant import (
                extract_ppt_elements,
                generate_slide_deck,
            )

            elements = await extract_ppt_elements(
                body,
                meta=_meta_dict(req.meta),
                llm=llm,
                chunk_chars=req.chunk_chars,
                overlap=req.overlap,
                max_repair_attempts=req.max_repair_attempts,
            )

            set_extract_done(run_id, elements)

            # 轻量事件：避免把整段元素塞进 SSE 内容
            yield formatter.format_chunk(
                json.dumps(
                    {
                        "event": "extract_done",
                        "one_liner": elements.get("one_liner", ""),
                        "outline_sections": len(elements.get("outline_sections") or []),
                    },
                    ensure_ascii=False,
                ),
                "streaming",
            )

            if req.elements_only:
                yield formatter.format_chunk(
                    json.dumps(
                        {"event": "done", "ppt_elements": elements},
                        ensure_ascii=False,
                    ),
                    "done",
                )
                return

            deck_task = asyncio.create_task(
                generate_slide_deck(
                    elements,
                    constraints=req.deck_constraints,
                    llm=llm,
                    single_slide=req.single_slide,
                    user_requirements=(req.meta.user_requirements or "").strip()
                    if req.meta
                    else None,
                    generation_mode=req.generation_mode,
                    parallelism=req.parallelism,
                    page_inputs=req.page_inputs,
                    on_slide_ready=on_slide_ready,
                    on_slide_failed=on_slide_failed,
                    max_repair_attempts=req.max_repair_attempts,
                )
            )

            while True:
                if deck_task.done() and queue.empty():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield formatter.format_chunk(
                        json.dumps(ev, ensure_ascii=False), "streaming"
                    )
                except asyncio.TimeoutError:
                    continue

            deck = await deck_task

            set_done(
                run_id,
                slide_deck=deck,
                slide_deck_markdown=slide_deck_to_markdown(deck),
            )
            yield formatter.format_chunk(
                json.dumps(
                    {
                        "event": "done",
                        "ppt_elements": elements,
                        "slide_deck": deck,
                        "slide_deck_markdown": slide_deck_to_markdown(deck),
                        "run_id": run_id,
                    },
                    ensure_ascii=False,
                ),
                "done",
            )
        except asyncio.CancelledError:
            # 客户端断开则取消内部任务
            set_cancelled(run_id)
            if deck_task and not deck_task.done():
                deck_task.cancel()
            raise
        except Exception as e:
            set_failed(run_id, str(e))
            yield formatter.format_error(str(e))
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/run-status")
async def ppt_run_status(run_id: str):
    rec = get_job(run_id)
    if not rec:
        return {"status": "not_found", "run_id": run_id}
    return {"status": "success", **job_to_public_dict(rec)}
