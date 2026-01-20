# 实施前测试验证清单

## 概述

在开始实施阶段1（基础改进）之前，需要完成以下测试验证，确保基础设施和现有功能正常工作。

## 一、基础设施测试

### 1.1 模型配置验证 ✅

**测试目标**：验证三种类型的模型配置是否正确

**测试方法**：
```bash
# 运行验证脚本
python scripts/validate_model_config.py
```

**验证项**：
- [ ] CHAT_MODEL 配置正确
- [ ] CODE_MODEL 配置正确
- [ ] REASONING_MODEL 配置正确
- [ ] 所有 API Key 可用
- [ ] 所有模型可以正常调用

**预期结果**：
- 所有模型配置验证通过
- 所有 API Key 测试成功

### 1.2 数据模型测试 ✅

**测试目标**：验证数据模型的序列化和反序列化

**测试文件**：`backend/core/agent/tests/orchestration/test_task_decomposition.py`

**验证项**：
- [ ] SubTask 序列化/反序列化
- [ ] ExecutionPlan 序列化/反序列化
- [ ] ExecutionState 序列化/反序列化
- [ ] ToolMetadata 序列化/反序列化

**运行测试**：
```bash
pytest backend/core/agent/tests/orchestration/test_task_decomposition.py -v
```

### 1.3 工具元数据测试 ✅

**测试目标**：验证工具元数据注册表功能

**测试文件**：`backend/core/agent/tests/orchestration/test_tool_metadata.py`

**验证项**：
- [ ] 工具元数据获取
- [ ] 推荐模型查询
- [ ] 推理需求检查
- [ ] 代码需求检查
- [ ] 并行能力检查

**运行测试**：
```bash
pytest backend/core/agent/tests/orchestration/test_tool_metadata.py -v
```

### 1.4 配置管理扩展测试

**测试目标**：验证配置管理的新增方法

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_config_manager.py`

**验证项**：
- [ ] `get_max_iterations_stream()` 返回正确值（默认 100）
- [ ] `get_max_iterations_non_stream()` 返回正确值（默认 5）
- [ ] `is_smart_model_selection_enabled()` 返回正确值（默认 true）
- [ ] `is_task_decomposition_enabled()` 返回正确值（默认 false）
- [ ] `is_parallel_execution_enabled()` 返回正确值（默认 false）
- [ ] 环境变量覆盖功能正常

**测试代码示例**：
```python
def test_config_manager_extensions():
    """测试配置管理扩展方法"""
    config_manager = get_model_config_manager()
    
    # 测试默认值
    assert config_manager.get_max_iterations_stream() == 100
    assert config_manager.get_max_iterations_non_stream() == 5
    assert config_manager.is_smart_model_selection_enabled() == True
    
    # 测试环境变量覆盖
    import os
    os.environ["MAX_TOOL_ITERATIONS_STREAM"] = "50"
    assert config_manager.get_max_iterations_stream() == 50
```

## 二、现有功能回归测试

### 2.1 模型选择逻辑测试 ✅

**测试目标**：验证现有模型选择逻辑正常工作

**测试文件**：`backend/core/agent/tests/orchestration/test_model_selection.py`

**验证项**：
- [ ] 简单对话任务选择对话模型
- [ ] 代码任务选择编程模型
- [ ] 推理任务选择推理模型
- [ ] 关键词匹配正常工作
- [ ] 模型切换功能正常

**运行测试**：
```bash
pytest backend/core/agent/tests/orchestration/test_model_selection.py -v
```

### 2.2 任务复杂度分析测试

**测试目标**：验证任务复杂度分析器功能

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_complexity_analyzer.py`

**验证项**：
- [ ] 简单任务识别（score < 0.2）
- [ ] 中等任务识别（0.2 <= score < 0.5）
- [ ] 复杂任务识别（score >= 0.5）
- [ ] 关键词检测正常工作
- [ ] 缓存机制正常工作
- [ ] LLM 辅助判断（如果启用）

**测试代码示例**：
```python
def test_complexity_analyzer():
    """测试任务复杂度分析器"""
    from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
    
    analyzer = TaskComplexityAnalyzer()
    
    # 简单任务
    simple_task = "今天天气怎么样？"
    analysis = analyzer.analyze_task(simple_task)
    assert analysis["score"] < 0.2
    
    # 复杂任务
    complex_task = "分析这个项目的代码结构并生成详细报告"
    analysis = analyzer.analyze_task(complex_task)
    assert analysis["score"] >= 0.3
```

### 2.3 集成测试场景 ✅

**测试目标**：验证端到端场景

**测试文件**：`backend/core/agent/tests/orchestration/test_integration_scenarios.py`

**验证项**：
- [ ] 所有测试场景的模型选择正确
- [ ] 端到端流程正常

