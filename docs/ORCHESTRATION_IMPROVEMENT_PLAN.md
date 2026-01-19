# 编排逻辑改进方案

## 文档关系

本文档与以下文档共同构成了项目的模型管理和编排系统：

- **[多模型支持与模型切换技术实现](./design/multi-model-support-and-switching.md)**：介绍多模型支持的技术实现，包括模型注册、提供商管理、模型切换机制等
- **本文档**：介绍如何在编排层面使用多模型系统，包括任务分解、模型选择策略、工具调用优化等

**文档职责划分**：
- **多模型支持文档**：关注"如何支持多模型"（技术实现层面）
- **本文档**：关注"如何使用多模型"（应用策略层面）

> 💡 **提示**：在使用本文档中的模型选择策略之前，请先了解 [多模型支持与模型切换技术实现](./design/multi-model-support-and-switching.md) 中的模型注册、切换机制和 API 使用方法。

## 当前编排逻辑分析

### 1. 当前流程

```
用户输入
  ↓
技能匹配（Skill Registry）
  ↓ (如果匹配)
技能执行
  ↓ (如果失败或不匹配)
模型选择（_select_model）
  ↓
LLM 调用（_chat_with_tools）
  ↓
工具调用循环（最多 5 轮）
  ↓
返回结果
```

### 2. 当前问题

#### 2.1 模型选择不够智能
- **问题**: 使用简单的关键词匹配，容易误判
- **问题**: 模型选择逻辑在任务开始时执行一次，无法根据执行情况动态调整
- **问题**: 推理模型和编程模型的使用场景区分不够清晰

#### 2.2 工具调用策略单一
- **问题**: 所有工具调用都使用同一个模型
- **问题**: 没有根据工具类型选择最适合的模型
- **问题**: 工具调用失败后没有智能重试或切换策略

#### 2.3 缺乏任务分解和规划
- **问题**: 复杂任务没有分解为子任务
- **问题**: 没有任务执行计划
- **问题**: 无法并行执行独立任务

#### 2.4 推理模型和编程模型使用不充分
- **问题**: 推理模型主要用于模型选择，没有用于任务规划
- **问题**: 编程模型主要用于代码生成，没有用于工具选择决策
- **问题**: 两种模型的能力没有充分发挥

---

## 改进方案

### 方案 1: 分层模型使用策略

> 📖 **技术基础**：本方案基于 [多模型支持与模型切换技术实现](./design/multi-model-support-and-switching.md) 中实现的模型注册表和 LLMService。在使用本方案前，请确保已了解模型切换机制和 API 使用方法。

#### 1.1 三层模型架构

系统将模型按照能力分为三层，每层负责不同的任务类型：

```
┌─────────────────────────────────────┐
│  推理模型 (Reasoning Model)         │
│  - 任务理解和分解                    │
│  - 工具选择决策                      │
│  - 执行策略规划                      │
│  - 支持思考过程输出                  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  对话模型 (Chat Model)               │
│  - 日常对话                          │
│  - 信息检索                          │
│  - 简单工具调用                      │
│  - 通用文本生成                      │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  编程模型 (Code Model)               │
│  - 代码生成和执行                     │
│  - 复杂脚本编写                      │
│  - 系统命令执行                      │
│  - 代码审查和优化                    │
└─────────────────────────────────────┘
```

**模型配置**（基于环境变量）：

系统通过 `.env` 文件中的环境变量配置三种类型的模型：

- **推理模型（REASONING_MODEL）**：
  - 环境变量：`REASONING_MODEL`
  - 默认值：`deepseek-reasoner`
  - 配置示例：
    ```bash
    REASONING_MODEL=deepseek-r1                    # DeepSeek 平台
    REASONING_MODEL=openai-o3                      # OpenAI 平台（通过 TheTurbo.ai 网关）
    REASONING_MODEL=bailian-deepseek-v3.2          # 百炼平台
    REASONING_MODEL=anthropic-claude-opus-4-20250514  # Anthropic 平台（通过 TheTurbo.ai 网关）
    ```

- **对话模型（CHAT_MODEL）**：
  - 环境变量：`CHAT_MODEL`
  - 默认值：`deepseek-chat`
  - 配置示例：
    ```bash
    CHAT_MODEL=openai-gpt-5                        # OpenAI 平台（通过 TheTurbo.ai 网关）
    CHAT_MODEL=bailian-qwen3-max                   # 百炼平台
    CHAT_MODEL=anthropic-claude-3-5-sonnet-20241022  # Anthropic 平台（通过 TheTurbo.ai 网关）
    ```

- **编程模型（CODE_MODEL）**：
  - 环境变量：`CODE_MODEL`
  - 默认值：`deepseek-coder`
  - 配置示例：
    ```bash
    CODE_MODEL=deepseek-coder                      # DeepSeek 平台
    CODE_MODEL=bailian-qwen3-coder-plus-2025-09-23  # 百炼平台
    CODE_MODEL=openai-gpt-5-codex                 # OpenAI 平台（通过 TheTurbo.ai 网关）
    ```

> 💡 **重要说明**：
> - 模型选择**不是自主的**，而是基于 `.env` 文件中的配置
> - 系统通过 `ModelConfigManager` 读取环境变量获取三种类型的模型
> - 编排系统根据任务类型从这三个配置的模型中选择一个使用
> - 使用 `LLMService.set_model()` 方法可以在不同模型之间切换，系统会自动处理提供商切换和客户端重新初始化
> - 详见 [多模型支持文档](./design/multi-model-support-and-switching.md) 和 `env.example` 文件

