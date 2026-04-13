#!/usr/bin/env python3
"""
Orchestrator 回归测试脚本：验证关键场景行为。
可单独运行，也可在 CI 中作为集成测试。
需要配置 LLM API Keys（.env 中的 DEEPSEEK_API_KEY 等）。
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def run_case(name: str, task: str, context: dict, expect_tool: bool = False) -> tuple[bool, str]:
    """运行单个用例，返回 (通过, 消息)"""
    from backend.core.agent.orchestrator import Orchestrator

    o = Orchestrator()
    tool_chunks = []
    content_chunks = []

    try:
        async for chunk in o.stream_process(task, context=context):
            if chunk.startswith("__TOOL__:"):
                try:
                    data = json.loads(chunk[9:].strip())
                    tool_chunks.append(data)
                except Exception:
                    pass
            elif not any(
                chunk.startswith(p)
                for p in ("__DEBUG__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")
            ):
                content_chunks.append(chunk)

        content = "".join(content_chunks)
        has_tool = len(tool_chunks) > 0

        if expect_tool and not has_tool:
            return False, f"期望有工具调用，实际无。内容长度={len(content)}"
        if not expect_tool and has_tool:
            return False, f"期望无工具调用，实际有 {len(tool_chunks)} 次"
        return True, f"通过 (tools={len(tool_chunks)}, content_len={len(content)})"
    except Exception as e:
        return False, f"异常: {e}"


async def main():
    cases = [
        # legacy metadata.type：编排侧归一为 general_chat，可与通用对话一样走工具
        ("legacy_code_assistant_ctx_期望可执行", "写 print(1) 执行看看", {"context_type": "code_assistant"}, True),
        ("legacy_work_assistant_ctx_整理待办无工具", "帮我整理待办", {"context_type": "work_assistant"}, False),
        ("general_chat_可选工具", "你好", {"context_type": "general_chat"}, False),
    ]

    print("=" * 60)
    print("Orchestrator 回归测试")
    print("=" * 60)

    passed = 0
    for name, task, ctx, expect_tool in cases:
        ok, msg = await run_case(name, task, ctx, expect_tool)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if ok:
            passed += 1

    print()
    print(f"结果: {passed}/{len(cases)} 通过")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
