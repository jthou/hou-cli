# TODO-011: 代码执行沙盒功能实现

## 任务概述

实现大模型代码执行沙盒功能，支持在安全的隔离环境中执行脚本代码（Python、bash、zsh、PowerShell、batch），提供资源限制、命令过滤、审计日志等安全机制。

**优先级**: P0（高优先级）  
**预计工时**: 5-7 天  
**创建时间**: 2025-01-XX  
**状态**: ⏳ 待开始

**关联文档**:
- [设计文档](../../docs/design/07-代码执行沙盒方案设计.md)

---

## TDD 原则说明

**TDD (Test-Driven Development) 流程**:
1. 🔴 **Red**: 先写测试，测试失败（当前阶段）
2. 🟢 **Green**: 实现功能，让测试通过
3. 🔵 **Refactor**: 重构代码，保持测试通过

**关键原则**:
- 测试必须先失败，然后才能通过
- 如果测试一开始就通过，说明测试无效
- 每个功能都要先写测试，再实现

**测试框架**: pytest

---

## 需求分析

### 用户场景

1. **LLM 工具调用执行代码**
   - LLM 调用 `execute_code` 工具执行 Python 脚本
   - 系统：在沙盒中安全执行，返回结果

2. **自动提取并执行代码**
   - LLM 生成包含代码块的回复
   - 系统：自动检测代码块，在沙盒中执行

3. **安全限制**
   - 禁止执行危险命令（rm -rf、sudo 等）
   - 限制资源使用（CPU、内存、时间）
   - 禁止访问敏感目录

---

## 任务分解

### 阶段 1: 基础执行器实现（P0）- 预计 1.5 天

#### 任务 1.1: 创建目录结构和数据模型（TDD）

**文件**: `backend/infrastructure/execution/`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/infrastructure/execution/tests/test_models.py
   import pytest
   from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult
   
   def test_execution_request_creation():
       """测试执行请求创建"""
       request = ExecutionRequest(
           code="print('hello')",
           language="python",
           timeout=30
       )
       assert request.code == "print('hello')"
       assert request.language == "python"
       assert request.timeout == 30
   ```
2. 🔴 **验证测试失败**: `pytest backend/infrastructure/execution/tests/test_models.py -v`
3. 🟢 **Green**: 实现数据模型
4. 🟢 **验证测试通过**: `pytest backend/infrastructure/execution/tests/test_models.py -v`

**实现步骤**:
1. 创建目录结构
   ```
   backend/infrastructure/execution/
   ├── __init__.py
   ├── models.py              # 数据模型
   ├── executor.py            # 执行器
   ├── secure_executor.py     # 安全包装器
   ├── result_handler.py      # 结果处理器
   └── tests/
       ├── __init__.py
       ├── test_models.py
       ├── test_executor.py
       ├── test_secure_executor.py
       └── test_result_handler.py
   ```
2. 定义数据模型（`models.py`）
   - `ExecutionRequest`: 执行请求
   - `ExecutionResult`: 执行结果
   - `ResourceUsage`: 资源使用情况

**验收标准**:
- [ ] 目录结构完整
- [ ] 数据模型定义完整
- [ ] 测试通过（TDD 验证）

---

#### 任务 1.2: 实现 SubprocessExecutor 基础功能（TDD）

**文件**: `backend/infrastructure/execution/executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/infrastructure/execution/tests/test_executor.py
   import pytest
   import asyncio
   from backend.infrastructure.execution.executor import SubprocessExecutor
   from backend.infrastructure.execution.models import ExecutionRequest
   
   @pytest.mark.asyncio
   async def test_execute_python_code():
       """测试执行 Python 代码"""
       executor = SubprocessExecutor()
       request = ExecutionRequest(
           code="print('hello')",
           language="python",
           timeout=10
       )
       result = await executor.execute(request)
       
       assert result.success is True
       assert "hello" in result.output
       assert result.exit_code == 0
   ```
2. 🔴 **验证测试失败**: `pytest backend/infrastructure/execution/tests/test_executor.py::test_execute_python_code -v`
3. 🟢 **Green**: 实现 SubprocessExecutor
4. 🟢 **验证测试通过**: `pytest backend/infrastructure/execution/tests/test_executor.py::test_execute_python_code -v`

**实现步骤**:
1. 实现 `SubprocessExecutor` 类
2. 实现 `execute()` 方法
   - 创建临时工作目录
   - 根据语言选择执行器
   - 使用 `asyncio.create_subprocess_exec` 执行
   - 捕获输出和错误
3. 实现临时目录管理
   - `_create_work_dir()`: 创建临时目录
   - `_cleanup_work_dir()`: 清理临时目录

**验收标准**:
- [ ] 可以执行 Python 代码
- [ ] 可以执行 bash 代码（Linux/macOS）
- [ ] 临时目录正确创建和清理
- [ ] 测试通过（TDD 验证）

---

#### 任务 1.3: 实现资源限制（TDD）

**文件**: `backend/infrastructure/execution/executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   @pytest.mark.asyncio
   async def test_memory_limit():
       """测试内存限制"""
       executor = SubprocessExecutor()
       request = ExecutionRequest(
           code="import sys; data = [0] * 100000000",  # 尝试分配大量内存
           language="python",
           timeout=10,
           memory_limit_mb=100  # 限制 100MB
       )
       result = await executor.execute(request)
       
       # 应该因为内存限制而失败或超时
       assert result.success is False or result.exit_code != 0
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现资源限制
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现 `_set_resource_limits()` 方法（Linux/macOS）
   - 使用 `resource` 模块设置内存限制
   - 使用 `resource` 模块设置 CPU 限制
