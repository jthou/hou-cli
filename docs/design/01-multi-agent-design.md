# 多 Agent 协作设计文档

## 概述

本文档详细说明多 Agent 协作架构的设计和实现，这是处理复杂任务的核心机制。

## 设计目标

1. **处理复杂任务**：将复杂任务分解为多个子任务，由不同的专门化 Agent 处理
2. **专业化分工**：每个 Agent 专注于特定领域，提高处理质量
3. **灵活组合**：根据任务需求动态组合不同的 Agent
4. **可扩展性**：易于添加新的专门化 Agent

## 架构组件

### 1. Orchestrator (编排器)

**职责**：
- 分析用户任务的复杂性
- 将任务分解为子任务
- 为每个子任务选择合适的 Agent
- 协调 Agent 的执行
- 聚合多个 Agent 的结果

**工作流程**：
```
用户请求
    ↓
任务分析 (LLM)
    ↓
任务分解
    ↓
Agent 选择
    ↓
执行协调 (Coordinator)
    ↓
结果聚合
    ↓
返回最终结果
```

### 2. Coordinator (协调器)

**职责**：
- 管理多个 Agent 的执行顺序
- 支持多种执行模式
- 处理 Agent 之间的依赖关系
- 管理执行状态和错误处理

**执行模式**：

#### 顺序执行 (Sequential)
```
Agent1 → Agent2 → Agent3
```
- 适用于有依赖关系的任务
- 前一个 Agent 的输出作为后一个的输入

#### 并行执行 (Parallel)
```
    Agent1
    Agent2  → 结果聚合
    Agent3
```
- 适用于独立的任务
- 提高执行效率

#### 流水线执行 (Pipeline)
```
Agent1 → Agent2 → Agent3
  ↓       ↓       ↓
结果1   结果2   结果3
```
- 前一个的输出作为后一个的输入
- 同时处理多个阶段

### 3. 专门化 Agent

每个 Agent 专注于特定领域：

| Agent | 职责 | 使用场景 |
|-------|------|---------|
| Chat Agent | 对话和问答 | 一般性对话、问题回答 |
| PDF Agent | PDF 处理 | 文档分析、总结、提取 |
| Code Agent | 代码生成 | 代码生成、修改、优化 |
| Research Agent | 信息检索 | 网络搜索、信息收集 |
| Tool Agent | 工具调用 | 执行外部工具、系统命令 |

## 实现细节

### Agent 基类

```python
# backend/agent/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.services.llm_service import LLMService
from backend.agent.state import AgentState

class BaseAgent(ABC):
    """Agent 基类，所有专门化 Agent 继承此类"""
    
    def __init__(
        self, 
        name: str, 
        description: str,
        capabilities: list = None
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.llm_service = LLMService()
        self.state = AgentState()
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Any:
        """
        执行任务
        
        Args:
            task: 任务描述，包含任务类型、参数等
        
        Returns:
            任务执行结果
        """
        pass
    
    async def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Agent 思考过程"""
        system_prompt = f"""你是 {self.name}，{self.description}
        
你的能力包括：
{chr(10).join(f"- {cap}" for cap in self.capabilities)}

请仔细思考并执行任务。"""
        
        if context:
            system_prompt += f"\n\n上下文信息：{context}"
        
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=prompt
        )
        return response
    
    async def collaborate(
        self, 
        other_agent: str, 
        message: str
    ) -> str:
        """与其他 Agent 协作"""
        await self.state.send_message(
            from_agent=self.name,
            to_agent=other_agent,
            message=message
        )
```

### Orchestrator 实现

