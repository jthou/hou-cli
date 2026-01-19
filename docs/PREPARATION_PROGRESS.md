# 编排改进计划 - 前期准备工作进度

## 已完成的工作

### 1. ✅ 环境配置准备

#### 1.1 模型配置验证
- ✅ 创建了 `ModelConfigValidator` 类（`backend/core/agent/utils/model_config_validator.py`）
- ✅ 实现了配置验证功能
- ✅ 实现了 API Key 可用性测试功能
- ✅ 创建了可执行脚本 `scripts/validate_model_config.py`

**使用方法**：
```bash
python scripts/validate_model_config.py
```

#### 1.2 API Key 可用性测试
- ✅ 集成在 `ModelConfigValidator` 中
- ✅ 支持异步测试所有配置的模型
- ✅ 生成详细的测试报告

### 2. ✅ 代码基础设施准备

#### 2.1 数据模型定义
- ✅ 创建了 `backend/core/agent/models.py`
- ✅ 定义了以下数据模型：
  - `TaskComplexity`：任务复杂度枚举
  - `SubTask`：子任务数据模型
  - `ExecutionPlan`：执行计划数据模型
  - `ExecutionState`：执行状态数据模型（支持保存和恢复）
  - `ToolMetadata`：工具元数据模型

**特性**：
- 所有模型都支持序列化（`to_dict()`）和反序列化（`from_dict()`）
- `ExecutionState` 支持保存到文件和从文件加载
- 完整的类型提示

#### 2.2 工具分类元数据
- ✅ 创建了 `backend/core/agent/tools/metadata.py`
- ✅ 实现了 `ToolMetadataRegistry` 单例类
- ✅ 为所有工具定义了默认元数据：
  - `requires_reasoning`：是否需要推理能力
  - `requires_code`：是否需要代码能力
  - `recommended_model`：推荐的模型类型
  - `complexity`：任务复杂度
  - `can_parallel`：是否可以并行执行

**已配置的工具元数据**：
- 代码执行类：`execute_code`, `jupyter` → `code` 模型
- 搜索检索类：`google_search`, `wikipedia`, `zhihu_zhida` → `chat` 模型
- 文件处理类：`file_search`, `file_organizer`, `pdf_parser` → `chat`/`reasoning` 模型
- 媒体处理类：`video_downloader`, `ffmpeg`, `whisper` → `chat`/`code` 模型
- 浏览器自动化：`browser` → `reasoning` 模型

#### 2.3 配置管理扩展
- ✅ 扩展了 `ModelConfigManager`（`backend/services/llm/model_config.py`）
- ✅ 添加了以下配置方法：
  - `get_max_iterations_stream()`：获取流式处理最大迭代次数（默认 100）
  - `get_max_iterations_non_stream()`：获取非流式处理最大迭代次数（默认 5）
  - `is_smart_model_selection_enabled()`：检查是否启用智能模型选择（默认 true）
  - `is_task_decomposition_enabled()`：检查是否启用任务分解（默认 false）
  - `is_parallel_execution_enabled()`：检查是否启用并行执行（默认 false）

- ✅ 更新了 `env.example`，添加了新的配置项：
  - `MAX_TOOL_ITERATIONS_STREAM`
  - `MAX_TOOL_ITERATIONS_NON_STREAM`
  - `ENABLE_SMART_MODEL_SELECTION`
  - `ENABLE_TASK_DECOMPOSITION`
  - `ENABLE_PARALLEL_EXECUTION`

#### 2.4 工具基类扩展
- ✅ 更新了 `Tool` 基类（`backend/core/agent/tools/base.py`）
- ✅ 添加了元数据属性支持：
  - `requires_reasoning`
  - `requires_code`
  - `recommended_model`
  - `can_parallel`

- ✅ 更新了 `ToolRegistry`（`backend/core/agent/tools/registry.py`）
- ✅ 工具注册时自动同步元数据到元数据注册表

### 3. ✅ 测试环境准备

#### 3.1 单元测试框架
- ✅ 创建了测试模块 `backend/core/agent/tests/orchestration/`
- ✅ 创建了以下测试文件：
  - `test_model_selection.py`：模型选择逻辑测试
  - `test_task_decomposition.py`：任务分解测试
  - `test_tool_metadata.py`：工具元数据测试
  - `test_integration_scenarios.py`：集成测试场景

#### 3.2 集成测试场景
- ✅ 定义了 6 个测试场景：
  1. 简单对话任务
  2. 代码生成任务
  3. 简单工具调用
  4. 搜索任务
  5. 复杂推理任务
  6. 多步骤任务

- ✅ 创建了测试场景文档（`backend/core/agent/tests/orchestration/README.md`）