2. 实现 Windows 平台处理
   - 使用超时机制（`asyncio.wait_for`）
   - 使用 `psutil` 监控资源使用
3. 实现资源监控
   - 使用 `psutil` 监控内存和 CPU 使用

**验收标准**:
- [ ] Linux/macOS 可以限制内存和 CPU
- [ ] Windows 使用超时机制
- [ ] 资源使用情况正确记录
- [ ] 测试通过（TDD 验证）

---

### 阶段 2: 安全包装器实现（P0）- 预计 1.5 天

#### 任务 2.1: 实现命令过滤（TDD）

**文件**: `backend/infrastructure/execution/secure_executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/infrastructure/execution/tests/test_secure_executor.py
   import pytest
   from backend.infrastructure.execution.secure_executor import SecureExecutor
   from backend.infrastructure.execution.models import ExecutionRequest
   
   @pytest.mark.asyncio
   async def test_block_dangerous_command():
       """测试阻止危险命令"""
       executor = SecureExecutor()
       request = ExecutionRequest(
           code="rm -rf /",  # 危险命令
           language="bash",
           timeout=10
       )
       result = await executor.execute_code_safely(request)
       
       assert result.success is False
       assert "not allowed" in result.error.lower() or "blocked" in result.error.lower()
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现命令过滤
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现 `SecureExecutor` 类
2. 实现命令白名单/黑名单检查
   - `_check_command_whitelist()`: 检查命令是否在白名单
   - `_check_command_blacklist()`: 检查命令是否在黑名单
3. 实现路径限制检查
   - `_check_restricted_paths()`: 检查是否访问受限路径
4. 实现语言验证
   - `_validate_language()`: 验证语言是否允许

**验收标准**:
- [ ] 危险命令被阻止（rm、sudo、chmod 等）
- [ ] 白名单命令允许执行
- [ ] 受限路径访问被阻止
- [ ] 测试通过（TDD 验证）

---

#### 任务 2.2: 实现输入验证和审计日志（TDD）

**文件**: `backend/infrastructure/execution/secure_executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   @pytest.mark.asyncio
   async def test_code_length_limit():
       """测试代码长度限制"""
       executor = SecureExecutor()
       long_code = "print('hello')" * 10000  # 超长代码
       request = ExecutionRequest(
           code=long_code,
           language="python",
           timeout=10
       )
       result = await executor.execute_code_safely(request)
       
       assert result.success is False
       assert "too long" in result.error.lower() or "limit" in result.error.lower()
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现输入验证
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现输入验证
   - 代码长度限制（10KB）
   - 参数验证