#### 1.2 模型选择决策树

```
任务输入
  ↓
是否需要复杂推理？
  ├─ 是 → 推理模型
  │   ├─ 任务分解
  │   ├─ 工具选择
  │   └─ 执行规划
  │   └─ 使用 LLMService.set_model(reasoning_model)
  │
  └─ 否 → 是否需要代码执行？
      ├─ 是 → 编程模型
      │   ├─ 代码生成
      │   └─ 命令执行
      │   └─ 使用 LLMService.set_model(code_model)
      │
      └─ 否 → 对话模型
          ├─ 日常对话
          └─ 简单工具调用
          └─ 使用 LLMService.set_model(chat_model)
```

**实现示例**：

```python
from backend.services.llm.llm_service import LLMService
from backend.services.llm.model_config import get_model_config_manager

# 初始化 LLMService（支持自动模型切换）
llm_service = LLMService()

# 从环境变量配置获取模型（通过 ModelConfigManager）
config_manager = get_model_config_manager()
chat_model = config_manager.get_chat_model()        # 从 CHAT_MODEL 环境变量读取
code_model = config_manager.get_code_model()        # 从 CODE_MODEL 环境变量读取
reasoning_model = config_manager.get_reasoning_model()  # 从 REASONING_MODEL 环境变量读取

# 根据任务类型选择模型（从配置的模型中选择）
if needs_reasoning:
    # 使用配置的推理模型
    llm_service.set_model(reasoning_model)
elif needs_code:
    # 使用配置的编程模型
    llm_service.set_model(code_model)
else:
    # 使用配置的对话模型
    llm_service.set_model(chat_model)

# 执行任务
response = await llm_service.chat(user_prompt=task)
```

> 📖 **配置说明**：
> - 模型选择基于 `.env` 文件中的 `CHAT_MODEL`、`CODE_MODEL`、`REASONING_MODEL` 环境变量
> - 系统通过 `ModelConfigManager` 统一管理模型配置
> - 编排系统根据任务类型从这三个配置的模型中选择一个使用
> - 详见 [多模型支持文档](./design/multi-model-support-and-switching.md) 中的"模型配置管理"章节

### 方案 2: 智能任务分解和规划

#### 2.1 使用推理模型进行任务分解

```python
async def decompose_task(self, task: str) -> List[SubTask]:
    """使用推理模型分解复杂任务"""
    prompt = f"""
    分析以下任务，将其分解为可执行的子任务：
    
    任务：{task}
    
    可用工具：
    {self._format_tools_for_llm()}
    
    请返回 JSON 格式的子任务列表，每个子任务包含：
    - name: 子任务名称
    - description: 子任务描述
    - required_tools: 需要的工具列表
    - dependencies: 依赖的其他子任务
    - estimated_complexity: 复杂度评估（simple/medium/complex）
    """
    
    # 使用推理模型
    response = await self.llm_service.chat(
        model=self.reasoning_model,
        system_prompt="你是一个任务规划专家，擅长将复杂任务分解为可执行的子任务。",
        user_prompt=prompt
    )
    
    return parse_subtasks(response)
```

#### 2.2 任务执行规划

```python
async def plan_execution(self, subtasks: List[SubTask]) -> ExecutionPlan:
    """使用推理模型规划任务执行"""
    prompt = f"""
    为以下子任务制定执行计划：
    
    子任务：
    {format_subtasks(subtasks)}
    
    请考虑：
    1. 任务依赖关系
    2. 可以并行执行的任务
    3. 每个任务最适合的模型（推理/对话/编程）
    4. 错误处理和重试策略
    
    返回 JSON 格式的执行计划。
    """
    
    # 使用推理模型
    plan = await self.llm_service.chat(
        model=self.reasoning_model,
        system_prompt="你是一个执行规划专家，擅长制定高效的任务执行计划。",
        user_prompt=prompt
    )
    
    return parse_execution_plan(plan)
```

### 方案 3: 动态模型切换

#### 3.1 根据工具类型选择模型

```python
from backend.services.llm.llm_service import LLMService
from backend.services.llm.model_config import get_model_config_manager

def select_model_for_tool(self, tool_name: str, task_context: Dict) -> str:
    """根据工具类型和任务上下文选择最适合的模型"""
    
    # 从环境变量配置获取模型
    config_manager = get_model_config_manager()
    chat_model = config_manager.get_chat_model()
    code_model = config_manager.get_code_model()
    reasoning_model = config_manager.get_reasoning_model()
    
    tool = self.tool_registry.get_tool(tool_name)
    
    # 代码执行工具 → 使用配置的编程模型
    if tool_name in ['execute_code', 'jupyter']:
        # 使用 LLMService 切换模型
        self.llm_service.set_model(code_model)
        return code_model
    
    # 需要复杂推理的工具 → 使用配置的推理模型
    if tool_name in ['browser', 'file_search']:
        # 检查任务复杂度
        if task_context.get('complexity') == 'high':
            self.llm_service.set_model(reasoning_model)
            return reasoning_model
    
    # 简单工具 → 使用配置的对话模型
    self.llm_service.set_model(chat_model)
    return chat_model
```

> 💡 **重要说明**：
> - 模型选择基于 `.env` 文件中的环境变量配置，不是硬编码的模型名称
> - `LLMService.set_model()` 会自动检测模型所属的提供商，如果需要切换提供商，会自动重新初始化客户端
> - 详见 [多模型支持文档](./design/multi-model-support-and-switching.md) 中的"动态模型切换"和"模型配置管理"章节

