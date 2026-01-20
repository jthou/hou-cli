# Tools 测试说明

## 测试文件列表

所有 tools 的测试文件都在此目录下，共 **22 个测试文件**。

### 新建的测试文件（8 个）

1. **test_google_search_tool.py** - GoogleSearchTool 测试
   - 需要：`GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`

2. **test_file_search_tool.py** - FileSearchTool 测试
   - 需要：无（本地文件系统搜索）

3. **test_wikipedia_tool.py** - WikipediaTool 测试
   - 需要：无（公开 API）

4. **test_mediawiki_tool.py** - MediaWikiTool 测试
   - 需要：`MEDIAWIKI_URL`（可选：认证信息）

5. **test_code_executor_tool.py** - CodeExecutorTool 测试
   - 需要：无（本地代码执行）

6. **test_gvim_tool.py** - GvimTool 测试
   - 需要：无（需要安装 gvim）

7. **test_browser_tool_cdp.py** - BrowserTool CDP 连接测试
   - 专门测试 Chrome DevTools Protocol (CDP) 连接功能
   - 检测浏览器环境配置问题（CDP 连接失败、浏览器未初始化等）
   - 需要：browser-use、DEEPSEEK_API_KEY、正确配置的浏览器环境

8. **test_zhihu_zhida_tool.py** - ZhihuZhidaTool 测试
   - 需要：`DEEPSEEK_API_KEY`（用于 browser 工具）

### 已有的测试文件（15 个）

- test_base.py
- test_browser_tool.py
- test_browser_tool_cdp.py
- test_ffmpeg_tool.py
- test_file_organizer_tool.py
- test_pdf_parser_tool.py
- test_video_downloader_tool.py
- test_weather_tool.py
- test_whisper_tool.py
- test_registry.py
- test_orchestrator_tool_integration.py
- test_weather_tool_integration.py
- test_video_downloader_tool_integration.py
- test_jwt_auth.py
- test_key_loader.py

## 环境变量配置

所有测试都使用 `load_dotenv()` 自动加载 `.env` 文件。

### 必需的环境变量

根据要测试的工具，需要在 `.env` 文件中配置相应的环境变量：

| 工具 | 环境变量 | 说明 |
|------|---------|------|
| GoogleSearchTool | `GOOGLE_SEARCH_API_KEY`<br>`GOOGLE_SEARCH_ENGINE_ID` | Google Custom Search API |
| MediaWikiTool | `MEDIAWIKI_URL`<br>`MEDIAWIKI_USERNAME` / `MEDIAWIKI_BOT_NAME`<br>`MEDIAWIKI_PASSWORD` / `MEDIAWIKI_BOT_PASSWORD` | MediaWiki 网站配置 |
| BrowserTool | `DEEPSEEK_API_KEY`<br>`BAILIAN_API_KEY` (可选)<br>`BROWSER_TOOL_VISION_MODEL` (可选) | LLM 服务配置 |
| ZhihuZhidaTool | `DEEPSEEK_API_KEY` | 需要 BrowserTool 支持 |
| WeatherTool | `WEATHER_JWT_PRIVATE_KEY`<br>`QWEATHER_CREDENTIAL_ID`<br>`QWEATHER_PROJECT_ID`<br>`QWEATHER_API_HOST` | 和风天气 API |
| PDFParserTool | `DASHSCOPE_API_KEY` 或 `ALIBABA_CLOUD_API_KEY` | 阿里云 DashScope API |

### 不需要 API Key 的工具

以下工具不需要 API Key，但可能需要安装相应的依赖：

- **FileSearchTool** - 本地文件系统搜索
- **WikipediaTool** - 公开 API
- **CodeExecutorTool** - 本地代码执行
- **GvimTool** - 需要安装 gvim
- **WhisperTool** - 需要安装 openai-whisper
- **FFmpegTool** - 需要安装 ffmpeg
- **VideoDownloaderTool** - 需要安装 yt-dlp/you-get

## 运行测试

### 运行所有工具测试

```bash
# 运行所有测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具的测试
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# 只运行单元测试（跳过集成测试）
pytest backend/core/agent/tools/tests/ -v -m "not integration"

# 只运行集成测试
pytest backend/core/agent/tools/tests/ -v -m "integration"
```

### 运行特定工具的测试

```bash
# GoogleSearchTool
pytest backend/core/agent/tools/tests/test_google_search_tool.py -v

# FileSearchTool
pytest backend/core/agent/tools/tests/test_file_search_tool.py -v

# WikipediaTool
pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v

# MediaWikiTool
pytest backend/core/agent/tools/tests/test_mediawiki_tool.py -v

# CodeExecutorTool
pytest backend/core/agent/tools/tests/test_code_executor_tool.py -v

# GvimTool
pytest backend/core/agent/tools/tests/test_gvim_tool.py -v

# BrowserTool CDP 连接测试
pytest backend/core/agent/tools/tests/test_browser_tool_cdp.py -v

# ZhihuZhidaTool
pytest backend/core/agent/tools/tests/test_zhihu_zhida_tool.py -v
```

## 测试特点

### 1. 自动读取 .env 文件

所有测试文件都使用 `load_dotenv()` 自动加载 `.env` 文件：

```python
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
```

### 2. 智能跳过机制

测试会根据环境变量和依赖自动跳过：

- **缺少 API Key**：使用 `@pytest.mark.skipif` 跳过需要 API Key 的测试
- **依赖未安装**：检查库是否可用（如 `JUPYTER_AVAILABLE`、`BROWSER_USE_AVAILABLE`）
- **平台不支持**：某些功能可能在某些平台不支持

### 3. Mock 测试

对于不需要真实环境的测试，使用 Mock 来模拟服务：

```python
with patch.object(tool, '_get_search_service') as mock_get_service:
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    # 测试逻辑
```

### 4. 集成测试标记

集成测试使用 `@pytest.mark.integration` 标记，可以单独运行：

```bash
# 只运行集成测试
pytest -m integration -v
```

## 测试覆盖

每个工具测试包含：

1. **单元测试**：
   - 工具初始化
   - 参数验证
   - 错误处理
   - 参数限制验证

2. **集成测试**：
   - 完整工作流
   - 真实环境测试
   - 错误场景测试

## 注意事项

1. **API Key 安全**：
   - `.env` 文件已添加到 `.gitignore`
   - 不要在测试代码中硬编码 API Keys
   - 使用 `env.example` 作为配置模板

2. **测试环境**：
   - 某些测试需要真实环境（如网络连接、本地工具）
   - 集成测试可能需要较长时间
   - 某些测试可能产生实际效果（如打开文件、执行代码）

3. **依赖安装**：
   - 某些工具需要额外的依赖
   - 测试会自动检测依赖是否可用
   - 缺少依赖的测试会被自动跳过