2. 实现审计日志
   - 记录所有执行请求
   - 记录执行结果
   - 记录安全事件（拒绝的操作）

**验收标准**:
- [ ] 超长代码被拒绝
- [ ] 审计日志正确记录
- [ ] 安全事件被记录
- [ ] 测试通过（TDD 验证）

---

### 阶段 3: 结果处理器实现（P0）- 预计 0.5 天

#### 任务 3.1: 实现结果处理（TDD）

**文件**: `backend/infrastructure/execution/result_handler.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/infrastructure/execution/tests/test_result_handler.py
   import pytest
   from backend.infrastructure.execution.result_handler import ResultHandler
   
   def test_truncate_large_output():
       """测试截断大输出"""
       handler = ResultHandler()
       large_output = "x" * (11 * 1024 * 1024)  # 11MB
       truncated = handler.truncate_output(large_output)
       
       assert len(truncated.encode('utf-8')) <= 10 * 1024 * 1024  # 10MB
       assert "... (输出已截断" in truncated
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现结果处理
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现 `ResultHandler` 类
2. 实现输出截断
   - `truncate_output()`: 截断超过 10MB 的输出
3. 实现错误格式化
   - `format_error()`: 格式化错误信息
4. 实现资源使用统计
   - `format_resource_usage()`: 格式化资源使用情况

**验收标准**:
- [ ] 大输出被正确截断
- [ ] 错误信息格式化正确
- [ ] 资源使用统计正确
- [ ] 测试通过（TDD 验证）

---

### 阶段 4: 工具集成（P0）- 预计 1 天

#### 任务 4.1: 实现 CodeExecutorTool（TDD）

**文件**: `backend/core/agent/tools/builtin/code_executor_tool.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/core/agent/tools/tests/test_code_executor_tool.py
   import pytest
   from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
   
   def test_tool_definition():
       """测试工具定义"""
       tool = CodeExecutorTool()
       assert tool.name == "execute_code"
       assert "python" in tool.description.lower()
       
       tool_dict = tool.to_dict()
       assert tool_dict["type"] == "function"
       assert tool_dict["function"]["name"] == "execute_code"
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现工具
4. 🟢 **验证测试通过**

**实现步骤**:
1. 创建 `CodeExecutorTool` 类，继承 `Tool`
2. 实现 `execute()` 方法
   - 调用 `SecureExecutor.execute_code_safely()`
   - 返回 `ToolResult`
3. 定义工具参数
   - `code`: 代码内容
   - `language`: 语言类型
   - `timeout`: 超时时间
   - `explanation`: 说明（可选）

**验收标准**:
- [ ] 工具定义正确
- [ ] 可以正确执行代码
- [ ] 返回格式符合 ToolResult
- [ ] 测试通过（TDD 验证）

---

#### 任务 4.2: 集成到 Orchestrator

**文件**: `backend/core/agent/orchestrator.py`

**实现步骤**:
1. 在 `_register_tools()` 中注册 `CodeExecutorTool`
2. 确保工具列表正确传递给 LLM

**验收标准**:
- [ ] 工具正确注册
- [ ] LLM 可以调用工具
- [ ] 工具执行结果正确返回

---

### 阶段 5: 自动提取执行器实现（P1）- 预计 1 天

#### 任务 5.1: 实现代码提取器（TDD）

