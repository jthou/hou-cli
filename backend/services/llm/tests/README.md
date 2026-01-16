# LLM 服务测试说明

## 测试文件结构

本目录包含以下测试文件，每个文件对应一个 LLM 提供商：

- `test_deepseek.py` - DeepSeek 平台测试
- `test_turbogateway_openai.py` - TheTurbo.ai 网关 - OpenAI 模型测试
- `test_turbogateway_anthropic.py` - TheTurbo.ai 网关 - Anthropic Claude 模型测试
- `test_turbogateway_google.py` - TheTurbo.ai 网关 - Google Gemini 模型测试
- `test_turbogateway_perplexity.py` - TheTurbo.ai 网关 - Perplexity Sonar 模型测试
- `test_bailian.py` - 百炼平台测试（文本模型）
- `test_bailian_vision.py` - 百炼平台视觉模型测试

## 测试内容

每个测试文件包含两个测试用例：

1. **非流式聊天测试** (`test_*_chat_non_streaming`)
   - 测试问题："hello，你是什么模型？"
   - 验证模型能正确连接并返回响应
   - 验证响应格式正确（字符串，非空）

2. **流式聊天测试** (`test_*_chat_streaming`)
   - 测试问题："hello，你是什么模型？"
   - 验证流式响应能正确接收多个数据块
   - 验证完整响应非空

### 视觉模型测试

`test_bailian_vision.py` 专门测试百炼平台的视觉模型：

- **测试的视觉模型**：
  - `qwen-vl-max-2025-08-13` - 超大规模视觉语言模型
  - `qwen3-vl-plus-2025-12-19` - 视觉智能体，支持深度思考
  - `qwen3-vl-flash-2025-10-15` - 轻量级视觉模型
  - `qwen-vl-plus-latest` - 支持超百万像素分辨率

- **测试内容**：
  - 非流式聊天测试（文本对话）
  - 流式聊天测试（文本对话）
  - 参数化测试（测试所有视觉模型）

**注意**：视觉模型测试目前只测试文本对话功能。完整的视觉功能测试（图像理解）需要在 Browser Tool 中使用。

## 运行测试

### 推荐方式：直接运行（避免 pytest 插件冲突）

```bash
# 运行所有测试（推荐）
python3 backend/services/llm/tests/run_tests_direct.py

# 在虚拟环境中运行
source venv/bin/activate
python3 backend/services/llm/tests/run_tests_direct.py
```

**注意**：如果您的环境中安装了 ROS，pytest 可能会因为插件冲突而无法运行。
推荐使用 `run_tests_direct.py` 来避免这个问题。

### 使用 pytest（如果环境支持）

```bash
# 从项目根目录运行
pytest backend/services/llm/tests/ -v

# 或进入测试目录
cd backend/services/llm/tests
pytest -v
```

**注意**：如果遇到 `PluginValidationError: unknown hook 'pytest_launch_collect_makemodule'` 错误，
这是因为 ROS 插件与 pytest 版本不兼容。请使用 `run_tests_direct.py` 代替。

### 已归档的文件

以下文件已移动到 `archived/` 目录（功能重复，不再推荐使用）：
- `pytest_plugin_filter.py` - pytest 插件过滤器
- `pytest_wrapper.py` - pytest 包装器
- `run_pytest.sh` - bash 脚本运行 pytest
- `run_tests.sh` - bash 脚本运行 pytest
- `run_tests_simple.py` - 简单的 pytest 运行器
- `test_manual.py` - 手动测试脚本（功能与 `run_tests_direct.py` 重复）
- `test_runner.py` - 测试文件验证器

详见 `archived/README.md`。

### 运行特定提供商的测试

```bash
# 测试 DeepSeek
pytest backend/services/llm/tests/test_deepseek.py

# 测试 TheTurbo.ai 网关 - OpenAI
pytest backend/services/llm/tests/test_turbogateway_openai.py

# 测试百炼平台（文本模型）
pytest backend/services/llm/tests/test_bailian.py

# 测试百炼平台（视觉模型）
pytest backend/services/llm/tests/test_bailian_vision.py
```

### 运行特定测试用例

```bash
# 只测试非流式
pytest backend/services/llm/tests/test_deepseek.py::TestDeepSeek::test_deepseek_chat_non_streaming

# 只测试流式
pytest backend/services/llm/tests/test_deepseek.py::TestDeepSeek::test_deepseek_chat_streaming
```

## 环境变量配置

测试需要配置相应的 API Key 环境变量：

### DeepSeek
```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key
```

### TheTurbo.ai 网关服务
```bash
# OpenAI
export OPENAI_API_KEY=your_openai_api_key

# Anthropic
export ANTHROPIC_API_KEY=your_anthropic_api_key

# Google
export GOOGLE_API_KEY=your_google_api_key

# xAI (注意：Grok 模型目前在 TheTurbo.ai 清单中不可用)
# export XAI_API_KEY=your_xai_api_key

# Perplexity
export PERPLEXITY_API_KEY=your_perplexity_api_key
```

### 百炼平台
```bash
export BAILIAN_API_KEY=your_bailian_api_key
# 或
export DASHSCOPE_API_KEY=your_dashscope_api_key
```

**注意**：视觉模型测试使用相同的 `BAILIAN_API_KEY`，因为视觉模型也是百炼平台提供的。

## 测试行为

- **如果 API Key 未设置**：测试会自动跳过（使用 `pytest.skip`）
- **如果 API Key 无效**：测试会失败，显示相应的错误信息
- **如果连接成功**：测试会验证响应格式和内容

## 测试输出

测试成功时会输出：
```
✅ [提供商] [流式/非流式] 响应: [响应内容前100个字符]...
```

例如：
```
✅ DeepSeek 非流式响应: 我是 DeepSeek Chat，一个由 DeepSeek 开发的大语言模型...
✅ OpenAI GPT-5 流式响应 (15 个块): 我是 GPT-5，由 OpenAI 开发...
```

## 注意事项

1. **API 费用**：这些测试会实际调用 LLM API，可能产生费用
2. **网络连接**：测试需要网络连接才能访问 LLM 服务
3. **测试时间**：流式测试可能需要较长时间，取决于网络速度
4. **API 限制**：注意 API 的速率限制，避免频繁运行测试
5. **视觉模型测试**：视觉模型测试目前只测试文本对话功能，完整的视觉功能（图像理解）需要在 Browser Tool 中使用

## 视觉模型测试说明

### 测试的视觉模型

在 `run_tests_direct.py` 和 `test_manual.py` 中，已添加以下视觉模型测试：

- `qwen-vl-max-2025-08-13` - 超大规模视觉语言模型（推荐，默认值）
- `qwen3-vl-plus-2025-12-19` - 视觉智能体，支持深度思考
- `qwen3-vl-flash-2025-10-15` - 轻量级视觉模型，速度快
- `qwen-vl-plus-latest` - 支持超百万像素分辨率

### 运行视觉模型测试

```bash
# 运行所有测试（包括视觉模型）
python3 backend/services/llm/tests/run_tests_direct.py

# 只运行视觉模型测试（pytest）
pytest backend/services/llm/tests/test_bailian_vision.py -v

# 测试特定视觉模型
pytest backend/services/llm/tests/test_bailian_vision.py::TestBailianVision::test_vision_models -v
```

### 视觉模型测试内容

- ✅ **文本对话**：验证视觉模型能正常进行文本对话
- ✅ **流式响应**：验证视觉模型的流式响应功能
- ⏭️ **图像理解**：完整的图像理解测试需要在 Browser Tool 中使用（见 `tests/test_browser_vision_simple.py`）