#### 3.2 根据执行结果动态调整

```python
async def process_with_adaptive_model(self, task: str, context: Dict):
    """使用自适应模型处理任务"""
    
    # 1. 初始模型选择
    current_model = await self._select_model(task)
    
    # 2. 执行任务
    result = await self._execute_with_model(current_model, task, context)
    
    # 3. 评估结果
    if result.needs_reasoning:
        # 切换到推理模型重新处理
        current_model = self.reasoning_model
        result = await self._execute_with_model(current_model, task, context)
    
    elif result.needs_code:
        # 切换到编程模型
        current_model = self.code_model
        result = await self._execute_with_model(current_model, task, context)
    
    return result
```

### 方案 4: 工具调用优化

#### 4.1 工具选择决策

```python
async def select_tools(self, task: str, available_tools: List[Tool]) -> List[Tool]:
    """使用推理模型选择最合适的工具"""
    
    prompt = f"""
    分析以下任务，选择最合适的工具：
    
    任务：{task}
    
    可用工具：
    {format_tools(available_tools)}
    
    请考虑：
    1. 任务的本质需求
    2. 工具的功能和限制
    3. 工具的组合使用
    4. 执行效率
    
    返回工具列表和选择理由。
    """
    
    # 使用推理模型进行工具选择
    response = await self.llm_service.chat(
        model=self.reasoning_model,
        system_prompt="你是一个工具选择专家，擅长为任务选择最合适的工具。",
        user_prompt=prompt
    )
    
    return parse_tool_selection(response)
```

#### 4.2 工具调用策略

```python
class ToolCallStrategy:
    """工具调用策略"""
    
    async def execute_tool(self, tool: Tool, params: Dict, model: str):
        """根据工具类型选择执行策略"""
        
        # 代码执行工具 → 使用编程模型验证参数
        if tool.name in ['execute_code', 'jupyter']:
            validated_params = await self._validate_with_code_model(tool, params)
            return await tool.execute(**validated_params)
        
        # 需要推理的工具 → 使用推理模型优化参数
        if tool.requires_reasoning:
            optimized_params = await self._optimize_with_reasoning_model(tool, params)
            return await tool.execute(**optimized_params)
        
        # 默认执行
        return await tool.execute(**params)
```

### 方案 5: 并行执行和优化

#### 5.1 识别可并行任务

```python
async def identify_parallel_tasks(self, subtasks: List[SubTask]) -> List[List[SubTask]]:
    """使用推理模型识别可以并行执行的任务"""
    
    prompt = f"""
    分析以下子任务，识别可以并行执行的任务组：
    
    子任务：
    {format_subtasks(subtasks)}
    
    考虑因素：
    1. 任务之间的依赖关系
    2. 资源竞争（如文件访问）
    3. 工具可用性
    
    返回可以并行执行的任务组。
    """
    
    # 使用推理模型
    response = await self.llm_service.chat(
        model=self.reasoning_model,
        system_prompt="你是一个并行执行优化专家。",
        user_prompt=prompt
    )
    
    return parse_parallel_groups(response)
```

#### 5.2 执行优化

```python
async def execute_optimized(self, plan: ExecutionPlan):
    """优化执行计划"""
    
    # 1. 识别并行任务
    parallel_groups = await self.identify_parallel_tasks(plan.subtasks)
    
    # 2. 并行执行
    results = []
    for group in parallel_groups:
        group_results = await asyncio.gather(*[
            self._execute_subtask(subtask) for subtask in group
        ])
        results.extend(group_results)
    
    # 3. 处理依赖任务
    for subtask in plan.sequential_tasks:
        result = await self._execute_subtask(subtask, context=results)
        results.append(result)
    
    return results
```

### 方案 6: 深度研究功能

> 📖 **技术基础**：本方案基于方案2（任务分解）和方案3（动态模型切换），专门用于需要深入信息收集和分析的研究类任务。详见 [深度研究功能设计](./DEEP_RESEARCH_DESIGN.md) 和 [使用指南](./DEEP_RESEARCH_USAGE.md)。

#### 6.1 功能概述

深度研究功能允许 AI 进行多轮、深入的信息收集、分析和综合，生成高质量的研究报告。适用于需要全面调研、深度分析的任务。

**核心能力**：
1. **多轮信息收集**：通过多轮搜索和工具调用收集信息
2. **智能分析**：使用推理模型分析和综合信息
3. **自适应迭代**：基于信息缺口自动决定是否继续研究
4. **报告生成**：生成结构化的研究报告

#### 6.2 研究流程

```python
from backend.core.agent.research import ResearchManager

class Orchestrator:
    def __init__(self):
        # ... 现有初始化 ...
        self.research_manager = ResearchManager(
            self.llm_service,
            self.tool_registry,
            self.planning_manager
        )
    
    async def deep_research(
        self,
        question: str,
        depth: str = "medium",  # "shallow", "medium", "deep"
        max_iterations: int = 5,
        context: Optional[Dict] = None
    ) -> ResearchReport:
        """执行深度研究"""
        session_id = context.get("session_id") if context else None
        return await self.research_manager.conduct_research(
            question,
            depth=depth,
            max_iterations=max_iterations,
            session_id=session_id
        )
```

#### 6.3 研究深度级别

**Shallow（浅层）**：
- 轮次：1-2 轮搜索
- 用途：快速回答简单问题
- 示例："Python 是什么？"

