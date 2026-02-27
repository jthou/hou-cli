# 任务类型设计：语音转文字、视频提音频

本文档定义两个新任务类型的完整设计，用于接入当前任务队列体系（与 `video_download`、`weather_query` 一致）。

---

## 1. 设计原则与对齐

- **任务定义**：在 `task_handlers.TASK_TYPES` 中唯一定义；`metadata_schema` 供 API/前端校验与展示。
- **执行契约**：Handler 成功返回 `{ "status": "success", "summary": "一句摘要", "data": {...} }`；失败建议返回统一结构 `{ "status": "error", "summary": "...", "error": { "code", "message", "details" } }`（见 2.5 节），不抛异常便于写入任务 result；若抛异常则由 Worker 写入任务 `error` 字符串。
- **路径安全**：输入/输出路径需校验存在性及可访问范围；输出目录建议限制在用户主目录下（与 `video_download` 的 `output_dir` 一致）。
- **长任务**：语音转文字、大文件提音频可能耗时较长，Worker 侧可配置超时（类似 `video_download`）。

---

## 2. 任务类型一：`speech_to_text`（语音转文字）

### 2.1 概述

| 项 | 说明 |
|----|------|
| **type** | `speech_to_text` |
| **name** | 语音转文字 |
| **description** | 使用 Whisper 将音频文件转成文字或字幕（支持 json/text/srt） |
| **底层工具** | `WhisperTool`（`backend/core/agent/tools/builtin/whisper_tool.py`） |

### 2.2 metadata_schema

| 字段 | type | required | description | placeholder / enum / default |
|------|------|----------|-------------|-----------------------------|
| **input_file** | string | **True** | 音频文件路径（支持 mp3, wav, m4a, flac 等） | 如：/Users/xx/audio.mp3 |
| **language** | string | False | 语言代码，auto 为自动检测 | zh, en, ja；默认 auto |
| **model** | string | False | Whisper 模型大小 | enum: tiny, base, small, medium, large；默认 base |
| **output_format** | string | False | 输出格式 | enum: json, text, srt；默认 srt（便于字幕场景） |
| **output_file** | string | False | 输出文件路径；不填则自动生成到项目默认输出目录 | 如：/Users/xx/out.srt |
| **output_dir** | string | False | 输出目录（仅当未指定 output_file 时生效） | 须在用户主目录下，留空则使用 ~/hou-cli/outputs |

**enum 详细（与现有 WhisperTool 一致）**：

- **model**：`[ {"value":"tiny","label":"Tiny"}, {"value":"base","label":"Base"}, {"value":"small","label":"Small"}, {"value":"medium","label":"Medium"}, {"value":"large","label":"Large"} ]`
- **output_format**：`[ {"value":"json","label":"JSON"}, {"value":"text","label":"纯文本"}, {"value":"srt","label":"字幕 SRT"} ]`

### 2.3 校验规则

- **input_file**：必填；非空字符串；对应路径需存在且为文件（可 `expanduser`）；建议限制在用户主目录或允许的根目录下，防止读取任意系统文件。
- **output_file** / **output_dir**：若提供，须在用户主目录下（使用 `normalize_output_dir` 或等价逻辑，`restrict_to_home=True`）；不提供则使用项目统一默认输出目录 `~/hou-cli/outputs`。

### 2.4 Handler 行为：`process_speech_to_text_task(task_info)`

1. **取参**：从 `task_info["metadata"]` 读取 `input_file`、`language`、`model`、`output_format`、`output_file`、`output_dir`。
2. **校验**：校验 `input_file` 存在、可读、路径安全；若指定 `output_file` 或 `output_dir`，做主目录限制。
3. **输出路径**：若未传 `output_file`，则根据 `output_dir`（经 `normalize_output_dir(..., restrict_to_home=True)`）或项目默认输出目录（`~/hou-cli/outputs`），生成默认输出路径（如 `{input_stem}_transcription.{srt|txt|json}`）。
4. **执行**：在 `asyncio.to_thread` 中调用 `WhisperTool().execute(...)`；将工具的进度回调映射到 `worker.update_task_progress`（见 2.6 节）。
5. **返回**：
   - 成功：`{ "status": "success", "summary": "已转写至 xxx.srt", "data": { ... } }`。
   - 失败：**不抛异常**，返回统一错误结构（见 2.5 节），由 Worker 将 `result` 写入任务；若 handler 抛异常，Worker 将异常信息写入任务的 `error` 字段。

