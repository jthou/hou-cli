#!/usr/bin/env python3
"""
写作助手问答复现 CLI：从命令行输入「参考信息 + 提问」，走与线上一致的 article_writing 编排路径，
便于对比审计页里的 system/user 与模型实际回复（例如模型索要「参考列表」时的复现）。

说明（避免误判）：
- 本路径是 **Orchestrator + 写作 system 提示词 + 单次 stream_chat**，不会启动 Python 类 **ArticleWritingAgent**
  （该类仅在命中 article_write / blog_writing 等**技能**时由技能内调用）。
- 调试日志里可能出现两条「LLM Request」：编排器记一条 + llm_service.stream_chat 内再记一条；若模型名曾显示为
  deepseek-chat 与 qwen3-max 各一次，属编排侧历史硬编码 bug（已改为 selected_model），不是「模型问了第二轮」。

时间：2026-03-21；理由：用户需在终端输入提问复现写作助手行为；方法：Orchestrator.stream_process +
context_type=article_writing，可选打印与 orchestrator 一致的 system/user 构造。

环境变量：
- ARTICLE_WRITING_REPLAY_MODEL：模型名，默认 qwen3-max（与 model_config 写作默认一致时可改）
- DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS：未设置时本脚本 setdefault true，避免写作技能抢答导致路径不一致；
  若需复现「技能命中」路径，可先 export DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS=false 再运行。

示例（与 UI 一致：无 -r 时仅发用户句；有 -r 时拼参考前缀 + 【用户本次提问】）：
  echo "新写全文：三级记忆…" | python scripts/replay_article_writing_cli.py
  python scripts/replay_article_writing_cli.py --dump-prompt -q "写一段引言"
  python scripts/replay_article_writing_cli.py -r @ref.txt -q "按上文润色"
  python scripts/replay_article_writing_cli.py --raw < full_user_message.txt
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 与 orchestrator.stream_process 中写作分支一致：助手默认跳过 skill prematch（若用户未显式关闭）
os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def reference_arg_to_block(raw: str) -> dict[str, str] | None:
    """单条 -r 参数 → 一条参考块；「（无）」等与 UI 空参考等价，返回 None。"""
    from backend.core.agent.article_writing_message_contract import is_no_reference_placeholder

    s = (raw or "").strip()
    if is_no_reference_placeholder(s):
        return None
    if s.startswith("@"):
        path = Path(s[1:]).expanduser()
        if not path.is_file():
            raise SystemExit(f"参考文件不存在: {path}")
        return {"title": path.name, "content": _read_text_file(path)}
    return {"title": "", "content": s}


def reference_args_to_blocks(ref_args: list[str] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for a in ref_args or []:
        b = reference_arg_to_block(a)
        if b:
            out.append(b)
    return out


def compute_article_writing_prompts(
    task: str,
    *,
    current_article: str | None = None,
) -> tuple[str, str, bool]:
    """
    复现 orchestrator 在 article_writing、无历史/无打分注入时对 system / user 的构造。
    current_article 非空时前置 build_article_draft_scope_prefix，顺序与 stream_process 一致：草稿 → 画像 → task → 字数/分节注入。
    返回 (system_prompt, user_prompt, use_doc_coauthoring)。
    """
    from backend.core.agent.system_prompt_templates import (
        DOC_COAUTHORING_WORKFLOW,
        get_article_writing_system_prompt,
    )
    from backend.core.agent.writing_profile import get_profile_block_for_prompt
    from backend.core.agent.article_writing_message_contract import (
        build_article_draft_scope_prefix,
        build_article_sectioning_hint_injection,
        build_article_word_count_constraint_injection,
        task_triggers_doc_coauthoring,
    )

    use_doc = task_triggers_doc_coauthoring(task)
    planning = DOC_COAUTHORING_WORKFLOW if use_doc else ""
    system_prompt = get_article_writing_system_prompt(
        planning_context=planning,
        feedback_history="",
    )
    user_prompt = task
    _dp = build_article_draft_scope_prefix(current_article)
    if _dp:
        user_prompt = _dp + user_prompt
    profile_block = get_profile_block_for_prompt()
    if profile_block:
        user_prompt = f"{profile_block}\n\n{user_prompt}"
    _wc = build_article_word_count_constraint_injection(task or "")
    if _wc:
        user_prompt = f"{user_prompt}\n\n{_wc}"
    _sec = build_article_sectioning_hint_injection(task or "")
    if _sec:
        user_prompt = f"{user_prompt}\n\n{_sec}"
    return system_prompt, user_prompt, use_doc


_META_PREFIXES = (
    "__DEBUG__",
    "__TOOL__",
    "__STATUS__",
    "__PROGRESS__",
    "__EVALUATION__",
    "__ORCH_TRACE__",
    "__CONFIRM__",
)


def _is_meta_chunk(chunk: str) -> bool:
    return any(chunk.startswith(p) for p in _META_PREFIXES)


async def run_stream(
    task: str,
    *,
    model: str,
    quiet_meta: bool,
) -> str:
    from backend.core.agent.orchestrator import Orchestrator

    o = Orchestrator()
    parts: list[str] = []
    context = {"context_type": "article_writing", "model": model}
    async for chunk in o.stream_process(task, context=context):
        if quiet_meta and _is_meta_chunk(chunk):
            continue
        parts.append(chunk)
    return "".join(parts)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="复现写作助手：输入提问（及可选参考），走 Orchestrator article_writing 流式路径。",
    )
    p.add_argument(
        "-q",
        "--question",
        help="用户本次提问（与 --reference 组合成标准 task；不填则从 stdin 读入作为整段提问）",
    )
    p.add_argument(
        "-r",
        "--reference",
        action="append",
        default=None,
        metavar="TEXT_OR_@FILE",
        help=(
            "参考正文或 @路径；可重复。省略或与 UI 一致地传 （无）/(无) 表示不附加参考块"
        ),
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="stdin 或 --question-file 的完整内容作为 task，不经过与 UI 一致的参考块拼装",
    )
    p.add_argument(
        "--question-file",
        "-f",
        type=Path,
        help="从文件读取提问或 raw 正文（与 stdin 二选一时优先文件）",
    )
    p.add_argument(
        "--article-file",
        type=Path,
        metavar="PATH",
        help=(
            "右侧文章草稿 Markdown 路径；用于 --dump-prompt/--show-prompt 时与线上一致注入【改稿范围】+【当前文章】。"
            "无 session 时直接流式调用 LLM 仍不会带草稿（仅提示拼装可用）。"
        ),
    )
    p.add_argument(
        "--model",
        default=os.getenv("ARTICLE_WRITING_REPLAY_MODEL", "qwen3-max"),
        help="模型名，写入 context['model']",
    )
    p.add_argument(
        "--dump-prompt",
        action="store_true",
        help="仅打印构造的 system / user（与当前 orchestrator 逻辑一致），不调用 LLM",
    )
    p.add_argument(
        "--show-prompt",
        action="store_true",
        help="调用 LLM 前先打印 system / user（可能较长）",
    )
    p.add_argument(
        "--no-quiet-meta",
        action="store_true",
        help="不过滤 __DEBUG__/__ORCH_TRACE__ 等元数据块（默认会过滤，仅保留模型正文）",
    )
    p.add_argument(
        "question_positional",
        nargs="?",
        help="提问正文（可选；未给 -q 且无 stdin 时使用）",
    )
    return p.parse_args(argv)


def _read_stdin_question() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


async def async_main(argv: list[str] | None) -> int:
    args = _parse_args(argv)
    quiet_meta = not args.no_quiet_meta

    raw_body: str | None = None
    user_q: str

    if args.question_file:
        body = _read_text_file(args.question_file)
        if args.raw:
            raw_body = body
            user_q = ""
        else:
            user_q = body
    else:
        user_q = (args.question or args.question_positional or "").strip()
        if not user_q:
            user_q = _read_stdin_question().strip()
        if args.raw:
            raw_body = user_q
            user_q = ""

    if raw_body is None and not user_q:
        print(
            "请提供提问：-q/--question、位置参数、--question-file 或管道 stdin",
            file=sys.stderr,
        )
        return 2

    from backend.core.agent.article_writing_message_contract import build_message_for_model

    blocks = reference_args_to_blocks(args.reference)
    if raw_body is not None:
        task = raw_body.strip()
    else:
        task = build_message_for_model(blocks, user_q)

    article_body: str | None = None
    if args.article_file:
        article_body = _read_text_file(args.article_file).strip() or None

    system_prompt, user_prompt, use_doc = compute_article_writing_prompts(
        task, current_article=article_body
    )

    if args.dump_prompt:
        print("=== doc_coauthoring 关键词触发 ===")
        print(use_doc)
        print(f"\n=== system_prompt ({len(system_prompt)} chars) ===")
        print(system_prompt)
        print(f"\n=== user_prompt ({len(user_prompt)} chars) ===")
        print(user_prompt)
        return 0

    if args.show_prompt:
        print(f"=== system_prompt ({len(system_prompt)} chars) ===\n{system_prompt}")
        print(f"\n=== user_prompt ({len(user_prompt)} chars) ===\n{user_prompt}")
        print("\n=== assistant stream ===\n")

    print(f"[replay] model={args.model} task_len={len(task)} doc_coauthoring={use_doc}", file=sys.stderr)

    out = await run_stream(task, model=args.model, quiet_meta=quiet_meta)
    sys.stdout.write(out)
    if out and not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main(None)))


if __name__ == "__main__":
    main()
