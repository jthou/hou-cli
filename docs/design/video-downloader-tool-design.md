# 视频下载工具集设计文档

## 概述

设计一个统一的视频下载工具集，整合 `you-get`（通用视频下载工具）和 `bili23-downloader`（B站专用下载工具），为 LLM Agent 提供视频下载能力。

## 设计目标

1. **统一接口**：提供统一的工具接口，隐藏底层实现细节
2. **智能选择**：根据视频来源自动选择最合适的下载工具
3. **功能完整**：支持多平台视频下载，特别优化 B 站支持
4. **易于扩展**：支持未来添加更多下载工具
5. **错误处理**：完善的错误处理和降级策略

## 架构设计

### 1. 工具层次结构

```
VideoDownloaderTool (主工具)
├── YouGetDownloader (you-get 适配器)
├── Bili23Downloader (bili23-downloader 适配器)
└── YtDlpDownloader (yt-dlp 适配器)
```

### 2. 工具选择策略

```
输入 URL
  │
  ├─ 检测平台类型
  │   ├─ Bilibili → 优先使用 bili23-downloader
  │   │              ├─ 成功 → 返回结果
  │   │              └─ 失败 → 降级到 you-get
  │   │
  │   └─ 其他平台 → 使用 you-get
  │
  └─ 返回下载结果
```

### 3. 类设计

#### 3.1 VideoDownloaderTool (主工具类)

**位置**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**职责**:
- 提供统一的工具接口
- 根据 URL 自动选择下载工具
- 处理参数验证和结果格式化
- 实现降级策略

**工具描述（给 LLM 使用）**:
```python
name="video_downloader"
description=(
    "从多个视频平台下载视频文件。"
    "支持 YouTube、Bilibili、优酷、腾讯视频、爱奇艺等多个平台。"
    "对于 Bilibili 视频，支持下载弹幕、字幕、封面等附加内容。"
    "\n\n"
    "功能特点："
    "\n- 自动识别视频平台并选择最佳下载工具"
    "\n- 支持自定义视频质量和格式"
    "\n- Bilibili 视频支持下载弹幕（ASS 格式）、字幕、封面、NFO 元数据"
    "\n- 支持断点续传和多线程下载（Bilibili）"
    "\n- 自动降级策略：如果首选工具失败，自动切换到备用工具"
    "\n\n"
    "支持的平台："
    "\n- Bilibili（哔哩哔哩）：支持投稿视频、番剧、电影等，支持弹幕和字幕下载"
    "\n- YouTube：支持视频和播放列表下载"
    "\n- 优酷、腾讯视频、爱奇艺等国内主流视频平台"
    "\n- Twitter、Facebook 等社交媒体视频"
    "\n- 更多平台请参考 you-get 支持的网站列表"
    "\n\n"
    "使用建议："
    "\n- 对于 Bilibili 视频，如果不指定 preferred_tool，会自动使用 bili23-downloader（功能更丰富）"
    "\n- 对于 YouTube 和其他平台，优先使用 yt-dlp（功能最强）"
    "\n- 如果需要只下载字幕或只提取音频，推荐使用 yt-dlp（功能最强）"
    "\n- 如果下载失败，工具会自动尝试备用下载器（降级策略）"
    "\n- 下载大文件时，建议指定 output_dir 以避免占用系统目录空间"
    "\n\n"
    "注意事项："
    "\n- 下载的视频仅供个人学习研究使用，请遵守相关版权法律法规"
    "\n- 某些平台可能需要登录或 Cookie，工具会自动处理（如果配置了）"
    "\n- 下载速度取决于网络状况和视频平台限制"
)
```

**参数**:
- `url` (string, required): 视频 URL
  - 描述: "要下载的视频链接。支持短链接（如 b23.tv）和完整 URL。"
  - 示例: "https://www.bilibili.com/video/BV1234567890" 或 "https://www.youtube.com/watch?v=xxx"
  
- `output_dir` (string, optional): 输出目录
  - 描述: "视频文件的保存目录。如果不指定，默认保存到系统下载目录（跨平台自适应）。"
  - 默认值: 系统下载目录
    - macOS: `~/Downloads/hou-cli-videos`
    - Linux: `~/Downloads/hou-cli-videos`
    - Windows: `%USERPROFILE%\Downloads\hou-cli-videos`
  - 示例: "/Users/username/Downloads/videos" 或 "C:\Users\username\Downloads\videos"
  
