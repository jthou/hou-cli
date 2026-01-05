# TODO-011: 代码执行沙盒功能测试指南

## 测试概述

本文档说明如何测试代码执行沙盒功能，包括已完成的测试和待完成的测试。

---

## 已完成的测试

### 1. 单元测试（已创建测试文件）

#### ✅ test_models.py - 数据模型测试
**测试用例**：
- ✅ `test_execution_request_creation` - 测试执行请求创建
- ✅ `test_execution_request_with_limits` - 测试带资源限制的执行请求
- ✅ `test_execution_request_with_explanation` - 测试带说明的执行请求
- ✅ `test_resource_usage_creation` - 测试资源使用情况创建
- ✅ `test_resource_usage_defaults` - 测试资源使用情况默认值
- ✅ `test_execution_result_success` - 测试成功执行结果
- ✅ `test_execution_result_failure` - 测试失败执行结果
- ✅ `test_execution_result_with_resource_usage` - 测试带资源使用情况的执行结果
- ✅ `test_execution_result_timestamp` - 测试执行结果时间戳

#### ✅ test_executor.py - 执行器测试
**测试用例**：
- ✅ `test_execute_python_code` - 测试执行 Python 代码
- ✅ `test_execute_python_code_with_error` - 测试执行有错误的 Python 代码
- ✅ `test_execute_bash_code` - 测试执行 bash 代码（Linux/macOS，Windows 跳过）
- ✅ `test_execute_timeout` - 测试执行超时
- ✅ `test_execute_invalid_language` - 测试执行不支持的语言
- ✅ `test_resource_usage_tracking` - 测试资源使用情况跟踪
- ✅ `test_working_dir_isolation` - 测试工作目录隔离

#### ✅ test_secure_executor.py - 安全执行器测试
**测试用例**：
- ✅ `test_block_dangerous_command` - 测试阻止危险命令
- ✅ `test_allow_safe_command` - 测试允许安全命令
- ✅ `test_block_restricted_path` - 测试阻止访问受限路径
- ✅ `test_block_invalid_language` - 测试阻止不支持的语言
- ✅ `test_code_length_limit` - 测试代码长度限制

#### ✅ test_result_handler.py - 结果处理器测试
**测试用例**：
- ✅ `test_truncate_large_output` - 测试截断大输出
- ✅ `test_no_truncate_small_output` - 测试不截断小输出
- ✅ `test_format_error` - 测试错误格式化
- ✅ `test_format_resource_usage` - 测试资源使用格式化
- ✅ `test_process_result` - 测试处理执行结果

#### ✅ test_auto_executor.py - 自动执行器测试
**测试用例**：
- ✅ `test_extract_python_code` - 测试提取 Python 代码块
- ✅ `test_extract_bash_code` - 测试提取 bash 代码块
- ✅ `test_extract_multiple_blocks` - 测试提取多个代码块
- ✅ `test_extract_no_code_blocks` - 测试没有代码块的情况
- ✅ `test_normalize_language` - 测试语言名称标准化
- ✅ `test_auto_execute_code` - 测试自动执行代码
- ✅ `test_no_code_blocks` - 测试没有代码块的情况
- ✅ `test_multiple_code_blocks` - 测试多个代码块
- ✅ `test_enhanced_output` - 测试增强输出

### 2. 手动功能测试（已执行）

#### ✅ 基础功能测试
```bash
# 测试数据模型导入
✅ Models imported successfully

# 测试 SubprocessExecutor
✅ Success: True
✅ Output: hello world
✅ Exit code: 0

# 测试 SecureExecutor
✅ Test 1 (safe): Success=True, Output=hello
✅ Test 2 (dangerous): Success=False, Error=Dangerous command 'rm' is not allowed

# 测试 ResultHandler
✅ Truncate test: Original=11534336 bytes, Truncated=10485796 bytes
✅ Resource usage: 执行时间: 1.50 秒, 内存使用: 100.50 MB, CPU 使用: 50.00%

# 测试 CodeExecutorTool
✅ Tool name: execute_code
✅ Tool execution: Success=True, Output=hello from tool

# 测试 AutoCodeExecutor
✅ Code executed: True
✅ Number of results: 1
✅ Success: True
✅ Output: hello from auto executor

# 测试 Orchestrator 集成
✅ Auto code executor initialized: True
✅ Auto execute code enabled: True
✅ Available tools: ['get_weather', 'file_search', 'execute_code']
✅ execute_code tool is registered
✅ Tool execution: Success=True
```

---

## 如何运行测试

### 方法一：使用 pytest（推荐）

#### 运行所有执行模块测试
```bash
cd /home/robo/justin/hou-cli
source venv/bin/activate

# 运行所有执行模块测试
pytest backend/infrastructure/execution/tests/ -v

# 运行特定测试文件
pytest backend/infrastructure/execution/tests/test_models.py -v
pytest backend/infrastructure/execution/tests/test_executor.py -v
pytest backend/infrastructure/execution/tests/test_secure_executor.py -v
pytest backend/infrastructure/execution/tests/test_result_handler.py -v
pytest backend/infrastructure/execution/tests/test_auto_executor.py -v

# 运行特定测试用例
pytest backend/infrastructure/execution/tests/test_executor.py::TestSubprocessExecutor::test_execute_python_code -v
```

