# Video Extract SRT Skill

视频字幕提取技能 - 专注于提取视频字幕文件（SRT格式）

## 功能

- 下载视频（如果提供 URL）
- 提取音频（如果视频包含音频流）
- 生成字幕文件（SRT 格式）

## 使用示例

### 通过 CLI 使用

```bash
# 为本地视频文件生成字幕
hou-cli chat "/home/user/video.mp4 提取字幕"

# 为在线视频生成字幕
hou-cli chat "https://www.bilibili.com/video/BV1B5xkzPEhx 提取字幕"
```

### 通过 Python API 使用

```python
from backend.core.agent.orchestrator import Orchestrator

orchestrator = Orchestrator()

# 自动匹配并执行技能
async for chunk in orchestrator.stream_process("为这个视频生成字幕 /path/to/video.mp4"):
    print(chunk, end='')
```

## 参数

- `url` (可选): 视频 URL
- `video_path` (可选): 视频文件路径
- `model` (可选): Whisper 模型大小，默认 `base`，可选值：`tiny`, `base`, `small`, `medium`, `large`
- `output_dir` (可选): 输出目录，默认与视频文件同目录

## 输出

- `video_path`: 视频文件路径
- `audio_path`: 音频文件路径（如果提取成功）
- `subtitle_path`: 字幕文件路径（SRT 格式）

## 特点

- **简化工作流**：只专注于字幕提取，不生成摘要或文章
- **支持无音频流视频**：如果视频没有音频流，会尝试直接使用视频文件生成字幕
- **智能缓存**：已生成的字幕文件会被缓存，避免重复处理
- **错误处理**：音频提取失败时会自动回退到使用视频文件

## 与 video_summary 的区别

- `video_extract_srt`: 只提取字幕文件，快速、专注
- `video_summary`: 提取字幕后还会生成摘要和文章，功能更全面但更耗时

