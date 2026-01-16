# 工具输入输出参数检查清单

## 概述

由于 LLM 可能会编写代码来调用工具，所有工具都必须有**严格的输入输出参数定义**。本文档列出了所有需要检查的工具。

## 工具分类

### 1. 基础工具（最常用，优先级最高）

#### ✅ 1.1 `execute_code` (CodeExecutorTool)
- **文件**: `backend/core/agent/tools/builtin/code_executor_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🔴 最高
- **检查项**:
  - [ ] 输入参数定义是否完整（code, language, timeout, explanation 等）
  - [ ] 输出格式是否严格定义（success, output, error, exit_code 等）
  - [ ] 是否有输出模式定义（ToolOutputSchema）
  - [ ] 输出示例是否完整

#### ✅ 1.2 `jupyter` (JupyterTool)
- **文件**: `backend/core/agent/tools/builtin/jupyter_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🔴 最高
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 1.3 `file_search` (FileSearchTool)
- **文件**: `backend/core/agent/tools/builtin/file_search_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🔴 最高
- **检查项**:
  - [ ] 输入参数定义是否完整（query, path, file_type, content_search, limit）
  - [ ] 输出格式是否严格定义（results, total, count, has_more, search_time_ms 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 1.4 `file_organizer` (FileOrganizerTool)
- **文件**: `backend/core/agent/tools/builtin/file_organizer_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 1.5 `pdf_parser` (PDFParserTool)
- **文件**: `backend/core/agent/tools/builtin/pdf_parser_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 1.6 `zhihu_zhida` (ZhihuZhidaTool)
- **文件**: `backend/core/agent/tools/builtin/zhihu_zhida_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 中
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

### 2. 网络搜索工具

#### ✅ 2.1 `browser` (BrowserTool)
- **文件**: `backend/core/agent/tools/builtin/browser_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🔴 最高
- **检查项**:
  - [ ] 输入参数定义是否完整（url, action, selector, wait_time 等）
  - [ ] 输出格式是否严格定义（title, content, links, images 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 2.2 `google_search` (GoogleSearchTool)
- **文件**: `backend/core/agent/tools/builtin/google_search_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🔴 最高
- **检查项**:
  - [ ] 输入参数定义是否完整（query, num_results 等）
  - [ ] 输出格式是否严格定义（results, total 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 2.3 `wikipedia` (WikipediaTool)
- **文件**: `backend/core/agent/tools/builtin/wikipedia_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 2.4 `mediawiki` (MediaWikiTool)
- **文件**: `backend/core/agent/tools/builtin/mediawiki_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 中
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

### 3. 特定功能工具

#### ✅ 3.1 `get_weather` (WeatherTool)
- **文件**: `backend/core/agent/tools/builtin/weather_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整（location, days 等）
  - [ ] 输出格式是否严格定义（current, forecast, aqi 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 3.2 `gvim` (GvimTool)
- **文件**: `backend/core/agent/tools/builtin/gvim_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟢 低
- **检查项**:
  - [ ] 输入参数定义是否完整
  - [ ] 输出格式是否严格定义
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 3.3 `video_downloader` (VideoDownloaderTool)
- **文件**: `backend/core/agent/tools/builtin/video_downloader_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整（url, quality, format 等）
  - [ ] 输出格式是否严格定义（results, errors, total 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 3.4 `ffmpeg` (FFmpegTool)
- **文件**: `backend/core/agent/tools/builtin/ffmpeg_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 高
- **检查项**:
  - [ ] 输入参数定义是否完整（operation, input_file, output_file 等）
  - [ ] 输出格式是否严格定义（success, output_path, duration 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

#### ✅ 3.5 `whisper` (WhisperTool)
- **文件**: `backend/core/agent/tools/builtin/whisper_tool.py`
- **状态**: ⚠️ 需要检查
- **优先级**: 🟡 中
- **检查项**:
  - [ ] 输入参数定义是否完整（audio_file, language, model 等）
  - [ ] 输出格式是否严格定义（transcription, segments, language 等）
  - [ ] 是否有输出模式定义
  - [ ] 输出示例是否完整

## 检查标准

### 输入参数检查

1. **参数定义完整性**:
   - [ ] 所有参数都有 `ToolParameter` 定义
   - [ ] 参数类型明确（string, integer, number, boolean, object, array）
   - [ ] 必需参数标记为 `required=True`
   - [ ] 可选参数有默认值或标记为 `required=False`
   - [ ] 枚举值参数有 `enum` 列表