- `quality` (string, optional): 视频质量
  - 描述: "要下载的视频质量。可选值：'best'（最佳质量）、'worst'（最低质量）、'1080p'、'720p'、'480p' 等。"
  - 默认值: "best"
  - 枚举值: ["best", "worst", "1080p", "720p", "480p", "360p", "240p"]
  
- `format` (string, optional): 视频格式
  - 描述: "视频文件格式。可选值：'mp4'、'flv'、'webm' 等。如果不指定，使用平台默认格式。"
  - 枚举值: ["mp4", "flv", "webm", "mkv", "auto"]
  
- `download_subtitle` (boolean, optional): 是否下载字幕
  - 描述: "是否下载视频字幕文件。对于 Bilibili 视频，会下载 SRT 或 ASS 格式字幕。"
  - 默认值: false
  
- `download_thumbnail` (boolean, optional): 是否下载封面
  - 描述: "是否下载视频封面图片。对于 Bilibili 视频，会下载封面图。"
  - 默认值: false
  
- `download_danmaku` (boolean, optional): 是否下载弹幕（仅 Bilibili）
  - 描述: "是否下载 Bilibili 弹幕文件（ASS 格式）。仅对 Bilibili 视频有效。"
  - 默认值: false
  
- `download_subtitle_only` (boolean, optional): 只下载字幕，不下载视频
  - 描述: "如果为 true，只下载字幕文件，不下载视频。适用于只需要字幕的场景。"
  - 默认值: false
  
- `extract_audio_only` (boolean, optional): 只提取音频，不下载视频
  - 描述: "如果为 true，只提取音频文件，不下载视频。适用于只需要音频的场景。"
  - 默认值: false
  
- `audio_format` (string, optional): 音频格式（仅当 extract_audio_only=true 时有效）
  - 描述: "音频文件格式。可选值：'mp3'、'm4a'、'opus'、'wav' 等。默认 'mp3'。"
  - 默认值: "mp3"
  - 枚举值: ["mp3", "m4a", "opus", "wav", "aac"]
  
- `audio_quality` (string, optional): 音频质量（仅当 extract_audio_only=true 时有效）
  - 描述: "音频质量（比特率）。可选值：'128k'、'192k'、'256k'、'320k' 等。默认 '192k'。"
  - 默认值: "192k"
  - 枚举值: ["128k", "192k", "256k", "320k"]
  
- `subtitle_languages` (array, optional): 字幕语言列表
  - 描述: "要下载的字幕语言代码列表（如 ['en', 'zh', 'zh-CN']）。如果不指定，下载所有可用字幕。"
  - 类型: array of strings
  - 示例: ["en", "zh"]
  
- `preferred_tool` (string, optional): 首选下载工具
  - 描述: "指定优先使用的下载工具。'auto'（自动选择，推荐）、'you-get'（通用工具）、'bili23'（B站专用工具）。"
  - 默认值: "auto"
  - 枚举值: ["auto", "you-get", "bili23"]
  
- `bilibili_only` (boolean, optional): 仅 B 站功能
  - 描述: "是否仅使用 Bilibili 专用功能（弹幕、字幕、封面等）。如果为 true，对于 Bilibili 视频会强制使用 bili23-downloader。"
  - 默认值: false

**方法**:
- `execute(**kwargs) -> ToolResult`: 执行下载
- `_detect_platform(url: str) -> str`: 检测视频平台
- `_select_downloader(url: str, preferred: str) -> DownloaderAdapter`: 选择下载工具
- `_download_with_fallback(url: str, **options) -> ToolResult`: 带降级的下载
- `_normalize_output_dir(output_dir: Optional[str]) -> Path`: 规范化输出目录（跨平台）
- `_get_default_download_dir() -> Path`: 获取系统默认下载目录（跨平台）

#### 3.2 DownloaderAdapter (抽象适配器基类)

**位置**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**职责**:
- 定义下载器适配器接口
- 提供统一的适配器规范