**Medium（中等）**：
- 轮次：3-5 轮搜索
- 用途：多角度分析，生成基本报告
- 示例："Python 异步编程的最佳实践"

**Deep（深度）**：
- 轮次：5+ 轮搜索
- 用途：全面分析，生成详细报告
- 示例："深度研究量子计算的最新进展"

#### 6.4 自动检测研究任务

```python
async def stream_process(self, task: str, context: Optional[Dict] = None):
    """流式处理任务"""
    
    # 检测是否是研究任务
    research_keywords = ["研究", "调研", "分析", "调查", "深度", "详细", "report"]
    is_research_task = any(kw in task.lower() for kw in research_keywords)
    
    if is_research_task:
        # 使用深度研究功能
        yield "开始深度研究...\n"
        
        report = await self.deep_research(
            task,
            depth="medium",
            context=context
        )
        
        yield f"\n# 研究报告\n\n"
        yield f"## 摘要\n{report.summary}\n\n"
        yield f"## 结论\n{report.conclusion}\n"
    else:
        # 正常流程
        async for chunk in self._stream_normal_process(task, context):
            yield chunk
```

#### 6.5 与规划文件集成

深度研究功能自动将研究发现记录到 `findings.md`：

```python
# 研究发现自动记录到规划文件
report = await research_manager.conduct_research(
    "研究问题",
    depth="medium",
    session_id="session_123"
)

# 研究发现已记录到 {session_id}_findings.md
```

#### 6.6 配置选项

在 `.env` 文件中添加：

```bash
# 深度研究配置
ENABLE_DEEP_RESEARCH=true
DEEP_RESEARCH_MAX_ITERATIONS=5
DEEP_RESEARCH_DEFAULT_DEPTH=medium
DEEP_RESEARCH_MIN_CONFIDENCE=0.8
```

#### 6.7 实施位置

**文件结构**：
```
backend/core/agent/research/
├── __init__.py          # 模块导出
├── models.py            # 数据模型（ResearchFinding, ResearchAnalysis, ResearchReport等）
└── manager.py           # 研究管理器（ResearchManager）
```

**集成点**：
- `orchestrator.py`：添加 `deep_research()` 方法和自动检测逻辑
- `stream_process()`：检测研究任务并调用深度研究功能

---

## 前期准备工作

在开始实施改进计划之前，需要完成以下前期准备工作：

### 1. 环境配置准备

#### 1.1 模型配置验证

确保 `.env` 文件中已正确配置三种类型的模型：

```bash
# 必需配置：三种类型的模型
CHAT_MODEL=deepseek-chat                    # 对话模型
CODE_MODEL=deepseek-coder                   # 编程模型
REASONING_MODEL=deepseek-reasoner            # 推理模型

# 对应的 API Key 配置
DEEPSEEK_API_KEY=sk-xxx                      # DeepSeek 平台
# 或
BAILIAN_API_KEY=sk-xxx                       # 百炼平台
# 或
TURBOGATEWAY_API_KEY=sk-xxx                  # TheTurbo.ai 网关（用于 OpenAI、Anthropic 等）
```

**验证步骤**：
```python
from backend.services.llm.model_config import get_model_config_manager

config_manager = get_model_config_manager()
validation_result = config_manager.validate_config()
# 检查：{"chat": True, "code": True, "reasoning": True}
```

#### 1.2 API Key 可用性测试

确保所有配置的模型 API Key 都可用：

```python
# 测试每个模型的 API Key
from backend.services.llm.llm_service import LLMService

config_manager = get_model_config_manager()

for model_type in ["chat", "code", "reasoning"]:
    model_name = config_manager.get_model_config_by_type(model_type).model_name
    try:
        llm_service = LLMService(model=model_name)
        # 简单测试调用
        response = await llm_service.chat(user_prompt="测试")
        print(f"✅ {model_type} 模型 ({model_name}) 可用")
    except Exception as e:
        print(f"❌ {model_type} 模型 ({model_name}) 不可用: {e}")
```

### 2. 代码基础设施准备

#### 2.1 数据模型定义

需要定义以下数据模型（如果尚未存在）：

```python
# backend/core/agent/models.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

@dataclass
class SubTask:
    """子任务"""
    name: str
    description: str
    required_tools: List[str]
    dependencies: List[str]  # 依赖的其他子任务名称
    estimated_complexity: TaskComplexity
    recommended_model: Optional[str] = None  # 推荐的模型类型

@dataclass
class ExecutionPlan:
    """执行计划"""
    subtasks: List[SubTask]
    parallel_groups: List[List[str]]  # 可以并行执行的任务组
    sequential_tasks: List[str]  # 需要顺序执行的任务
    error_handling_strategy: Dict[str, Any]

@dataclass
class ExecutionState:
    """执行状态（用于恢复）"""
    session_id: str
    messages: List[Dict]
    current_iteration: int
    tool_call_history: List[Dict]
    last_tool_result: Optional[Dict] = None
```

#### 2.2 工具分类元数据

为工具添加分类和元数据：

```python
# 在 ToolRegistry 或工具基类中添加
class ToolMetadata:
    """工具元数据"""
    requires_reasoning: bool = False  # 是否需要推理
    requires_code: bool = False       # 是否需要代码能力
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    recommended_model: Optional[str] = None  # 推荐的模型类型
```

#### 2.3 配置管理扩展

扩展配置管理，支持执行控制参数：

