#!/usr/bin/env python3
"""
后端代码助手测试：用用户的实际问题验证是否调用 execute_code/exec 工具。
不依赖前端，直接调用 orchestrator.stream_process。
"""
import asyncio
import json
import sys
from pathlib import Path

# 确保项目根目录在 path 中
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main():
    from backend.core.agent.orchestrator import Orchestrator

    # 用户的实际问题（简化版）
    task = """写一段shell，执行看看

一、脚本功能
脚本用于检查当前目录下所有文件数量。执行后输出文件总数。

二、代码示例
#!/bin/bash
count=$(ls -l | grep -v '^d' | wc -l)
echo "当前目录下文件数量为: $count"

三、使用说明
将代码保存为 count_files.sh
执行 chmod +x count_files.sh
运行 ./count_files.sh 查看结果

四、注意事项
此脚本仅统计普通文件，不包含目录。如需统计目录，可修改 grep -v '^d' 部分。

写一段python，执行看看

print("Hello, world!")
这段代码在 Python 3 环境中可直接运行，输出：
Hello, world!
"""

    print("=" * 60)
    print("代码助手后端测试")
    print("=" * 60)
    print("任务预览:", task[:200].replace("\n", " ") + "...")
    print()

    o = Orchestrator()
    ctx = {"context_type": "code_assistant"}

    tool_chunks = []
    content_chunks = []
    full_output = []

    print("开始 stream_process（context_type=code_assistant）...")
    async for chunk in o.stream_process(task, context=ctx):
        full_output.append(chunk)
        if chunk.startswith("__TOOL__:"):
            try:
                data = json.loads(chunk[9:].strip())
                tool_chunks.append(data)
                name = data.get("name", "?")
                success = data.get("success", False)
                print(f"  [TOOL] {name} success={success}")
            except Exception:
                pass
        elif not chunk.startswith("__DEBUG__:") and not chunk.startswith("__STATUS__:"):
            content_chunks.append(chunk)

    content = "".join(content_chunks)
    print()
    print("=" * 60)
    print("结果")
    print("=" * 60)
    print(f"工具调用次数: {len(tool_chunks)}")
    if tool_chunks:
        for i, tc in enumerate(tool_chunks, 1):
            print(f"  {i}. {tc.get('name')} success={tc.get('success')}")
            if tc.get("result"):
                out = tc["result"].get("output", "")
                if out:
                    print(f"     输出: {out[:100]}..." if len(out) > 100 else f"     输出: {out}")
    else:
        print("  ⚠️ 未检测到工具调用")

    print()
    print("文本内容长度:", len(content))
    if content:
        print("内容预览:", content[:300].replace("\n", " ") + "...")
    print()

    if tool_chunks:
        print("✅ 后端正常：代码助手调用了执行工具")
        return 0
    else:
        print("❌ 后端异常：未调用 execute_code/exec，仅返回文本")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