**方法**:
- `download(url: str, output_dir: str, **options) -> DownloadResult`: 执行下载
- `is_available() -> bool`: 检查工具是否可用
- `supports_platform(url: str) -> bool`: 检查是否支持该平台
- `get_supported_platforms() -> List[str]`: 获取支持的平台列表

#### 3.3 YouGetDownloader (you-get 适配器)

**位置**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**职责**:
- 封装 you-get 的调用
- 处理 you-get 的输出和错误

**实现方式**:
- 方式 1（推荐）: 通过命令行调用 `you-get`
- 方式 2: 直接导入 you-get 的 Python API（如果可用）

**支持的功能**:
- 多平台视频下载
- 质量选择
- 格式选择
- 字幕下载（部分平台）

#### 3.4 Bili23Downloader (bili23-downloader 适配器)

**位置**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**职责**:
- 封装 bili23-downloader 的调用
- 处理 B 站特殊功能（弹幕、字幕、封面等）

**实现方式**:
- 方式 1: 通过命令行调用（如果有 CLI）
- 方式 2: 直接导入 bili23-downloader 的 Python API（如果可用）
- 方式 3: 通过 HTTP API（如果有）

**支持的功能**:
- 视频下载
- 弹幕下载（ASS 格式）
- 字幕下载
- 封面下载
- NFO 元数据下载
- 多线程下载
- 断点续传

#### 3.5 YtDlpDownloader (yt-dlp 适配器)

**位置**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**职责**:
- 封装 yt-dlp 的调用
- 提供强大的字幕和音频提取功能

**实现方式**:
- 方式 1（推荐）: 通过 Python API 直接导入 `yt_dlp`
- 方式 2: 通过命令行调用 `yt-dlp`

**支持的功能**:
- 多平台视频下载（YouTube、Bilibili、优酷等）
- **单独下载字幕**（不下载视频）- 核心优势
- **单独提取音频**（不下载视频）- 核心优势
- 支持多种字幕格式（SRT、ASS、VTT 等）
- 支持多种音频格式（MP3、M4A、OPUS、WAV 等）
- 字幕语言选择
- 音频质量选择
- 播放列表下载
- 格式选择和质量选择

**优势**:
- 功能最强大，支持最多平台
- 字幕和音频提取功能最强
- 活跃维护，更新频繁

## 实现细节

### 1. 平台检测

```python
def _detect_platform(url: str) -> str:
    """检测视频平台类型"""
    url_lower = url.lower()
    
    if 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
        return 'bilibili'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'youku.com' in url_lower:
        return 'youku'
    elif 'iqiyi.com' in url_lower:
        return 'iqiyi'
    # ... 更多平台
    else:
        return 'unknown'
```

### 2. 工具选择逻辑

```python
def _select_downloader(url: str, preferred: str = 'auto', **options) -> DownloaderAdapter:
    """选择下载工具"""
    platform = self._detect_platform(url)
    
    # 特殊功能优先使用 yt-dlp
    if options.get('download_subtitle_only') or options.get('extract_audio_only'):
        if YtDlpDownloader().is_available():
            return YtDlpDownloader()
        # 降级到其他工具
    
    # 用户指定了首选工具
    if preferred == 'bili23' and platform == 'bilibili':
        return Bili23Downloader()
    elif preferred == 'yt-dlp':
        return YtDlpDownloader()
    elif preferred == 'you-get':
        return YouGetDownloader()
    
    # 自动选择
    if platform == 'bilibili':
        # B 站优先使用 bili23-downloader
        if Bili23Downloader().is_available():
            return Bili23Downloader()
        # 降级到 yt-dlp 或 you-get
        if YtDlpDownloader().is_available():
            return YtDlpDownloader()
        return YouGetDownloader()
    elif platform == 'youtube':
        # YouTube 优先使用 yt-dlp
        if YtDlpDownloader().is_available():
            return YtDlpDownloader()
        return YouGetDownloader()
    else:
        # 其他平台优先使用 yt-dlp
        if YtDlpDownloader().is_available():
            return YtDlpDownloader()
        return YouGetDownloader()
```

### 3. 降级策略

