# 媒体文件命名规范

视频下载、音频提取、字幕提取等功能的输出文件采用统一命名规则，便于一眼识别视频、音频、字幕之间的对应关系。

## 命名规则

| 类型 | 模式 | 示例 |
|------|------|------|
| **视频** | `{base}.{ext}` | `访谈标题.mp4` |
| **音频** | `{base}_audio.{ext}` | `访谈标题_audio.mp3` |
| **字幕** | `{base}_subtitle.{lang}.{ext}` 或 `{base}_subtitle.{ext}` | `访谈标题_subtitle.zh.srt`、`音频名_subtitle.srt` |

- **base**：基础名。视频下载来自标题；本地视频/音频提取来自输入文件主名（不含扩展名）
- **ext**：扩展名（mp4、mp3、srt 等）
- **lang**：语言代码（如 zh、en），仅当有多语言字幕时使用

## 应用场景

### 1. 视频下载 (video_download)

- **完整视频**：`%(title)s.%(ext)s` → `访谈标题.mp4`
- **仅音频**：`%(title)s_audio.%(ext)s` → `访谈标题_audio.mp3`
- **仅字幕**：`%(title)s_subtitle.%(lang)s.%(ext)s` → `访谈标题_subtitle.zh.srt`
- **视频+字幕**：视频同上；字幕同上

### 2. 视频提取音频 (video_extract_audio)

- 输入：`访谈标题.mp4`
- 输出：`{input_stem}_audio.{ext}` → `访谈标题_audio.mp3`

### 3. 语音转文字 (speech_to_text)

- 输入：`访谈标题_audio.mp3`（或任意音频）
- 输出：`{input_stem}_subtitle.{ext}` → `访谈标题_audio_subtitle.srt`

## 管道示例

```
视频下载(完整)     → 访谈标题.mp4
       ↓
视频提取音频       → 访谈标题_audio.mp3
       ↓
语音转文字         → 访谈标题_audio_subtitle.srt
```

或：

```
视频下载(仅音频)   → 访谈标题_audio.mp3
       ↓
语音转文字         → 访谈标题_audio_subtitle.srt
```

## 实现位置

- `backend/core/agent/tools/builtin/video_downloader_tool.py`：yt-dlp outtmpl
- `backend/infrastructure/execution/task_handlers.py`：video_extract_audio、speech_to_text 的默认输出路径