### 2.5 错误处理与返回格式

**统一错误返回结构**（写入任务 `result` 或由 Worker 写入 `error` 时保持一致）：

```json
{
  "status": "error",
  "summary": "一句给用户看的简短说明",
  "error": {
    "code": "ERROR_CODE",
    "message": "详细错误信息",
    "details": "可选，如异常堆栈或路径"
  }
}
```

**建议错误码**：

| code | 含义 | 典型触发 |
|------|------|----------|
| `INPUT_FILE_NOT_FOUND` | 输入文件不存在 | 路径错误或文件已删除 |
| `INPUT_PATH_OUTSIDE_HOME` | 输入路径不在允许范围内 | 路径安全校验失败 |
| `OUTPUT_PATH_DENIED` | 输出路径不可写或越界 | output_dir 超出主目录 |
| `WHISPER_NOT_AVAILABLE` | Whisper 未安装或加载失败 | 未安装 openai-whisper 或依赖 |
| `UNSUPPORTED_FORMAT` | 文件格式不支持 | 非音频或无法解码 |
| `TRANSCRIPTION_FAILED` | 转写过程失败 | 模型异常、OOM、内部错误 |
| `TIMEOUT` | 执行超时 | Worker 侧 wait_for 超时 |

**Handler 内失败时的具体处理示例**（返回 dict，不抛异常，便于统一写入 result）：

```python
# 失败时返回约定结构，由调用方写入任务 result
def _err(code: str, summary: str, message: str, details: str = None):
    return {
        "status": "error",
        "summary": summary,
        "error": {"code": code, "message": message, "details": details or ""}
    }

# 示例：输入文件不存在
input_path = Path(metadata["input_file"]).expanduser().resolve()
if not input_path.exists():
    return _err("INPUT_FILE_NOT_FOUND", "输入文件不存在", f"指定的音频文件不存在: {input_path}")

# 示例：路径不在主目录下
try:
    input_path.relative_to(Path.home().resolve())
except ValueError:
    return _err("INPUT_PATH_OUTSIDE_HOME", "路径不允许", "输入路径必须在用户主目录下")

# 示例：Whisper 未安装
except ImportError as e:
    return _err("WHISPER_NOT_AVAILABLE", "Whisper 未安装或路径错误", str(e))

# 示例：转写过程异常
except Exception as e:
    return _err("TRANSCRIPTION_FAILED", "转写失败", str(e), details=traceback.format_exc())
```

若 handler 选择**抛异常**，Worker 会将 `str(e)` 写入任务的 `error` 字段，此时前端展示的仍是字符串；若要前端解析 `code`，建议 handler 返回上述 dict 而非抛异常。

### 2.6 进度反馈机制

- **更新频率**：建议每 **15–30 秒** 至少更新一次进度（与 WhisperTool 内部现有 `report_interval=30` 对齐）；长时间无输出时前端可显示「转写中…」。
- **进度值**：Whisper 无精确百分比时，可用 0～99 表示进行中、100 表示完成；或传 `progress=0` 仅更新 `message` 文案。
- **进度回调实现示例**（在 handler 内挂到 WhisperTool）：

```python
worker = get_task_worker()

def on_progress(pct: int, msg: str):
    try:
        worker.update_task_progress(pct or 0, msg or "转写中...")
    except Exception:
        pass

tool = WhisperTool()
if hasattr(tool, "report_progress"):
    tool.report_progress = on_progress
# 若 WhisperTool 使用 progress_callback 属性名，则设为 tool.progress_callback = on_progress
result = await asyncio.to_thread(
    lambda: tool.execute(audio_file=..., language=..., model=..., output_format=..., output_file=...)
)
```

- **video_extract_audio**：提取音频通常较快（分钟级），可不做细粒度进度，仅在开始/完成时更新 `message` 即可。

### 2.7 依赖与可选

- **Whisper**：已纳入 `requirements.txt`（`openai-whisper`），执行 `make start` 时会自动执行 `pip install -r requirements.txt` 安装。若未安装或加载失败，返回 `WHISPER_NOT_AVAILABLE` 及明确 message。
- **进度**：按 2.6 将 WhisperTool 的 `report_progress` 或 `progress_callback` 映射到 `worker.update_task_progress`。