```python
# backend/agent/orchestrator.py
from typing import List, Dict, Any, Optional
from backend.agent.coordinator import AgentCoordinator, ExecutionMode
from backend.agent.agents.chat_agent import ChatAgent
from backend.agent.agents.pdf_agent import PDFAgent
from backend.agent.agents.code_agent import CodeAgent
from backend.services.llm_service import LLMService

class Orchestrator:
    """Agent 编排器，负责任务分解和 Agent 协调"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.coordinator = AgentCoordinator()
        
        # 注册所有可用的 Agent
        self.agents = {
            "chat": ChatAgent(),
            "pdf": PDFAgent(),
            "code": CodeAgent(),
            # ... 其他 Agent
        }
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """
        处理复杂任务
        
        Args:
            task: 用户任务描述
            context: 上下文信息
        
        Returns:
            最终结果
        """
        # 1. 任务分析
        task_plan = await self.analyze_task(task, context)
        
        # 2. 任务分解
        subtasks = self.decompose_task(task_plan)
        
        # 3. 执行协调
        results = await self.coordinator.execute(
            subtasks,
            mode=ExecutionMode[task_plan.get("execution_mode", "SEQUENTIAL")]
        )
        
        # 4. 结果聚合
        final_result = await self.aggregate_results(results, task)
        
        return final_result
    
    async def analyze_task(
        self, 
        task: str, 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        分析任务，确定需要的 Agent 和执行模式
        """
        analysis_prompt = f"""分析以下任务，确定：
1. 需要哪些 Agent（从以下选择：chat, pdf, code, research, tool）
2. 执行模式（sequential, parallel, pipeline）
3. 子任务列表

可用 Agent：
- chat: 对话和问答
- pdf: PDF 文档处理
- code: 代码生成和修改
- research: 信息检索和研究
- tool: 工具调用和执行

任务：{task}

请以 JSON 格式返回分析结果：
{{
    "agents_needed": ["agent1", "agent2"],
    "execution_mode": "sequential|parallel|pipeline",
    "subtasks": [
        {{
            "agent_type": "agent_name",
            "task": "子任务描述",
            "dependencies": []
        }}
    ]
}}"""
        
        response = await self.llm_service.chat(analysis_prompt)
        # 解析 JSON 响应
        import json
        task_plan = json.loads(response)
        return task_plan
    
    def decompose_task(self, task_plan: Dict) -> List[Dict]:
        """将任务计划分解为可执行的子任务"""
        return task_plan.get("subtasks", [])
    
    async def aggregate_results(
        self, 
        results: List[Dict], 
        original_task: str
    ) -> str:
        """
        聚合多个 Agent 的结果
        """
        if len(results) == 1:
            return results[0]["result"]
        
        # 使用 LLM 聚合结果
        aggregation_prompt = f"""原始任务：{original_task}

以下是多个 Agent 的执行结果：
{chr(10).join(f"{i+1}. {r['agent']}: {r['result']}" for i, r in enumerate(results))}

请将这些结果整合成一个完整的回答。"""
        
        aggregated = await self.llm_service.chat(aggregation_prompt)
        return aggregated
```

### Coordinator 实现

```python
# backend/agent/coordinator.py
import asyncio
from typing import List, Dict, Any
from enum import Enum
from backend.agent.state import AgentState

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    PIPELINE = "pipeline"      # 流水线执行

class AgentCoordinator:
    """Agent 协调器，管理多个 Agent 的执行"""
    
    def __init__(self):
        self.state = AgentState()
        self.execution_history = []
    
    async def execute(
        self, 
        subtasks: List[Dict],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        agents_registry: Dict = None
    ) -> List[Dict]:
        """
        执行多个子任务
        
        Args:
            subtasks: 子任务列表
            mode: 执行模式
            agents_registry: Agent 注册表
        
        Returns:
            执行结果列表
        """
        if mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(subtasks, agents_registry)
        elif mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(subtasks, agents_registry)
        elif mode == ExecutionMode.PIPELINE:
            return await self._execute_pipeline(subtasks, agents_registry)
    
    async def _execute_sequential(
        self, 
        subtasks: List[Dict],
        agents_registry: Dict
    ) -> List[Dict]:
        """顺序执行"""
        results = []
        for subtask in subtasks:
            try:
                agent = agents_registry[subtask["agent_type"]]
                result = await agent.execute(subtask["task"])
                results.append({
                    "subtask": subtask,
                    "result": result,
                    "agent": subtask["agent_type"],
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "subtask": subtask,
                    "result": None,
                    "agent": subtask["agent_type"],
                    "status": "error",
                    "error": str(e)
                })
        return results
    
    async def _execute_parallel(
        self, 
        subtasks: List[Dict],
        agents_registry: Dict
    ) -> List[Dict]:
        """并行执行"""
        async def execute_subtask(subtask):
            try:
                agent = agents_registry[subtask["agent_type"]]
                result = await agent.execute(subtask["task"])
                return {
                    "subtask": subtask,
                    "result": result,
                    "agent": subtask["agent_type"],
                    "status": "success"
                }
            except Exception as e:
                return {
                    "subtask": subtask,
                    "result": None,
                    "agent": subtask["agent_type"],
                    "status": "error",
                    "error": str(e)
                }
        
        tasks = [execute_subtask(st) for st in subtasks]
        results = await asyncio.gather(*tasks)
        return list(results)
    
    async def _execute_pipeline(
        self, 
        subtasks: List[Dict],
        agents_registry: Dict
    ) -> List[Dict]:
        """流水线执行"""
        results = []
        previous_result = None
        
        for subtask in subtasks:
            try:
                agent = agents_registry[subtask["agent_type"]]
                
                # 将前一个结果作为上下文
                if previous_result:
                    subtask["task"]["context"] = previous_result
                
                result = await agent.execute(subtask["task"])
                results.append({
                    "subtask": subtask,
                    "result": result,
                    "agent": subtask["agent_type"],
                    "status": "success"
                })
                previous_result = result
            except Exception as e:
                results.append({
                    "subtask": subtask,
                    "result": None,
                    "agent": subtask["agent_type"],
                    "status": "error",
                    "error": str(e)
                })
                break  # 流水线中断
        
        return results
```