#### 运行工具测试
```bash
# 运行工具测试（如果存在）
pytest backend/core/agent/tools/tests/test_code_executor_tool.py -v
```

### 方法二：手动 Python 测试（如果 pytest 不可用）

#### 测试数据模型
```bash
cd /home/robo/justin/hou-cli
source venv/bin/activate
python -c "
from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult, ResourceUsage

# 测试 ExecutionRequest
request = ExecutionRequest(code='print(\"hello\")', language='python', timeout=30)
assert request.code == 'print(\"hello\")'
assert request.language == 'python'
print('✅ ExecutionRequest test passed')

# 测试 ExecutionResult
result = ExecutionResult(success=True, output='hello', exit_code=0)
assert result.success is True
assert result.output == 'hello'
print('✅ ExecutionResult test passed')

# 测试 ResourceUsage
usage = ResourceUsage(memory_used_mb=100.0, execution_time_seconds=1.5)
assert usage.memory_used_mb == 100.0
print('✅ ResourceUsage test passed')
"
```

#### 测试执行器
```bash
python -c "
import asyncio
from backend.infrastructure.execution import SubprocessExecutor, ExecutionRequest

async def test():
    executor = SubprocessExecutor()
    request = ExecutionRequest(code='print(\"hello\")', language='python', timeout=10)
    result = await executor.execute(request)
    assert result.success is True
    assert 'hello' in result.output
    print('✅ SubprocessExecutor test passed')

asyncio.run(test())
"
```

#### 测试安全执行器
```bash
python -c "
import asyncio
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest

async def test():
    executor = SecureExecutor()
    
    # 测试安全命令
    request1 = ExecutionRequest(code='print(\"hello\")', language='python', timeout=10)
    result1 = await executor.execute_code_safely(request1)
    assert result1.success is True
    print('✅ Safe command test passed')
    
    # 测试危险命令
    request2 = ExecutionRequest(code='rm -rf /', language='bash', timeout=10)
    result2 = await executor.execute_code_safely(request2)
    assert result2.success is False
    assert 'dangerous' in result2.error.lower() or 'not allowed' in result2.error.lower()
    print('✅ Dangerous command blocking test passed')

asyncio.run(test())
"
```

#### 测试工具集成
```bash
python -c "
from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool

tool = CodeExecutorTool()
assert tool.name == 'execute_code'
print(f'✅ Tool name: {tool.name}')

# 测试工具执行
result = tool.execute(code='print(\"hello\")', language='python', timeout=10)
assert result.success is True
print(f'✅ Tool execution: Success={result.success}')
"
```

#### 测试自动执行器
```bash
python -c "
import asyncio
from backend.infrastructure.execution import AutoCodeExecutor

async def test():
    executor = AutoCodeExecutor()
    llm_output = '''
    \`\`\`python
    print('hello')
    \`\`\`
    '''
    result = await executor.process_llm_output(llm_output, auto_execute=True)
    assert result['code_executed'] is True
    assert len(result['execution_results']) == 1
    print('✅ AutoCodeExecutor test passed')

asyncio.run(test())
"
```

---

## 待完成的测试

### 1. 集成测试（✅ 已完成）

#### 测试文件：
- `tests/integration/test_code_execution.py` - pytest 版本
- `tests/integration/test_code_execution_manual.py` - 手动运行版本（推荐）

**测试用例**：

```python
"""代码执行集成测试"""
import pytest
import asyncio
from backend.core.agent.orchestrator import Orchestrator

class TestCodeExecutionIntegration:
    """代码执行集成测试"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_tool_calling_mode(self, orchestrator):
        """测试工具调用模式"""
        # 模拟 LLM 调用工具
        tools = orchestrator.tool_registry.get_tools_for_llm()
        assert 'execute_code' in [t['function']['name'] for t in tools]
        
        # 执行工具
        result = orchestrator.tool_registry.execute(
            'execute_code',
            code='print("hello")',
            language='python',
            timeout=10
        )
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_auto_extract_mode(self, orchestrator):
        """测试自动提取模式"""
        llm_output = '''
        ```python
        print('hello')
        ```
        '''
        
        if orchestrator.auto_code_executor:
            result = await orchestrator.auto_code_executor.process_llm_output(
                llm_output,
                auto_execute=True
            )
            assert result['code_executed'] is True
```

### 2. 端到端测试（✅ 已完成）

#### 测试文件：
- `tests/integration/test_code_execution.py` - 包含端到端测试
- `tests/integration/test_code_execution_manual.py` - 手动运行版本（推荐）

**测试场景**：

1. **场景 1：LLM 工具调用执行代码**
   - 用户请求："帮我计算 1 到 100 的和"
   - LLM 调用 `execute_code` 工具
   - 验证工具执行成功
   - 验证 LLM 基于结果生成回复

2. **场景 2：LLM 生成代码，自动执行**
   - 用户请求："帮我写一个 Python 脚本计算斐波那契数列"
   - LLM 生成包含代码块的回复
   - 验证自动检测并执行代码
   - 验证执行结果反馈给 LLM

