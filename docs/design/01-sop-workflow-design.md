# SOP 流程编排设计文档

## 概述

本文档详细说明 SOP (Standard Operating Procedure) 标准操作流程的设计和实现。SOP 用于定义和执行标准化的任务流程，确保任务按照预定义的步骤执行，提高一致性和可重复性。

## 设计目标

1. **标准化执行**：定义可重复的标准流程
2. **质量控制**：通过预定义流程保证执行质量
3. **效率提升**：避免每次都重新分析和规划
4. **灵活配置**：支持条件分支、循环、错误处理
5. **易于维护**：通过配置文件定义流程，易于修改

## 核心概念

### 1. SOP 流程定义

SOP 流程通过 YAML 或 JSON 文件定义，包含：
- **流程元信息**：名称、版本、描述
- **步骤定义**：每个步骤的 Agent、动作、参数
- **依赖关系**：步骤之间的依赖
- **条件分支**：基于条件的流程分支
- **输出定义**：流程的输出格式

### 2. 流程执行引擎

负责：
- 加载和解析流程定义
- 按顺序执行步骤
- 处理依赖关系
- 执行条件分支
- 管理流程状态
- 错误处理和重试

### 3. 流程识别器

负责：
- 分析用户任务
- 匹配 SOP 模板
- 决定使用 SOP 还是动态编排

## 流程定义格式

### 基本结构

```yaml
name: 流程名称
version: 1.0
description: 流程描述

# 输入参数定义
inputs:
  - name: file_path
    type: string
    required: true
    description: 文件路径

# 流程步骤
steps:
  - id: step1
    name: 步骤名称
    agent: agent_name
    action: action_name
    params:
      param1: value1
    depends_on: []  # 依赖的步骤ID
    timeout: 30     # 超时时间（秒）
    retry:
      max_attempts: 3
      delay: 5

# 输出定义
output:
  field1: ${step1.result.field}
  field2: ${step2.result}
```

### 步骤类型

#### 1. 简单步骤

```yaml
steps:
  - id: load_document
    name: 加载文档
    agent: pdf
    action: load
    params:
      file_path: ${input.file_path}
```

#### 2. 条件步骤

```yaml
steps:
  - id: check_condition
    name: 检查条件
    agent: chat
    action: check
    params:
      data: ${previous_step.result}
    
  - id: branch_step
    name: 条件分支
    condition: ${check_condition.result.is_valid}
    on_true:
      - id: process_valid
        agent: pdf
        action: process
        params:
          data: ${check_condition.result}
    on_false:
      - id: handle_invalid
        agent: chat
        action: report_error
        params:
          error: ${check_condition.result.error}
```

#### 3. 循环步骤

```yaml
steps:
  - id: process_items
    name: 处理列表
    loop:
      items: ${input.items}
      item_var: item
      steps:
        - id: process_item
          agent: pdf
          action: process
          params:
            item: ${item}
```

#### 4. 并行步骤

```yaml
steps:
  - id: parallel_processing
    name: 并行处理
    parallel: true
    steps:
      - id: task1
        agent: pdf
        action: task1
      - id: task2
        agent: code
        action: task2
```

## 实现细节

### 流程执行引擎

