#!/usr/bin/env python3
"""
PPT 助手同步 CLI：与 /api/ppt-assistant/* 共用 services.ppt_assistant。

用法（在项目根目录）:
  python -m backend.cli.ppt_assistant_cli extract -i article.txt -o elements.json
  python -m backend.cli.ppt_assistant_cli deck -i elements.json -o deck.json
  python -m backend.cli.ppt_assistant_cli run -i article.txt -o-dir ./out
  python -m backend.cli.ppt_assistant_cli refine -d slide_deck.json -t 1 -I "更口语化" -o out.json
  python -m backend.cli.ppt_assistant_cli export-pptx -i deck.json -o deck.pptx
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    from shared.load_env import load_env

    load_env(PROJECT_ROOT)


def _read_text(path: Optional[str], stdin_if_none: bool) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if stdin_if_none:
        return sys.stdin.read()
    raise click.UsageError("请指定 -i/--input 或管道输入")


def _llm_service(*, temperature: float, model: Optional[str] = None):
    from backend.services.llm.llm_service import LLMService

    m = (model or "").strip()
    if m:
        return LLMService(temperature=temperature, model=m)
    return LLMService(temperature=temperature)


def _write_json(out_path: Optional[str], data: Dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not out_path or out_path == "-":
        sys.stdout.write(text)
    else:
        Path(out_path).write_text(text, encoding="utf-8")


async def _extract_async(
    article: str,
    meta: Dict[str, Any],
    chunk: int,
    overlap: int,
    out: str,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
):
    from backend.services.ppt_assistant import extract_ppt_elements

    m = dict(meta or {})
    ur = (user_requirements or "").strip()
    if ur:
        m["user_requirements"] = ur
    llm = _llm_service(temperature=0.35, model=model)
    data = await extract_ppt_elements(
        article,
        meta=m or None,
        llm=llm,
        chunk_chars=chunk,
        overlap=overlap,
        max_repair_attempts=max_repair,
    )
    _write_json(out, {"ppt_elements": data})


async def _deck_async(
    elements: Dict[str, Any],
    constraints: str,
    out: str,
    *,
    single_slide: bool,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
    generation_mode: str,
    parallelism: int,
):
    from backend.services.ppt_assistant import generate_slide_deck, slide_deck_to_markdown

    llm = _llm_service(temperature=0.45, model=model)
    deck = await generate_slide_deck(
        elements,
        constraints=constraints,
        llm=llm,
        single_slide=single_slide,
        user_requirements=user_requirements.strip() or None,
        max_repair_attempts=max_repair,
        generation_mode=generation_mode,
        parallelism=parallelism,
    )
    md = slide_deck_to_markdown(deck)
    _write_json(out, {"slide_deck": deck, "slide_deck_markdown": md})


async def _run_async(
    article: str,
    meta: Dict[str, Any],
    deck_constraints: str,
    chunk: int,
    overlap: int,
    elements_only: bool,
    out_dir: Path,
    *,
    single_slide: bool,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
    generation_mode: str,
    parallelism: int,
):
    from backend.services.ppt_assistant import run_ppt_pipeline, slide_deck_to_markdown

    m = dict(meta or {})
    ur = (user_requirements or "").strip()
    if ur:
        m["user_requirements"] = ur
    llm = _llm_service(temperature=0.4, model=model)
    result = await run_ppt_pipeline(
        article,
        meta=m or None,
        deck_constraints=deck_constraints,
        llm=llm,
        chunk_chars=chunk,
        overlap=overlap,
        elements_only=elements_only,
        single_slide=single_slide,
        max_repair_attempts=max_repair,
        generation_mode=generation_mode,
        parallelism=parallelism,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ppt_elements.json").write_text(
        json.dumps(result["ppt_elements"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    deck = result.get("slide_deck")
    if deck is not None:
        (out_dir / "slide_deck.json").write_text(
            json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "slide_deck.md").write_text(
            slide_deck_to_markdown(deck), encoding="utf-8"
        )


async def _refine_async(
    deck: Dict[str, Any],
    targets: str,
    instructions: str,
    out: str,
    *,
    elements: Optional[Dict[str, Any]],
    locks_json: Optional[str],
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
):
    import json as _json

    from backend.services.ppt_assistant import refine_slide_deck, slide_deck_to_markdown

    idxs = [int(x.strip()) for x in targets.split(",") if x.strip()]
    if not idxs:
        raise click.UsageError("请用 --targets 指定页 index，逗号分隔，如 1 或 1,2")
    locks_map: Optional[Dict[int, list]] = None
    if locks_json:
        raw = _json.loads(locks_json)
        if not isinstance(raw, dict):
            raise click.UsageError("locks-json 必须是 JSON 对象")
        locks_map = {}
        for k, v in raw.items():
            locks_map[int(k)] = list(v or [])
    llm = _llm_service(temperature=0.45, model=model)
    new_deck = await refine_slide_deck(
        deck,
        target_slide_indexes=idxs,
        instructions=instructions,
        llm=llm,
        ppt_elements=elements,
        locks=locks_map,
        user_requirements=user_requirements.strip() or None,
        max_repair_attempts=max_repair,
    )
    md = slide_deck_to_markdown(new_deck)
    _write_json(out, {"slide_deck": new_deck, "slide_deck_markdown": md})


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """PPT 助手命令行（同步封装 asyncio）。"""
    _load_env()


@main.command("extract")
@click.option(
    "--input",
    "-i",
    "input_path",
    type=str,
    default=None,
    help="文章文件；可省略则从 stdin 读",
)
@click.option("--output", "-o", "out_path", type=str, default="-", help="输出 JSON，默认 stdout")
@click.option("--chunk-chars", type=int, default=10_000, show_default=True)
@click.option("--overlap", type=int, default=400, show_default=True)
@click.option(
    "--user-requirements",
    "-U",
    type=str,
    default="",
    help="用户意见与需求，与文章一并送入抽取模型",
)
@click.option(
    "--model",
    "-M",
    type=str,
    default=None,
    help="模型 id（与 UI 可选列表一致）；省略则用环境默认",
)
@click.option(
    "--max-repair",
    type=int,
    default=2,
    show_default=True,
    help="JSON 校验失败时 repair 轮数；0 表示不 repair",
)
def extract_cmd(
    input_path: Optional[str],
    out_path: str,
    chunk_chars: int,
    overlap: int,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
):
    article = _read_text(input_path, stdin_if_none=True)
    asyncio.run(
        _extract_async(
            article,
            {},
            chunk_chars,
            overlap,
            out_path,
            user_requirements,
            model,
            max_repair,
        )
    )


@main.command("deck")
@click.option("--input", "-i", "input_path", type=str, required=True, help="ppt_elements JSON 文件")
@click.option("--output", "-o", "out_path", type=str, default="-")
@click.option("--constraints", "-c", type=str, default="")
@click.option(
    "--multi-slide",
    is_flag=True,
    help="生成多页幻灯片（默认单页汇总）",
)
@click.option(
    "--user-requirements",
    "-U",
    type=str,
    default="",
    help="用户意见与需求，生成 deck 时一并送入模型",
)
@click.option(
    "--model",
    "-M",
    type=str,
    default=None,
    help="模型 id；省略则用环境默认",
)
@click.option("--max-repair", type=int, default=2, show_default=True)
@click.option(
    "--generation-mode",
    type=click.Choice(["sequential", "parallel"], case_sensitive=False),
    default="sequential",
    show_default=True,
    help="多页生成模式（parallel：页级并行 draft；需配合 --multi-slide）",
)
@click.option(
    "--parallelism",
    type=int,
    default=4,
    show_default=True,
    help="parallel 模式并发上限（页级）",
)
def deck_cmd(
    input_path: str,
    out_path: str,
    constraints: str,
    multi_slide: bool,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
    generation_mode: str,
    parallelism: int,
):
    blob = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if "ppt_elements" in blob:
        elements = blob["ppt_elements"]
    else:
        elements = blob
    asyncio.run(
        _deck_async(
            elements,
            constraints,
            out_path,
            single_slide=not multi_slide,
            user_requirements=user_requirements,
            model=model,
            max_repair=max_repair,
            generation_mode=generation_mode,
            parallelism=parallelism,
        )
    )


@main.command("run")
@click.option("--input", "-i", "input_path", type=str, default=None, help="文章文件；省略则从 stdin 读")
@click.option(
    "--out-dir",
    "-d",
    type=click.Path(path_type=Path),
    default=Path("ppt_out"),
    show_default=True,
)
@click.option("--deck-constraints", "-c", type=str, default="")
@click.option("--elements-only", is_flag=True, help="仅抽取 ppt_elements，不生成 slide_deck")
@click.option("--chunk-chars", type=int, default=10_000, show_default=True)
@click.option("--overlap", type=int, default=400, show_default=True)
@click.option(
    "--multi-slide",
    is_flag=True,
    help="生成多页幻灯片（默认单页汇总）",
)
@click.option(
    "--user-requirements",
    "-U",
    type=str,
    default="",
    help="用户意见与需求，抽取与生成 deck 时一并送入模型",
)
@click.option(
    "--model",
    "-M",
    type=str,
    default=None,
    help="模型 id；全流程使用同一模型；省略则用环境默认",
)
@click.option("--max-repair", type=int, default=2, show_default=True)
@click.option(
    "--generation-mode",
    type=click.Choice(["sequential", "parallel"], case_sensitive=False),
    default="sequential",
    show_default=True,
    help="多页生成模式（parallel：页级并行 draft；需配合 --multi-slide）",
)
@click.option(
    "--parallelism",
    type=int,
    default=4,
    show_default=True,
    help="parallel 模式并发上限（页级）",
)
def run_cmd(
    input_path: Optional[str],
    out_dir: Path,
    deck_constraints: str,
    elements_only: bool,
    chunk_chars: int,
    overlap: int,
    multi_slide: bool,
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
    generation_mode: str,
    parallelism: int,
):
    article = _read_text(input_path, stdin_if_none=True)
    asyncio.run(
        _run_async(
            article,
            {},
            deck_constraints,
            chunk_chars,
            overlap,
            elements_only,
            out_dir,
            single_slide=not multi_slide,
            user_requirements=user_requirements,
            model=model,
            max_repair=max_repair,
            generation_mode=generation_mode,
            parallelism=parallelism,
        )
    )


@main.command("export-pptx")
@click.option(
    "--input",
    "-i",
    "input_path",
    type=str,
    required=True,
    help="slide_deck JSON 文件（可含 slide_deck 键）",
)
@click.option(
    "--output",
    "-o",
    "out_path",
    type=str,
    required=True,
    help="输出 .pptx 路径",
)
def export_pptx_cmd(input_path: str, out_path: str):
    blob = json.loads(Path(input_path).read_text(encoding="utf-8"))
    deck = blob["slide_deck"] if "slide_deck" in blob else blob
    from backend.services.ppt_assistant.pptx_export import slide_deck_to_pptx_bytes

    data = slide_deck_to_pptx_bytes(deck)
    Path(out_path).write_bytes(data)
    click.echo(f"已写入 {out_path}（{len(data)} 字节）")


@main.command("refine")
@click.option(
    "--deck",
    "-d",
    "deck_path",
    type=str,
    required=True,
    help="slide_deck JSON 文件（可含 slide_deck 键）",
)
@click.option(
    "--targets",
    "-t",
    type=str,
    required=True,
    help="要重写的页 index，逗号分隔，如 1 或 1,2",
)
@click.option(
    "--instructions",
    "-I",
    type=str,
    required=True,
    help="修改要求（自然语言）",
)
@click.option("--output", "-o", "out_path", type=str, default="-")
@click.option(
    "--elements",
    "-e",
    type=str,
    default=None,
    help="可选 ppt_elements JSON 文件，供 refine 作上下文",
)
@click.option(
    "--locks-json",
    type=str,
    default=None,
    help='可选：JSON 对象，键为页 index 字符串，如 {"1":["title","bullets"]}',
)
@click.option("--user-requirements", "-U", type=str, default="")
@click.option("--model", "-M", type=str, default=None)
@click.option("--max-repair", type=int, default=2, show_default=True)
def refine_cmd(
    deck_path: str,
    targets: str,
    instructions: str,
    out_path: str,
    elements: Optional[str],
    locks_json: Optional[str],
    user_requirements: str,
    model: Optional[str],
    max_repair: int,
):
    blob = json.loads(Path(deck_path).read_text(encoding="utf-8"))
    deck = blob["slide_deck"] if "slide_deck" in blob else blob
    el: Optional[Dict[str, Any]] = None
    if elements:
        eb = json.loads(Path(elements).read_text(encoding="utf-8"))
        el = eb.get("ppt_elements", eb)
    asyncio.run(
        _refine_async(
            deck,
            targets,
            instructions,
            out_path,
            elements=el,
            locks_json=locks_json,
            user_requirements=user_requirements,
            model=model,
            max_repair=max_repair,
        )
    )


if __name__ == "__main__":
    main()
