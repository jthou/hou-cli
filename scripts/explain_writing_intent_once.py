#!/usr/bin/env python3
# 时间：2026-03-22；理由：终端单次调用意图解读 Agent，无需跑完整写作流；方法：stdin 或 --file 读入用户指令
"""
从标准输入或文件读取「用户指令」（可含正文节选 + 修改意见），调用 explain_writing_instruction_intent，打印结构化意图。

  python scripts/explain_writing_intent_once.py < my_instruction.txt
  python scripts/explain_writing_intent_once.py --file path/to.txt
  INTENT_INTERPRETER_MODEL=qwen-turbo-latest python scripts/explain_writing_intent_once.py --file ...

需在项目 venv 下运行（依赖 openai / 已配置 API）。
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


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, help="用户指令文件 UTF-8")
    args = ap.parse_args()
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    text = (text or "").strip()
    if not text:
        print("（空输入）", file=sys.stderr)
        return 1

    from backend.core.agent.intent_interpreter import explain_writing_instruction_intent

    m = (os.getenv("INTENT_INTERPRETER_MODEL") or "").strip() or None
    r = await explain_writing_instruction_intent(text, model=m)
    print("intent_summary:", r.intent_summary)
    print("revision_scope:", r.revision_scope)
    print("must_preserve_substance:")
    for x in r.must_preserve_substance:
        print("  -", x)
    print("stylistic_constraints:")
    for x in r.stylistic_constraints:
        print("  -", x)
    if r.ambiguity_notes:
        print("ambiguity_notes:", r.ambiguity_notes)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
