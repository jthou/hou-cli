# Tools 测试快速开始

## 最简单的测试方法

### 1. 安装依赖

```bash
# 确保安装了所有依赖
pip install -r requirements.txt

# 或至少安装这些核心依赖
pip install pytest httpx python-dotenv
```

### 2. 运行最简单的测试（不需要任何配置）

```bash
# 测试工具初始化（所有工具都支持）
pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"

# 测试参数验证（所有工具都支持）
pytest backend/core/agent/tools/tests/ -v -k "test_missing"

# 测试 WikipediaTool（不需要 API Key）
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py::TestWikipediaTool::test_tool_initialization -v
```

### 3. 配置环境变量（可选）

如果需要运行集成测试，在 `.env` 文件中配置：

```bash
# 最小配置（用于基础测试）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 完整配置（用于所有测试）
# 见 env.example 文件
```

### 4. 运行完整测试

```bash
# 运行所有单元测试（快速）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 运行所有测试（包括集成测试）
pytest backend/core/agent/tools/tests/ -v
```

## 测试输出解读

### ✅ PASSED - 测试通过
```
test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization PASSED
```

### ⏭️ SKIPPED - 测试跳过（正常）
```
test_google_search_tool.py::TestGoogleSearchTool::test_execute_search SKIPPED [1] 
需要设置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID
```
**说明**：这是正常的，表示测试被智能跳过（缺少配置或依赖）

### ❌ FAILED - 测试失败（需要检查）
```
test_google_search_tool.py::TestGoogleSearchTool::test_execute_search FAILED
```
**说明**：需要检查错误信息，可能是：
- 环境变量配置错误
- 依赖未安装
- 网络问题
- 代码问题

### ⚠️ ERROR - 导入错误（需要安装依赖）
```
ERROR: ModuleNotFoundError: No module named 'httpx'
```
**说明**：缺少依赖，需要安装：
```bash
pip install httpx
```

## 推荐测试顺序

### 第一步：验证环境

```bash
# 检查 pytest 是否可用
pytest --version

# 检查 Python 环境
python3 --version
```

### 第二步：运行基础测试

```bash
# 测试工具初始化（所有工具）
pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"

# 如果成功，说明环境配置正确
```

### 第三步：运行不需要 API Key 的测试

```bash
# WikipediaTool（公开 API）
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# FileSearchTool（本地文件系统）
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v
```

### 第四步：配置 API Keys 后运行集成测试

```bash
# 在 .env 文件中配置 API Keys 后
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
```

## 常见错误解决

### 错误 1: ModuleNotFoundError: No module named 'httpx'

```bash
# 解决方法
pip install httpx
```

### 错误 2: ModuleNotFoundError: No module named 'dotenv'

```bash
# 解决方法
pip install python-dotenv
```

### 错误 3: 测试被跳过

这是**正常的**！测试会根据环境自动跳过：
- 缺少 API Key → 跳过需要 API Key 的测试
- 依赖未安装 → 跳过需要依赖的测试

**解决方法**：配置相应的环境变量或安装依赖

## 测试命令速查

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# 运行特定测试方法
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization -v

# 只运行单元测试（快速）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试
pytest backend/core/agent/tools/tests/ -v -m "integration"

# 查看测试覆盖率
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=term
```

