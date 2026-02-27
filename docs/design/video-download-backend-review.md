# 视频下载后端实现检查

## 1. 整体架构

- **任务类型**：`video_download` 在 `task_handlers.TASK_TYPES` 中定义，metadata 含 `url`（必填）、`quality`、`download_subtitle`、`extract_audio_only`。
- **处理流程**：`process_video_download_task` 校验 url → 在 `asyncio.to_thread` 中调用 `VideoDownloaderTool().execute()` → 进度通过 `worker.update_task_progress` 回写 → 成功返回 `{ status, summary, data }`。
- **工具层**：`VideoDownloaderTool`（`video_downloader_tool.py`）内部按 URL 平台与选项选择两种适配器之一：**YtDlpDownloader**、**YouGetDownloader**。

### 1.1 任务如何定义

- **类型注册表**：`backend/infrastructure/execution/task_handlers.py` 中的 **TASK_TYPES** 是任务类型的唯一定义源。每个 key（如 `video_download`、`weather_query`）对应：
  - **name**：展示用名称（如「视频下载」）
  - **description**：简短说明
  - **metadata_schema**：创建任务时前端/API 使用的参数 schema；每个字段支持 `type`、`required`、`description`、`placeholder`、`default`、**enum**（`[{"value":"x","label":"显示名"}]`）
- **校验**：创建任务时由 **validate_task_creation(task_type, metadata)** 根据 `TASK_TYPES[task_type].metadata_schema` 校验必填、空串、enum 取值；通过才允许写入队列。
- **持久化形态**：任务在 **TaskQueueDB**（SQLite）中一条记录包含：`task_id`、`task_type`、`task_name`、`status`（queued/running/completed/failed/cancelled）、`priority`、`metadata`（JSON）、`result`、`error`、`progress`、`message`、`worker_id`、时间戳等。执行结果写入 `result`（JSON，如 `{ "status": "success", "summary": "...", "data": {...} }`），失败时写入 `error`。

因此：**“任务” = 在 TASK_TYPES 里注册的 type + 经 schema 校验的 metadata，落库后由 Worker 拉取并交给对应 handler 执行。**

### 1.2 后端架构主体模块关系

- **API 层**（`backend/api/`）  
  - **task_queue_routes**：对外提供任务队列 HTTP 接口（创建/列表/详情/取消/重启/Worker 列表/定时任务等）。  
  - 依赖：**task_handlers**（`validate_task_creation`、`get_available_task_types`、`get_task_type_info`）、**TaskQueueDB**（`create_task`、`list_tasks`、`get_task`、`cancel_task` 等）。

- **基础设施 · 存储**（`backend/infrastructure/storage/`）  
  - **task_queue_db**：**TaskQueueDB** 单例，SQLite 持久化任务表、Worker 表、定时任务表；提供 `create_task`、`acquire_task`、`complete_task`、`cancel_task`、`update_task_progress`、`list_workers`、`register_worker` 等。  
  - 被 API（task_queue_routes）和 **TaskWorker** 共同使用。

- **基础设施 · 执行**（`backend/infrastructure/execution/`）  
  - **task_worker**：**TaskWorker** 单例，在 `main.py` 生命周期内启动；循环轮询 `task_queue_db.acquire_task()`，取到任务后根据 `task_type` 查 **task_handlers** 并 `await handler(task_info)`，用 `task_queue_db.complete_task` / `cancel_task` / `update_task_progress` 更新状态。  
  - **task_handlers**：定义 **TASK_TYPES** 和每个类型的 async handler（如 `process_video_download_task`）；`register_default_handlers()` 把各 handler 注册到 TaskWorker。Handler 内部可再调 **core** 层能力（如 `VideoDownloaderTool`）。

- **核心 · Agent 工具**（`backend/core/agent/tools/builtin/`）  
  - **video_downloader_tool**：实现具体下载逻辑（yt-dlp/you-get 适配器），被 **task_handlers** 里的 `process_video_download_task` 调用；也可被 Agent 编排器直接调。

- **基础设施 · 监控**（`backend/infrastructure/monitoring/`）  
  - **heartbeat**：心跳监控定期用 **TaskQueueDB** 检查 Worker 存活、清理僵死任务、触发定时任务入队。

