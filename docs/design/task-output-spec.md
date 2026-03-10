# 任务输出规范（output_spec）

每个任务类型需清晰描述其输出内容、格式、文件名规则与默认路径，便于用户理解与管道编排。

---

## 1. output_spec 字段说明

| 字段 | 说明 |
|------|------|
| **content** | 输出内容描述：任务产出的具体内容（如「视频文件」「字幕文本」「天气数据」） |
| **format** | 输出格式：文件扩展名、MIME 类型或数据结构（如 mp3、JSON、PNG） |
| **naming_rule** | 输出文件名规则：自动生成时的命名规则（如 `{输入stem}_subtitle.srt`） |
| **default_path** | 默认输出路径：用户未指定时使用 `~/hou-cli/outputs/{task_type}/`，便于磁盘清理识别归属 |

---

## 2. 各任务类型 output_spec 一览

| 任务类型 | content | format | naming_rule | default_path |
|----------|---------|--------|-------------|--------------|
| video_download | 视频或音频文件 | 平台原格式 / mp3 等 | 由 yt-dlp/you-get 决定 | ~/hou-cli/outputs/video_download |
| speech_to_text | 语音转文字结果 | srt/json/txt | 输入主名_subtitle.ext | ~/hou-cli/outputs/speech_to_text |
| video_extract_audio | 提取的音频轨 | mp3/wav/aac 等 | 输入主名_audio.ext | ~/hou-cli/outputs/video_extract_audio |
| image_generation | 生成的图片 | PNG | gen_时间戳_序号.png | ~/hou-cli/outputs/image_generation |
| weather_query | 天气数据 | JSON | 无本地文件 | 无 |
| web_search | 搜索结果 | JSON | 无本地文件 | 无 |
| disk_scan | 磁盘占用报告 | JSON | 无本地文件 | 无 |
| mediawiki_write | Wiki 页面 | Wikitext | 由 title 指定 | 无 |
| url_to_wiki | 抓取翻译文章 | Markdown/Wiki | 由 wiki_title 推断 | 无 |
| pdf_to_wiki | PDF 转 Wiki | Wikitext | 主标题/第k部分 | 无 |
| wiki_directory_refresh | 目录页 | Wikitext | 默认「网文与PDF翻译目录」 | 无 |
| wechat_mp_draft | 公众号草稿 | 微信 API | media_id | 无 |

---

## 3. 与 pipeline_outputs 的关系

- **output_spec**：面向用户与文档，描述「任务产出什么、怎么命名、放哪」
- **pipeline_outputs**：面向管道编排，描述「result 中可供下游绑定的路径与类型」

有 `pipeline_outputs` 的任务（如 video_download、speech_to_text）通常也有 `output_spec`；无文件产出的任务（如 weather_query）仅有 `output_spec` 说明 result 结构。

---

## 4. 统一输出路径规则

所有产生本地文件的任务类型，默认输出路径统一为 `~/hou-cli/outputs/{task_type}/`，例如：

- `~/hou-cli/outputs/video_download/` — 视频下载
- `~/hou-cli/outputs/speech_to_text/` — 字幕提取
- `~/hou-cli/outputs/video_extract_audio/` — 音频提取
- `~/hou-cli/outputs/image_generation/` — 图片生成

磁盘清理时可按子目录识别文件归属，便于按任务类型批量清理。