---

## 3. 任务类型二：`video_extract_audio`（本地视频提取音频）

### 3.1 概述

| 项 | 说明 |
|----|------|
| **type** | `video_extract_audio` |
| **name** | 视频提取音频 |
| **description** | 从本地视频文件中提取音频轨并保存为音频文件 |
| **底层工具** | `FFmpegTool`（`backend/core/agent/tools/builtin/ffmpeg_tool.py`），`operation=extract_audio` |

### 3.2 metadata_schema

| 字段 | type | required | description | placeholder / enum / default |
|------|------|----------|-------------|-----------------------------|
| **input_file** | string | **True** | 本地视频文件路径 | 如：/Users/xx/video.mp4 |
| **output_file** | string | False | 输出音频文件路径；不填则自动生成到项目默认输出目录 | 如：/Users/xx/audio.mp3 |
| **output_dir** | string | False | 输出目录（仅当未指定 output_file 时生效） | 须在用户主目录下，留空则使用 ~/hou-cli/outputs |
| **audio_format** | string | False | 音频格式 | enum: mp3, wav, aac, flac, ogg；默认 mp3 |
| **audio_quality** | string | False | 音频码率/质量 | 默认 192k；可选 128k, 256k, 320k 等 |

**enum 详细（与 FFmpegTool 一致）**：

- **audio_format**：`[ {"value":"mp3","label":"MP3"}, {"value":"wav","label":"WAV"}, {"value":"aac","label":"AAC"}, {"value":"flac","label":"FLAC"}, {"value":"ogg","label":"OGG"} ]`
- **audio_quality**：可选 `[ {"value":"128k","label":"128k"}, {"value":"192k","label":"192k"}, {"value":"256k","label":"256k"}, {"value":"320k","label":"320k"} ]`

### 3.3 校验规则

- **input_file**：必填；非空；路径存在且为文件；建议限制在用户主目录下（或白名单目录），防止读取任意路径。
- **output_file** / **output_dir**：若提供，须在用户主目录下；不提供则使用项目统一默认输出目录 `~/hou-cli/outputs`，文件名由输入 stem + 扩展名（如 `.mp3`）生成。

### 3.4 Handler 行为：`process_video_extract_audio_task(task_info)`

1. **取参**：从 `task_info["metadata"]` 读取 `input_file`、`output_file`、`output_dir`、`audio_format`、`audio_quality`。
2. **校验**：校验 `input_file` 存在、可读、路径安全；若指定 `output_file` 或 `output_dir`，做主目录限制。
3. **输出路径**：若未传 `output_file`，则根据 `output_dir`（经 `normalize_output_dir(..., restrict_to_home=True)`）或项目默认输出目录（`~/hou-cli/outputs`），生成默认输出路径（如 `{input_stem}.mp3`），扩展名由 `audio_format` 决定。
4. **执行**：在 `asyncio.to_thread` 中调用 `FFmpegTool().execute(operation="extract_audio", input_file=..., output_file=..., audio_format=..., audio_quality=...)`。
5. **返回**：
   - 成功：`{ "status": "success", "summary": "已提取至 xxx.mp3", "data": { ... } }`。
   - 失败：与 2.5 节一致，返回统一错误结构；建议错误码：`INPUT_FILE_NOT_FOUND`、`INPUT_PATH_OUTSIDE_HOME`、`OUTPUT_PATH_DENIED`、`FFMPEG_NOT_FOUND`、`EXTRACT_AUDIO_FAILED`。

### 3.5 依赖与可选

- **FFmpeg**：依赖系统安装（如 `brew install ffmpeg`）；若未找到，返回 `FFMPEG_NOT_FOUND` 及明确 message。
- **进度**：extract_audio 通常较快，仅在开始/完成时更新 `message` 即可；若需要可后续在 FFmpegTool 侧增加进度回调。

---

## 4. 路径安全统一约定

- **输入路径（input_file）**：
  - 必须存在且为文件。
  - 建议：`Path(input_file).expanduser().resolve()` 后，检查 `path.relative_to(Path.home().resolve())` 或白名单目录，禁止读写主目录外的路径。
- **输出路径（output_file / output_dir）**：
  - 与 `video_download` 一致：使用 `normalize_output_dir(output_dir, restrict_to_home=True)` 或对 `output_file` 的父目录做同样主目录限制；未指定则使用项目统一默认输出目录 `~/hou-cli/outputs`，超出主目录则拒绝。