```python
def _download_with_fallback(url: str, **options) -> ToolResult:
    """带降级的下载"""
    primary_downloader = self._select_downloader(url, options.get('preferred_tool', 'auto'))
    
    try:
        result = primary_downloader.download(url, **options)
        if result.success:
            return result
    except Exception as e:
        logger.warning(f"Primary downloader failed: {e}")
    
    # 降级到 you-get
    if not isinstance(primary_downloader, YouGetDownloader):
        try:
            fallback_downloader = YouGetDownloader()
            if fallback_downloader.is_available():
                return fallback_downloader.download(url, **options)
        except Exception as e:
            logger.error(f"Fallback downloader also failed: {e}")
    
    return ToolResult(
        success=False,
        error=f"All downloaders failed for URL: {url}"
    )
```

### 4. 命令行调用封装

#### you-get 调用示例

```python
def _call_you_get(self, url: str, output_dir: str, **options) -> DownloadResult:
    """调用 you-get"""
    cmd = ['python', '-m', 'you_get']
    
    # 添加输出目录
    if output_dir:
        cmd.extend(['-o', output_dir])
    
    # 添加质量选项
    if options.get('quality'):
        cmd.extend(['-q', options['quality']])
    
    # 添加格式选项
    if options.get('format'):
        cmd.extend(['-f', options['format']])
    
    # 添加 URL
    cmd.append(url)
    
    # 执行命令
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=self._get_you_get_path()
    )
    
    return self._parse_you_get_output(result)
```

#### bili23-downloader 调用示例

```python
def _call_bili23(self, url: str, output_dir: Optional[str] = None, **options) -> DownloadResult:
    """调用 bili23-downloader"""
    # 规范化输出目录（如果未指定，使用系统默认下载目录）
    normalized_dir = self._normalize_output_dir(output_dir)
    
    # 检查是否有 CLI 接口
    # 如果没有，可能需要直接调用 Python API
    # 或者通过 HTTP API（如果有）
    
    # 示例：通过 Python API
    import sys
    sys.path.insert(0, self._get_bili23_path())
    
    from bili23_downloader import download_video
    
    result = download_video(
        url=url,
        output_dir=str(normalized_dir),
        quality=options.get('quality', 'best'),
        download_subtitle=options.get('download_subtitle', False),
        download_thumbnail=options.get('download_thumbnail', False),
    )
    
    return self._parse_bili23_result(result)
```

#### yt-dlp 调用示例

```python
def _call_yt_dlp(self, url: str, output_dir: Optional[str] = None, **options) -> DownloadResult:
    """调用 yt-dlp"""
    # 规范化输出目录（如果未指定，使用系统默认下载目录）
    normalized_dir = self._normalize_output_dir(output_dir)
    
    # 使用 yt-dlp Python API
    import sys
    sys.path.insert(0, self._get_yt_dlp_path())
    
    import yt_dlp
    
    ydl_opts = {
        'outtmpl': str(normalized_dir / '%(title)s.%(ext)s'),
    }
    
    # 只下载字幕
    if options.get('download_subtitle_only'):
        ydl_opts.update({
            'writesubtitles': True,
            'writeautomaticsub': True,
            'skip_download': True,
        })
        if options.get('subtitle_languages'):
            ydl_opts['subtitleslangs'] = options['subtitle_languages']
    
    # 只提取音频
    elif options.get('extract_audio_only'):
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.get('audio_format', 'mp3'),
                'preferredquality': options.get('audio_quality', '192'),
            }],
        })
    else:
        # 正常下载视频
        if options.get('quality'):
            ydl_opts['format'] = self._convert_quality_to_yt_dlp_format(options['quality'])
        if options.get('download_subtitle'):
            ydl_opts['writesubtitles'] = True
            if options.get('subtitle_languages'):
                ydl_opts['subtitleslangs'] = options['subtitle_languages']
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return self._parse_yt_dlp_result(info, normalized_dir)
    except Exception as e:
        return DownloadResult(success=False, error=str(e))
```

## LLM Function Calling 格式

工具注册到 LLM 时的 JSON Schema 格式：

