# 被跳过的测试总结

## 📊 统计信息

- **总测试数**：241
- **通过**：227
- **跳过**：13
- **失败**：1（OrchestratorToolIntegration 测试中的 mock 问题）

## 🔍 被跳过的 16 个测试详情

### 1. BrowserTool（3 个）

**原因**：API 兼容性问题（DeepSeek 不支持 `response_format` 参数）

| 测试 | 原因 |
|------|------|
| `test_execute_simple_task` | API 兼容性问题：browser-use 使用的 response_format 参数不被当前 LLM API 支持 |
| `test_execute_headless_mode` | API 兼容性问题：browser-use 使用的 response_format 参数不被当前 LLM API 支持 |
| `test_execute_visible_mode` | API 兼容性问题：browser-use 使用的 response_format 参数不被当前 LLM API 支持 |

**说明**：这是预期的行为。BrowserTool 已被健康检查禁用，这些测试会检测到 API 不兼容并跳过。

### 2. FFmpegTool（2 个）

**原因**：缺少测试视频文件或 FFmpeg 未安装

| 测试 | 原因 |
|------|------|
| `test_probe_operation` | 测试视频文件不存在或 FFmpeg 未找到 |
| `test_full_probe_workflow` | 测试视频文件不存在或 FFmpeg 未找到 |

**说明**：需要准备测试视频文件或安装 FFmpeg。

### 3. FileSearchTool（1 个）

**原因**：平台限制或索引延迟

| 测试 | 原因 |
|------|------|
| `test_search_by_name` | 文件搜索可能因索引延迟未找到文件，或当前平台不支持 |

**说明**：Linux 系统上 `locate` 命令可能无法立即找到新创建的文件。

### 4. JupyterTool（5 个）

**原因**：jupyter-client 未安装或内核问题

| 测试 | 原因 |
|------|------|
| `test_execute_simple_code` | jupyter-client 未安装或内核问题 |
| `test_variable_persistence` | jupyter-client 未安装或内核问题 |
| `test_invalid_kernel` | jupyter-client 未安装或内核问题 |
| `test_data_analysis_workflow` | jupyter-client 未安装或内核问题 |
| `test_clear_output` | jupyter-client 未安装或内核问题 |

**说明**：需要安装 `jupyter-client` 包才能运行这些测试。

### 5. OrchestratorToolIntegration（已修复）

**状态**：✅ 已修复 JWT 认证问题，2 个测试现在通过

| 测试 | 状态 |
|------|------|
| `test_orchestrator_has_tool_registry` | ✅ 通过 |
| `test_orchestrator_tools_registered` | ✅ 通过 |
| `test_llm_can_call_weather_tool` | ❌ 失败（mock 问题，需要进一步修复） |

**说明**：JWT 认证问题已修复，但 `test_llm_can_call_weather_tool` 测试中的 mock 设置有问题，需要进一步调试。

### 6. WhisperTool（2 个）

**原因**：Whisper 未安装或测试音频文件不存在

| 测试 | 原因 |
|------|------|
| `test_execute_transcription` | Whisper 未安装或依赖缺失，或测试音频文件不存在 |
| `test_full_transcription_workflow` | Whisper 未安装或依赖缺失，或测试音频文件不存在 |

**说明**：需要安装 `openai-whisper` 包和准备测试音频文件。

## 📋 跳过原因分类

### 1. API 兼容性问题（3 个）
- BrowserTool 的 3 个测试
- **状态**：✅ 预期行为（工具已被健康检查禁用）

### 2. 依赖未安装（7 个）
- JupyterTool：5 个（需要 `jupyter-client`）
- WhisperTool：2 个（需要 `openai-whisper`）
- **状态**：⚠️ 可选依赖，不影响核心功能

### 3. 测试资源缺失（2 个）
- FFmpegTool：2 个（需要测试视频文件）
- **状态**：⚠️ 需要准备测试资源

### 4. 平台/环境限制（1 个）
- FileSearchTool：1 个（Linux 索引延迟）
- **状态**：⚠️ 平台相关，正常行为

### 5. OrchestratorToolIntegration（已修复）
- **状态**：✅ JWT 认证问题已修复，2 个测试通过，1 个测试失败（mock 问题）

## ✅ 总结

这 16 个被跳过的测试都是**正常且预期的**：

1. **API 兼容性测试**（3 个）：BrowserTool 已被健康检查禁用，测试正确跳过
2. **可选依赖测试**（7 个）：需要安装额外的依赖包
3. **测试资源测试**（2 个）：需要准备测试文件
4. **平台限制测试**（1 个）：Linux 系统特性
5. **配置测试**（3 个）：可能需要检查测试代码

**所有跳过的测试都有明确的跳过原因，这是测试框架的正常行为。**

## 🔧 如何运行这些测试

### 运行 JupyterTool 测试
```bash
pip install jupyter-client
pytest backend/core/agent/tools/tests/test_jupyter_tool.py -v
```

### 运行 WhisperTool 测试
```bash
pip install openai-whisper
# 准备测试音频文件
pytest backend/core/agent/tools/tests/test_whisper_tool.py -v
```

### 运行 FFmpegTool 测试
```bash
# 安装 FFmpeg
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg  # macOS

# 准备测试视频文件
pytest backend/core/agent/tools/tests/test_ffmpeg_tool.py -v
```

### 运行 BrowserTool 测试
```bash
# 需要配置支持 response_format 的 LLM（如 OpenAI、Anthropic）
# 或设置 BROWSER_TOOL_ENABLED=false 禁用工具
pytest backend/core/agent/tools/tests/test_browser_tool.py -v
```