```python
# 在 env.example 中添加
# 工具调用循环最大迭代次数
MAX_TOOL_ITERATIONS_STREAM = 100      # 流式处理
MAX_TOOL_ITERATIONS_NON_STREAM = 5   # 非流式处理

# 是否启用智能模型选择
ENABLE_SMART_MODEL_SELECTION = true

# 是否启用任务分解
ENABLE_TASK_DECOMPOSITION = true

# 是否启用并行执行
ENABLE_PARALLEL_EXECUTION = true
```

### 3. 测试环境准备

#### 3.1 单元测试框架

准备测试基础设施：

```python
# tests/orchestration/test_model_selection.py
# tests/orchestration/test_task_decomposition.py
# tests/orchestration/test_parallel_execution.py
# tests/orchestration/test_execution_state.py
```

#### 3.2 集成测试场景

准备测试场景：

```python
# 测试场景列表
TEST_SCENARIOS = [
    {
        "name": "简单对话任务",
        "task": "今天天气怎么样？",
        "expected_model": "chat",
        "expected_iterations": 1
    },
    {
        "name": "代码生成任务",
        "task": "写一个 Python 函数计算斐波那契数列",
        "expected_model": "code",
        "expected_iterations": 2
    },
    {
        "name": "复杂推理任务",
        "task": "分析这个项目的代码结构并生成报告",
        "expected_model": "reasoning",
        "expected_iterations": 5,
        "should_decompose": True
    }
]
```

### 4. 监控和日志准备

#### 4.1 性能监控

准备监控指标：

```python
# 需要监控的指标
METRICS = {
    "model_selection_time": [],      # 模型选择耗时
    "task_decomposition_time": [],    # 任务分解耗时
    "tool_call_count": [],           # 工具调用次数
    "model_switch_count": [],         # 模型切换次数
    "execution_time": [],             # 总执行时间
    "api_call_count": {},            # 各模型的 API 调用次数
}
```

#### 4.2 日志增强

增强日志记录：

```python
# 需要记录的日志
LOGGING_CONFIG = {
    "model_selection": {
        "level": "INFO",
        "format": "模型选择: {task} -> {model} (耗时: {time}ms)"
    },
    "task_decomposition": {
        "level": "INFO",
        "format": "任务分解: {task} -> {subtask_count} 个子任务"
    },
    "model_switch": {
        "level": "INFO",
        "format": "模型切换: {from_model} -> {to_model} (原因: {reason})"
    }
}
```

### 5. 文档和规范准备

#### 5.1 API 文档

准备 API 文档模板：

```markdown
# 新增 API 文档
- TaskDecomposer API
- ExecutionPlanner API
- ExecutionStateManager API
- ParallelExecutor API
```

#### 5.2 代码规范

制定代码规范：

- 命名规范（SubTask、ExecutionPlan 等）
- 错误处理规范
- 日志记录规范
- 测试覆盖要求

### 6. 风险评估和缓解准备

#### 6.1 回滚方案

准备回滚机制：

```python
# 功能开关
FEATURE_FLAGS = {
    "smart_model_selection": True,      # 可以快速关闭
    "task_decomposition": False,        # 分阶段启用
    "parallel_execution": False,        # 分阶段启用
    "execution_state_save": False       # 分阶段启用
}
```

#### 6.2 降级策略

准备降级策略：

```python
# 如果新功能失败，自动降级到旧逻辑
if not enable_smart_model_selection:
    # 使用原有的简单关键词匹配
    return simple_keyword_match(task)
```

### 7. 依赖检查

#### 7.1 Python 依赖

确保以下依赖已安装：

```bash
# 必需依赖（应该已存在）
- openai (用于 LLM 调用)
- httpx (用于 HTTP 客户端)
- asyncio (用于异步执行)

# 可能需要的新依赖
- pydantic (用于数据验证，如果使用)
- tenacity (用于重试机制，如果使用)
```

#### 7.2 系统依赖

确保系统依赖可用：

```bash
# 检查工具依赖
- 代码执行工具依赖
- 浏览器工具依赖
- 其他工具依赖
```

### 8. 数据准备

#### 8.1 测试数据

准备测试数据：

```python
# 测试任务集合
TEST_TASKS = {
    "simple": ["今天天气怎么样？", "执行 ls /home"],
    "medium": ["写一个 Python 函数", "搜索 Python 教程"],
    "complex": ["分析项目代码并生成报告", "下载视频并提取字幕"]
}
```

#### 8.2 基准测试

建立基准测试：

```python
# 记录当前性能基准
BASELINE_METRICS = {
    "average_response_time": 0,
    "average_tool_calls": 0,
    "success_rate": 0
}
```

### 9. 团队准备

#### 9.1 知识培训

- 多模型系统使用培训
- 任务分解策略培训
- 并行执行原理培训
- 深度研究功能使用培训

#### 9.2 代码审查准备

- 制定代码审查清单
- 准备审查模板
- 确定审查流程

### 10. 检查清单

在开始实施前，请确认：

- [ ] `.env` 文件中已配置三种类型的模型
- [ ] 所有配置的模型 API Key 已验证可用
- [ ] 数据模型已定义（SubTask、ExecutionPlan 等）
- [ ] 工具分类元数据已添加
- [ ] 配置管理已扩展支持新参数
- [ ] 测试框架已准备
- [ ] 监控和日志系统已增强
- [ ] API 文档模板已准备
- [ ] 代码规范已制定
- [ ] 回滚方案已准备
- [ ] 降级策略已设计
- [ ] 所有依赖已安装
- [ ] 测试数据已准备
- [ ] 基准测试已建立
- [ ] 团队培训已完成