---

## 5. 与任务队列的集成

### 5.1 注册与命名

- 在 **task_handlers.py** 的 `TASK_TYPES` 中增加上述两类的 `name`、`description`、`metadata_schema`。
- 在 **register_default_handlers()** 中注册：
  - `worker.register_handler("speech_to_text", process_speech_to_text_task)`
  - `worker.register_handler("video_extract_audio", process_video_extract_audio_task)`
- 在 **task_queue_routes._generate_task_name** 中：
  - `speech_to_text`：如 `语音转文字 {input_file 短名} {MM-DD HH:MM}`。
  - `video_extract_audio`：如 `视频提音频 {input_file 短名} {MM-DD HH:MM}`。

### 5.2 API

- 无需新增路由：仍使用 `POST /api/task-queue/tasks`，`task_type` 传 `speech_to_text` 或 `video_extract_audio`，`metadata` 按 schema 传。
- `GET /api/task-queue/task-types` 会通过 `get_available_task_types()` 自动包含新类型及其 `metadata_schema`。

### 5.3 Worker 超时

- 在 **task_worker._execute_task** 中，对这两种任务类型使用 `asyncio.wait_for(handler(...), timeout=...)`，超时则标记任务失败并写入 `error`（建议 `error` 中含 `code: "TIMEOUT"` 或 summary 注明「执行超时」）。
- **建议超时配置**（秒）：

```python
# task_worker.py 或配置中
TASK_TIMEOUT_SECONDS = {
    "video_download": 30 * 60,       # 已有：30 分钟
    "speech_to_text": 60 * 60,       # 1 小时（长音频 + large 模型可能较久）
    "video_extract_audio": 30 * 60, # 30 分钟
}
timeout = TASK_TIMEOUT_SECONDS.get(task_type)
if timeout:
    result = await asyncio.wait_for(handler(task_info), timeout=timeout)
else:
    result = await handler(task_info)
```

### 5.4 前端

- 任务创建页若根据 `GET /api/task-queue/task-types` 动态渲染表单，则新类型会自动出现；可为 `speech_to_text`、`video_extract_audio` 增加单独入口或文案说明。

### 5.5 性能基准与并发

**性能基准（参考，视硬件与文件而定）**：

| 场景 | 预期时间 | 说明 |
|------|----------|------|
| 1 小时音频转写（base 模型） | 约 30–60 分钟 | CPU/GPU 差异大；large 更慢 |
| 1 小时音频转写（large 模型） | 约 1–2 小时 | 显存约 4GB+ |
| 1GB 视频提取音频 | 约 5–10 分钟 | 以 FFmpeg 为主 |
| 内存占用 | Whisper large 约 4GB，FFmpeg 约 100MB | 多任务时需考虑 |

**并发与资源**：

- **Worker 单进程**：同一 Worker 串行执行任务，语音转写会长时间占用该 Worker；若多任务堆积，可考虑为 `speech_to_text` 单独 Worker 或限流。
- **多 Worker**：多进程/多机 Worker 可并行执行不同任务；单机多 Worker 时注意总内存（尤其 Whisper large）。
- **建议**：不在本设计内强制并发上限；实现时可在配置中提供「最大并发 speech_to_text」等开关，便于运维调优。

---

## 6. 实施清单

| 步骤 | 项 | 说明 |
|------|----|------|
| 1 | TASK_TYPES | 在 task_handlers.py 中增加 speech_to_text、video_extract_audio 的完整 schema |
| 2 | 路径校验 | 实现 _validate_input_path_in_home / 复用 normalize_output_dir，在 handler 内校验 input_file、output |
| 3 | process_speech_to_text_task | 实现 async handler，调用 WhisperTool，统一错误返回格式（2.5），进度回调（2.6） |
| 4 | process_video_extract_audio_task | 实现 async handler，调用 FFmpegTool extract_audio，统一错误返回格式 |
| 5 | register_default_handlers | 注册上述两个 handler |
| 6 | _generate_task_name | 为两种类型生成任务名 |
| 7 | task_worker 超时 | 按 5.3 配置 speech_to_text=3600s、video_extract_audio=1800s |
| 8 | 测试 | 按 6.1 单测 + 6.2 API/集成测试 + 6.3 边界与错误用例 |
| 9 | 前端 | 可选：任务创建页增加入口或说明 |

