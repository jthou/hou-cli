#!/usr/bin/env python3
"""
验证 google_search 在 LLM 中的使用：通过 Orchestrator 发送搜索类任务，检查是否调用了 google_search 工具。

用法（项目根目录）：
  python scripts/verify_google_search_in_llm.py [搜索关键词]
  例如：python scripts/verify_google_search_in_llm.py
        python scripts/verify_google_search_in_llm.py "Python 最新版本"

需配置 .env 中的 LLM（如 DEEPSEEK_API_KEY），会实际调用 LLM 和 DuckDuckGo。
"""
import os
import sys
import json
import asyncio

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from pathlib import Path
from shared.load_env import load_env
load_env(Path(_root))


def parse_chunks(chunks: list) -> dict:
    """解析流式 chunk，提取 __TOOL__ 和 __DEBUG__ 中的工具调用信息"""
    tools_called = []
    debug_tools = []
    content_parts = []
    for chunk in chunks:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        s = chunk.strip()
        if s.startswith("__TOOL__:"):
            try:
                data = json.loads(s[len("__TOOL__:"):])
                if data.get("type") == "tool":
                    tools_called.append({
                        "name": data.get("name"),
                        "success": data.get("success"),
                        "has_result": data.get("result") is not None,
                    })
            except json.JSONDecodeError:
                pass
        elif s.startswith("__DEBUG__:"):
            try:
                data = json.loads(s[len("__DEBUG__:"):])
                details = data.get("details") or {}
                if "tools" in details:
                    debug_tools.extend(details["tools"])
                if details.get("name"):
                    debug_tools.append(details["name"])
            except json.JSONDecodeError:
                pass
        elif s and not s.startswith("__") and not s.startswith("data:"):
            content_parts.append(s)
    return {
        "tools_called": tools_called,
        "debug_tools": debug_tools,
        "content_preview": "".join(content_parts)[:500] if content_parts else "",
    }


async def main():
    query = (sys.argv[1] if len(sys.argv) > 1 else "Python 最新版本").strip()
    task = f"搜索一下 {query}，简要告诉我结果。"

    print(f"验证 google_search 在 LLM 中的使用")
    print("-" * 50)
    print(f"任务: {task}")
    print()

    try:
        from backend.core.agent.orchestrator import Orchestrator
    except ImportError as e:
        print(f"错误: 无法导入 Orchestrator: {e}")
        sys.exit(1)

    orch = Orchestrator()
    # 使用 general_chat 以获取工具（含 google_search），否则会走 article_writing 等无工具分支
    session_id = orch.context_manager.create_session(metadata={"type": "general_chat"})

    print("正在调用 stream_process（会实际请求 LLM 和 DuckDuckGo）...")
    chunks = []
    async for chunk in orch.stream_process(
        task, context={"session_id": session_id, "context_type": "general_chat"}
    ):
        chunks.append(chunk)

    parsed = parse_chunks(chunks)

    # 检查是否调用了 google_search
    tool_names = [t["name"] for t in parsed["tools_called"]]
    debug_tool_names = parsed["debug_tools"]
    used_google_search = "google_search" in tool_names or "google_search" in debug_tool_names

    print()
    print("结果:")
    print(f"  工具调用: {tool_names or '(无)'}")
    if parsed["tools_called"]:
        for t in parsed["tools_called"]:
            status = "✅" if t["success"] else "❌"
            print(f"    - {t['name']}: {status} (有结果: {t['has_result']})")
    print()

    if used_google_search:
        print("✅ 验证通过: LLM 已调用 google_search 工具")
        if parsed["content_preview"]:
            print(f"   回复预览: {parsed['content_preview'][:200]}...")
    else:
        print("❌ 验证未通过: 未检测到 google_search 调用")
        print(f"   实际调用的工具: {tool_names or debug_tool_names or '无'}")
        if parsed["content_preview"]:
            print(f"   回复预览: {parsed['content_preview'][:300]}...")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