## 实施建议

### 阶段 1: 基础改进（1-2 周）

**前提条件**：完成前期准备 1-4 项

1. **改进模型选择逻辑**
   - 使用推理模型进行更智能的模型选择
   - 添加任务复杂度评估
   - 实现快速规则判断（保留现有逻辑作为 fallback）

2. **工具调用优化**
   - 根据工具类型选择模型
   - 添加工具参数验证和优化

### 阶段 2: 任务分解（2-3 周）

**前提条件**：阶段 1 完成，前期准备 5-7 项完成

3. **实现任务分解**
   - 使用推理模型分解复杂任务
   - 识别任务依赖关系
   - 创建执行计划

4. **动态模型切换**
   - 根据执行结果切换模型
   - 实现自适应策略

### 阶段 3: 高级优化（3-4 周）

**前提条件**：阶段 2 完成，前期准备 8-10 项完成

5. **并行执行**
   - 识别可并行任务
   - 实现并行执行框架

6. **性能优化**
   - 缓存模型选择结果
   - 优化工具调用顺序
   - 实现智能重试

---

## 预期效果

### 1. 模型使用效率提升
- **推理模型**: 用于任务规划、工具选择、策略制定（充分发挥推理能力）
- **编程模型**: 用于代码生成、命令执行（充分发挥编程能力）
- **对话模型**: 用于日常对话、简单工具调用（保持高效）

### 2. 任务执行效率提升
- 复杂任务分解为子任务，执行更清晰
- 并行执行独立任务，速度提升
- 智能工具选择，减少无效调用
- 深度研究功能，生成高质量研究报告

### 3. 用户体验提升
- 更准确的工具选择
- 更快的响应速度
- 更好的错误处理

---

## 测试策略

### 1. 单元测试
- 模型选择逻辑测试
- 任务分解测试
- 工具选择测试

### 2. 集成测试
- 端到端任务执行测试
- 模型切换测试
- 并行执行测试
- 深度研究功能测试

### 3. 性能测试
- 执行时间对比
- 模型调用次数统计
- 资源使用监控

---

## 风险与缓解

### 风险 1: 模型调用次数增加
- **缓解**: 实现结果缓存，避免重复调用
- **缓解**: 使用快速规则判断，减少 LLM 调用

### 风险 2: 执行时间增加
- **缓解**: 并行执行独立任务
- **缓解**: 优化模型选择逻辑

### 风险 3: 复杂度增加
- **缓解**: 分阶段实施，逐步验证
- **缓解**: 保留现有逻辑作为 fallback

---

## 当前工具和服务状态

### 已测试的工具（24 个）

根据 `backend/core/agent/tools/tests/` 目录，当前有以下工具的测试：

1. **代码执行类**
   - `code_executor_tool` - 代码执行工具（613 行测试，覆盖全面）
   - `jupyter_tool` - Jupyter 交互式执行

2. **文件操作类**
   - `file_search_tool` - 文件搜索
   - `file_organizer_tool` - 文件组织
   - `pdf_parser_tool` - PDF 解析（501 行测试，支持多种后端）

3. **网络搜索类**
   - `google_search_tool` - Google 搜索
   - `wikipedia_tool` - Wikipedia 搜索
   - `zhihu_zhida_tool` - 知乎搜索

4. **媒体处理类**
   - `video_downloader_tool` - 视频下载
   - `ffmpeg_tool` - 视频处理
   - `whisper_tool` - 语音识别

5. **浏览器和编辑类**
   - `browser_tool` - 浏览器自动化
   - `gvim_tool` - 编辑器集成
   - `mediawiki_tool` - MediaWiki 编辑

6. **其他工具**
   - `weather_tool` - 天气查询
   - `orchestrator_tool_integration` - 编排器集成测试

### 工具测试覆盖情况

- **代码执行工具**: 覆盖全面，包括参数验证、资源使用、风险检测、Bash 脚本等
- **PDF 解析工具**: 支持多种后端（pypdf、pdfplumber、camelot），有真实 PDF 测试
- **其他工具**: 基本功能测试覆盖

### 工具分类建议

基于测试结果，可以将工具分为以下类别：

1. **代码执行类** → 使用编程模型
2. **搜索检索类** → 使用对话模型（简单）或推理模型（复杂查询）
3. **文件处理类** → 使用对话模型（简单）或编程模型（复杂操作）
4. **媒体处理类** → 使用编程模型（FFmpeg）或对话模型（下载）
5. **浏览器自动化** → 使用推理模型（需要复杂决策）

## 推理模型的执行控制

### 执行轮数限制

推理模型在执行工具调用循环时有轮数限制：

1. **流式处理（stream_process）**：
   - 最大迭代次数：**100 轮**
   - 位置：`orchestrator.py` 的 `_chat_with_tools_stream()` 方法
   - 说明：适用于需要长时间运行和实时反馈的复杂任务

2. **非流式处理（process_dynamic）**：
   - 最大迭代次数：**5 轮**
   - 位置：`orchestrator.py` 的 `_chat_with_tools()` 方法
   - 说明：适用于快速响应的简单任务

#### 设计理由分析

**为什么非流式处理限制为 5 轮？**

这个设计基于以下考虑：

1. **用户体验优先**：
   - 非流式处理是**同步等待**模式，用户需要等待所有结果返回才能看到响应
   - 如果轮数太多（如 100 轮），用户会长时间等待而没有任何反馈
   - 5 轮是一个合理的快速响应限制，大多数简单任务可以在 5 轮内完成