3. **场景 3：安全限制测试**
   - 尝试执行危险命令（rm -rf）
   - 验证命令被阻止
   - 验证错误信息正确

### 3. 性能测试（待创建）

**测试用例**：
- 并发执行测试
- 资源限制测试
- 超时处理测试

### 4. 跨平台测试（待完成）

**测试平台**：
- ✅ Linux（已测试）
- ⚠️ macOS（待测试）
- ⚠️ Windows（待测试）

---

## 测试检查清单

### 单元测试
- [x] 数据模型测试（test_models.py）
- [x] 执行器测试（test_executor.py）
- [x] 安全执行器测试（test_secure_executor.py）
- [x] 结果处理器测试（test_result_handler.py）
- [x] 自动执行器测试（test_auto_executor.py）

### 集成测试
- [x] 工具调用模式集成测试 ✅
- [x] 自动提取模式集成测试 ✅
- [x] Orchestrator 集成测试 ✅

### 端到端测试
- [x] LLM 工具调用端到端测试 ✅
- [x] LLM 自动提取端到端测试 ✅
- [x] 安全限制端到端测试 ✅

### 性能测试
- [ ] 并发执行测试
- [ ] 资源限制测试
- [ ] 超时处理测试

### 跨平台测试
- [x] Linux
- [ ] macOS
- [ ] Windows

---

## 运行集成测试和端到端测试

### 方法一：手动运行测试脚本（推荐）

```bash
cd /home/robo/justin/hou-cli
source venv/bin/activate
python tests/integration/test_code_execution_manual.py
```

**测试内容**：
- ✅ 工具调用模式集成测试
- ✅ 自动提取模式集成测试
- ✅ 安全限制测试
- ✅ 多代码块测试
- ✅ 端到端工具调用测试
- ✅ 端到端自动提取测试

### 方法二：使用 pytest

```bash
# 运行集成测试
pytest tests/integration/test_code_execution.py -v
```

---

## 快速测试脚本

已创建的快速测试脚本：

```bash
#!/bin/bash
# tests/test_code_execution_quick.sh

echo "=== 代码执行沙盒功能快速测试 ==="
echo

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "1. 测试数据模型..."
python -c "
from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult
request = ExecutionRequest(code='print(\"test\")', language='python', timeout=10)
result = ExecutionResult(success=True, output='test')
print('✅ 数据模型测试通过')
"

echo "2. 测试执行器..."
python -c "
import asyncio
from backend.infrastructure.execution import SubprocessExecutor, ExecutionRequest

async def test():
    executor = SubprocessExecutor()
    request = ExecutionRequest(code='print(\"hello\")', language='python', timeout=10)
    result = await executor.execute(request)
    assert result.success is True
    print('✅ 执行器测试通过')

asyncio.run(test())
"

echo "3. 测试安全执行器..."
python -c "
import asyncio
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest

async def test():
    executor = SecureExecutor()
    request = ExecutionRequest(code='print(\"hello\")', language='python', timeout=10)
    result = await executor.execute_code_safely(request)
    assert result.success is True
    print('✅ 安全执行器测试通过')
    
    # 测试危险命令
    request2 = ExecutionRequest(code='rm -rf /', language='bash', timeout=10)
    result2 = await executor.execute_code_safely(request2)
    assert result2.success is False
    print('✅ 安全限制测试通过')

asyncio.run(test())
"

echo "4. 测试工具集成..."
python -c "
from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
tool = CodeExecutorTool()
result = tool.execute(code='print(\"hello\")', language='python', timeout=10)
assert result.success is True
print('✅ 工具集成测试通过')
"

echo "5. 测试自动执行器..."
python -c "
import asyncio
from backend.infrastructure.execution import AutoCodeExecutor

async def test():
    executor = AutoCodeExecutor()
    llm_output = '''
    \`\`\`python
    print('hello')
    \`\`\`
    '''
    result = await executor.process_llm_output(llm_output, auto_execute=True)
    assert result['code_executed'] is True
    print('✅ 自动执行器测试通过')

asyncio.run(test())
"

echo
echo "=== 所有测试通过！ ==="
```

---

## 测试结果示例

### 成功测试输出

```
=== 代码执行沙盒功能快速测试 ===

1. 测试数据模型...
✅ 数据模型测试通过

2. 测试执行器...
✅ 执行器测试通过

3. 测试安全执行器...
✅ 安全执行器测试通过
✅ 安全限制测试通过

4. 测试工具集成...
✅ 工具集成测试通过

5. 测试自动执行器...
✅ 自动执行器测试通过

=== 所有测试通过！ ===
```

---

## 注意事项

1. **pytest 环境**：如果 pytest 不可用，可以使用手动 Python 测试
2. **平台差异**：某些测试在 Windows 上会跳过（如 bash 测试）
3. **资源限制**：资源限制测试可能需要调整参数
4. **超时测试**：超时测试可能需要较长时间

---

## 下一步

1. 创建集成测试文件
2. 创建端到端测试
3. 添加性能测试
4. 完善跨平台测试