**文件**: `backend/infrastructure/execution/auto_executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   # backend/infrastructure/execution/tests/test_auto_executor.py
   import pytest
   from backend.infrastructure.execution.auto_executor import CodeExtractor
   
   def test_extract_python_code():
       """测试提取 Python 代码块"""
       extractor = CodeExtractor()
       output = """
       可以使用以下代码：
       ```python
       print('hello')
       ```
       """
       blocks = extractor.extract_code_blocks(output)
       
       assert len(blocks) == 1
       assert blocks[0]["language"] == "python"
       assert "print('hello')" in blocks[0]["code"]
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现代码提取
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现 `CodeExtractor` 类
2. 实现 `extract_code_blocks()` 方法
   - 使用正则表达式提取代码块
   - 支持多种代码块格式（```python、```bash 等）
3. 实现代码清理
   - `clean_command()`: 清理代码（去除注释等）

**验收标准**:
- [ ] 可以提取 Python 代码块
- [ ] 可以提取 bash 代码块
- [ ] 可以提取 PowerShell 代码块
- [ ] 代码清理正确
- [ ] 测试通过（TDD 验证）

---

#### 任务 5.2: 实现自动执行器（TDD）

**文件**: `backend/infrastructure/execution/auto_executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   @pytest.mark.asyncio
   async def test_auto_execute_code():
       """测试自动执行代码"""
       executor = AutoCodeExecutor()
       llm_output = """
       可以使用以下代码：
       ```python
       print('hello')
       ```
       """
       result = await executor.process_llm_output(llm_output, auto_execute=True)
       
       assert result["code_executed"] is True
       assert len(result["execution_results"]) == 1
       assert result["execution_results"][0]["result"]["success"] is True
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现自动执行
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现 `AutoCodeExecutor` 类
2. 实现 `process_llm_output()` 方法
   - 提取代码块
   - 执行代码（调用 SecureExecutor）
   - 构建增强的输出
3. 实现结果反馈构建
   - `_build_enhanced_output()`: 构建包含执行结果的输出

**验收标准**:
- [ ] 可以自动检测并执行代码
- [ ] 执行结果正确反馈
- [ ] 测试通过（TDD 验证）

---

#### 任务 5.3: 集成到 Orchestrator

**文件**: `backend/core/agent/orchestrator.py`

**实现步骤**:
1. 在 `__init__()` 中初始化 `AutoCodeExecutor`
2. 在 `process_dynamic()` 中集成自动提取逻辑
3. 实现配置项（是否启用自动提取）

**验收标准**:
- [ ] 自动提取功能正确集成
- [ ] 配置项生效
- [ ] 可以正确反馈执行结果给 LLM

---

### 阶段 6: 跨平台支持（P1）- 预计 1 天

#### 任务 6.1: 实现平台检测和语言映射（TDD）

**文件**: `backend/infrastructure/execution/executor.py`

**TDD 步骤**:
1. 🔴 **Red**: 编写测试
   ```python
   import pytest
   import platform
   from backend.infrastructure.execution.executor import SubprocessExecutor
   
   def test_platform_detection():
       """测试平台检测"""
       executor = SubprocessExecutor()
       current_platform = executor._detect_platform()
       
       assert current_platform in ["linux", "darwin", "windows"]
       assert current_platform == platform.system().lower()
   ```
2. 🔴 **验证测试失败**
3. 🟢 **Green**: 实现平台检测
4. 🟢 **验证测试通过**

**实现步骤**:
1. 实现平台检测
   - `_detect_platform()`: 检测当前平台
2. 实现语言映射表
   - `LANGUAGE_MAPPING`: 定义各平台支持的语言和执行器
3. 实现执行器选择
   - `_get_executor_command()`: 根据语言和平台选择执行器

**验收标准**:
- [ ] 平台检测正确
- [ ] 语言映射正确
- [ ] 执行器选择正确
- [ ] 测试通过（TDD 验证）

---

#### 任务 6.2: 实现 Windows 平台特殊处理

**文件**: `backend/infrastructure/execution/executor.py`

**实现步骤**:
1. 实现 Windows 资源限制（简化版）
   - 主要依赖超时机制
   - 使用 `psutil` 监控资源
