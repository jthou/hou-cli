#!/usr/bin/env python3
# 时间：2026-03-22；理由：复现 UI 与通用对话同源编排流式路径；方法：直接调用 Orchestrator.stream_process（context_type=general_chat）
"""
命令行复现「通用对话」流式过程（与前端 WebSocket/SSE 调用的编排器一致）。

示例：
  python scripts/test_general_chat_stream.py --task "你好"
  python scripts/test_general_chat_stream.py --task-file ./sample_news.txt
  # 正文含 https 链接（如写作参考块）时，默认 auto 会允许技能预匹配；若只想测「纯对话+工具」请加：
  # 若 bailian-kimi-k2-thinking 报 403 FreeTierOnly：控制台关闭「仅免费」或换模型后再跑
  GENERAL_CHAT_SKILL_PREMATCH=off .venv/bin/python scripts/test_general_chat_stream.py \\
    --task-file scripts/fixtures/general_chat_miit_citation_audit.txt
  # 临时覆盖推理模型（避免 bailian-kimi-k2-thinking 报 403 FreeTierOnly，无需改 .env）
  python scripts/test_general_chat_stream.py --reasoning-model qwen3-max --task "测试"
  # 与 UI「深度思考」一致：强制使用 REASONING_MODEL
  python scripts/test_general_chat_stream.py --deep-thinking --task "分析三步计划"

选项 --verbose 会原样打印 __DEBUG__/__ORCH_TRACE__ 等行（默认忽略，仅看助手正文）。
"""
from __future__ import annotations

import argparse
import asyncio
import os
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
    parser.add_argument(
        "--reasoning-model",
        type=str,
        default=None,
        help="覆盖 REASONING_MODEL（须在 import 编排器前设置；用于临时避开 Kimi 免费额度 403）",
    )
    parser.add_argument(
        "--deep-thinking",
        action="store_true",
        help="等同前端深度思考：context.model=reasoning（走 REASONING_MODEL）",
    )
    args = parser.parse_args()

    root = _project_root()
    sys.path.insert(0, str(root))
    # 时间：2026-03-13；理由：CLI 单次跑需换推理模型；方法：先于 Orchestrator 加载 model_config
    if args.reasoning_model and args.reasoning_model.strip():
        os.environ["REASONING_MODEL"] = args.reasoning_model.strip()

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
        if args.deep_thinking:
            ctx["model"] = "reasoning"
            ctx["deep_thinking"] = True

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