2. **任务复杂度分离**：
   - **非流式处理**：设计用于**简单任务**（日常对话、简单工具调用等）
   - **流式处理**：设计用于**复杂任务**（需要多轮工具调用、长时间运行的任务）
   - 复杂任务应该使用流式处理，可以实时反馈进度，用户体验更好

3. **资源管理**：
   - 非流式处理会**占用连接直到完成**，限制轮数可以防止资源长时间占用
   - 5 轮限制可以快速释放资源，提高系统吞吐量

4. **快速失败原则**：
   - 如果 5 轮内无法完成任务，说明任务可能过于复杂
   - 应该提示用户使用流式处理或重新设计任务分解策略

**使用建议**：

```python
# ✅ 适合非流式处理（5轮限制）
- 简单查询："今天天气怎么样？"
- 单次工具调用："执行 ls /home"
- 简单对话："解释一下 Python 的列表推导式"

# ❌ 不适合非流式处理（需要流式处理）
- 复杂任务："分析这个项目的代码结构并生成报告"
- 多步骤任务："搜索相关信息，然后生成一篇文章"
- 长时间运行："下载视频并提取字幕"
```

**改进建议**：

如果发现 5 轮限制不够用，可以考虑：

1. **配置化限制**：
   ```python
   # 在环境变量中配置
   MAX_TOOL_ITERATIONS_NON_STREAM = 5  # 默认值
   MAX_TOOL_ITERATIONS_STREAM = 100    # 默认值
   ```

2. **智能切换**：
   ```python
   # 如果非流式处理达到限制，自动切换到流式处理
   if iteration >= max_iterations:
       # 提示用户任务较复杂，建议使用流式处理
       return "任务较复杂，建议使用流式处理模式"
   ```

3. **任务复杂度预判**：
   ```python
   # 在开始执行前，判断任务复杂度
   if is_complex_task(task):
       # 直接使用流式处理
       return stream_process(task)
   else:
       # 使用非流式处理
       return process_dynamic(task)
   ```

**代码实现**：

```python
# 流式处理
async def _chat_with_tools_stream(...):
    max_iterations = 100  # 最多 100 轮工具调用循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        # ... 工具调用逻辑 ...
    
    # 达到最大迭代次数
    yield "抱歉，工具调用未能成功获取信息。"

# 非流式处理
async def _chat_with_tools(...):
    max_iterations = 5  # 最多 5 轮工具调用循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        # ... 工具调用逻辑 ...
```

### 停止机制

系统提供以下停止机制：

1. **自动停止**：
   - 达到最大迭代次数时自动停止
   - LLM 返回最终回复（无工具调用）时停止
   - 工具执行失败且无法继续时停止

2. **任务取消**：
   - 通过 `TaskManager.cancel_task()` 取消任务
   - 任务状态会更新为 `CANCELLED`
   - 正在执行的工具调用会被中断

**代码实现**：

```python
from backend.core.agent.task_manager import task_manager

# 取消任务
async def cancel_task(task_id: str):
    success = await task_manager.cancel_task(task_id)
    if success:
        print(f"任务 {task_id} 已取消")
```

### 用户打断机制

#### 当前实现

1. **KeyboardInterrupt 处理**：
   - 在流式响应中处理 `KeyboardInterrupt`
   - 位置：`llm_service.py` 的 `stream_chat()` 方法

2. **任务管理器取消**：
   - 前端可以通过 API 调用取消任务
   - 任务状态会更新，但正在执行的工具调用可能无法立即中断

#### 改进建议

**方案 1：增强中断信号处理**

```python
import signal
import asyncio

class InterruptibleOrchestrator:
    """支持中断的编排器"""
    
    def __init__(self):
        self._interrupted = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._handle_interrupt)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """处理中断信号"""
        self._interrupted = True
        logger.info("收到中断信号，准备停止执行")
    
    async def _chat_with_tools_stream(self, ...):
        """支持中断的工具调用循环"""
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            # 检查中断标志
            if self._interrupted:
                yield "执行已被用户中断"
                return
            
            iteration += 1
            # ... 正常执行逻辑 ...
```

**方案 2：任务级别的中断检查**

```python
async def _chat_with_tools_stream(self, ...):
    """在每轮循环中检查任务状态"""
    max_iterations = 100
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # 检查任务是否被取消
        if task_id:
            task_info = task_manager.get_task(task_id)
            if task_info and task_info.status == TaskStatus.CANCELLED:
                yield "任务已被取消"
                return
        
        # ... 继续执行 ...
```

### 打断后的恢复机制

#### 当前状态

**问题**：系统目前**没有实现**打断后的恢复机制。

- 消息历史保存在 `ContextManager` 中
- 任务状态保存在 `TaskManager` 中
- 但中断后无法自动恢复到中断点继续执行

#### 改进方案

**方案 1：保存执行状态**

```python
@dataclass
class ExecutionState:
    """执行状态"""
    session_id: str
    messages: List[Dict]  # 消息历史
    current_iteration: int  # 当前迭代次数
    tool_call_history: List[Dict]  # 工具调用历史
    last_tool_result: Optional[Dict] = None  # 最后一个工具调用结果
    
    def save(self, file_path: str):
        """保存状态到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                "session_id": self.session_id,
                "messages": self.messages,
                "current_iteration": self.current_iteration,
                "tool_call_history": self.tool_call_history,
                "last_tool_result": self.last_tool_result
            }, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> 'ExecutionState':
        """从文件加载状态"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return cls(**data)
```

