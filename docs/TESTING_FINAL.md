# 测试最终指南

## ✅ ROS 插件冲突已解决！

现在可以使用以下方法运行测试，无需担心 ROS 插件冲突。

## 🚀 推荐方法

### 方法 1：使用 Python 测试脚本（最简单，推荐）

```bash
# 运行所有测试
python3 backend/core/agent/tools/tests/run_tests.py

# 运行特定测试
python3 backend/core/agent/tools/tests/run_tests.py -k "test_tool_initialization"

# 运行并显示详细信息
python3 backend/core/agent/tools/tests/run_tests.py -v
```

**优点**：
- ✅ 自动处理 ROS 插件冲突（已验证）
- ✅ 自动加载 .env 文件
- ✅ 跨平台（Windows/Linux/macOS）
- ✅ 不需要 bash
- ✅ 自动移除 ROS 路径

### 方法 2：使用 Bash 测试脚本

```bash
# 运行所有测试
bash backend/core/agent/tools/tests/run_tests.sh

# 运行特定测试
bash backend/core/agent/tools/tests/run_tests.sh -k "test_tool_initialization"
```

**优点**：
- ✅ 自动处理 ROS 插件冲突
- ✅ 自动检测虚拟环境
- ✅ 自动配置 PYTHONPATH

### 方法 3：直接使用 pytest（需要手动禁用插件）

```bash
# 如果直接使用 pytest，需要手动禁用 ROS 插件
pytest backend/core/agent/tools/tests/ -v \
    -p no:launch_testing_ros_pytest_entrypoint \
    -p no:colcon_core
```

**注意**：如果遇到 ROS 插件冲突，请使用方法 1 或 2。

## 📋 测试结果

运行测试脚本后，你会看到类似这样的输出：

```
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0
plugins: asyncio-1.3.0, langsmith-0.6.0, anyio-4.12.0, mock-3.15.1, cov-7.0.0
collected 241 items

backend/core/agent/tools/tests/test_browser_tool.py::TestBrowserTool::test_tool_initialization PASSED
backend/core/agent/tools/tests/test_code_executor_tool.py::TestCodeExecutorTool::test_tool_initialization PASSED
...
=============== 11 passed, 230 deselected, 24 warnings in 0.72s ================
```

## 🔧 环境配置

### 必需配置

```bash
# DeepSeek API（用于 LLM 服务和 Browser Tool）
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
```

## ⚠️ 常见问题

### Q1: 仍然遇到 ROS 插件冲突？

**A**: 确保使用测试脚本（方法 1 或 2），不要直接运行 `pytest`。

### Q2: 测试被跳过？

**A**: 这是正常的！测试会根据环境自动跳过：
- 缺少 API Key → 跳过需要 API Key 的测试
- 依赖未安装 → 跳过需要依赖的测试

### Q3: ModuleNotFoundError？

**A**: 安装缺失的依赖：
```bash
pip install pytest httpx python-dotenv
```

## 📚 相关文档

- **详细测试指南**：`docs/testing-guide.md`
- **快速开始**：`docs/TESTING_QUICK_START.md`
- **如何测试**：`docs/how-to-test-tools.md`
- **故障排除**：`backend/core/agent/tools/tests/README_TROUBLESHOOTING.md`
- **测试覆盖总结**：`docs/tools-test-coverage-summary.md`

## 🎯 下一步

1. **运行测试**：`python3 backend/core/agent/tools/tests/run_tests.py`
2. **配置环境变量**：在 `.env` 文件中填入你的 API Keys
3. **运行完整测试**：`python3 backend/core/agent/tools/tests/run_tests.py -v`