```python
# backend/workflow/workflow_engine.py
from typing import Dict, Any, List, Optional
import yaml
import asyncio
from pathlib import Path
from backend.agent.orchestrator import Orchestrator
from backend.workflow.workflow_state import WorkflowState
from backend.workflow.step_executor import StepExecutor

class WorkflowEngine:
    """SOP 流程执行引擎"""
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.workflows: Dict[str, Dict] = {}
        self.state = WorkflowState()
        self.step_executor = StepExecutor(orchestrator)
    
    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 SOP 流程"""
        # 1. 加载流程定义
        workflow_def = await self.load_workflow(workflow_name)
        
        # 2. 验证输入
        self.validate_inputs(workflow_def, input_data)
        
        # 3. 初始化状态
        self.state.init(workflow_def, input_data)
        
        # 4. 执行步骤
        await self.execute_steps(workflow_def["steps"])
        
        # 5. 收集输出
        output = self.collect_output(workflow_def)
        
        return output
    
    async def load_workflow(self, workflow_name: str) -> Dict:
        """加载流程定义"""
        if workflow_name in self.workflows:
            return self.workflows[workflow_name]
        
        workflow_path = Path(f"workflows/{workflow_name}.yaml")
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow {workflow_name} not found")
        
        with open(workflow_path) as f:
            workflow_def = yaml.safe_load(f)
        
        # 验证流程定义
        self.validate_workflow(workflow_def)
        
        self.workflows[workflow_name] = workflow_def
        return workflow_def
    
    def validate_workflow(self, workflow_def: Dict):
        """验证流程定义"""
        required_fields = ["name", "version", "steps"]
        for field in required_fields:
            if field not in workflow_def:
                raise ValueError(f"Missing required field: {field}")
    
    def validate_inputs(self, workflow_def: Dict, input_data: Dict):
        """验证输入参数"""
        inputs_spec = workflow_def.get("inputs", [])
        for input_spec in inputs_spec:
            name = input_spec["name"]
            required = input_spec.get("required", False)
            
            if required and name not in input_data:
                raise ValueError(f"Missing required input: {name}")
    
    async def execute_steps(self, steps: List[Dict]):
        """执行流程步骤"""
        executed_steps = set()
        
        while len(executed_steps) < len(steps):
            # 找到可以执行的步骤（依赖已满足）
            ready_steps = [
                s for s in steps
                if s["id"] not in executed_steps
                and self.can_execute(s, executed_steps)
            ]
            
            if not ready_steps:
                # 检查是否有循环依赖
                remaining = [s["id"] for s in steps if s["id"] not in executed_steps]
                raise Exception(f"Cannot execute remaining steps: {remaining}")
            
            # 执行就绪的步骤
            for step in ready_steps:
                await self.execute_step(step)
                executed_steps.add(step["id"])
    
    def can_execute(self, step: Dict, executed_steps: set) -> bool:
        """检查步骤是否可以执行"""
        depends_on = step.get("depends_on", [])
        return all(dep in executed_steps for dep in depends_on)
    
    async def execute_step(self, step: Dict):
        """执行单个步骤"""
        step_id = step["id"]
        
        try:
            # 检查是否有条件分支
            if "condition" in step:
                await self.execute_conditional_step(step)
            # 检查是否有循环
            elif "loop" in step:
                await self.execute_loop_step(step)
            # 检查是否并行
            elif step.get("parallel", False):
                await self.execute_parallel_steps(step)
            else:
                # 普通步骤
                result = await self.step_executor.execute(step, self.state)
                self.state.set_step_result(step_id, result)
        
        except Exception as e:
            # 错误处理
            if step.get("retry"):
                result = await self.retry_step(step, e)
                self.state.set_step_result(step_id, result)
            else:
                raise
    
    async def execute_conditional_step(self, step: Dict):
        """执行条件分支步骤"""
        condition_expr = step["condition"]
        condition_result = self.state.evaluate_condition(condition_expr)
        
        branch_steps = step.get("on_true" if condition_result else "on_false", [])
        
        for branch_step in branch_steps:
            await self.execute_step(branch_step)
    
    async def execute_loop_step(self, step: Dict):
        """执行循环步骤"""
        loop_config = step["loop"]
        items = self.state.resolve_variable(loop_config["items"])
        item_var = loop_config["item_var"]
        
        results = []
        for item in items:
            # 设置循环变量
            self.state.set_variable(item_var, item)
            
            # 执行循环内的步骤
            for loop_step in loop_config["steps"]:
                result = await self.step_executor.execute(loop_step, self.state)
                results.append(result)
        
        self.state.set_step_result(step["id"], results)
    
    async def execute_parallel_steps(self, step: Dict):
        """执行并行步骤"""
        parallel_steps = step["steps"]
        
        tasks = [
            self.step_executor.execute(s, self.state)
            for s in parallel_steps
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 保存所有步骤的结果
        for s, r in zip(parallel_steps, results):
            self.state.set_step_result(s["id"], r)
    
    async def retry_step(self, step: Dict, error: Exception) -> Any:
        """重试失败的步骤"""
        retry_config = step.get("retry", {})
        max_attempts = retry_config.get("max_attempts", 3)
        delay = retry_config.get("delay", 5)
        
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(delay)
                result = await self.step_executor.execute(step, self.state)
                return result
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                error = e
        
        raise error
    
    def collect_output(self, workflow_def: Dict) -> Dict[str, Any]:
        """收集流程输出"""
        output_spec = workflow_def.get("output", {})
        return self.state.resolve_output(output_spec)
```