2. **参数描述清晰**:
   - [ ] 每个参数都有清晰的 `description`
   - [ ] 描述说明参数的用途和格式要求
   - [ ] 对于复杂参数，提供示例

3. **参数验证**:
   - [ ] `validate_parameters()` 方法正确实现
   - [ ] 类型验证正确
   - [ ] 枚举值验证正确
   - [ ] 必需参数检查正确

### 输出格式检查

1. **输出模式定义**:
   - [ ] 定义了 `ToolOutputSchema`
   - [ ] 输出类型明确（object, array, string 等）
   - [ ] 对象属性完整定义（properties）
   - [ ] 数组元素类型定义（items）
   - [ ] 输出描述清晰

2. **输出示例**:
   - [ ] 提供了完整的输出示例
   - [ ] 示例覆盖所有字段
   - [ ] 示例格式正确

3. **输出验证**:
   - [ ] `execute()` 方法返回的 `ToolResult.data` 符合 `output_schema`
   - [ ] 输出格式验证逻辑正确
   - [ ] 错误情况下的输出格式也明确定义

### 工具描述检查

1. **工具描述**:
   - [ ] `description` 清晰说明工具功能
   - [ ] 描述包含使用场景
   - [ ] 描述包含限制说明
   - [ ] 描述包含最佳实践

2. **工具元数据**（可选，阶段 1）:
   - [ ] 定义了 `ToolMetadata`
   - [ ] 包含使用场景列表
   - [ ] 包含使用示例
   - [ ] 包含限制说明
   - [ ] 包含最佳实践
   - [ ] 包含相关工具列表

## 实施优先级

### 阶段 0：严格的输入输出定义（必须完成）

**优先级排序**（按使用频率和重要性）：

1. **🔴 最高优先级**（立即完成）:
   - `execute_code` - 代码执行工具，LLM 最常使用
   - `file_search` - 文件搜索工具，基础功能
   - `browser` - 浏览器工具，网络访问
   - `google_search` - Google 搜索工具，信息检索
   - `jupyter` - Jupyter 工具，交互式代码执行

2. **🟡 高优先级**（尽快完成）:
   - `file_organizer` - 文件整理工具
   - `pdf_parser` - PDF 解析工具
   - `wikipedia` - Wikipedia 搜索工具
   - `get_weather` - 天气工具
   - `video_downloader` - 视频下载工具
   - `ffmpeg` - FFmpeg 工具

3. **🟢 中低优先级**（后续完成）:
   - `zhihu_zhida` - 知乎直达工具
   - `mediawiki` - MediaWiki 工具
   - `gvim` - Gvim 编辑器工具
   - `whisper` - Whisper 语音转文字工具

## 检查步骤

1. **读取工具文件**，查看当前实现
2. **检查输入参数定义**，确保完整和正确
3. **检查输出格式**，确保有明确的定义
4. **添加输出模式定义**（ToolOutputSchema）
5. **添加输出示例**
6. **更新工具描述**，包含输出格式说明
7. **测试验证**，确保输出格式符合定义

## 检查工具

可以使用以下命令快速检查工具：

```bash
# 列出所有工具
python3 -c "from backend.core.agent.orchestrator import Orchestrator; o = Orchestrator(); print('\n'.join(o.tool_registry.list_tools()))"

# 检查特定工具的输入输出定义
python3 -c "from backend.core.agent.tools.builtin.file_search_tool import FileSearchTool; t = FileSearchTool(); print(t.to_dict())"
```

## 进度跟踪

- [ ] 阶段 0：严格的输入输出定义（0/15 完成）
  - [ ] execute_code
  - [ ] jupyter
  - [ ] file_search
  - [ ] file_organizer
  - [ ] pdf_parser
  - [ ] zhihu_zhida
  - [ ] browser
  - [ ] google_search
  - [ ] wikipedia
  - [ ] mediawiki
  - [ ] get_weather
  - [ ] gvim
  - [ ] video_downloader
  - [ ] ffmpeg
  - [ ] whisper

- [ ] 阶段 1：增强工具描述和元数据（0/15 完成）

- [ ] 阶段 2：优化 System Prompt（0/1 完成）

- [ ] 阶段 3：增强工具调用循环（0/2 完成）

