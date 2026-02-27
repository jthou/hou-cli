# 语音转文字、视频提音频任务：试用说明

## 一、距离试用还差什么

### 1. 环境与依赖（必须）

| 任务类型 | 依赖 | 说明 |
|----------|------|------|
| **语音转文字** | Whisper | 已写入 `requirements.txt`（`openai-whisper`），`make start` 时会执行 `pip install -r requirements.txt` 自动安装 |
| **视频提音频** | FFmpeg | 系统已安装 FFmpeg（如 `brew install ffmpeg`），且 `ffmpeg` 在 PATH 中 |

- Worker 已随主进程启动（`main.py` 内 `register_default_handlers()` + `worker.start()`），无需单独起进程。
- 输入文件**必须**是用户主目录下**已存在**的本地路径（如 `/Users/xxx/audio.mp3`），否则执行会返回 `INPUT_FILE_NOT_FOUND` 或 `INPUT_PATH_OUTSIDE_HOME`。

### 2. 前端结果展示（建议）

- **当前**：任务详情里 `TaskResultDisplay` 对 `speech_to_text`、`video_extract_audio` 及 `result.status === 'error'` 会退回为整块 JSON 展示，可读性一般。
- **建议**：对 `result.status === 'error'` 展示为红色提示框（summary + error.message/code）；对两种新类型成功结果展示 summary + 输出文件路径（语音转文字可带正文摘要）。这样试用时无需看原始 JSON。

### 3. 可选

- 列表页对「已完成但 result.status === 'error'」的任务用不同样式或副文案（如「执行失败」），与真正成功区分。
- 在 SETUP.md 或 README 中增加一节「语音转文字与视频提音频任务」，指向本试用说明与 `backend/externals/README.md`。

---

## 二、试用步骤（环境就绪后）

1. **启动应用**  
   在项目根目录执行 `make start`（会先安装 `requirements.txt` 依赖再启动后端）；或按项目常规方式启动后端（含 Worker）与前端。

2. **准备输入文件**  
   - 语音转文字：将一段音频（如 mp3/wav/m4a）放到用户主目录下某路径，例如 `~/Downloads/test.mp3`。  
   - 视频提音频：将视频文件放到主目录下，例如 `~/Downloads/video.mp4`。

3. **创建任务**  
   - 打开「任务管理」页，点击「创建任务」。  
   - 选择「语音转文字」或「视频提取音频」，在必填项「输入文件」中填写上述路径（如 `/Users/你的用户名/Downloads/test.mp3`）。  
   - 可选：选择模型、输出格式、输出目录等。  
   - 提交创建。

4. **查看结果**  
   - 在任务列表中可看状态（待执行 → 运行中 → 已完成）和一句摘要（result_summary）。  
   - 点击「查看详情」查看完整 result；成功时为 summary + 输出文件路径（及语音转文字时的正文等）；失败时为统一错误结构（code、message、details），前端若已按建议改造会以红色提示框展示。

5. **常见失败**  
   - `INPUT_FILE_NOT_FOUND`：路径填错或文件不存在。  
   - `INPUT_PATH_OUTSIDE_HOME`：路径不在用户主目录下。  
   - `WHISPER_NOT_AVAILABLE`：未安装 Whisper 或依赖。  
   - `FFMPEG_NOT_FOUND`：未安装或未在 PATH 中找到 FFmpeg。  
   - `TIMEOUT`：执行超时（语音转文字约 1 小时、视频提音频约 30 分钟）。

---

## 三、小结

- **必须**：安装并可用 Whisper（语音转文字）、FFmpeg（视频提音频），且输入为主目录下已存在文件。  
- **建议**：前端对错误结果与两种新类型成功结果做友好展示，便于试用。  
- **可选**：列表页区分「执行失败」与成功、在 SETUP/README 中增加说明。