### 步骤执行器

```python
# backend/workflow/step_executor.py
from typing import Dict, Any
from backend.workflow.workflow_state import WorkflowState

class StepExecutor:
    """步骤执行器"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    async def execute(
        self,
        step: Dict,
        state: WorkflowState
    ) -> Any:
        """执行步骤"""
        # 解析参数
        params = state.resolve_params(step.get("params", {}))
        
        # 获取 Agent
        agent_name = step["agent"]
        agent = self.orchestrator.agents[agent_name]
        
        # 构建任务
        task = {
            "action": step["action"],
            **params
        }
        
        # 执行任务
        result = await agent.execute(task)
        
        return result
```

### 流程状态管理（增强版）

```python
# backend/workflow/workflow_state.py
from typing import Dict, Any, Optional
import re
from datetime import datetime

class WorkflowState:
    """流程状态管理（增强版）"""
    
    def __init__(self):
        self.input_data: Dict[str, Any] = {}
        self.step_results: Dict[str, Any] = {}
        self.workflow_def: Optional[Dict] = None
        self.variables: Dict[str, Any] = {}
    
    def init(self, workflow_def: Dict, input_data: Dict):
        """初始化流程状态"""
        self.workflow_def = workflow_def
        self.input_data = input_data
        self.step_results = {}
        self.variables = {
            "input": input_data,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_step_result(self, step_id: str, result: Any):
        """保存步骤结果"""
        self.step_results[step_id] = result
        self.variables[step_id] = {"result": result}
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
    
    def resolve_variable(self, variable_expr: str) -> Any:
        """解析变量表达式"""
        if not isinstance(variable_expr, str):
            return variable_expr
        
        # 匹配 ${path.to.value} 格式
        pattern = r'\$\{([^}]+)\}'
        match = re.search(pattern, variable_expr)
        
        if not match:
            return variable_expr
        
        path = match.group(1)
        parts = path.split('.')
        
        value = self.variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)]
            else:
                return None
            if value is None:
                return None
        
        return value
    
    def resolve_params(self, params: Dict) -> Dict:
        """解析参数，支持变量替换"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self.resolve_variable(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_params(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_variable(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved
    
    def evaluate_condition(self, condition_expr: str) -> bool:
        """评估条件表达式"""
        # 解析条件表达式
        # 支持简单比较：${step1.result.length > 100}
        # 这里简化实现，实际可以使用更强大的表达式引擎
        
        # 提取变量和操作符
        # 例如：${step1.result.length} > 100
        if ">" in condition_expr:
            left, right = condition_expr.split(">", 1)
            left_value = self.resolve_variable(left.strip())
            right_value = self.resolve_variable(right.strip())
            return left_value > right_value
        elif "<" in condition_expr:
            left, right = condition_expr.split("<", 1)
            left_value = self.resolve_variable(left.strip())
            right_value = self.resolve_variable(right.strip())
            return left_value < right_value
        elif "==" in condition_expr:
            left, right = condition_expr.split("==", 1)
            left_value = self.resolve_variable(left.strip())
            right_value = self.resolve_variable(right.strip())
            return left_value == right_value
        else:
            # 默认作为变量解析，非空为真
            value = self.resolve_variable(condition_expr)
            return bool(value)
    
    def resolve_output(self, output_spec: Dict) -> Dict[str, Any]:
        """解析输出定义"""
        output = {}
        for key, value_template in output_spec.items():
            if isinstance(value_template, str):
                output[key] = self.resolve_variable(value_template)
            elif isinstance(value_template, dict):
                output[key] = self.resolve_output(value_template)
            elif isinstance(value_template, list):
                output[key] = [
                    self.resolve_variable(item) if isinstance(item, str)
                    else item
                    for item in value_template
                ]
            else:
                output[key] = value_template
        return output
```

## 完整示例

### PDF 分析 SOP

