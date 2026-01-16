# Tools 测试指南

## 快速开始

### 1. 配置环境变量

首先，确保 `.env` 文件已配置必要的 API Keys：

```bash
# 复制示例文件（如果还没有）
cp env.example .env

# 编辑 .env 文件，填入你的 API Keys
vim .env  # 或使用你喜欢的编辑器
```

### 2. 安装依赖

```bash
# 安装项目依赖（包含所有必需的包）
pip install -r requirements.txt

# 或安装测试相关依赖
pip install pytest pytest-asyncio pytest-cov httpx python-dotenv

# 如果缺少其他依赖，根据错误信息安装
# 例如：pip install httpx mwclient wikipedia-api
```

### 3. 运行测试

```bash
# 运行所有工具测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# 只运行单元测试（跳过集成测试，更快）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试（需要真实环境）
pytest backend/core/agent/tools/tests/ -v -m "integration"
```

## 详细测试步骤

### 步骤 1：检查环境变量

查看需要哪些环境变量：

```bash
# 查看 env.example 文件
cat env.example | grep -E "GOOGLE_SEARCH|MEDIAWIKI|DEEPSEEK|WEATHER" | head -20
```

### 步骤 2：运行基础测试（不需要 API Key）

这些测试不需要 API Key，可以立即运行：

```bash
# FileSearchTool - 本地文件系统搜索
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v

# WikipediaTool - 公开 API
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# CodeExecutorTool - 本地代码执行
pytest backend/core/agent/tools/tests/test_code_executor_tool.py -v
```

### 步骤 3：运行需要 API Key 的测试

配置相应的环境变量后运行：

```bash
# GoogleSearchTool - 需要 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# MediaWikiTool - 需要 MEDIAWIKI_URL
pytest backend/core/agent/tools/tests/test_mediawiki_tool.py -v

# BrowserTool - 需要 DEEPSEEK_API_KEY
pytest backend/core/agent/tools/tests/test_browser_tool.py -v

# ZhihuZhidaTool - 需要 DEEPSEEK_API_KEY
pytest backend/core/agent/tools/tests/test_zhihu_zhida_tool.py -v

# WeatherTool - 需要和风天气 API 配置
pytest backend/core/agent/tools/tests/test_weather_tool.py -v
```

### 步骤 4：运行需要本地工具的测试

这些测试需要安装相应的工具：

```bash
# GvimTool - 需要安装 gvim
pytest backend/core/agent/tools/tests/test_gvim_tool.py -v

# JupyterTool - 需要安装 jupyter-client
pytest backend/core/agent/tools/tests/test_jupyter_tool.py -v

# WhisperTool - 需要安装 openai-whisper
pytest backend/core/agent/tools/tests/test_whisper_tool.py -v

# FFmpegTool - 需要安装 ffmpeg
pytest backend/core/agent/tools/tests/test_ffmpeg_tool.py -v
```

## 测试输出说明

### 成功输出示例

```
test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization PASSED
test_google_search_tool.py::TestGoogleSearchTool::test_missing_query PASSED
test_google_search_tool.py::TestGoogleSearchTool::test_execute_search SKIPPED
```

### 跳过测试说明

如果看到 `SKIPPED`，说明：
- ✅ **正常情况**：测试被智能跳过（缺少 API Key、依赖未安装等）
- 测试会显示跳过原因，例如：
  ```
  SKIPPED [1] backend/core/agent/tools/tests/test_google_search_tool.py:52: 
  需要设置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID
  ```

### 失败测试说明

如果看到 `FAILED`，需要检查：
1. **环境变量是否正确配置**
2. **依赖是否已安装**
3. **网络连接是否正常**（对于需要网络的测试）

## 环境变量配置清单

### 必需配置（基础功能）

