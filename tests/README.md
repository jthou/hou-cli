# 测试目录说明

## 目录结构

```
tests/
├── integration/          # 集成测试（真实后端，pytest）
│   ├── test_code_execution.py
│   ├── test_e2e_chat.py
│   ├── test_multi_turn_chat.py
│   ├── test_api_planning_integration.py
│   ├── test_orchestrator_planning_task_integration.py
│   └── ...
│
└── scripts/             # 快速验证脚本（手动测试，可选）
    ├── test_browser_*.py
    ├── test_whisper_*.py
    └── ...
```

## 测试类型

### 集成测试 (`tests/integration/`)

- **用途**：测试跨模块的集成功能
- **特点**：使用真实后端，需要配置环境变量
- **运行方式**：`pytest tests/integration/ -v`

### 快速验证脚本 (`tests/scripts/`)

- **用途**：快速验证功能、手动测试、调试
- **特点**：可能包含硬编码路径，主要用于开发
- **运行方式**：直接运行 Python 脚本

## 标准测试位置

标准的 pytest 测试文件应该位于：

- **Tools 测试**：`backend/core/agent/tools/tests/`
- **Services 测试**：`backend/services/{service_name}/tests/`
- **Agent 测试**：`backend/core/agent/tests/`
- **API 测试**：`backend/api/tests/`

## 运行测试

### 运行所有集成测试

```bash
pytest tests/integration/ -v
```

### 运行所有单元测试

```bash
pytest backend/ -v
```

### 运行所有测试

```bash
pytest backend/ tests/integration/ -v
```

### 运行特定测试

```bash
# 运行特定文件
pytest tests/integration/test_code_execution.py -v

# 运行特定测试类
pytest tests/integration/test_code_execution.py::TestCodeExecution -v

# 运行特定测试方法
pytest tests/integration/test_code_execution.py::TestCodeExecution::test_basic_execution -v
```

## 注意事项

1. **集成测试需要环境配置**：
   - 设置必要的环境变量（API Keys 等）
   - 确保后端服务可用

2. **快速验证脚本**：
   - 可能包含硬编码路径
   - 主要用于开发和调试
   - 不是标准的 pytest 测试

3. **测试文件命名**：
   - 集成测试：`test_*.py`
   - 脚本：可以是任意名称

