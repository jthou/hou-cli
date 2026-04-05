"""slide_deck → 百炼文生图：逐页生成「整页幻灯片视觉」用图（对齐 banana-slides 心智：交付物为可演示画面）。"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from backend.services.ppt_assistant.bullets import bullet_parts, bullet_slide_hint
from backend.services.ppt_assistant.slide_text_layout import (
    effective_text_scheme,
    slide_body_long_text,
    slide_lead_text,
    slide_subtitle_text,
    TEXT_SCHEME_LONG_PROSE,
    TEXT_SCHEME_TITLE_LEAD,
    TEXT_SCHEME_TITLE_ONLY,
    TEXT_SCHEME_TITLE_SUBTITLE_LEAD,
)
from backend.services.ppt_assistant.slide_image_store import (
    SlideImageJob,
    record_slide_image,
    record_slide_image_error,
)

# 16:9 与 ImageGenService / 百炼 wan 常见规格一致
SLIDE_IMAGE_SIZE = "1280*720"


def _slide_sort_index(slide: Dict[str, Any], fallback: int) -> int:
    try:
        return int(slide.get("index", fallback))
    except (TypeError, ValueError):
        return fallback


def valid_slide_indexes_from_deck(deck: Dict[str, Any]) -> Set[int]:
    """slide_deck 中实际出现的页 index 集合（与 sorted_slides_from_deck 一致）。"""
    return {i for i, _ in sorted_slides_from_deck(deck)}


def sorted_slides_from_deck(deck: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    slides = deck.get("slides")
    if not isinstance(slides, list):
        return []
    valid = [s for s in slides if isinstance(s, dict)]
    indexed = [(i, s) for i, s in enumerate(valid)]
    indexed.sort(key=lambda t: _slide_sort_index(t[1], t[0] + 1))
    out: List[Tuple[int, Dict[str, Any]]] = []
    for _, s in indexed:
        idx = _slide_sort_index(s, len(out) + 1)
        out.append((idx, s))
    return out


def build_slide_visual_prompt(
    slide: Dict[str, Any],
    deck: Dict[str, Any],
    *,
    style_note: str = "",
) -> str:
    """
    构造百炼文生图 prompt：企业演示风、16:9、可读中文标题与要点（模型能力决定最终字形准确度）。
    """
    deck_title = str(deck.get("deck_title") or "").strip()
    kind = str(slide.get("kind") or "content").strip()
    title = str(slide.get("title") or "").strip()
    bullets = slide.get("bullets") if isinstance(slide.get("bullets"), list) else []
    lines: List[str] = []
    for b in bullets:
        t, _ = bullet_parts(b)
        if not t:
            continue
        h = bullet_slide_hint(b)
        lines.append(f"{t}" + (f"（小字提示：{h}）" if h else ""))
    bullets_text = "；".join(lines[:8]) if lines else ""

    style = (style_note or "").strip()
    style_clause = f"用户风格要求：{style}。" if style else ""

    if kind == "title":
        core = (
            f"宽屏16:9专业演示文稿封面。主标题用醒目大号字展示：「{title}」。"
            f"副标题区域：「{deck_title or '演示'}」。"
            "顶部一条商务蓝横色块，其余大面积干净留白或浅渐变，简洁大气，无杂乱装饰。"
        )
    elif kind == "transition":
        core = (
            f"宽屏16:9章节过渡页。中央突出章节标题：「{title}」。"
            "背景简洁、浅灰或浅蓝商务风，可有细分隔线，适合口头讲解承上启下。"
        )
    else:
        scheme = effective_text_scheme(slide)
        lead = slide_lead_text(slide)
        sub = slide_subtitle_text(slide)
        prose = slide_body_long_text(slide)
        if scheme == TEXT_SCHEME_TITLE_ONLY:
            core = (
                f"宽屏16:9 商务PPT内页。仅页顶约15%蓝色标题条写「{title}」，"
                "下方整页大面积干净留白或极浅灰渐变，无列表、无长正文，极简汇报风。"
            )
        elif scheme == TEXT_SCHEME_TITLE_LEAD:
            core = (
                f"宽屏16:9 商务PPT内页。蓝色标题条「{title}」。"
                f"标题下主文区一段较短说明文字（约2～5行、字号中等醒目），内容为：{lead or '（摘要句）'}。"
                "右侧约40%浅蓝示意区可放小图标装饰；无项目符号列表。"
            )
        elif scheme == TEXT_SCHEME_TITLE_SUBTITLE_LEAD:
            core = (
                f"宽屏16:9 商务PPT内页。蓝色标题条「{title}」。"
                f"其下左侧先一行略小的次级标题「{sub or '（小标题）'}」，"
                f"再接一段短说明（2～4行）：{lead or '（提要）'}。"
                "右侧浅蓝示意区与文字对齐，无圆角手机风。"
            )
        elif scheme == TEXT_SCHEME_LONG_PROSE:
            excerpt = (prose or bullets_text or "（说明正文）")[:900]
            core = (
                f"宽屏16:9 商务PPT内页。蓝色标题条「{title}」。"
                f"下方左侧主栏为一块连续正文（小号字多行段落、可读），内容要点：{excerpt}。"
                "右侧约40%浅蓝示意区；不要做成多条项目符号列表，以段落排版为主。"
            )
        else:
            core = (
                f"宽屏16:9 商务PPT内页。布局：上方约15%为蓝色标题条，内写清晰中文标题「{title}」。"
                f"下方左侧白色区域列出要点（短句，分点）：{bullets_text or '（条理清晰的信息图）'}。"
                "右侧约40%为浅蓝色示意区，可放简洁图标、流程箭头或数据卡片剪影，与文字协调。"
                "整体配色：标题条演示蓝、正文白底深灰字，对比高、无水印、无变形字。"
            )

    return (
        f"{core}{style_clause}"
        "高清、扁平方角版面，禁止圆角手机壳风格，禁止恐怖谷人物特写。"
    ).strip()


async def generate_slide_images(
    deck: Dict[str, Any],
    job: SlideImageJob,
    *,
    style_note: str = "",
    image_model: Optional[str] = None,
    style_reference_urls: Optional[List[str]] = None,
    on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    parallelism: int = 1,
    only_indexes: Optional[Set[int]] = None,
) -> None:
    """
    调用百炼生成 PNG，写入 job.base_dir/slide_{index}.png。
    - parallelism>1 时页级并行（每页独立临时目录，避免文件名冲突）。
    - only_indexes 非空时仅生成指定页（补跑失败页或用户指定页）。
    - style_reference_urls：整组任务共用的风格参考图（多模态模型如 wan2.6-image 下优先走图+文）。

    on_event:
      slide_image_ready: { page_index, url }
      slide_image_failed: { page_index, error }
    """
    from backend.services.llm.image_gen_service import ImageGenService

    svc = ImageGenService(model=image_model)
    pairs = sorted_slides_from_deck(deck)
    if only_indexes is not None and len(only_indexes) > 0:
        pairs = [(i, s) for i, s in pairs if i in only_indexes]
    if not pairs:
        return

    sem = asyncio.Semaphore(max(1, min(int(parallelism or 1), 8)))

    async def run_one(page_index: int, s: Dict[str, Any]) -> None:
        async with sem:
            prompt = build_slide_visual_prompt(s, deck, style_note=style_note)
            out_file = job.base_dir / f"slide_{page_index}.png"
            tmp_dir = job.base_dir / "_tmp" / str(page_index)
            try:
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                result = await svc.generate(
                    prompt,
                    model=image_model,
                    size=SLIDE_IMAGE_SIZE,
                    n=1,
                    output_dir=str(tmp_dir),
                    reference_image_urls=style_reference_urls,
                )
                saved = (result.get("output_file") or "").strip()
                src = Path(saved) if saved else None
                if src and src.is_file():
                    if src.resolve() != out_file.resolve():
                        shutil.copy2(src, out_file)
                elif not out_file.is_file():
                    raise RuntimeError(result.get("error") or "未写入 slide 图片文件")

                if not out_file.is_file():
                    raise RuntimeError("slide 图片复制失败")

                abs_path = str(out_file.resolve())
                record_slide_image(job.job_id, page_index, abs_path)
                if on_event:
                    on_event(
                        "slide_image_ready",
                        {
                            "page_index": page_index,
                            "url": f"/api/ppt-assistant/slide-images/file/{job.job_id}/{page_index}",
                        },
                    )
            except Exception as e:
                err = str(e) or type(e).__name__
                record_slide_image_error(job.job_id, page_index, err)
                if on_event:
                    on_event(
                        "slide_image_failed",
                        {"page_index": page_index, "error": err},
                    )
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    await asyncio.gather(*(run_one(i, s) for i, s in pairs))


async def generate_slide_images_sequential(
    deck: Dict[str, Any],
    job: SlideImageJob,
    *,
    style_note: str = "",
    image_model: Optional[str] = None,
    style_reference_urls: Optional[List[str]] = None,
    on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> None:
    """兼容旧名：顺序 = 并行度 1。"""
    await generate_slide_images(
        deck,
        job,
        style_note=style_note,
        image_model=image_model,
        style_reference_urls=style_reference_urls,
        on_event=on_event,
        parallelism=1,
    )