```json
{
  "type": "function",
  "function": {
    "name": "video_downloader",
    "description": "从多个视频平台下载视频文件。支持 YouTube、Bilibili、优酷、腾讯视频、爱奇艺等多个平台。对于 Bilibili 视频，支持下载弹幕、字幕、封面等附加内容。自动识别平台并选择最佳下载工具，支持自定义质量和格式。",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "要下载的视频链接。支持短链接（如 b23.tv）和完整 URL。示例：https://www.bilibili.com/video/BV1234567890"
        },
        "output_dir": {
          "type": "string",
          "description": "视频文件的保存目录。如果不指定，默认保存到系统下载目录（跨平台自适应）：macOS/Linux 为 ~/Downloads/hou-cli-videos，Windows 为 %USERPROFILE%\\Downloads\\hou-cli-videos。示例：/Users/username/Downloads/videos"
        },
        "quality": {
          "type": "string",
          "description": "要下载的视频质量。可选值：'best'（最佳质量）、'worst'（最低质量）、'1080p'、'720p'、'480p' 等。默认 'best'。",
          "enum": ["best", "worst", "1080p", "720p", "480p", "360p", "240p"]
        },
        "format": {
          "type": "string",
          "description": "视频文件格式。可选值：'mp4'、'flv'、'webm'、'mkv'、'auto'（自动选择）。如果不指定，使用平台默认格式。",
          "enum": ["mp4", "flv", "webm", "mkv", "auto"]
        },
        "download_subtitle": {
          "type": "boolean",
          "description": "是否下载视频字幕文件。对于 Bilibili 视频，会下载 SRT 或 ASS 格式字幕。默认 false。"
        },
        "download_thumbnail": {
          "type": "boolean",
          "description": "是否下载视频封面图片。对于 Bilibili 视频，会下载封面图。默认 false。"
        },
        "download_danmaku": {
          "type": "boolean",
          "description": "是否下载 Bilibili 弹幕文件（ASS 格式）。仅对 Bilibili 视频有效。默认 false。"
        },
        "preferred_tool": {
          "type": "string",
          "description": "指定优先使用的下载工具。'auto'（自动选择，推荐）、'yt-dlp'（功能最强，推荐用于字幕和音频）、'you-get'（通用工具）、'bili23'（B站专用工具）。默认 'auto'。",
          "enum": ["auto", "yt-dlp", "you-get", "bili23"]
        },
        "bilibili_only": {
          "type": "boolean",
          "description": "是否仅使用 Bilibili 专用功能（弹幕、字幕、封面等）。如果为 true，对于 Bilibili 视频会强制使用 bili23-downloader。默认 false。"
        }
      },
      "required": ["url"]
    }
  }
}
```

## 使用示例

### 1. 基本使用（LLM 调用示例）

**用户请求**: "帮我下载这个 Bilibili 视频：https://www.bilibili.com/video/BV1234567890"

**LLM 调用**:
```python
tool.execute(
    url="https://www.bilibili.com/video/BV1234567890",
    quality="best"
    # output_dir 未指定，自动使用系统下载目录
)
```

**返回结果**:
```python
ToolResult(
    success=True,
    data={
        "video_path": "/Users/username/Downloads/hou-cli-videos/视频标题.mp4",  # macOS
        # 或 "C:\\Users\\username\\Downloads\\hou-cli-videos\\视频标题.mp4"  # Windows
        "platform": "bilibili",
        "tool_used": "bili23-downloader",
        "quality": "1080p",
        "file_size": "500MB",
        "duration": "00:15:30"
    }
)
```

### 2. B 站特殊功能（LLM 调用示例）

**用户请求**: "下载这个 Bilibili 视频，要包含弹幕和字幕：https://www.bilibili.com/video/BV1234567890"

**LLM 调用**:
```python
tool.execute(
    url="https://www.bilibili.com/video/BV1234567890",
    quality="best",
    download_subtitle=True,
    download_thumbnail=True,
    download_danmaku=True,
    bilibili_only=True  # 使用 bili23-downloader 的特殊功能
    # output_dir 未指定，自动使用系统下载目录
)
```

**返回结果**:
```python
ToolResult(
    success=True,
    data={
        "video_path": "/Users/username/Downloads/hou-cli-videos/视频标题.mp4",  # macOS
        "subtitle_path": "/Users/username/Downloads/hou-cli-videos/视频标题.ass",
        "danmaku_path": "/Users/username/Downloads/hou-cli-videos/视频标题.xml",
        "thumbnail_path": "/Users/username/Downloads/hou-cli-videos/视频标题.jpg",
        "platform": "bilibili",
        "tool_used": "bili23-downloader",
        "quality": "1080p"
    }
)
```

