#!/usr/bin/env python3
# 时间：2026-03-22；理由：复现 UI 与通用对话同源编排流式路径；方法：直接调用 Orchestrator.stream_process（context_type=general_chat）
"""
命令行复现「通用对话」流式过程（与前端 WebSocket/SSE 调用的编排器一致）。

示例：
  python scripts/test_general_chat_stream.py --task "你好"
  python scripts/test_general_chat_stream.py --task-file ./sample_news.txt
  GENERAL_CHAT_SKILL_PREMATCH=off python scripts/test_general_chat_stream.py --task "测试"

选项 --verbose 会原样打印 __DEBUG__/__ORCH_TRACE__ 等行（默认忽略，仅看助手正文）。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="通用对话 stream_process CLI 复现")
    parser.add_argument("--task", type=str, default="", help="用户消息")
    parser.add_argument("--task-file", type=Path, default=None, help="从文件读入用户消息（UTF-8）")
    parser.add_argument("--session-id", type=str, default=None, help="可选，复用已有会话 id")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印 __DEBUG__ / __ORCH_TRACE__ / __TOOL__ 等内部块",
    )
    args = parser.parse_args()

    root = _project_root()
    sys.path.insert(0, str(root))

    if args.task_file:
        task = args.task_file.read_text(encoding="utf-8")
    else:
        task = (args.task or "").strip() or "你好，简单自我介绍。"

    async def run() -> None:
        from backend.core.agent.orchestrator import Orchestrator

        orch = Orchestrator()
        ctx: dict = {"context_type": "general_chat"}
        if args.session_id:
            ctx["session_id"] = args.session_id

        prefixes_skip = ("__DEBUG__:", "__TOOL__:", "__STATUS__:", "__PROGRESS__:", "__EVALUATION__:")
        async for chunk in orch.stream_process(task, context=ctx):
            if not args.verbose:
                if chunk.startswith(prefixes_skip) or chunk.startswith("__ORCH_TRACE__"):
                    continue
            print(chunk, end="", flush=True)
        print()

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