```yaml
# workflows/pdf_analysis_sop.yaml
name: PDF分析标准流程
version: 1.0
description: 标准化的PDF文档分析和总结流程

inputs:
  - name: file_path
    type: string
    required: true
    description: PDF文件路径

steps:
  - id: step1_load
    name: 加载PDF文档
    agent: pdf
    action: load
    params:
      file_path: ${input.file_path}
    timeout: 30
    
  - id: step2_extract
    name: 提取文本内容
    agent: pdf
    action: extract_text
    depends_on: [step1_load]
    params:
      document_id: ${step1_load.result.document_id}
    
  - id: step3_analyze
    name: 内容分析
    agent: chat
    action: analyze
    depends_on: [step2_extract]
    params:
      text: ${step2_extract.result.text}
      analysis_type: comprehensive
    
  - id: step4_summarize
    name: 生成摘要
    agent: chat
    action: summarize
    depends_on: [step3_analyze]
    params:
      analysis_result: ${step3_analyze.result}
    
  - id: step5_validate
    name: 结果验证
    condition: ${step4_summarize.result.length > 100}
    depends_on: [step4_summarize]
    on_true:
      - id: format_output
        agent: chat
        action: format_output
        params:
          summary: ${step4_summarize.result}
    on_false:
      - id: retry_summarize
        agent: chat
        action: retry_summarize
        params:
          analysis_result: ${step3_analyze.result}

output:
  summary: ${step4_summarize.result}
  analysis: ${step3_analyze.result}
  metadata:
    document_id: ${step1_load.result.document_id}
    processed_at: ${timestamp}
```

### 代码审查 SOP

```yaml
# workflows/code_review_sop.yaml
name: 代码审查标准流程
version: 1.0
description: 标准化的代码审查流程

inputs:
  - name: code_path
    type: string
    required: true
  - name: review_criteria
    type: array
    required: false
    default: ["quality", "performance", "security"]

steps:
  - id: load_code
    name: 加载代码
    agent: code
    action: load
    params:
      path: ${input.code_path}
  
  - id: analyze_code
    name: 代码分析
    agent: code
    action: analyze
    depends_on: [load_code]
    params:
      code: ${load_code.result.code}
  
  - id: review_parallel
    name: 并行审查
    parallel: true
    depends_on: [analyze_code]
    steps:
      - id: quality_review
        agent: code
        action: review_quality
        params:
          code: ${load_code.result.code}
          analysis: ${analyze_code.result}
      
      - id: performance_review
        agent: code
        action: review_performance
        params:
          code: ${load_code.result.code}
          analysis: ${analyze_code.result}
      
      - id: security_review
        agent: code
        action: review_security
        params:
          code: ${load_code.result.code}
          analysis: ${analyze_code.result}
  
  - id: generate_report
    name: 生成审查报告
    agent: chat
    action: generate_report
    depends_on: [review_parallel]
    params:
      reviews:
        quality: ${quality_review.result}
        performance: ${performance_review.result}
        security: ${security_review.result}

output:
  report: ${generate_report.result}
  reviews:
    quality: ${quality_review.result}
    performance: ${performance_review.result}
    security: ${security_review.result}
```

## 最佳实践

1. **流程设计**
   - 保持步骤简单和专注
   - 明确步骤之间的依赖关系
   - 合理使用条件分支和循环
   - 添加适当的错误处理和重试

2. **参数管理**
   - 使用变量引用保持灵活性
   - 为参数提供默认值
   - 验证输入参数

3. **错误处理**
   - 为关键步骤添加重试机制
   - 定义清晰的错误消息
   - 支持部分结果返回

4. **性能优化**
   - 使用并行执行提高效率
   - 合理设置超时时间
   - 缓存可复用的结果

## 总结

SOP 流程编排提供了：

- ✅ **标准化执行**：确保任务按照预定义流程执行
- ✅ **质量控制**：通过流程保证执行质量
- ✅ **可重复性**：相同任务每次执行方式一致
- ✅ **灵活配置**：支持条件、循环、并行等复杂流程
- ✅ **易于维护**：通过配置文件定义，易于修改和扩展

SOP 与动态编排结合，为系统提供了完整的任务处理能力。