**依赖关系小结**：  
`api (task_queue_routes)` → `infrastructure/storage (TaskQueueDB)` + `infrastructure/execution (task_handlers 校验与类型查询)`  
`task_worker` → `TaskQueueDB`（拉取/更新任务）+ `task_handlers`（执行）  
`task_handlers` → `task_worker`（更新进度）+ `core/agent/tools`（如 VideoDownloaderTool）  
`main.py` 启动时：创建 TaskWorker、`register_default_handlers()`、`worker.start()`，并启动心跳监控（使用 TaskQueueDB）。

## 2. 已具备的能力（成熟部分）

- **多引擎**：yt-dlp、you-get（pip 安装）按平台与 `preferred_tool` 自动/指定选择。
- **平台识别**：`_detect_platform(url)` 识别 bilibili、youtube、youku、iqiyi、腾讯视频、twitter、facebook 等。
- **选项**：质量（best/1080p/720p/480p/360p）、下载字幕、仅提取音频、仅下载字幕、字幕语言、音频格式/质量、cookies 文件/从浏览器提取、B 站弹幕等；yt-dlp 侧有完整选项与进度钩子。
- **B 站**：412 等错误时自动尝试从 Chrome/Firefox/Safari/Edge 提取 cookies 并重试；请求头与 yt-dlp 选项已针对 B 站做适配。
- **FFmpeg**：使用系统 FFmpeg（需预先安装）；提取音频时检测 MP3 编码器，不可用时回退到 AAC。
- **进度**：`progress_callback` 从下载器传到任务进度，任务详情可展示百分比与状态。
- **错误与降级**：you-get 登录/模块冲突等有明确错误文案；多引擎间自动降级（yt-dlp ↔ you-get）。
- **测试**：`test_task_handlers.py` 覆盖 video_download 成功返回结构、缺 url 抛错；`test_video_downloader_tool.py` / `test_video_downloader_tool_integration.py` 覆盖工具选择、执行与参数。

## 3. 任务队列与工具层对齐（已实施）

任务创建时的 **metadata_schema** 与 **process_video_download_task** 已与工具层对齐，以下能力均可通过任务 API/前端传入：

| 能力           | 工具层 VideoDownloaderTool | 任务 handler 是否传入 |
|----------------|---------------------------|------------------------|
| url            | ✅                        | ✅                     |
| output_dir     | ✅                        | ✅（metadata，且 restrict_to_home） |
| quality        | ✅                        | ✅                     |
| download_subtitle | ✅                     | ✅                     |
| extract_audio_only | ✅                    | ✅                     |
| download_thumbnail | ✅                    | ✅（schema 已暴露）   |
| preferred_tool | ✅                        | ✅（schema 已暴露）   |
| cookies_file   | ✅                        | ✅（schema 已暴露）   |
| cookies_from_browser | ✅                  | ✅（schema 已暴露）   |
| subtitle_languages | ✅                    | ✅（逗号分隔字符串）  |
| download_subtitle_only | ✅               | ✅                     |
| audio_format / audio_quality | ✅           | ✅                     |
| download_danmaku | ✅                      | ✅                     |

- **实施说明**：`TASK_TYPES["video_download"]["metadata_schema"]` 已增加上述可选字段；`process_video_download_task` 从 `metadata` 读取并传入工具。`output_dir` 使用 `normalize_output_dir(..., restrict_to_home=True)` 限制在用户主目录下。

## 4. Cookie、浏览器信息与反爬虫

### 4.1 已考虑并实现的部分（仅 yt-dlp 路径）

- **Cookies**
  - **文件**：`cookies_file` 支持 Netscape 或 JSON 格式；`_load_cookies_from_file()` 校验文件存在与首行格式后交给 yt-dlp 的 `cookiefile`。
  - **浏览器**：`cookies_from_browser` 支持 chrome/firefox/safari/edge，通过 **browser_cookie3** 从浏览器 Cookie 库按域名（默认 bilibili.com）提取，写入临时 Netscape 格式文件再传给 yt-dlp。依赖：`pip install browser-cookie3`；部分环境需当前用户、钥匙串权限或已解锁的浏览器配置。
