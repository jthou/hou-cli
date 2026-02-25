# 视频下载相关测试计划：能力 → 功能 → 集成

约定：
- **能力测试**：视频下载、反爬虫等**领域能力**（平台识别、引擎选择与降级、下载行为、cookie/412/headers）。
- **功能测试**：**本系统**的接口、字段、结构、API（任务 schema、校验、路由、返回结构、LLM tool schema）。
- **集成测试**：多组件协作（API+DB、Registry+Tool、真实外部或真实 Worker）。

---

## 一、能力测试（先做）

### 1.1 视频下载能力

| # | 项 | 状态 | 所在文件/类 |
|---|----|------|-------------|
| 1 | 平台检测：bilibili/youtube/youku/iqiyi/twitter/facebook/unknown | ✅ 已有 | test_video_downloader_tool.py / TestPlatformDetection |
| 2 | YouGet 适配器：is_available、supports_platform、download 成功/失败 | ✅ 已有 | TestYouGetDownloader |
| 3 | YtDlp 适配器：is_available、supports_platform、仅字幕/仅音频、quality 转换 | ✅ 已有 | TestYtDlpDownloader |
| 4 | 引擎选择：仅字幕/仅音频→yt-dlp；B 站 auto→you-get；YouTube auto→yt-dlp；preferred 指定 | ✅ 已有 | TestDownloaderSelection |
| 5 | 工具执行：有 URL 时选下载器并执行成功；缺 URL 报错；主引擎失败时 fallback | ✅ 已有 | TestVideoDownloaderTool（execute_*） |
| 6 | （可选）进度回调在下载过程中被调用 | ⬜ 待补 | test_video_downloader_tool.py |
| 7 | （可选）options 正确传入 yt-dlp（format、writesubtitles、postprocessors 等） | ⬜ 待补 | 能力侧可加断言 ydl_opts 结构 |

### 1.2 反爬虫能力

| # | 项 | 状态 | 说明 |
|---|----|------|------|
| 1 | B 站 URL 时 yt-dlp 收到 http_headers（User-Agent、Referer 等） | ✅ 已补 | 能力测试：mock 内层，断言传入 ydl 的 opts 含 http_headers |
| 2 | cookies_file 有效时 ydl_opts 含 cookiefile | ✅ 已补 | _load_cookies_from_file 返回路径时，download 中 opts 应有 cookiefile |
| 3 | cookies_from_browser 指定时尝试提取并写入 cookiefile | ✅ 已补 | mock _extract_cookies_from_browser 返回路径，断言 cookiefile 被设置 |
| 4 | 412 错误时（B 站、未显式 cookie）尝试浏览器提取并重试 | ✅ 已补 | mock 第一次 DownloadError(412)，第二次成功，断言最终 success 且可能带 cookies_auto_extracted |
| 5 | 登录/机器人错误时返回文案含 cookie 建议 | ✅ 已补 | mock DownloadError 含 LOGIN_REQUIRED/登录，断言 error 字符串含 cookie 相关建议 |

---

## 二、功能测试（后做）

### 2.1 任务与校验（本系统契约）

| # | 项 | 状态 | 所在文件/类 |
|---|----|------|-------------|
| 1 | video_download handler 返回含 status、summary、data | ✅ 已有 | test_task_handlers.py / TestTaskHandlerResultShape |
| 2 | 缺 url 抛 ValueError；非法 URL（内网/非 http(s)）抛 ValueError | ✅ 已有 | TestTaskHandlerValidation, TestVideoDownloadUrlValidation |
| 3 | validate_task_creation：video_download 必填 url、quality enum、无效 type | ✅ 已有 | TestValidateTaskCreation |
| 4 | （可选）video_download metadata_schema 全字段在 get_available_task_types 中一致 | ✅ 已补 | 功能测试：GET task-types 与 TASK_TYPES 对齐 |

### 2.2 任务队列 API（本系统接口）

| # | 项 | 状态 | 所在文件 |
|---|----|------|----------|
| 1 | POST 创建任务：成功/无效 type/缺必填/非法 priority | ✅ 已有 | test_task_queue_routes.py |
| 2 | GET 列表/详情、取消、重启、list workers、cleanup | ✅ 已有 | test_task_queue_routes.py |
| 3 | 响应结构：success、task_id、message、result_summary 等 | ✅ 已有 | test_list_tasks_response_includes_result_summary 等 |
| 4 | （可选）video_download 创建时 metadata 全可选字段透传 | ✅ 已补 | 功能：创建时传 output_dir、preferred_tool、cookies_from_browser 等，断言 DB 层收到 |

### 2.3 工具对 LLM 的接口（本系统 schema）

| # | 项 | 状态 | 所在文件 |
|---|----|------|----------|
| 1 | 工具注册名、to_dict 含 function.name、parameters.properties/required | ✅ 已有 | test_video_downloader_tool_integration.py |
| 2 | preferred_tool enum、quality enum 等与实现一致 | ✅ 已有 | test_llm_function_calling_schema |
| 3 | 缺 url 时 validate_parameters 报错；无效 quality 报错 | ✅ 已有 | test_llm_call_parameter_validation, test_llm_call_error_handling |

---

## 三、集成测试（最后做）

| # | 项 | 状态 | 说明 |
|---|----|------|------|
| 1 | 天气查询真实 API（LiveEnv） | ✅ 已有 | test_task_handlers.py / TestWeatherQueryLiveEnv |
| 2 | ToolRegistry + VideoDownloaderTool 执行（mock 下载器） | ✅ 已有 | test_registry_execute_success, test_llm_call_scenario_1~4 |
| 3 | （可选）任务队列 API + 真实 TaskQueueDB（SQLite）创建/列表/详情 | ✅ 已补 | 集成：不用 mock_task_queue_db，用真实 DB 或内存 SQLite |
| 4 | （可选）video_download 端到端：POST 创建 → Worker 拉取 → process_video_download_task（mock 工具）→ 完成写回 | ✅ 已补 | 集成：真实 Worker 循环 + mock VideoDownloaderTool.execute |

---

## 执行顺序

1. **先做能力测试**：补 1.2 反爬虫能力 5 条；可选补 1.1 的 6、7。
2. **再做功能测试**：补 2.1/2.2/2.3 中标记 ⬜ 的项（可选）。
3. **最后做集成测试**：补 3 的 3、4（可选）。

当前已有用例已覆盖大部分能力（下载与选择）和全部核心功能（handler 契约、API、LLM schema）；缺口集中在**反爬虫能力的单测**与**可选集成**。
