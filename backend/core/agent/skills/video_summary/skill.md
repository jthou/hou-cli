# 视频摘要技能 (Video Summary Skill)

## 概述

视频摘要技能是一个完整的视频内容分析工具，能够自动下载视频、提取音频、生成字幕、阅读内容并生成带时间戳的摘要和文章。

## 功能特性

### 核心功能

1. **视频下载**
   - 支持多种视频平台（Bilibili、YouTube 等）
   - 自动选择最佳下载工具（yt-dlp、you-get）
   - 支持断点续传和重试

2. **音频提取**
   - 使用 FFmpeg 提取音频
   - 支持多种音频格式（MP3、WAV 等）
   - 自动质量优化

3. **字幕生成**
   - 使用 Whisper 进行语音转文字
   - 支持多种模型大小（tiny/base/small/medium/large）
   - 实时进度显示
   - 实时 SRT 文件写入

4. **内容分析**
   - 自动读取和解析字幕文件
   - 提取时间戳索引（纯文本格式，容错率高）
   - 支持长文本自动分块处理

5. **摘要生成**
   - 基于字幕内容生成摘要
   - 每个关键点标注时间戳 `[HH:MM:SS]`
   - 支持用户需求导向（如"重点关注技术细节"）
   - 支持交互式调整（多轮反馈优化）

6. **文章生成**
   - 基于摘要和字幕生成结构化文章
   - 支持多种格式（Markdown、HTML、Text）
   - 保留时间戳标注
   - 支持长文本分块处理

### 高级特性

1. **时间戳提取和映射**
   - 自动提取字幕段落的时间戳
   - 建立关键点与时间戳的映射关系
   - 纯文本格式输出（容错率高）
   - 为视频剪裁提供数据基础

2. **长文本处理**
   - 自动检测文本长度
   - 智能分块（按段落，保持语义完整性）
   - 层次化摘要和文章生成
   - 支持超大视频（> 80K 字符）

3. **交互式摘要调整**
   - 支持多轮反馈优化
   - 支持长度、内容重点、风格、结构调整
   - 保存调整历史
   - 智能理解用户意图

## 参数说明

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `url` | string | 否 | - | 视频 URL（如果视频已下载，可留空） |
| `video_path` | string | 否 | - | 视频文件路径（如果视频已下载） |
| `model` | string | 否 | base | Whisper 模型大小（tiny/base/small/medium/large） |
| `summary_length` | integer | 否 | 200 | 摘要长度（字数） |
| `article_length` | integer | 否 | 1000 | 文章长度（字数） |
| `article_format` | string | 否 | markdown | 文章格式（markdown/html/text） |
| `output_dir` | string | 否 | - | 输出目录（可选） |
| `user_query` | string | 否 | - | 用户问题或需求（用于指导摘要生成） |
| `enable_interactive` | boolean | 否 | false | 是否启用交互式摘要调整 |
| `max_refinement_iterations` | integer | 否 | 3 | 最大摘要调整轮数 |

## 工作流程

### 标准流程（15 步）

```
1. 检查并下载视频
   ↓
2. 检查并提取音频
   ↓
3. 生成字幕（SRT 格式）
   ↓
4. 读取字幕文件（提取时间戳索引）
   ↓
5. 检查文本长度并分块（如果需要）
   ↓
6. 生成初始摘要（带时间戳标注）
   ├─→ 短文本：直接生成
   └─→ 长文本：分块生成 → 合并
   ↓
7. 统一摘要输出
   ↓
8. 交互式摘要调整（可选）
   ↓
9. 获取最终摘要
   ↓
10. 提取时间戳映射
   ↓
11. 生成文章
    ├─→ 短文本：直接生成
    └─→ 长文本：分块生成 → 合并
```

### 时间戳处理流程

```
字幕文件（SRT）
  ↓
解析段落和时间戳
  ↓
生成时间戳索引（纯文本格式）
  ↓
摘要生成时标注时间戳
  ↓
提取时间戳映射
  ↓
输出结构化时间戳数据
```

## 输出格式

### 摘要输出

**文本格式**（带时间戳标注）：
```
视频介绍了 Python 异步编程 [00:05:30]，包括 async/await 语法 [00:08:15] 和实际应用 [00:12:00]。
```

**时间戳映射**（纯文本格式）：
```
=== TIMESTAMP_MAPPING ===
TOTAL_KEY_POINTS: 3

=== KEY_POINTS ===
1|[00:05:30]|00:05:30|00:08:15|330.000|495.000|165.000|10,11,12|视频介绍了 Python 异步编程
2|[00:08:15]|00:08:15|00:12:00|495.000|720.000|225.000|13,14,15|包括 async/await 语法
3|[00:12:00]|00:12:00|00:15:00|720.000|900.000|180.000|18,19,20|实际应用案例
```