- **浏览器态请求头（B 站）**  
  当 URL 为 bilibili.com / b23.tv 时，yt-dlp 使用固定的一组「像浏览器」的 headers，减轻被识别为脚本：
  - `User-Agent`: Chrome 120（Macintosh）
  - `Referer` / `Origin`: https://www.bilibili.com
  - `Accept`、`Accept-Language`、`Accept-Encoding`、`Connection`
  - `Sec-Fetch-Dest`、`Sec-Fetch-Mode`、`Sec-Fetch-Site`、`Sec-Fetch-User`、`Cache-Control`、`DNT`
- **反爬与重试**
  - **412 自动处理**：yt-dlp 报错中含 412 或 Precondition Failed 且为 B 站且未显式传 cookie 时，会依次尝试从 chrome → firefox → safari → edge 提取 bilibili.com cookies，用提取到的 cookie 自动重试一次；成功则结果中带 `cookies_auto_extracted`。
  - **通用**：`retries=3`，`sleep_interval=1`、`sleep_interval_requests=1`，降低请求频率。
  - **B 站提取器**：`extractor_args.bilibili` 占位（username/password 为 None），便于后续扩展。

### 4.2 差异与局限

- **you-get 路径未使用 cookie/反爬能力**：YouGetDownloader 通过 subprocess 调用 you-get，只传 `-o` 输出目录、可选 `-f` 格式和 URL，**没有**传入 cookies、自定义 User-Agent 或其它 headers。因此走 you-get 时无法用「浏览器 cookie / 自定义请求头」绕过登录或反爬，需依赖 you-get 自身逻辑或优先用 yt-dlp（`preferred_tool='yt-dlp'`）。
- **任务队列已支持 cookie**：metadata_schema 与 handler 已支持 `cookies_file`、`cookies_from_browser`，任务创建/API 可传入。
- **User-Agent 固定**：当前为固定 Chrome 120，长期可能被识别为旧版或触发「请升级浏览器」；未做 UA 轮换或可配置。
- **临时 cookie 文件**：已实施清理——YtDlpDownloader.download() 在 finally 中删除从浏览器提取的临时 cookie 文件（含 412 自动重试时生成的）。

### 4.3 小结

- Cookie（文件 + 浏览器）、浏览器态请求头、412 自动重试与限速重试均在 **YtDlpDownloader** 中实现；任务队列已可传 cookie；临时 cookie 文件用后已清理。you-get 路径仍未接入 cookie/请求头。

## 5. 二次检查补充（遗漏与修复）

- **前后端 quality 不一致（已修复）**：已在 `metadata_schema.quality.enum` 中增加 `360p`，与前端和工具层一致。
- **output_dir 路径安全（已实施）**：`normalize_output_dir(..., restrict_to_home=True)`（`shared/platform_utils.py`）对任务/API 传入路径做 `resolve()` 并限制在用户主目录下，超出则回退默认下载目录。
- **任务执行无超时（已实施）**：`task_worker._execute_task` 对 `video_download` 使用 `asyncio.wait_for(handler(...), timeout=VIDEO_DOWNLOAD_TASK_TIMEOUT)`（默认 30 分钟），超时则标记任务失败。
- **临时 cookie 文件（已实施）**：YtDlpDownloader.download() 在 finally 中统一删除从浏览器提取的临时 cookie 文件（含 412 自动重试生成的）。
- **URL 校验（已实施）**：`process_video_download_task` 调用 `_validate_video_download_url`：仅允许 http/https，禁止 file: 等；禁止主机名为 localhost、环回与私网 IP，降低 SSRF 风险。单测见 `TestVideoDownloadUrlValidation`、`test_video_download_invalid_url_raises`。

## 6. 小结

- **已成熟**：任务注册与执行流程、yt-dlp/you-get 双引擎选择与降级、B 站 412 与 cookies 自动重试、进度回调、错误提示、FFmpeg/音频格式处理、单元/集成测试覆盖；前后端 quality 已对齐；任务 schema 与 handler 已与工具层对齐（含 cookie、output_dir、超时、临时文件清理）；URL 校验（http(s)+ 禁止内网/本地）；前端视频下载页已扩展表单。
- **已移除**：bili23-downloader 未在系统中集成，已从代码与 externals 中彻底去除；B 站下载仅使用 yt-dlp/you-get。