```bash
# DeepSeek API（必需，用于 LLM 服务和 Browser Tool）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 可选配置（按需配置）

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

# 百炼平台（用于视觉模型）
BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BROWSER_TOOL_VISION_MODEL=qwen-vl-max-2025-08-13

# PDF 解析
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 测试场景示例

### 场景 1：快速验证所有工具初始化

```bash
# 运行所有工具的初始化测试（不需要 API Key）
pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization"
```

### 场景 2：测试参数验证

```bash
# 测试所有工具的参数验证
pytest backend/core/agent/tools/tests/ -v -k "test_missing"
```

### 场景 3：测试错误处理

```bash
# 测试所有工具的错误处理
pytest backend/core/agent/tools/tests/ -v -k "error"
```

### 场景 4：完整集成测试

```bash
# 运行所有集成测试（需要配置所有 API Keys）
pytest backend/core/agent/tools/tests/ -v -m "integration"
```

## 常见问题

### Q1: 测试被跳过，显示 "需要设置 XXX_API_KEY"

**A**: 这是正常的。测试会自动检测环境变量，如果缺少必需的 API Key，会跳过相关测试。

**解决方法**：
1. 在 `.env` 文件中配置相应的 API Key
2. 重新运行测试

### Q2: 测试失败，显示 "ModuleNotFoundError"

**A**: 缺少 Python 依赖包。

**解决方法**：
```bash
# 安装缺失的依赖
pip install <package_name>

# 或安装所有依赖
pip install -r requirements.txt
```

### Q3: 测试失败，显示 "未找到" 或 "not found"

**A**: 缺少本地工具（如 gvim、ffmpeg、jupyter）。

**解决方法**：
```bash
# 安装相应的工具
# gvim
sudo apt-get install vim-gtk  # Linux
brew install macvim  # macOS

# ffmpeg
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg  # macOS

# jupyter
pip install jupyter-client
```

### Q4: 集成测试很慢

**A**: 集成测试需要真实环境，可能需要网络请求，所以较慢。

**解决方法**：
```bash
# 只运行单元测试（更快）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 或运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool -v
```

### Q5: 如何查看测试覆盖率？

**A**: 使用 pytest-cov：

```bash
# 安装 pytest-cov
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 测试最佳实践

### 1. 先运行单元测试

```bash
# 单元测试通常很快，不需要真实环境
pytest backend/core/agent/tools/tests/ -v -m "not integration"
```

### 2. 逐步配置 API Keys

```bash
# 先测试不需要 API Key 的工具
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# 然后配置 API Keys，测试需要 API Key 的工具
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
```

### 3. 使用测试标记

```bash
# 只运行快速测试
pytest backend/core/agent/tools/tests/ -v -m "not integration and not slow"

# 只运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v
```

### 4. 查看详细输出

```bash
# 使用 -v 查看详细信息
pytest backend/core/agent/tools/tests/ -v

# 使用 -vv 查看更详细的信息
pytest backend/core/agent/tools/tests/ -vv

# 使用 -s 显示 print 输出
pytest backend/core/agent/tools/tests/ -v -s
```

## 测试命令速查表

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具测试
pytest backend/core/agent/tools/tests/test_<tool_name>_tool.py -v

# 运行特定测试类
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool -v

# 运行特定测试方法
pytest backend/core/agent/tools/tests/test_google_search_tool.py::TestGoogleSearchTool::test_tool_initialization -v

# 只运行单元测试
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试
pytest backend/core/agent/tools/tests/ -v -m "integration"

# 运行测试并显示覆盖率
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=term

# 运行测试并生成 HTML 覆盖率报告
pytest backend/core/agent/tools/tests/ --cov=backend.core.agent.tools.builtin --cov-report=html
```

## 下一步

1. **配置环境变量**：在 `.env` 文件中填入你的 API Keys
2. **运行基础测试**：先运行不需要 API Key 的测试
3. **逐步扩展**：配置更多 API Keys，运行更多测试
4. **查看覆盖率**：使用 `--cov` 查看测试覆盖率