### 3. YouTube 视频下载（LLM 调用示例）

**用户请求**: "下载这个 YouTube 视频：https://www.youtube.com/watch?v=xxx"

**LLM 调用**:
```python
tool.execute(
    url="https://www.youtube.com/watch?v=xxx",
    quality="720p",
    preferred_tool="you-get"
    # output_dir 未指定，自动使用系统下载目录
)
```

**返回结果**:
```python
ToolResult(
    success=True,
    data={
        "video_path": "/Users/username/Downloads/hou-cli-videos/视频标题.mp4",  # macOS
        "platform": "youtube",
        "tool_used": "you-get",
        "quality": "720p"
    }
)
```

### 4. 下载失败自动降级（LLM 调用示例）

**用户请求**: "下载这个视频：https://www.bilibili.com/video/BV1234567890"

**LLM 调用**:
```python
tool.execute(
    url="https://www.bilibili.com/video/BV1234567890"
)
```

**工具行为**:
1. 尝试使用 bili23-downloader
2. 如果失败（例如工具不可用），自动降级到 you-get
3. 返回下载结果或错误信息

**返回结果（失败）**:
```python
ToolResult(
    success=False,
    error="下载失败：视频不存在或需要登录。错误详情：HTTP 403 Forbidden。已尝试降级到 you-get，但仍然失败。"
)
```

## 错误处理

### 1. 工具不可用

- 检查工具是否已安装/可用
- 如果不可用，自动降级到其他工具
- 如果所有工具都不可用，返回明确的错误信息

### 2. 下载失败

- 捕获并记录详细错误信息
- 尝试降级到其他工具
- 返回用户友好的错误消息

### 3. 参数验证

- 验证 URL 格式
- 验证输出目录是否存在/可写
- 验证质量/格式选项是否有效

## 测试策略

### 1. 单元测试

- 测试平台检测逻辑
- 测试工具选择逻辑
- 测试参数验证
- 测试错误处理

### 2. 集成测试

- 测试 you-get 适配器（使用 mock 或真实调用）
- 测试 bili23-downloader 适配器（使用 mock 或真实调用）
- 测试降级策略

### 3. 端到端测试

- 测试真实视频下载（可选，需要网络）
- 测试不同平台的下载
- 测试错误场景

## 依赖管理

### 1. 运行时依赖

- `you-get`: 通过 submodule 集成，或通过 pip 安装
- `bili23-downloader`: 通过 submodule 集成

### 2. 可选依赖

- `ffmpeg`: 用于视频格式转换（如果 bili23-downloader 需要）

## 未来扩展

### 1. 支持更多下载工具

- ✅ `yt-dlp`: 已集成，功能强大的下载工具
- `annie`: 另一个通用下载工具（可选）

### 2. 支持更多功能

- 批量下载
- 下载列表管理
- 下载进度跟踪
- 下载历史记录

### 3. 性能优化

- 并发下载
- 断点续传
- 下载速度限制

## 文件结构

```
backend/core/agent/tools/builtin/
├── video_downloader_tool.py          # 主工具类
└── __init__.py                       # 导出工具

backend/externals/
├── you-get/                          # you-get submodule
├── bili23-downloader/                # bili23-downloader submodule
└── yt-dlp/                           # yt-dlp submodule
```

## 注意事项

1. **版权和法律**: 确保用户了解下载内容的版权限制
2. **资源消耗**: 视频下载会消耗大量带宽和存储空间
3. **错误处理**: 提供清晰的错误信息，帮助用户诊断问题
4. **性能**: 大文件下载可能需要较长时间，考虑异步处理
5. **安全性**: 验证 URL 和文件路径，防止路径遍历攻击

## 待确认事项

1. **bili23-downloader API**: 需要确认是否有 Python API 或 CLI 接口
2. **you-get 集成方式**: 确认是通过命令行还是直接导入
3. **异步支持**: 是否需要异步下载支持
4. **进度报告**: 是否需要实时下载进度反馈
5. **文件命名**: 下载文件的命名规则

