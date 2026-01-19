# 下一步实施指南

## 当前状态

✅ **已完成**：前期准备工作（环境配置、代码基础设施、测试环境）

## 下一步：阶段1 - 基础改进

根据编排改进计划，下一步应该实施**阶段1：基础改进**，包括两个主要任务：

### 🎯 任务 1：改进模型选择逻辑

#### 1.1 集成任务复杂度评估（推荐先做）

**现状**：
- ✅ 已有 `TaskComplexityAnalyzer` 类（`backend/core/agent/planning/complexity.py`）
- ✅ 已有 `TaskComplexity` 枚举（`backend/core/agent/models.py`）
- ❌ 尚未集成到模型选择逻辑中

**需要做**：
1. 在 `orchestrator.py` 的 `_select_model()` 方法中调用复杂度评估
2. 根据复杂度调整模型选择策略
3. 添加缓存机制（避免重复评估）

**代码位置**：
- `backend/core/agent/orchestrator.py` 的 `_select_model()` 方法（2543行开始）

**实施步骤**：
```python
# 1. 在 _select_model() 方法开始处添加复杂度评估
from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
from backend.core.agent.models import TaskComplexity

complexity_analyzer = TaskComplexityAnalyzer()
complexity = await complexity_analyzer.analyze_complexity(task)

# 2. 根据复杂度调整选择策略
if complexity == TaskComplexity.COMPLEX:
    # 复杂任务优先使用推理模型
    return reasoning_model
elif complexity == TaskComplexity.SIMPLE:
    # 简单任务优先使用对话模型
    return chat_model
# MEDIUM 复杂度继续使用现有逻辑
```

#### 1.2 优化快速规则判断

**现状**：
- ✅ 已有快速规则判断（关键词匹配）
- ⚠️ 关键词列表可以扩展
- ⚠️ 匹配逻辑可以改进

**需要做**：
1. 扩展关键词列表（参考 `TaskComplexityAnalyzer` 的关键词）
2. 改进匹配逻辑（考虑上下文、权重）
3. 添加测试

**代码位置**：
- `backend/core/agent/orchestrator.py` 的 `_select_model()` 方法（2568-2588行）

#### 1.3 优化 LLM 模型选择

**现状**：
- ✅ 已有 LLM 模型选择逻辑
- ⚠️ 提示词可以优化
- ⚠️ 结果解析可以改进

**需要做**：
1. 优化提示词（更清晰的标准、添加示例）
2. 改进结果解析（更健壮的提取逻辑）
3. 添加降级策略

### 🎯 任务 2：工具调用优化

#### 2.1 根据工具类型选择模型（推荐先做）

**现状**：
- ✅ 已有工具元数据注册表（`tool_metadata_registry`）
- ✅ 已有工具元数据（推荐模型、复杂度等）
- ❌ 尚未在工具调用时使用

**需要做**：
1. 在工具调用前，根据工具元数据选择模型
2. 实现模型切换逻辑
3. 记录模型切换历史

**代码位置**：
- `backend/core/agent/orchestrator.py` 的 `_chat_with_tools()` 方法（2284行开始）
- `backend/core/agent/orchestrator.py` 的 `_chat_with_tools_stream()` 方法（1884行开始）

**实施步骤**：
```python
# 在工具调用前添加模型选择
from backend.core.agent.tools.metadata import tool_metadata_registry

# 检测到工具调用时
if hasattr(response, 'tool_calls') and response.tool_calls:
    for tool_call in response.tool_calls:
        tool_name = tool_call.function.name
        
        # 获取工具推荐的模型
        recommended_model = tool_metadata_registry.get_recommended_model(tool_name)
        
        if recommended_model:
            # 切换到推荐模型
            config_manager = get_model_config_manager()
            if recommended_model == "code":
                self.llm_service.set_model(config_manager.get_code_model())
            elif recommended_model == "reasoning":
                self.llm_service.set_model(config_manager.get_reasoning_model())
            elif recommended_model == "chat":
                self.llm_service.set_model(config_manager.get_chat_model())
```