2. 实现 Windows 命令执行
   - PowerShell 执行
   - Batch 执行

**验收标准**:
- [ ] Windows 平台可以执行 PowerShell
- [ ] Windows 平台可以执行 Batch
- [ ] 超时机制正常工作

---

### 阶段 7: 集成测试和文档（P1）- 预计 0.5 天

#### 任务 7.1: 编写集成测试

**文件**: `tests/integration/test_code_execution.py`

**实现步骤**:
1. 编写端到端测试
   - 测试工具调用模式
   - 测试自动提取模式
2. 编写性能测试
   - 测试并发执行
   - 测试资源限制

**验收标准**:
- [ ] 端到端测试通过
- [ ] 性能测试通过

---

#### 任务 7.2: 更新文档

**文件**: `docs/`

**实现步骤**:
1. 更新 README（如果需要）
2. 添加使用示例
3. 添加配置说明

**验收标准**:
- [ ] 文档完整
- [ ] 示例清晰

---

## TDD 验证检查清单

### 每个任务阶段

- [ ] **Red 阶段**: 测试必须失败
  - 运行测试 → 确认失败
  - 如果测试一开始就通过，说明测试无效

- [ ] **Green 阶段**: 实现最小功能
  - 实现能让测试通过的最小代码
  - 运行测试 → 确认通过

- [ ] **Refactor 阶段**: 重构代码
  - 优化代码结构
  - 运行测试 → 确认仍然通过

### 测试有效性验证

**验证测试是否有效的方法**:

1. **测试必须先失败**:
   ```bash
   # 编写测试后，先运行（应该失败）
   pytest backend/infrastructure/execution/tests/test_models.py -v
   # 预期: FAILED（因为功能未实现）
   ```

2. **实现功能后必须通过**:
   ```bash
   # 实现功能后，运行测试（应该通过）
   pytest backend/infrastructure/execution/tests/test_models.py -v
   # 预期: PASSED
   ```

3. **如果测试一开始就通过，说明测试无效**:
   - 检查测试是否真的在测试功能
   - 检查测试是否使用了 Mock 而不是真实实现

---

## 运行测试命令

### 运行单个测试文件

```bash
# 运行数据模型测试
pytest backend/infrastructure/execution/tests/test_models.py -v

# 运行执行器测试
pytest backend/infrastructure/execution/tests/test_executor.py -v

# 运行安全执行器测试
pytest backend/infrastructure/execution/tests/test_secure_executor.py -v

# 运行结果处理器测试
pytest backend/infrastructure/execution/tests/test_result_handler.py -v

# 运行工具测试
pytest backend/core/agent/tools/tests/test_code_executor_tool.py -v

# 运行自动执行器测试
pytest backend/infrastructure/execution/tests/test_auto_executor.py -v
```

### 运行所有执行模块测试

```bash
# 运行所有执行模块测试
pytest backend/infrastructure/execution/ -v

# 运行所有工具测试
pytest backend/core/agent/tools/tests/ -v

# 运行集成测试
pytest tests/integration/test_code_execution.py -v
```

### 运行特定测试用例

```bash
# 运行特定测试用例
pytest backend/infrastructure/execution/tests/test_executor.py::test_execute_python_code -v

# 运行带标记的测试
pytest -m "not slow" backend/infrastructure/execution/tests/ -v
```

---

## 注意事项

1. **安全第一**: 所有安全限制必须严格执行
2. **跨平台兼容**: 确保 Linux、macOS、Windows 都能正常工作
3. **资源限制**: 必须有效限制 CPU、内存、时间
4. **错误处理**: 完善的错误处理和日志记录
5. **测试覆盖**: 确保关键功能都有测试覆盖

---

## 完成标准

- [ ] 所有阶段任务完成
- [ ] 所有测试通过（TDD 验证）
- [ ] 集成测试通过
- [ ] 文档更新完成
- [ ] 代码审查通过

