"""代码执行集成测试（手动运行版本）"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.tools.base import ToolResult


async def test_tool_calling_mode():
    """测试工具调用模式"""
    print("=== 测试工具调用模式 ===")
    
    orchestrator = Orchestrator()
    
    # 验证工具已注册
    tools = orchestrator.tool_registry.get_tools_for_llm()
    tool_names = [t['function']['name'] for t in tools]
    assert 'exec_py' in tool_names, "exec_py 工具未注册"
    print("✅ 工具注册验证通过")
    
    # 执行工具
    result = orchestrator.tool_registry.execute(
        'exec_py',
        code='print("hello from tool calling")',
        language='python',
        timeout=10
    )
    
    assert result.success is True
    assert 'hello from tool calling' in result.data.get('output', '')
    print(f"✅ 工具执行成功: {result.data.get('output', '').strip()}")
    print()


async def test_auto_extract_mode():
    """测试自动提取模式"""
    print("=== 测试自动提取模式 ===")
    
    orchestrator = Orchestrator()
    
    if not orchestrator.auto_code_executor:
        print("⚠️  自动代码执行器未初始化，跳过测试")
        return
    
    # 模拟 LLM 输出（包含代码块）
    llm_output = """
    可以使用以下 Python 代码来计算 1 到 100 的和：
    
    ```python
    print(sum(range(1, 101)))
    ```
    """
    
    # 测试自动提取和执行
    result = await orchestrator.auto_code_executor.process_llm_output(
        llm_output,
        auto_execute=True,
        require_confirmation=False
    )
    
    assert result['code_executed'] is True
    assert len(result['execution_results']) == 1
    exec_result = result['execution_results'][0]['result']
    assert exec_result['success'] is True
    assert '5050' in exec_result['output']  # 1+2+...+100 = 5050
    print(f"✅ 自动提取执行成功: {exec_result['output'].strip()}")
    print()


async def test_security_blocking():
    """测试安全限制"""
    print("=== 测试安全限制 ===")
    
    orchestrator = Orchestrator()
    
    # 测试工具调用模式下的安全限制
    result = orchestrator.tool_registry.execute(
        'exec_shell',
        code='rm -rf /',
        timeout=10
    )
    
    assert result.success is False
    assert 'dangerous' in result.error.lower() or 'not allowed' in result.error.lower()
    print(f"✅ 危险命令被阻止: {result.error[:60]}...")
    print()


async def test_multiple_code_blocks():
    """测试多个代码块"""
    print("=== 测试多个代码块 ===")
    
    orchestrator = Orchestrator()
    
    if not orchestrator.auto_code_executor:
        print("⚠️  自动代码执行器未初始化，跳过测试")
        return
    
    llm_output = """
    ```python
    print('first')
    ```
    
    ```python
    print('second')
    ```
    """
    
    result = await orchestrator.auto_code_executor.process_llm_output(
        llm_output,
        auto_execute=True
    )
    
    assert result['code_executed'] is True
    assert len(result['execution_results']) == 2
    print(f"✅ 第一个代码块: {result['execution_results'][0]['result']['output'].strip()}")
    print(f"✅ 第二个代码块: {result['execution_results'][1]['result']['output'].strip()}")
    print()


async def test_e2e_tool_calling():
    """端到端测试：工具调用模式"""
    print("=== 端到端测试：工具调用模式 ===")
    
    orchestrator = Orchestrator()
    
    # 模拟工具调用流程
    # 1. LLM 决定调用工具
    result = orchestrator.tool_registry.execute(
        'exec_py',
        code='result = sum(range(1, 11)); print(result)',
        timeout=10
    )
    
    assert result.success is True
    output = result.data.get('output', '').strip()
    assert '55' in output  # 1+2+...+10 = 55
    
    # 2. 模拟 LLM 基于结果生成回复
    print(f"✅ 代码执行成功，输出: {output}")
    print(f"✅ LLM 可以基于此结果生成回复")
    print()


async def test_e2e_auto_extract():
    """端到端测试：自动提取模式"""
    print("=== 端到端测试：自动提取模式 ===")
    
    orchestrator = Orchestrator()
    
    if not orchestrator.auto_code_executor:
        print("⚠️  自动代码执行器未初始化，跳过测试")
        return
    
    # 模拟 LLM 生成包含代码块的回复
    llm_output = """
    可以使用以下代码计算斐波那契数列的前 10 项：
    
    ```python
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        print(a)
        a, b = b, a+b
fib(10)
    ```
    """
    
    # 自动提取并执行
    result = await orchestrator.auto_code_executor.process_llm_output(
        llm_output,
        auto_execute=True
    )
    
    assert result['code_executed'] is True
    exec_result = result['execution_results'][0]['result']
    assert exec_result['success'] is True
    print(f"✅ 代码自动执行成功")
    print(f"✅ 执行结果已包含在增强输出中")
    print(f"✅ LLM 可以基于执行结果生成最终回复")
    print()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("代码执行集成测试和端到端测试")
    print("=" * 60)
    print()
    
    try:
        await test_tool_calling_mode()
        await test_auto_extract_mode()
        await test_security_blocking()
        await test_multiple_code_blocks()
        await test_e2e_tool_calling()
        await test_e2e_auto_extract()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

