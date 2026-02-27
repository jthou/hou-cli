# 视频转语音、语音转文字：当前状态与任务队列接入

## 一、当前状态

### 1. 视频转语音 / 视频提音频

| 能力 | 实现位置 | 输入 | 状态 |
|------|----------|------|------|
| **从 URL 只下音频** | `video_downloader_tool` | 视频 URL | ✅ 已有，`extract_audio_only=true` |
| **从本地视频提音频** | `ffmpeg_tool` | 本地视频路径 | ✅ 已有，`operation=extract_audio` |

- **video_download**：在任务队列中已有任务类型；选「仅提取音频」即相当于「视频 URL → 音频文件」。
- **ffmpeg 提音频**：仅作为 **LLM 可调用的工具** 存在（orchestrator 已注册），**未**作为独立任务类型接入任务队列。

### 2. 语音转文字

| 能力 | 实现位置 | 输入 | 状态 |
|------|----------|------|------|
| **语音转文字 / 字幕** | `whisper_tool` | 本地音频路径 | ✅ 已有，依赖 `pip install openai-whisper` |

- **WhisperTool**：`audio_file`（必填）、`language`、`model`、`output_format`（json/text/srt）、`output_file`。
- 已在 **orchestrator** 中注册，供对话/LLM 调用；**未**作为独立任务类型接入任务队列。
- 测试需环境变量 `WHISPER_TEST_AUDIO_FILE` 或跳过（见 `test_whisper_tool.py`）。

---

## 二、如何接入当前任务列表体系

任务列表体系 = `TASK_TYPES` + `process_*_task` handler + API 创建/列表/详情 + Worker 执行。接入方式与 `video_download` 一致。

### 1. 可选新增任务类型

| 任务类型 | 含义 | 底层工具 |
|----------|------|----------|
| `video_extract_audio` | 本地视频 → 音频文件 | FFmpegTool `operation=extract_audio` |
| `speech_to_text` | 音频/视频 → 文字或字幕 | WhisperTool（视频需先走 ffmpeg 提音频或 video_download 提音频） |

说明：

- **仅「从 URL 下视频并只保留音频」**：无需新类型，用现有 `video_download` + `extract_audio_only: true` 即可。
- 若希望用户在**任务列表**里单独创建「本地视频提音频」「语音转文字」任务，再增加上述两种类型。

### 2. 接入步骤（以 `speech_to_text` 为例）

1. **在 `task_handlers.py` 的 `TASK_TYPES` 中增加**  
   - `speech_to_text`：`name`、`description`、`metadata_schema`。  
   - 建议必填：`input_file`（音频路径，或约定先由其他任务产出）；可选：`language`、`model`、`output_format`、`output_file`。

2. **实现 handler**  
   - `async def process_speech_to_text_task(task_info) -> Dict`：  
     - 从 `task_info["metadata"]` 取参。  
     - 调用 `WhisperTool().execute(audio_file=..., language=..., model=..., output_format=..., output_file=...)`（可在 `asyncio.to_thread` 中执行，与 `process_video_download_task` 一致）。  
     - 返回约定结构：`{"status": "success"|"error", "summary": "...", "data": {...}}`。

3. **注册 handler**  
   - 在 `register_default_handlers()` 中：  
     `worker.register_handler("speech_to_text", process_speech_to_text_task)`。

4. **任务名与 API**  
   - 在 `task_queue_routes._generate_task_name` 中为 `speech_to_text` 生成任务名（如基于 `input_file` 或时间戳）。  
   - 无需改 API 路由：创建任务仍用 `POST /api/task-queue/tasks`，`task_type: "speech_to_text"`，`metadata` 按 schema 传。

5. **长任务超时（可选）**  
   - 若语音转文字可能很长，在 `task_worker.py` 的 `_execute_task` 里对 `task_type == "speech_to_text"` 做类似 `video_download` 的 `asyncio.wait_for(handler(...), timeout=...)`。

6. **前端**  
   - 任务创建页若按 `GET /api/task-queue/task-types` 动态生成表单，则只需后端 schema 正确即可；必要时为 `speech_to_text` 增加单独入口或文案。

### 3. `video_extract_audio` 接入（若需要）

- 在 `TASK_TYPES` 中增加 `video_extract_audio`，schema 至少：`input_file`（本地视频路径）、`output_file` 或输出目录+自动命名；可选 `audio_format`、`audio_quality`。
- 实现 `process_video_extract_audio_task`：调用 `FFmpegTool().execute(operation="extract_audio", input_file=..., output_file=..., audio_format=..., audio_quality=...)`。
- 其余同上面：注册 handler、任务名、可选超时、前端。

---

## 三、小结

| 能力 | 工具状态 | 任务队列状态 | 接入建议 |
|------|----------|--------------|----------|
| 视频 URL → 音频 | video_downloader（extract_audio_only） | ✅ 已有 video_download | 无需新类型 |
| 本地视频 → 音频 | ffmpeg_tool extract_audio | ❌ 未接入 | 可选新增 `video_extract_audio` |
| 语音 → 文字/字幕 | whisper_tool | ❌ 未接入 | 新增 `speech_to_text`，按上面步骤接入 |

按上述步骤即可把「语音转文字」和（可选）「本地视频提音频」接入当前任务列表体系，与 `video_download`、`weather_query` 一致。
