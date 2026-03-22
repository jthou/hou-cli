#!/usr/bin/env python3
# 时间：2026-03-22；理由：复现写作助手「修改意见 + 重写开篇」；方法：article_writing + build_message_for_model
# 时间：2026-03-22；理由：用户需要意图解读 Agent 做语义验收；方法：--assert-mode intent → intent_interpreter.judge_*；离线用 substring
"""
调试写作助手：参考块 = 待改开篇；用户提问 = 修改意见 +「重写这一段」。

与 Web 一致：`build_message_for_model` 会加【用户本次提问】。

用法：
  python scripts/test_article_writing_opening_rewrite.py
  python scripts/test_article_writing_opening_rewrite.py --assert-mode intent    # 默认：LLM 语义裁判（需 API）
  python scripts/test_article_writing_opening_rewrite.py --assert-mode substring # 离线：用户原话子串验收
  python scripts/test_article_writing_opening_rewrite.py --explain-intent      # 先打印「意图解读」再跑写作
  python scripts/test_article_writing_opening_rewrite.py --check-ctx-meta     # 仅校验流内是否下发写作 __CTX_META__（默认要求含参考块项）
  python scripts/test_article_writing_opening_rewrite.py --check-ctx-meta --check-ctx-meta-allow-no-reference  # 不要求 items 含 injected_reference（无参考块场景）
  ARTICLE_WRITING_TEST_MODEL=qwen3-max INTENT_INTERPRETER_MODEL=qwen-turbo-latest python scripts/...

环境变量：
  ARTICLE_WRITING_TEST_MODEL — 写作流模型
  INTENT_INTERPRETER_MODEL   — 意图解读/裁判专用模型（可选，默认同 LLMService 默认）
  ENABLE_ARTICLE_WRITING_CTX_META — 须为 true（默认）才能通过 --check-ctx-meta
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.agent.article_writing_message_contract import build_message_for_model
from backend.core.context.article_writing_context_meta import (
    parse_first_ctx_meta_payload_from_stream_chunks,
    validate_article_writing_ctx_meta_response,
)

# ---------------------------------------------------------------------------
# 与用户场景一致的素材（可改）
# ---------------------------------------------------------------------------
DRAFT_OPENING = """什么是代理工程（Agentic Engineering）？
想象一下，未来的软件不仅能执行指令，还能主动思考、规划并自主完成复杂任务——这正是代理工程（Agentic Engineering）所描绘的图景。作为人工智能与系统工程交叉的前沿领域，代理工程致力于构建具备目标驱动、环境感知和自主决策能力的智能体系统，正在重新定义人机协作的边界。随着大语言模型（LLM）和自主智能体技术的迅猛发展，理解并掌握代理工程的核心理念与实践方法，已成为开发者、研究者乃至企业战略制定者的关键能力。本文将深入解析代理工程的基本概念、关键技术、典型架构，并探讨其在现实场景中的应用潜力与挑战。"""

USER_INSTRUCTION = """修改意见：

开篇部分，用我个人的经历来引出：25年前，我刚入行的时候，教我写代码的师哥就说过，怎么写代码并不重要，写什么代码，很重要。