## 使用示例

### 示例 1：PDF 分析 + 代码生成

```python
# 用户请求："分析这个PDF文件，然后根据内容生成Python代码"

orchestrator = Orchestrator()
result = await orchestrator.process(
    "分析 document.pdf 文件，然后根据内容生成Python代码"
)

# Orchestrator 会：
# 1. 分析任务，确定需要 PDF Agent 和 Code Agent
# 2. 使用 Pipeline 模式执行
# 3. PDF Agent 先分析文档
# 4. Code Agent 根据分析结果生成代码
# 5. 聚合结果返回
```

### 示例 2：并行文档处理

```python
# 用户请求："同时分析这两个PDF文件，然后对比结果"

result = await orchestrator.process(
    "同时分析 doc1.pdf 和 doc2.pdf，然后对比结果"
)

# Orchestrator 会：
# 1. 分析任务，确定需要 2 个 PDF Agent 和 1 个 Chat Agent
# 2. 使用 Parallel 模式并行处理两个 PDF
# 3. 使用 Chat Agent 对比结果
```

### 示例 3：复杂研究任务

```python
# 用户请求："研究Python异步编程，生成示例代码，并创建总结文档"

result = await orchestrator.process(
    "研究Python异步编程，生成示例代码，并创建总结文档"
)

# Orchestrator 会：
# 1. 分析任务，确定需要 Research Agent、Code Agent、Chat Agent
# 2. 使用 Pipeline 模式
# 3. Research Agent 研究主题
# 4. Code Agent 生成示例代码
# 5. Chat Agent 创建总结文档
```

## 扩展新 Agent

添加新的专门化 Agent 非常简单：

```python
# backend/agent/agents/custom_agent.py
from backend.agent.agents.base_agent import BaseAgent
from typing import Dict, Any

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="自定义Agent",
            description="你的Agent功能描述",
            capabilities=["能力1", "能力2"]
        )
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """实现你的Agent逻辑"""
        # 获取任务参数
        param1 = task.get("param1")
        param2 = task.get("param2")
        
        # 执行任务
        result = await self.think(
            f"处理任务：{task.get('task')}，参数：{param1}, {param2}"
        )
        
        return {
            "agent": self.name,
            "result": result
        }

# 在 Orchestrator 中注册
class Orchestrator:
    def __init__(self):
        # ...
        self.agents = {
            # ... 现有 Agent
            "custom": CustomAgent(),  # 添加新Agent
        }
```

## 最佳实践

1. **Agent 职责单一**：每个 Agent 应该专注于一个特定领域
2. **清晰的接口**：Agent 的 execute 方法应该有清晰的输入输出
3. **错误处理**：每个 Agent 应该处理自己的错误，不影响其他 Agent
4. **状态管理**：使用 AgentState 管理 Agent 之间的通信
5. **可测试性**：每个 Agent 应该可以独立测试

## 总结

多 Agent 协作架构提供了：

- ✅ **处理复杂任务的能力**：通过任务分解和 Agent 协作
- ✅ **专业化分工**：每个 Agent 专注于特定领域
- ✅ **灵活的执行模式**：支持顺序、并行、流水线执行
- ✅ **易于扩展**：可以轻松添加新的专门化 Agent
- ✅ **容错性**：单个 Agent 失败不影响整体流程

这种架构使得系统能够处理各种复杂的任务，同时保持代码的模块化和可维护性。