#### 2.2 增强工具参数验证

**现状**：
- ✅ 已有基础参数验证（`Tool.validate_parameters()`）
- ⚠️ 可以使用模型优化参数
- ⚠️ 验证逻辑可以增强

**需要做**：
1. 使用模型优化工具参数（推理模型优化、编程模型验证）
2. 改进验证逻辑（类型转换、修正）
3. 添加参数缓存

## 推荐实施顺序

### 第一步：集成任务复杂度评估（1-2天）

**为什么先做**：
- 复杂度评估是模型选择的基础
- 已有现成的 `TaskComplexityAnalyzer`，只需集成
- 影响范围小，风险低

**具体步骤**：
1. 在 `_select_model()` 中添加复杂度评估调用
2. 根据复杂度调整模型选择策略
3. 添加单元测试
4. 验证效果

### 第二步：根据工具类型选择模型（1-2天）

**为什么其次**：
- 工具元数据已准备好，只需使用
- 可以立即看到效果（工具调用更准确）
- 为后续优化打下基础

**具体步骤**：
1. 在工具调用前添加模型选择逻辑
2. 实现模型切换
3. 添加测试
4. 验证效果

### 第三步：优化快速规则判断（1天）

**为什么第三**：
- 改进现有逻辑，风险低
- 可以快速提升准确率
- 不依赖其他功能

### 第四步：增强工具参数验证（1-2天）

**为什么最后**：
- 相对独立的功能
- 可以逐步优化
- 不影响核心流程

## 开始实施

### 立即开始：集成任务复杂度评估

**文件**：`backend/core/agent/orchestrator.py`

**修改位置**：`_select_model()` 方法（约2543行）

**代码示例**：
```python
async def _select_model(self, task: str) -> str:
    """使用推理模型智能选择最适合的模型"""
    from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
    from backend.core.agent.models import TaskComplexity
    
    config_manager = get_model_config_manager()
    chat_model = config_manager.get_chat_model()
    code_model = config_manager.get_code_model()
    reasoning_model = config_manager.get_reasoning_model()
    
    # 1. 任务复杂度评估
    complexity_analyzer = TaskComplexityAnalyzer()
    complexity = await complexity_analyzer.analyze_complexity(task)
    
    # 2. 根据复杂度快速判断
    if complexity == TaskComplexity.COMPLEX:
        # 复杂任务优先使用推理模型
        return reasoning_model
    elif complexity == TaskComplexity.SIMPLE:
        # 简单任务，继续使用快速规则判断
        pass  # 继续执行下面的快速规则判断
    
    # 3. 快速规则判断（现有逻辑）
    task_lower = task.lower()
    # ... 现有代码 ...
    
    # 4. LLM 模型选择（现有逻辑，但可以优化）
    # ... 现有代码 ...
```

## 测试计划

### 单元测试

1. **复杂度评估集成测试**
   - 测试不同复杂度的任务
   - 测试模型选择结果

2. **工具类型模型选择测试**
   - 测试不同工具调用时的模型选择
   - 测试模型切换逻辑

### 集成测试

1. **端到端测试**
   - 测试完整任务流程
   - 验证模型选择准确性

## 预期效果

完成阶段1后，预期：

1. **模型选择准确率提升 20-30%**
2. **工具调用成功率提升 10-15%**
3. **响应时间优化（快速规则判断更快）**

## 需要帮助？

如果实施过程中遇到问题，可以：

1. 查看 `docs/PHASE1_IMPLEMENTATION_PLAN.md` 获取详细计划
2. 查看 `docs/ORCHESTRATION_IMPROVEMENT_PLAN.md` 了解整体方案
3. 查看 `backend/core/agent/planning/complexity.py` 了解复杂度分析器
4. 查看 `backend/core/agent/tools/metadata.py` 了解工具元数据

