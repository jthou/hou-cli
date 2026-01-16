# 如何测试 Tools

## 快速开始

### 方法 1：使用 Python 测试脚本（推荐，自动处理 ROS 插件冲突）

```bash
# 1. 确保在虚拟环境中（如果使用虚拟环境）
source venv/bin/activate  # 或 .venv/bin/activate

# 2. 确保安装了依赖
pip install pytest httpx python-dotenv

# 3. 使用 Python 测试脚本运行所有测试
python3 backend/core/agent/tools/tests/run_tests.py

# 4. 运行特定测试
python3 backend/core/agent/tools/tests/run_tests.py -k "test_tool_initialization"
```

### 方法 1b：使用 Bash 测试脚本

```bash
# 使用 Bash 测试脚本
bash backend/core/agent/tools/tests/run_tests.sh
```

### 方法 2：直接使用 pytest

```bash
# 1. 确保在虚拟环境中
source venv/bin/activate

# 2. 确保安装了依赖
pip install pytest httpx python-dotenv

# 3. 运行所有工具测试（如果遇到 ROS 插件冲突，使用方法 1）
pytest backend/core/agent/tools/tests/ -v

# 4. 运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
```

### 方法 2：使用测试脚本

```bash
# 运行测试示例脚本
bash backend/core/agent/tools/tests/run_tests_example.sh
```

## 详细步骤

### 步骤 1：检查环境

```bash
# 检查 Python 版本
python3 --version

# 检查 pytest
pytest --version

# 检查依赖
python3 -c "import httpx; print('httpx: OK')"
python3 -c "from dotenv import load_dotenv; print('python-dotenv: OK')"
```

### 步骤 2：配置环境变量（可选）

如果需要运行集成测试，在 `.env` 文件中配置：

```bash
# 复制示例文件
cp env.example .env

# 编辑配置文件
vim .env  # 填入你的 API Keys
```

### 步骤 3：运行测试

#### 3.1 运行基础测试（不需要 API Key）

```bash
# 测试所有工具的初始化
pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"

# 测试参数验证
pytest backend/core/agent/tools/tests/ -v -k "test_missing"
```

#### 3.2 运行不需要 API Key 的工具测试

```bash
# WikipediaTool（公开 API）
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# FileSearchTool（本地文件系统）
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v
```

#### 3.3 运行需要 API Key 的工具测试

```bash
# GoogleSearchTool（需要 GOOGLE_SEARCH_API_KEY）
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# MediaWikiTool（需要 MEDIAWIKI_URL）
pytest backend/core/agent/tools/tests/test_mediawiki_tool.py -v

# BrowserTool（需要 DEEPSEEK_API_KEY）
pytest backend/core/agent/tools/tests/test_browser_tool.py -v
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

**说明**：这是正常的！测试会根据环境自动跳过：
- 缺少 API Key → 跳过需要 API Key 的测试
- 依赖未安装 → 跳过需要依赖的测试

### ❌ FAILED - 测试失败

```
test_google_search_tool.py::TestGoogleSearchTool::test_execute_search FAILED
```

**需要检查**：
1. 环境变量是否正确配置
2. API Key 是否有效
3. 网络连接是否正常

### ⚠️ ERROR - 导入错误

```
ERROR: ModuleNotFoundError: No module named 'httpx'
```

**解决方法**：
```bash
pip install httpx
```

## 测试命令速查

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# 运行特定测试类
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool -v

# 运行特定测试方法
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization -v

# 只运行单元测试（快速）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试
pytest backend/core/agent/tools/tests/ -v -m "integration"

# 查看测试覆盖率
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=term
```

## 环境变量配置清单

### 必需配置

```bash
# DeepSeek API（必需，用于 LLM 服务）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 可选配置（按需）

```bash
# Google Search
GOOGLE_SEARCH_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_ENGINE_ID=012345678901234567890:abcdefghijk

# MediaWiki
MEDIAWIKI_URL=http://www.jthou.com/mediawiki
MEDIAWIKI_USERNAME=myusername
MEDIAWIKI_PASSWORD=your_password_here

# 和风天气
WEATHER_JWT_PRIVATE_KEY=your_jwt_private_key
QWEATHER_CREDENTIAL_ID=your_credential_id
QWEATHER_PROJECT_ID=your_project_id
QWEATHER_API_HOST=test-host.re.qweatherapi.com
```

## 常见问题

### Q1: 测试被跳过是正常的吗？

**A**: 是的！测试会根据环境自动跳过：
- 缺少 API Key → 跳过需要 API Key 的测试
- 依赖未安装 → 跳过需要依赖的测试

这是**智能跳过机制**，不是错误。

### Q2: 如何运行所有测试（包括被跳过的）？

**A**: 被跳过的测试不会运行，这是 pytest 的正常行为。如果需要运行某个测试：
1. 配置相应的环境变量
2. 安装相应的依赖
3. 重新运行测试

### Q3: 如何查看测试覆盖率？

**A**: 
```bash
# 安装 pytest-cov
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 推荐测试流程

1. **先运行基础测试**（验证环境）
   ```bash
   pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"
   ```

2. **运行不需要 API Key 的测试**（验证功能）
   ```bash
   pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v
   pytest backend/core/agent/tools/tests/test_file_search_tool.py -v
   ```

3. **配置 API Keys 后运行集成测试**（验证完整功能）
   ```bash
   # 在 .env 文件中配置 API Keys
   pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
   ```

## 更多信息

- 详细测试指南：`docs/testing-guide.md`
- 测试覆盖总结：`docs/tools-test-coverage-summary.md`
- 测试快速开始：`backend/core/agent/tools/tests/QUICK_START.md`

