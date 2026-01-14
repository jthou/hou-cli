# 规划功能和任务管理功能集成测试

本目录包含规划功能和任务管理功能的集成测试。

## 测试文件说明

### 单元测试

- `backend/core/agent/tests/test_orchestrator_planning_integration.py`
  - 测试 Orchestrator 中规划功能和任务管理功能的集成
  - 测试规划文件创建、技能执行、工具调用、对话评估等

- `backend/core/agent/tests/test_task_manager_integration.py`
  - 测试任务管理器的功能
  - 测试任务创建、进度更新、状态管理等

### 集成测试

- `tests/integration/test_orchestrator_planning_task_integration.py`
  - 测试 Orchestrator 中规划功能和任务管理功能的完整集成
  - 测试复杂任务处理、技能执行、工具调用、消息格式等

- `tests/integration/test_api_planning_integration.py`
  - 测试API中规划功能的集成
  - 测试聊天端点、流式聊天端点、复杂任务处理等

### API测试

- `backend/api/tests/test_stream_api_planning_integration.py`
  - 测试流式API中规划功能和任务管理功能的集成
  - 测试消息格式、调试消息、状态消息、工具消息等

- `backend/api/tests/test_task_api.py`
  - 测试任务管理API
  - 测试获取任务、列出任务、取消任务等

## 运行测试

### 运行所有集成测试

```bash
pytest tests/integration/ -v
```

### 运行单元测试

```bash
pytest backend/core/agent/tests/test_orchestrator_planning_integration.py -v
pytest backend/core/agent/tests/test_task_manager_integration.py -v
```

### 运行API测试

```bash
pytest backend/api/tests/test_stream_api_planning_integration.py -v
pytest backend/api/tests/test_task_api.py -v
```

### 运行特定测试

```bash
# 运行特定测试类
pytest tests/integration/test_orchestrator_planning_task_integration.py::TestOrchestratorPlanningTaskIntegration -v

# 运行特定测试方法
pytest tests/integration/test_orchestrator_planning_task_integration.py::TestOrchestratorPlanningTaskIntegration::test_complex_task_creates_planning_files_and_task_record -v
```

## 测试覆盖的功能

### 规划功能

- ✅ 复杂任务检测
- ✅ 规划文件创建（task_plan.md, findings.md, progress.md）
- ✅ 规划文件更新（工具调用、进度更新、错误记录）
- ✅ 对话评估记录到规划文件

### 任务管理功能

- ✅ 任务创建
- ✅ 任务进度更新
- ✅ 任务状态管理
- ✅ 任务查询和列表

### 集成功能

- ✅ 技能执行时同时更新规划文件和任务管理器
- ✅ 工具调用后更新规划文件
- ✅ 对话评估结果记录到规划文件
- ✅ 统一的消息格式（StreamMessageBuilder）
- ✅ 长任务的进度同步更新

## 环境变量

测试需要以下环境变量：

- `ENABLE_PLANNING=true` - 启用规划功能
- `PLANNING_WORK_DIR` - 规划文件工作目录（测试中使用临时目录）
- `PLANNING_COMPLEXITY_THRESHOLD` - 复杂度阈值（测试中设置为0.2）
- `DEEPSEEK_API_KEY` - LLM API密钥（测试中使用mock）

## 注意事项

1. 测试使用 Mock 来避免实际的 LLM 调用
2. 测试使用临时目录来存储规划文件
3. 测试会自动清理任务管理器状态
4. 某些测试可能需要异步支持（使用 `@pytest.mark.asyncio`）

