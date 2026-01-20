# Tool 描述问题分析报告

## 发现的问题

### 1. ❌ **whisper_tool** - 错误信息

**问题位置：** `backend/core/agent/tools/builtin/whisper_tool.py:96`

**问题描述：**
```
"重要：默认会转录完整的音频文件，除非明确指定了时间范围。"
```

**问题：** whisper_tool 实际上**没有时间范围参数**，无法指定时间范围。这个描述是错误的，会误导 LLM 认为可以指定时间范围。

**建议修复：**
```
"重要：默认会转录完整的音频文件。"
或
"重要：会转录完整的音频文件（当前版本不支持时间范围限制）。"
```

---

### 2. ⚠️ **ffmpeg_tool** - 有歧义

**问题位置：** `backend/core/agent/tools/builtin/ffmpeg_tool.py:495`

**问题描述：**
```
"extract_audio - 从视频中提取音频（默认提取完整音频，除非使用 cut 操作）"
```

**问题：** 这个描述有歧义。`extract_audio` 和 `cut` 是两个**独立的操作**，不能混用。描述中的"除非使用 cut 操作"容易让人误解为可以在 extract_audio 中使用 cut 操作，但实际上它们是分开的。

**建议修复：**
```
"extract_audio - 从视频中提取音频（默认提取完整音频）"
```

**相关描述（第 501 行）：**
```
"重要：除非明确指定了时间范围（如 cut 操作），否则所有操作都会处理完整文件。"
```
这个描述是正确的，但可以更清晰。

**建议优化：**
```
"重要：所有操作默认处理完整文件。只有 cut 操作可以指定时间范围来裁剪片段。"
```

---

### 3. ⚠️ **file_search_tool** - 信息不准确

**问题位置：** `backend/core/agent/tools/builtin/file_search_tool.py:71`

**问题描述：**
```
"注意：根据用户需求，自行决定 query 和 file_type 参数的值。"
"可以使用通配符、正则表达式模式或具体的文件扩展名。"
```

**问题：** 从代码实现看（`backend/services/file_search_service/query_builder.py`），file_search 使用的是 macOS Spotlight (mdfind)，它**只支持通配符**，**不支持正则表达式**。描述中提到的"正则表达式模式"是不准确的。

**建议修复：**
```
"注意：根据用户需求，自行决定 query 和 file_type 参数的值。"
"可以使用通配符（如 '*.py'、'test*'）或具体的文件扩展名（如 '.py'、'.xlsx'）。"
"注意：不支持正则表达式，只支持通配符模式。"
```

---

### 4. ✅ **gvim_tool** - 描述正确

**验证：** 代码中确实有验证逻辑（第 137-141 行），要求至少提供一个参数，所以描述"二选一"是正确的。

---

### 5. ⚠️ **video_downloader_tool** - 信息可能不够准确

**问题位置：** `backend/core/agent/tools/builtin/video_downloader_tool.py:1023`

**问题描述：**
```
"支持断点续传和多线程下载（Bilibili）"
```

**问题：** 这个描述暗示只有 Bilibili 支持断点续传和多线程下载，但实际上其他下载工具（如 yt-dlp）也可能支持这些功能。这个描述可能不够准确。

**建议修复：**
```
"支持断点续传和多线程下载（具体支持情况取决于使用的下载工具）"
或
"Bilibili 视频支持断点续传和多线程下载"
（如果确实只有 Bilibili 支持，则保持原描述）
```

---

## 其他潜在问题

### 6. **browser_tool** - 描述可能不够详细

**问题位置：** `backend/core/agent/tools/builtin/browser_tool.py:130-140`

**问题：** 描述提到了 `user_data_dir` 参数，但没有明确说明这个参数的作用和如何使用。对于需要登录的网站，这个信息很重要。

**建议：** 可以添加更详细的使用示例。

---

### 7. **mediawiki_tool** - 描述中有代码引用

**问题位置：** `backend/core/agent/tools/builtin/mediawiki_tool.py:70-72`

**问题描述：**
```
"当输出 MediaWiki 页面列表时，请使用 format_page_link() 或 format_page_list_with_links() 函数"
"为每个页面标题添加可点击的链接。这些函数可以从 backend.services.mediawiki.utils 导入。"
```

**问题：** 这个描述是给 LLM 的，但提到了具体的函数名和导入路径。LLM 可能无法直接调用这些函数，这个描述可能不够实用。

**建议：** 可以改为更通用的描述，或者说明如何生成 Markdown 链接。

---

## 总结

**需要立即修复的问题：**
1. ✅ whisper_tool - 错误信息（提到不存在的参数）
2. ⚠️ ffmpeg_tool - 有歧义（extract_audio 描述）
3. ⚠️ file_search_tool - 信息不准确（提到不支持的正则表达式）

**可以优化的地方：**
4. ⚠️ video_downloader_tool - 信息可能不够准确
5. ⚠️ browser_tool - 可以更详细
6. ⚠️ mediawiki_tool - 描述中的代码引用可能不够实用