重写这一段"""

# 仅 --assert-mode substring 时使用：与修改意见同步维护
MUST_INCORPORATE_FROM_USER: list[str] = [
    "25年前，我刚入行的时候",
    "教我写代码的师哥就说过",
    "怎么写代码并不重要，写什么代码，很重要",
]


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _extract_content(chunks: list[str], *, verbose: bool) -> str:
    skip = (
        "__DEBUG__",
        "__TOOL__",
        "__STATUS__",
        "__PROGRESS__",
        "__EVALUATION__",
        "__ORCH_TRACE__",
        "__CTX_META__",
        "__CONFIRM__",
    )
    if verbose:
        return "".join(chunks)
    return "".join(c for c in chunks if not any(c.startswith(p) for p in skip))


def _check_substring_requirements(content: str) -> tuple[bool, str]:
    if len(content.strip()) < 40:
        return False, f"输出过短（{len(content)} 字符）"
    norm_out = _normalize_ws(content)
    missing: list[str] = []
    for phrase in MUST_INCORPORATE_FROM_USER:
        p = (phrase or "").strip()
        if not p:
            continue
        if _normalize_ws(p) not in norm_out:
            missing.append(p)
    if missing:
        return (
            False,
            "[substring 模式] 下列用户要点未以原话形式出现：\n  - " + "\n  - ".join(missing),
        )
    return True, "[substring 模式] 用户要点句均已出现"


def _judge_model() -> str | None:
    return (os.getenv("INTENT_INTERPRETER_MODEL") or "").strip() or None


def _check_article_writing_ctx_meta(
    chunks: list[str],
    *,
    expect_reference: bool,
) -> tuple[bool, str, object]:
    """时间：2026-03-13；理由：P2 写作 __CTX_META__ 可脚本回归；方法：复用 backend 解析/校验。返回 (ok, msg, payload|None)。"""
    payload = parse_first_ctx_meta_payload_from_stream_chunks(chunks)
    ok, msg = validate_article_writing_ctx_meta_response(
        payload, expect_reference=expect_reference
    )
    return ok, msg, payload


async def run(
    *,
    verbose: bool,
    assert_mode: str,
    explain_intent: bool,
    check_ctx_meta: bool,
    check_ctx_meta_expect_reference: bool,
) -> tuple[int, str, str]:
    from backend.core.agent.intent_interpreter import (
        explain_writing_instruction_intent,
        judge_writing_output_vs_instruction,
    )
    from backend.core.agent.orchestrator import Orchestrator

    article_model = os.getenv("ARTICLE_WRITING_TEST_MODEL", "qwen-max")
    judge_model = _judge_model()
    reference_blocks = [{"title": "待改稿·开篇", "content": DRAFT_OPENING}]
    task = build_message_for_model(reference_blocks, USER_INSTRUCTION)

    print(f"写作模型: {article_model}")
    if assert_mode == "intent" or explain_intent:
        print(f"意图解读/裁判模型: {judge_model or '(LLMService 默认)'}")
    print(f"参考块: 待改稿·开篇（{len(DRAFT_OPENING)} 字）")
    print("用户提问（节选）:", USER_INSTRUCTION.replace("\n", " ")[:200], "…")
    print()

    if explain_intent:
        print("--- 意图解读 Agent（仅用户指令）---")
        try:
            intent = await explain_writing_instruction_intent(
                USER_INSTRUCTION, model=judge_model
            )
            print(f"  intent_summary: {intent.intent_summary}")
            print(f"  revision_scope: {intent.revision_scope}")
            print(f"  must_preserve_substance: {intent.must_preserve_substance}")
            print(f"  stylistic_constraints: {intent.stylistic_constraints}")
            if intent.ambiguity_notes:
                print(f"  ambiguity_notes: {intent.ambiguity_notes}")
        except Exception as e:
            print(f"  （意图解读失败: {e}）")
        print("--- 意图解读结束 ---\n")

    o = Orchestrator()
    chunks: list[str] = []
    context = {"context_type": "article_writing", "model": article_model}

    async for chunk in o.stream_process(task, context=context):
        chunks.append(chunk)

    content = _extract_content(chunks, verbose=verbose)

    if check_ctx_meta:
        ok, ctx_msg, ctx_payload = _check_article_writing_ctx_meta(
            chunks, expect_reference=check_ctx_meta_expect_reference
        )
        if verbose and ctx_payload is not None:
            # 时间：2026-03-13；理由：排障时需看完整 meta；方法：与 --verbose 其它控制帧一致，单独打印 JSON
            print("--- __CTX_META__ 解析结果（verbose）---")
            try:
                print(json.dumps(ctx_payload, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"  （无法序列化: {e}）")
            print("--- ---\n")
        print(ctx_msg)
        if not ok:
            return 3, ctx_msg, content

    if assert_mode == "none":
        return 0, "未启用验收（--assert-mode none）", content

    if assert_mode == "substring":
        ok, msg = _check_substring_requirements(content)
        return (0 if ok else 1), msg, content

    # intent
    try:
        judgment = await judge_writing_output_vs_instruction(
            USER_INSTRUCTION, content, model=judge_model
        )
        lines = [
            "--- 意图验收 Agent（用户指令 vs 模型输出）---",
            f"  satisfied: {judgment.satisfied}",
            f"  confidence: {judgment.confidence}",
            f"  rationale: {judgment.rationale}",
        ]
        if judgment.unmet_points:
            lines.append(f"  unmet_points: {judgment.unmet_points}")
        msg = "\n".join(lines)
        ok = judgment.satisfied and judgment.confidence != "low"
        if judgment.satisfied and judgment.confidence == "low":
            ok = False
            msg += "\n  （confidence=low，判为未通过；可换 INTENT_INTERPRETER_MODEL 或人工复核）"
        code = 0 if ok else 1
        return code, msg, content
    except Exception as e:
        return (
            2,
            f"意图验收 Agent 调用失败（{e}）。无 API 时请使用 --assert-mode substring 或 --assert-mode none。",
            content,
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="写作助手复现：可选意图解读 Agent 做语义验收",
    )
    ap.add_argument(
        "--assert-mode",
        choices=("intent", "substring", "none"),
        default="intent",
        help="intent=LLM 语义裁判（默认）；substring=用户原话子串；none=不验收",
    )
    ap.add_argument("--no-assert", action="store_true", help="已废弃，请用 --assert-mode none")
    ap.add_argument("--verbose", action="store_true", help="保留 __DEBUG__/__ORCH_TRACE__ 等帧")
    ap.add_argument(
        "--explain-intent",
        action="store_true",
        help="写作前先调用意图解读 Agent，打印结构化意图",
    )
    ap.add_argument(
        "--check-ctx-meta",
        action="store_true",
        help="流式结束后校验是否下发写作 __CTX_META__；默认要求 items 含 injected_reference；失败退出码 3",
    )
    ap.add_argument(
        "--check-ctx-meta-allow-no-reference",
        action="store_true",
        help="与 --check-ctx-meta 联用：不强制要求 injected_reference（无参考块 / 自定义 task 场景）",
    )
    args = ap.parse_args()
    mode = "none" if args.no_assert else args.assert_mode

    print("=" * 60)
    _ctx_ref = ""
    if args.check_ctx_meta:
        _ctx_ref = " ctx_expect_reference=%s" % (not args.check_ctx_meta_allow_no_reference)
    print(
        "写作助手调试：assert_mode=%s check_ctx_meta=%s%s"
        % (mode, args.check_ctx_meta, _ctx_ref)
    )
    print("=" * 60)

    code, msg, content = asyncio.run(
        run(
            verbose=args.verbose,
            assert_mode=mode,
            explain_intent=args.explain_intent,
            check_ctx_meta=args.check_ctx_meta,
            check_ctx_meta_expect_reference=not args.check_ctx_meta_allow_no_reference,
        )
    )
    print(msg)
    print()
    print("--- 模型输出 ---")
    print(content)
    print("--- 结束 ---")
    return code


if __name__ == "__main__":
    sys.exit(main())
