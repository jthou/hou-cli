# 编排系统测试

## 测试结构

```
orchestration/
├── __init__.py
├── test_model_selection.py          # 模型选择逻辑测试
├── test_task_decomposition.py        # 任务分解测试
├── test_tool_metadata.py            # 工具元数据测试
└── test_integration_scenarios.py     # 集成测试场景
```

## 运行测试

### 运行所有编排测试

```bash
pytest backend/core/agent/tests/orchestration/ -v
```

### 运行特定测试

```bash
# 模型选择测试
pytest backend/core/agent/tests/orchestration/test_model_selection.py -v

# 任务分解测试
pytest backend/core/agent/tests/orchestration/test_task_decomposition.py -v

# 工具元数据测试
pytest backend/core/agent/tests/orchestration/test_tool_metadata.py -v

# 集成测试场景
pytest backend/core/agent/tests/orchestration/test_integration_scenarios.py -v
```

## 测试场景

集成测试场景定义在 `test_integration_scenarios.py` 中，包括：

1. **简单对话任务**：测试对话模型选择
2. **代码生成任务**：测试编程模型选择
3. **简单工具调用**：测试代码模型选择
4. **搜索任务**：测试对话模型选择
5. **复杂推理任务**：测试推理模型选择
6. **多步骤任务**：测试推理模型和任务分解

## 前置条件

运行测试前，请确保：

1. `.env` 文件中已配置三种类型的模型：
   - `CHAT_MODEL`
   - `CODE_MODEL`
   - `REASONING_MODEL`

2. 对应的 API Key 已配置并可用

3. 运行验证脚本检查配置：
   ```bash
   python scripts/validate_model_config.py
   ```