### 文章输出

支持 Markdown、HTML、Text 格式，包含：
- 标题
- 摘要（带时间戳）
- 详细内容
- 时间戳参考

## 使用示例

### 示例 1：基本使用

```python
from backend.core.agent.skills.video_summary import VideoSummarySkill

skill = VideoSummarySkill(executor)
result = await skill.execute({
    "url": "https://www.bilibili.com/video/BV1B5xkzPEhx",
    "summary_length": 200,
    "article_length": 1000
})
```

### 示例 2：带用户需求

```python
result = await skill.execute({
    "url": "https://www.bilibili.com/video/BV1B5xkzPEhx",
    "user_query": "重点关注技术实现细节",
    "summary_length": 300
})
```

### 示例 3：交互式调整

```python
result = await skill.execute({
    "url": "https://www.bilibili.com/video/BV1B5xkzPEhx",
    "enable_interactive": True,
    "max_refinement_iterations": 5
})
```

## 依赖工具

- `video_downloader`: 视频下载工具
- `ffmpeg`: 音频提取工具
- `whisper`: 语音转文字工具
- `code_executor`: 代码执行工具（用于字幕解析和时间戳提取）

## 配置参数

### 长文本处理配置

```yaml
long_text_handling:
  max_text_length: 80000        # 文本长度阈值（字符）
  max_tokens_per_chunk: 15000 # 每个分块的最大 token 数
  llm_context_window: 32000     # LLM 上下文窗口大小
  llm_output_tokens: 2000       # 预留给 LLM 输出的 token 数
  llm_prompt_tokens: 1000       # 预留给 LLM prompt 的 token 数
```

### 时间戳提取配置

```yaml
timestamp_extraction:
  enabled: true                 # 是否提取时间戳
  format: "simple"             # 时间戳格式：simple (HH:MM:SS) 或 detailed (HH:MM:SS.mmm)
  include_segments: true        # 是否包含关联的字幕段落索引
  generate_mapping: true        # 是否生成时间戳映射
  output_format: "text"         # 输出格式：text (纯文本，容错率高)
```

### 交互式摘要调整配置

```yaml
interactive_refinement:
  enabled: false                # 默认不启用，需要用户显式开启
  max_iterations: 3             # 最大调整轮数
  auto_present: true            # 自动展示摘要
  feedback_timeout: 300         # 等待用户反馈的超时时间（秒）
  save_history: true            # 是否保存调整历史
```

## 错误处理

### 错误处理策略

| 步骤 | 策略 | 说明 |
|------|------|------|
| 视频下载 | retry | 最多重试 3 次，延迟 5 秒 |
| 音频提取 | fail | 失败则终止，无法继续 |
| 字幕生成 | retry | 最多重试 2 次，延迟 10 秒 |
| 字幕读取 | fail | 失败则终止，无法继续 |
| 摘要生成 | fallback | 失败时使用降级方案 |
| 文章生成 | partial | 返回部分结果 |

### 降级方案

- 摘要生成失败：使用字幕前 100 字作为摘要
- 文章生成失败：返回分块结果的简单拼接
- 分块处理失败：跳过该分块，继续处理其他分块

## 性能优化

1. **缓存机制**
   - 检查已下载的视频文件
   - 检查已提取的音频文件
   - 检查已生成的字幕文件

2. **并行处理**
   - 支持分块并行处理（未来优化）

3. **进度报告**
   - 实时进度更新
   - 步骤级别的进度信息

## 限制和注意事项

1. **视频格式**
   - 支持主流视频格式（MP4、AVI、MKV 等）
   - 某些平台可能有格式限制

2. **字幕质量**
   - 依赖 Whisper 模型的准确性
   - 嘈杂音频可能影响转录质量

3. **长文本处理**
   - 超大视频（> 80K 字符）需要分块处理
   - 分块可能影响整体语义连贯性

4. **时间戳精度**
   - 时间戳基于字幕段落
   - 关键点可能跨越多个段落

## 未来改进

1. **智能参数提取**
   - 使用 LLM 从用户输入中提取参数
   - 自动补全缺失参数

2. **更多视频平台支持**
   - 扩展下载工具支持
   - 优化平台特定处理

3. **摘要质量提升**
   - 更智能的关键点提取
   - 更准确的时间戳标注

4. **视频剪裁集成**
   - 基于时间戳映射自动剪裁视频
   - 生成高亮片段集合

## 相关文档

- [技能架构设计](../agent-tool-skill-architecture.md)
- [时间戳提取技术文档](references/timestamp_extraction.md)
- [交互式摘要调整技术文档](references/interactive_refinement.md)
- [长文本处理策略](references/long_text_handling.md)




