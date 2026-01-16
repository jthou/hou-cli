# 测试快速开始指南

## 最简单的测试方法

### 方法 1：使用 Python 测试脚本（推荐，自动处理 ROS 插件冲突）

```bash
# 1. 确保在项目根目录
cd /home/robo/justin/hou-cli

# 2. 激活虚拟环境（如果使用虚拟环境）
source venv/bin/activate  # 或 .venv/bin/activate

# 3. 使用 Python 测试脚本运行测试
python3 backend/core/agent/tools/tests/run_tests.py

# 或运行特定测试
python3 backend/core/agent/tools/tests/run_tests.py -k "test_tool_initialization"
```

### 方法 2：使用 Bash 测试脚本

```bash
# 使用 Bash 测试脚本
bash backend/core/agent/tools/tests/run_tests.sh
```

### 方法 2：直接使用 pytest

```bash
# 1. 确保在项目根目录
cd /home/robo/justin/hou-cli

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 运行测试（如果遇到 ROS 插件冲突，使用方法 1）
pytest backend/core/agent/tools/tests/ -v
```

### 方法 2：运行简单示例

```bash
# 运行测试示例脚本
cd /home/robo/justin/hou-cli
PYTHONPATH=/home/robo/justin/hou-cli python3 backend/core/agent/tools/tests/test_simple_example.py
```

## 测试步骤

### 步骤 1：检查环境

```bash
# 检查 Python
python3 --version

# 检查 pytest
pytest --version

# 检查依赖
python3 -c "import httpx; print('httpx: OK')" || echo "需要安装: pip install httpx"
python3 -c "from dotenv import load_dotenv; print('python-dotenv: OK')" || echo "需要安装: pip install python-dotenv"
```

### 步骤 2：运行基础测试

```bash
# 测试所有工具的初始化（不需要 API Key）
pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"

# 测试 WikipediaTool（不需要 API Key）
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# 测试 FileSearchTool（不需要 API Key）
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v
```

### 步骤 3：配置环境变量（可选）

如果需要运行集成测试，在 `.env` 文件中配置：

```bash
# 复制示例文件
cp env.example .env

# 编辑配置文件
vim .env  # 填入你的 API Keys
```

### 步骤 4：运行完整测试

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
```

## 测试输出说明

### ✅ PASSED - 测试通过
```
test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization PASSED
```

### ⏭️ SKIPPED - 测试跳过（正常）
```
test_google_search_tool.py::TestGoogleSearchTool::test_execute_search SKIPPED [1]
需要设置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID
```
**说明**：这是正常的！测试会根据环境自动跳过。

### ❌ FAILED - 测试失败
需要检查错误信息。

### ⚠️ ERROR - 导入错误
通常是缺少依赖，需要安装：
```bash
pip install httpx python-dotenv
```

## 常用命令

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# 只运行单元测试（快速）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试
pytest backend/core/agent/tools/tests/ -v -m "integration"
```

## 更多信息

- 详细测试指南：`docs/testing-guide.md`
- 测试覆盖总结：`docs/tools-test-coverage-summary.md`
- 如何测试：`docs/how-to-test-tools.md`