### 6.1 单元测试（handler 与工具）

- **process_speech_to_text_task**：mock WhisperTool.execute，断言成功时返回 `status/summary/data` 结构；断言缺 `input_file` 时返回 `INPUT_FILE_NOT_FOUND` 或校验失败；断言 input_file 不存在时返回错误码；断言路径越界时返回 `INPUT_PATH_OUTSIDE_HOME`。
- **process_video_extract_audio_task**：mock FFmpegTool.execute，断言成功返回结构；断言缺 input_file、input 不存在、FFmpeg 不可用时返回对应错误结构。
- **路径校验函数**：单测 `_validate_input_path_in_home` 在允许/禁止路径下的行为。

### 6.2 API 与集成测试

- **创建任务**：`POST /api/task-queue/tasks`，`task_type=speech_to_text`，`metadata` 含合法 `input_file`（或 mock 存在），断言 200 与 `task_id`；同样测 `video_extract_audio`。
- **GET task-types**：断言响应中含 `speech_to_text`、`video_extract_audio`，且其 `metadata_schema` 含必填 `input_file` 及枚举字段。
- **列表/详情**：创建任务后 GET 列表、GET 详情，断言 `task` 含 `metadata`、`status`、执行完成后含 `result`（或 `error`）；断言 `result.status` 与 `result.error.code`（失败时）符合 2.5 节。
- **透传**：创建时传可选字段（如 `output_format`、`audio_format`），断言 DB/详情中 `metadata` 与传入一致，且 handler 实际收到并生效（可用 mock 断言工具被调用的参数）。

### 6.3 边界与错误用例

- **speech_to_text**：缺 `input_file` → 400 或创建后首次执行返回错误码；`input_file` 指向不存在路径 → 执行结果 `INPUT_FILE_NOT_FOUND`；`input_file` 为主目录外路径 → `INPUT_PATH_OUTSIDE_HOME`；Whisper 未安装（mock）→ `WHISPER_NOT_AVAILABLE`；超时（mock 长时间执行）→ 任务 `error` 含超时信息。
- **video_extract_audio**：缺 `input_file` → 同上；输入文件不存在 → `INPUT_FILE_NOT_FOUND`；输出目录只读或越界 → `OUTPUT_PATH_DENIED`；FFmpeg 未找到（mock）→ `FFMPEG_NOT_FOUND`。
- **校验层**：`validate_task_creation("speech_to_text", {})` 返回 False 且提示缺 `input_file`；非法 enum 值（如 `model=invalid`）返回校验失败。

---

## 7. 与现有能力的关系

- **视频 URL → 音频**：仍使用现有 **video_download** 任务，`extract_audio_only: true`，无需新任务类型。
- **视频 → 音频 → 文字**：可由用户先创建 **video_extract_audio**（或 video_download 仅音频），再对产出音频创建 **speech_to_text**；或后续在编排层支持「组合任务」自动串联，本设计不强制。

本文档为构建这两个任务类型的权威设计说明，实现时以本设计为准并与现有 video_download / weather_query 风格保持一致。

---

## 8. 实施状态（已落地）

| 步骤 | 项 | 状态 |
|------|----|------|
| 1 | TASK_TYPES | ✅ 已增加 speech_to_text、video_extract_audio 及完整 metadata_schema |
| 2 | 路径校验 | ✅ _validate_input_path_in_home、_validate_output_path_in_home，handler 内校验 |
| 3 | process_speech_to_text_task | ✅ 统一错误返回、进度回调挂 worker.update_task_progress |
| 4 | process_video_extract_audio_task | ✅ 统一错误返回、FFmpegTool extract_audio |
| 5 | register_default_handlers | ✅ 已注册两种类型 |
| 6 | _generate_task_name | ✅ task_queue_routes 已为两种类型生成任务名 |
| 7 | task_worker 超时 | ✅ TASK_TIMEOUT_SECONDS：speech_to_text=3600，video_extract_audio=1800 |
| 8 | 测试 | ✅ 单测（handler/路径/校验）、API（创建/task-types/透传）、边界（不存在/主目录外/非法 enum） |
| 9 | 前端 | ✅ 任务创建页选择语音转文字/视频提音频时展示「输入文件须为主目录下本地路径」说明 |