**运行测试**：
```bash
pytest backend/core/agent/tests/orchestration/test_integration_scenarios.py -v
```

## 三、新功能测试（实施前准备）

### 3.1 复杂度评估集成测试

**测试目标**：验证复杂度评估与模型选择的集成

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_complexity_integration.py`

**验证项**：
- [ ] 复杂度评估结果正确映射到模型选择
- [ ] 简单任务优先使用对话模型
- [ ] 复杂任务优先使用推理模型
- [ ] 中等复杂度任务结合分数和任务类型判断
- [ ] 缓存机制不影响结果准确性

**测试代码示例**：
```python
@pytest.mark.asyncio
async def test_complexity_based_model_selection():
    """测试基于复杂度的模型选择"""
    orchestrator = Orchestrator()
    
    # 简单任务应该选择对话模型
    simple_task = "今天天气怎么样？"
    model = await orchestrator._select_model(simple_task)
    config_manager = get_model_config_manager()
    assert model == config_manager.get_chat_model()
    
    # 复杂任务应该选择推理模型
    complex_task = "分析这个项目的代码结构并生成详细报告"
    model = await orchestrator._select_model(complex_task)
    assert model == config_manager.get_reasoning_model()
```

### 3.2 工具类型模型选择测试

**测试目标**：验证根据工具类型选择模型的功能

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_tool_model_selection.py`

**验证项**：
- [ ] 代码工具调用时选择编程模型
- [ ] 推理工具调用时选择推理模型
- [ ] 简单工具调用时选择对话模型
- [ ] 模型切换正常工作
- [ ] 多工具调用时的模型选择策略

**测试代码示例**：
```python
@pytest.mark.asyncio
async def test_tool_based_model_selection():
    """测试基于工具类型的模型选择"""
    from backend.core.agent.tools.metadata import tool_metadata_registry
    from backend.services.llm.model_config import get_model_config_manager
    
    config_manager = get_model_config_manager()
    
    # 代码工具应该推荐编程模型
    model = tool_metadata_registry.get_recommended_model("execute_code")
    assert model == "code"
    
    # 浏览器工具应该推荐推理模型
    model = tool_metadata_registry.get_recommended_model("browser")
    assert model == "reasoning"
```

### 3.3 深度研究功能测试

**测试目标**：验证深度研究功能的基础功能

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_deep_research.py`

**验证项**：
- [ ] ResearchManager 初始化正常
- [ ] 研究计划创建功能
- [ ] 信息收集功能
- [ ] 信息分析功能
- [ ] 报告生成功能
- [ ] 与规划文件集成

**测试代码示例**：
```python
@pytest.mark.asyncio
async def test_research_manager_basic():
    """测试研究管理器基础功能"""
    from backend.core.agent.research import ResearchManager
    
    research_manager = ResearchManager(
        llm_service=llm_service,
        tool_registry=tool_registry,
        planning_manager=planning_manager
    )
    
    # 测试研究计划创建
    plan = await research_manager._create_research_plan(
        "Python 异步编程",
        depth="medium"
    )
    assert plan.question == "Python 异步编程"
    assert len(plan.steps) > 0
```

## 四、性能测试

### 4.1 模型选择性能测试

**测试目标**：验证模型选择的性能

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_performance.py`

**验证项**：
- [ ] 快速规则判断时间 < 100ms
- [ ] 复杂度评估时间 < 500ms（规则判断）
- [ ] LLM 模型选择时间 < 10s（如果使用）
- [ ] 缓存命中率 > 80%（重复任务）

**测试代码示例**：
```python
import time

def test_model_selection_performance():
    """测试模型选择性能"""
    orchestrator = Orchestrator()
    
    # 测试快速规则判断
    start = time.time()
    model = await orchestrator._select_model("执行 ls /home")
    elapsed = time.time() - start
    
    assert elapsed < 0.1  # 应该很快
```

### 4.2 工具元数据查询性能

**测试目标**：验证工具元数据查询性能

**验证项**：
- [ ] 元数据查询时间 < 1ms
- [ ] 批量查询性能正常

## 五、边界情况测试

### 5.1 异常情况处理

**测试目标**：验证异常情况的处理

**验证项**：
- [ ] 模型配置缺失时的降级处理
- [ ] API Key 无效时的错误处理
- [ ] 工具不存在时的处理
- [ ] 复杂度分析失败时的降级
- [ ] LLM 调用超时时的处理

### 5.2 边界值测试

**测试目标**：验证边界值的处理

**验证项**：
- [ ] 空任务字符串
- [ ] 极长任务字符串
- [ ] 特殊字符处理
- [ ] 分数边界值（0.19 vs 0.21, 0.49 vs 0.51）

## 六、集成测试

### 6.1 端到端测试

**测试目标**：验证完整流程

**需要创建的测试**：`backend/core/agent/tests/orchestration/test_e2e.py`