**方案 2：恢复执行**

```python
async def resume_execution(
    self,
    execution_state: ExecutionState,
    tools: Optional[list] = None
) -> AsyncIterator[str]:
    """从保存的状态恢复执行"""
    
    # 恢复消息历史
    messages = execution_state.messages
    
    # 从上次中断的地方继续
    max_iterations = 100
    iteration = execution_state.current_iteration
    
    while iteration < max_iterations:
        iteration += 1
        
        # 检查是否应该继续
        if self._should_stop():
            # 保存当前状态
            execution_state.current_iteration = iteration
            execution_state.messages = messages
            execution_state.save(f"state_{execution_state.session_id}.json")
            yield "执行已暂停，状态已保存"
            return
        
        # 继续执行...
        response = await self.llm_service.chat(messages=messages, tools=tools)
        # ... 处理响应和工具调用 ...
```

**方案 3：基于消息历史的恢复**

```python
async def resume_from_history(
    self,
    session_id: str,
    tools: Optional[list] = None
) -> AsyncIterator[str]:
    """基于消息历史恢复执行"""
    
    # 获取历史消息
    history = self.context_manager.get_messages_for_llm(
        session_id,
        max_messages=None,
        max_tokens=None
    )
    
    # 检查最后一条消息
    if history and history[-1]["role"] == "tool":
        # 最后一条是工具结果，说明工具已执行但 LLM 还未响应
        # 继续让 LLM 处理工具结果
        messages = history
    else:
        # 需要重新开始或继续
        messages = history
    
    # 继续执行工具调用循环
    async for chunk in self._chat_with_tools_stream(
        messages=messages,
        tools=tools
    ):
        yield chunk
```

### 实施建议

#### 阶段 1：基础改进（1 周）

1. **统一最大迭代次数配置**：
   ```python
   # 在配置文件中
   MAX_TOOL_ITERATIONS_STREAM = 100  # 流式处理
   MAX_TOOL_ITERATIONS_NON_STREAM = 5  # 非流式处理
   ```

2. **增强中断处理**：
   - 在每轮循环中检查任务状态
   - 支持 `KeyboardInterrupt` 和任务取消
   - 优雅地停止执行并保存状态

#### 阶段 2：状态保存（2 周）

3. **实现执行状态保存**：
   - 定期保存执行状态（消息历史、工具调用历史等）
   - 支持手动保存和自动保存
   - 状态文件格式设计

#### 阶段 3：恢复机制（2 周）

4. **实现恢复功能**：
   - 从保存的状态恢复执行
   - 基于消息历史恢复执行
   - 处理恢复时的边界情况

### 使用示例

#### 中断和恢复流程

```python
# 1. 开始执行任务
task_id = await orchestrator.stream_process("复杂任务")

# 2. 用户中断（通过 API 或信号）
await task_manager.cancel_task(task_id)

# 3. 保存执行状态（自动或手动）
execution_state = ExecutionState(
    session_id=session_id,
    messages=messages,
    current_iteration=iteration,
    tool_call_history=tool_calls
)
execution_state.save(f"state_{session_id}.json")

# 4. 恢复执行
saved_state = ExecutionState.load(f"state_{session_id}.json")
async for chunk in orchestrator.resume_execution(saved_state):
    print(chunk)
```

## 参考资源

### 核心代码
- 当前编排逻辑: `backend/core/agent/orchestrator.py`
- 任务管理器: `backend/core/agent/task_manager.py`
- 模型配置: `backend/services/llm/model_config.py`
- 工具测试: `backend/core/agent/tools/tests/` (24 个测试文件)
- 技能匹配: `backend/core/agent/skills/registry.py`
- 技能匹配逻辑: `backend/core/agent/skills/SKILL_MATCHING_LOGIC.md`

### 相关文档
- **[多模型支持与模型切换技术实现](./design/multi-model-support-and-switching.md)**：多模型系统的技术实现细节
  - 模型注册表（ModelRegistry）的使用
  - LLMService 的 API 和模型切换机制
  - 模型推荐系统的使用方法
  - 推理模型的思考过程处理
- **[深度研究功能设计](./DEEP_RESEARCH_DESIGN.md)**：深度研究功能的详细设计
  - 研究流程和架构
  - 研究策略和数据模型
  - 与规划文件的集成
- **[深度研究功能使用指南](./DEEP_RESEARCH_USAGE.md)**：深度研究功能的使用方法和示例

### 技术实现细节

在使用本文档中的方案时，需要了解以下技术细节：

1. **模型切换**：使用 `LLMService.set_model()` 方法，支持"平台-模型"格式
2. **模型推荐**：使用 `LLMService.recommend_models()` 方法根据任务类型推荐模型
3. **思考过程**：推理模型的思考过程处理机制（详见多模型支持文档）
4. **提供商切换**：系统会自动处理不同提供商之间的切换
5. **执行控制**：
   - 流式处理最多 100 轮工具调用
   - 非流式处理最多 5 轮工具调用
   - 支持任务取消，但恢复机制待实现
6. **深度研究**：
   - 使用 `ResearchManager` 进行多轮信息收集和分析
   - 支持三种研究深度（shallow, medium, deep）
   - 自动将研究发现记录到 `findings.md`
   - 详见 [深度研究功能设计](./DEEP_RESEARCH_DESIGN.md)

