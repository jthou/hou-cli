# 阶段2：任务分解和动态模型切换实施计划

## 概述

阶段2的主要目标是实现智能任务分解和动态模型切换，让系统能够处理更复杂的任务，并根据执行情况动态调整模型选择策略。

## 前提条件

✅ **阶段1已完成**：
- 集成任务复杂度评估
- 根据工具类型选择模型
- 优化快速规则判断
- 增强工具参数验证

✅ **前期准备已完成**：
- 数据模型定义（SubTask, ExecutionPlan, ExecutionState）
- 工具元数据系统
- 配置管理扩展
- 测试框架

## 任务清单

### 任务 2.1：实现任务分解

#### 2.1.1 创建任务分解器

**目标**：使用推理模型将复杂任务分解为可执行的子任务

**实施步骤**：

1. **创建任务分解器类**
   - 文件：`backend/core/agent/planning/task_decomposer.py`
   - 功能：
     - 使用推理模型分析任务
     - 识别子任务和依赖关系
     - 评估每个子任务的复杂度
     - 推荐每个子任务的模型类型

2. **集成到 Orchestrator**
   - 在 `stream_process()` 和 `process()` 中调用
   - 根据复杂度决定是否分解
   - 使用 `TaskComplexityAnalyzer` 判断是否需要分解

3. **实现子任务解析**
   - 解析 LLM 返回的 JSON 格式
   - 转换为 `SubTask` 对象
   - 验证子任务的完整性

**代码位置**：
- 需要创建：`backend/core/agent/planning/task_decomposer.py`
- 需要修改：`backend/core/agent/orchestrator.py`

**代码示例**：
```python
class TaskDecomposer:
    """任务分解器"""
    
    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry):
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.complexity_analyzer = TaskComplexityAnalyzer()
    
    async def decompose_task(self, task: str) -> List[SubTask]:
        """使用推理模型分解复杂任务"""
        # 1. 检查是否需要分解
        if not self.complexity_analyzer.is_complex_task(task):
            return [SubTask(name="主任务", description=task)]
        
        # 2. 使用推理模型分解
        config_manager = get_model_config_manager()
        reasoning_model = config_manager.get_reasoning_model()
        
        prompt = f"""
        分析以下任务，将其分解为可执行的子任务：
        
        任务：{task}
        
        可用工具：
        {self._format_tools_for_llm()}
        
        请返回 JSON 格式的子任务列表，每个子任务包含：
        - name: 子任务名称
        - description: 子任务描述
        - required_tools: 需要的工具列表
        - dependencies: 依赖的其他子任务名称列表
        - estimated_complexity: 复杂度评估（simple/medium/complex）
        - recommended_model: 推荐的模型类型（chat/code/reasoning）
        """
        
        response = await self.llm_service.chat(
            model=reasoning_model,
            system_prompt="你是一个任务规划专家，擅长将复杂任务分解为可执行的子任务。",
            user_prompt=prompt
        )
        
        # 3. 解析响应
        return self._parse_subtasks(response, task)
```

#### 2.1.2 创建执行计划生成器

**目标**：根据子任务创建执行计划，识别依赖关系和并行执行机会

**实施步骤**：

1. **创建执行计划生成器**
   - 文件：`backend/core/agent/planning/execution_planner.py`
   - 功能：
     - 分析子任务依赖关系
     - 识别可并行执行的任务
     - 生成执行顺序
     - 创建 `ExecutionPlan` 对象

2. **依赖关系分析**
   - 使用图算法分析依赖
   - 识别关键路径
   - 优化执行顺序

3. **并行执行识别**
   - 识别无依赖关系的任务
   - 创建并行执行组
   - 考虑资源限制

**代码位置**：
- 需要创建：`backend/core/agent/planning/execution_planner.py`

**代码示例**：
```python
class ExecutionPlanner:
    """执行计划生成器"""
    
    async def plan_execution(self, subtasks: List[SubTask]) -> ExecutionPlan:
        """使用推理模型规划任务执行"""
        # 1. 分析依赖关系
        dependency_graph = self._build_dependency_graph(subtasks)
        
        # 2. 识别可并行执行的任务
        parallel_groups = self._identify_parallel_groups(subtasks, dependency_graph)
        
        # 3. 生成执行顺序
        execution_order = self._generate_execution_order(subtasks, dependency_graph)
        
        # 4. 创建执行计划
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            task_description="",  # 从上下文获取
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            sequential_tasks=execution_order,
            estimated_total_time=self._estimate_total_time(subtasks, parallel_groups)
        )
```

#### 2.1.3 集成任务分解到 Orchestrator

**目标**：在 Orchestrator 中集成任务分解功能

**实施步骤**：

1. **添加任务分解开关**
   - 检查 `ENABLE_TASK_DECOMPOSITION` 环境变量
   - 根据复杂度决定是否分解

2. **修改执行流程**
   - 在 `stream_process()` 和 `process()` 中添加分解逻辑
   - 如果任务需要分解，先分解再执行
   - 按执行计划执行子任务

3. **子任务执行**
   - 按顺序执行子任务
   - 处理子任务之间的依赖
   - 收集子任务结果

**代码位置**：
- `backend/core/agent/orchestrator.py` 的 `stream_process()` 和 `process()` 方法

### 任务 2.2：动态模型切换

#### 2.2.1 根据执行结果切换模型

**目标**：根据任务执行结果动态调整模型选择

