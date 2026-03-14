#!/usr/bin/env python3
"""
简单的测试示例 - 演示如何测试工具

运行方法：
    python3 backend/core/agent/tools/tests/test_simple_example.py
    或
    pytest backend/core/agent/tools/tests/test_simple_example.py -v
"""
import os
import sys
from pathlib import Path

# 添加项目路径
# test_simple_example.py 在 backend/core/agent/tools/tests/
# 需要向上5级到项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

os.chdir(project_root)

from shared.load_env import load_env
load_env(project_root)

print("=" * 60)
print("Tools 测试示例")
print("=" * 60)
print()


def test_google_search_tool():
    """测试 GoogleSearchTool"""
    print("测试 GoogleSearchTool...")
    try:
        from backend.core.agent.tools.builtin.google_search_tool import (
            GoogleSearchTool
        )

        tool = GoogleSearchTool()
        print(f"  ✅ 工具初始化成功: {tool.name}")
        print(f"  ✅ 参数数量: {len(tool.parameters)}")

        # 测试参数验证
        result = tool.execute()
        if not result.success:
            print(f"  ✅ 参数验证正常: {result.error[:50]}...")
        else:
            print("  ⚠️  参数验证异常")

        # 检查 API Key
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        if api_key and engine_id:
            print("  ✅ API Key 已配置，可以运行集成测试")
        else:
            print("  ⏭️  API Key 未配置，集成测试将被跳过")
    except Exception as e:
        print(f"  ❌ 错误: {e}")


def test_wikipedia_tool():
    """测试 WikipediaTool"""
    print("\n测试 WikipediaTool...")
    try:
        from backend.core.agent.tools.builtin.wikipedia_tool import (
            WikipediaTool
        )

        tool = WikipediaTool()
        print(f"  ✅ 工具初始化成功: {tool.name}")
        print(f"  ✅ 参数数量: {len(tool.parameters)}")

        # 测试参数验证
        result = tool.execute(action="search")
        if not result.success:
            print(f"  ✅ 参数验证正常: {result.error[:50]}...")
        else:
            print("  ⚠️  参数验证异常")

        # Wikipedia 不需要 API Key
        print("  ✅ 不需要 API Key，可以直接测试")
    except Exception as e:
        print(f"  ❌ 错误: {e}")


def test_file_search_tool():
    """测试 FileSearchTool"""
    print("\n测试 FileSearchTool...")
    try:
        from backend.core.agent.tools.builtin.file_search_tool import (
            FileSearchTool
        )

        tool = FileSearchTool()
        print(f"  ✅ 工具初始化成功: {tool.name}")
        print(f"  ✅ 参数数量: {len(tool.parameters)}")

        # 测试参数验证
        result = tool.execute()
        if not result.success:
            print(f"  ✅ 参数验证正常: {result.error[:50]}...")
        else:
            print("  ⚠️  参数验证异常")

        # FileSearchTool 不需要 API Key
        print("  ✅ 不需要 API Key，可以直接测试")
    except Exception as e:
        print(f"  ❌ 错误: {e}")


if __name__ == "__main__":
    print("开始测试...\n")

    test_google_search_tool()
    test_wikipedia_tool()
    test_file_search_tool()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("下一步")
    print("=" * 60)
    print("1. 运行完整测试: pytest backend/core/agent/tools/tests/ -v")
    print("2. 运行特定工具: pytest backend/core/agent/tools/tests/test_google_search_tool.py -v")
    print("3. 查看测试指南: docs/how-to-test-tools.md")