## 文件清单

### 新增文件

1. **数据模型**：
   - `backend/core/agent/models.py`

2. **工具元数据**：
   - `backend/core/agent/tools/metadata.py`

3. **验证工具**：
   - `backend/core/agent/utils/model_config_validator.py`
   - `scripts/validate_model_config.py`

4. **测试文件**：
   - `backend/core/agent/tests/orchestration/__init__.py`
   - `backend/core/agent/tests/orchestration/test_model_selection.py`
   - `backend/core/agent/tests/orchestration/test_task_decomposition.py`
   - `backend/core/agent/tests/orchestration/test_tool_metadata.py`
   - `backend/core/agent/tests/orchestration/test_integration_scenarios.py`
   - `backend/core/agent/tests/orchestration/README.md`

### 修改文件

1. **工具基类**：
   - `backend/core/agent/tools/base.py`：添加元数据属性支持

2. **工具注册表**：
   - `backend/core/agent/tools/registry.py`：添加元数据同步

3. **配置管理**：
   - `backend/services/llm/model_config.py`：添加执行控制参数方法

4. **配置文件**：
   - `env.example`：添加新的配置项

## 使用方法

### 1. 验证模型配置

```bash
# 运行验证脚本
python scripts/validate_model_config.py
```

### 2. 运行测试

```bash
# 运行所有编排测试
pytest backend/core/agent/tests/orchestration/ -v

# 运行特定测试
pytest backend/core/agent/tests/orchestration/test_model_selection.py -v
```

### 3. 使用工具元数据

```python
from backend.core.agent.tools.metadata import tool_metadata_registry

# 获取工具推荐的模型
model = tool_metadata_registry.get_recommended_model("execute_code")
# 返回: "code"

# 检查工具是否需要推理
needs_reasoning = tool_metadata_registry.requires_reasoning("browser")
# 返回: True

# 检查工具是否可以并行执行
can_parallel = tool_metadata_registry.can_parallel("google_search")
# 返回: True
```

### 4. 使用数据模型

```python
from backend.core.agent.models import SubTask, ExecutionPlan, TaskComplexity

# 创建子任务
subtask = SubTask(
    name="搜索信息",
    description="搜索相关信息",
    required_tools=["google_search"],
    recommended_model="chat",
    estimated_complexity=TaskComplexity.SIMPLE
)

# 创建执行计划
plan = ExecutionPlan(
    subtasks=[subtask],
    parallel_groups=[["任务1", "任务2"]],
    sequential_tasks=[]
)

# 序列化
data = plan.to_dict()

# 反序列化
restored_plan = ExecutionPlan.from_dict(data)
```

### 5. 使用配置管理

```python
from backend.services.llm.model_config import get_model_config_manager

config_manager = get_model_config_manager()

# 获取最大迭代次数
max_iterations = config_manager.get_max_iterations_stream()  # 默认 100

# 检查功能开关
if config_manager.is_smart_model_selection_enabled():
    # 使用智能模型选择
    pass
```

## 下一步工作

根据编排改进计划，下一步应该实施：

### 阶段 1: 基础改进（1-2 周）

1. **改进模型选择逻辑**
   - 使用推理模型进行更智能的模型选择
   - 添加任务复杂度评估
   - 实现快速规则判断（保留现有逻辑作为 fallback）

2. **工具调用优化**
   - 根据工具类型选择模型（使用工具元数据）
   - 添加工具参数验证和优化

### 阶段 2: 任务分解（2-3 周）

3. **实现任务分解**
   - 使用推理模型分解复杂任务
   - 识别任务依赖关系
   - 创建执行计划

4. **动态模型切换**
   - 根据执行结果切换模型
   - 实现自适应策略

### 阶段 3: 高级优化（3-4 周）

5. **并行执行**
   - 识别可并行任务
   - 实现并行执行框架

6. **性能优化**
   - 缓存模型选择结果
   - 优化工具调用顺序
   - 实现智能重试

## 注意事项

1. **环境变量配置**：
   - 确保 `.env` 文件中已配置 `CHAT_MODEL`、`CODE_MODEL`、`REASONING_MODEL`
   - 确保对应的 API Key 已配置

2. **测试运行**：
   - 运行测试前先运行验证脚本检查配置
   - 某些测试需要实际的 API 调用，可能会产生费用

3. **功能开关**：
   - 新功能通过环境变量控制，默认关闭（分阶段启用）
   - 可以在 `.env` 文件中启用/禁用功能

4. **向后兼容**：
   - 所有新功能都是可选的，不影响现有功能
   - 工具元数据有默认值，未配置的工具也能正常工作