**实施步骤**：

1. **执行结果分析**
   - 分析工具调用结果
   - 识别是否需要切换模型
   - 评估当前模型是否合适

2. **模型切换策略**
   - 如果工具调用失败，尝试切换模型
   - 如果任务复杂度增加，切换到推理模型
   - 如果需要代码生成，切换到代码模型

3. **切换历史记录**
   - 记录模型切换历史
   - 用于调试和优化

**代码位置**：
- `backend/core/agent/orchestrator.py` 的 `_chat_with_tools()` 和 `_chat_with_tools_stream()` 方法

**代码示例**：
```python
async def _execute_with_adaptive_model(self, task: str, context: Dict):
    """使用自适应模型执行任务"""
    # 1. 初始模型选择
    current_model = await self._select_model(task)
    self.llm_service.set_model(current_model)
    
    # 2. 执行任务
    result = await self._execute_task(task, context)
    
    # 3. 评估结果并切换
    if result.needs_reasoning:
        # 切换到推理模型
        config_manager = get_model_config_manager()
        reasoning_model = config_manager.get_reasoning_model()
        if current_model != reasoning_model:
            logger.info(f"切换到推理模型: {reasoning_model}")
            self.llm_service.set_model(reasoning_model)
            result = await self._execute_task(task, context)
    
    elif result.needs_code:
        # 切换到代码模型
        config_manager = get_model_config_manager()
        code_model = config_manager.get_code_model()
        if current_model != code_model:
            logger.info(f"切换到代码模型: {code_model}")
            self.llm_service.set_model(code_model)
            result = await self._execute_task(task, context)
    
    return result
```

#### 2.2.2 实现自适应策略

**目标**：根据任务执行情况自动调整策略

**实施步骤**：

1. **执行状态监控**
   - 监控工具调用成功率
   - 监控模型切换次数
   - 监控执行时间

2. **策略调整**
   - 如果工具调用频繁失败，调整模型选择
   - 如果执行时间过长，优化策略
   - 如果模型切换频繁，优化选择逻辑

3. **学习机制**
   - 记录成功和失败的案例
   - 优化模型选择规则
   - 改进任务分解策略

**代码位置**：
- `backend/core/agent/orchestrator.py`

## 实施顺序

### 第一步：实现任务分解（优先级：高）

1. 创建 `TaskDecomposer` 类
2. 实现任务分解逻辑
3. 集成到 Orchestrator
4. 添加测试

**预计时间**：3-4 天

### 第二步：创建执行计划生成器（优先级：高）

1. 创建 `ExecutionPlanner` 类
2. 实现依赖关系分析
3. 实现并行执行识别
4. 添加测试

**预计时间**：2-3 天

### 第三步：集成任务分解到 Orchestrator（优先级：高）

1. 修改执行流程
2. 实现子任务执行
3. 处理依赖关系
4. 添加测试

**预计时间**：2-3 天

### 第四步：动态模型切换（优先级：中）

1. 实现执行结果分析
2. 实现模型切换策略
3. 添加切换历史记录
4. 添加测试

**预计时间**：2-3 天

### 第五步：自适应策略（优先级：低）

1. 实现执行状态监控
2. 实现策略调整
3. 添加学习机制
4. 添加测试

**预计时间**：2-3 天

## 测试计划

### 单元测试

1. **任务分解测试**
   - 测试简单任务（不分解）
   - 测试复杂任务（分解）
   - 测试依赖关系识别
   - 测试子任务解析

2. **执行计划测试**
   - 测试依赖关系分析
   - 测试并行执行识别
   - 测试执行顺序生成

3. **动态模型切换测试**
   - 测试执行结果分析
   - 测试模型切换逻辑
   - 测试切换历史记录

### 集成测试

1. **端到端测试**
   - 测试完整任务分解和执行流程
   - 测试模型切换效果
   - 测试并行执行

2. **性能测试**
   - 测试任务分解时间
   - 测试执行计划生成时间
   - 测试模型切换开销

## 预期效果

1. **任务处理能力提升**
   - 能够处理更复杂的任务
   - 任务执行更清晰有序
   - 减少执行错误

2. **模型使用效率提升**
   - 根据执行情况动态调整
   - 减少不必要的模型切换
   - 提高模型选择准确率

3. **执行效率提升**
   - 并行执行独立任务
   - 优化执行顺序
   - 减少总执行时间

## 风险与缓解

### 风险 1：任务分解质量不高

**缓解**：
- 使用推理模型进行分解
- 添加验证和修正机制
- 提供手动调整选项

### 风险 2：模型切换开销

**缓解**：
- 只在必要时切换
- 缓存模型选择结果
- 优化切换逻辑

### 风险 3：并行执行冲突

**缓解**：
- 识别资源冲突
- 添加锁机制
- 提供串行执行选项

## 时间估算

- **任务 2.1**：7-10 天
- **任务 2.2**：4-6 天
- **测试和优化**：2-3 天
- **总计**：13-19 天（约 2-3 周）

## 开始实施

建议从**任务 2.1.1（创建任务分解器）**开始，因为它是其他功能的基础。

## 相关文档

- [编排改进计划](./ORCHESTRATION_IMPROVEMENT_PLAN.md)
- [阶段1完成总结](./PHASE1_COMPLETION_SUMMARY.md)
- [数据模型定义](./PREPARATION_PROGRESS.md#数据模型定义)