**验证项**：
- [ ] 简单任务完整流程
- [ ] 复杂任务完整流程
- [ ] 研究任务完整流程
- [ ] 模型切换流程
- [ ] 工具调用流程

### 6.2 与现有系统集成测试

**测试目标**：验证与现有系统的兼容性

**验证项**：
- [ ] 与规划文件系统集成
- [ ] 与任务管理器集成
- [ ] 与上下文管理器集成
- [ ] 与技能系统集成

## 七、测试执行计划

### 阶段1：基础设施测试（1天）

1. **运行现有测试**（30分钟）
   ```bash
   pytest backend/core/agent/tests/orchestration/ -v
   ```

2. **创建缺失的测试**（4小时）
   - 配置管理扩展测试
   - 复杂度分析器测试
   - 性能测试

3. **修复测试失败**（2小时）
   - 修复任何失败的测试
   - 确保所有测试通过

### 阶段2：新功能测试（1天）

1. **创建集成测试**（4小时）
   - 复杂度评估集成测试
   - 工具类型模型选择测试
   - 深度研究功能测试

2. **创建端到端测试**（3小时）
   - 完整流程测试
   - 系统集成测试

3. **边界情况测试**（1小时）
   - 异常处理测试
   - 边界值测试

### 阶段3：性能测试（0.5天）

1. **性能基准测试**（2小时）
   - 建立性能基准
   - 记录性能指标

2. **性能优化验证**（2小时）
   - 验证缓存效果
   - 验证优化措施

## 八、测试通过标准

### 必须通过（阻塞性）

- [ ] 所有基础设施测试通过
- [ ] 所有现有功能回归测试通过
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 模型配置验证通过
- [ ] API Key 测试通过

### 应该通过（非阻塞性）

- [ ] 性能测试达到基准
- [ ] 边界情况测试通过
- [ ] 端到端测试通过

## 九、测试报告模板

测试完成后，应生成测试报告，包括：

1. **测试执行摘要**
   - 测试总数
   - 通过数
   - 失败数
   - 跳过数

2. **测试覆盖情况**
   - 代码覆盖率
   - 功能覆盖率

3. **性能指标**
   - 模型选择时间
   - 复杂度评估时间
   - API 调用次数

4. **问题清单**
   - 发现的问题
   - 严重程度
   - 修复计划

## 十、快速验证脚本

创建快速验证脚本 `scripts/quick_validation.py`：

```python
#!/usr/bin/env python3
"""快速验证脚本"""
import subprocess
import sys

def run_tests():
    """运行所有关键测试"""
    tests = [
        "backend/core/agent/tests/orchestration/test_model_selection.py",
        "backend/core/agent/tests/orchestration/test_tool_metadata.py",
        "backend/core/agent/tests/orchestration/test_task_decomposition.py",
    ]
    
    for test in tests:
        print(f"运行测试: {test}")
        result = subprocess.run(
            ["pytest", test, "-v"],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"❌ 测试失败: {test}")
            print(result.stdout.decode())
            return False
        print(f"✅ 测试通过: {test}")
    
    return True

if __name__ == "__main__":
    if run_tests():
        print("\n✅ 所有关键测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查")
        sys.exit(1)
```

## 当前测试状态（更新）

### ✅ 已修复的问题

1. **模型选择逻辑**：
   - ✅ 推理关键词优先检查
   - ✅ 多步骤任务识别
   - ✅ 模式匹配支持（"生成.*文章"等）

2. **工具元数据单例**：
   - ✅ 添加初始化标志
   - ✅ 确保元数据正确初始化

### ⚠️ 待解决的问题

1. **测试隔离问题**：
   - 工具元数据测试在批量运行时失败
   - 可能原因：测试之间的状态污染
   - 需要：添加测试清理或隔离机制

### 📊 测试通过率

- **总体**：20/24 通过（83%）
- **模型选择**：5/5 通过（100%）✅
- **任务分解**：4/4 通过（100%）✅
- **集成场景**：6/6 通过（100%）✅
- **工具元数据**：2/6 通过（33%）⚠️

## 总结

在实施阶段1之前，需要：

1. ✅ **完成基础设施测试**（大部分已完成）
2. ⚠️ **修复测试隔离问题**（工具元数据测试）
3. ⚠️ **补充缺失的测试**（配置管理、复杂度分析器、性能测试）
4. ⚠️ **创建新功能测试**（复杂度集成、工具模型选择、深度研究）
5. ⚠️ **运行所有测试并确保通过**
6. ⚠️ **建立性能基准**

**预计时间**：2-3 天

**优先级**：
- **P0（必须）**：修复测试隔离问题、基础设施测试、回归测试
- **P1（重要）**：新功能测试、集成测试
- **P2（可选）**：性能测试、边界情况测试

