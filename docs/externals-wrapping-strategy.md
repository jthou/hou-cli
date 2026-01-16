# Externals 第三方库封装策略

## 问题

`externals/` 目录下的第三方工具（如 `browser-use`、`whisper`、`yt-dlp`、`ffmpeg` 等），是否需要被封装成 Services？

## 当前情况分析

### 当前使用方式

**直接使用（当前方式）：**
- `browser_tool.py` → 直接使用 `browser_use` 库
- `video_downloader_tool.py` → 直接使用 `yt_dlp`、`you-get`、`bili23-downloader`
- `whisper_tool.py` → 直接使用 `whisper` 库
- `ffmpeg_tool.py` → 直接调用 `ffmpeg` 可执行文件

**封装成 Services（已有例子）：**
- `google_search_service` → 封装 Google Custom Search API
- `file_search_service` → 封装系统文件搜索 API
- `wikipedia_service` → 封装 Wikipedia API

## 判断标准

### 需要封装成 Services 的情况

1. **API 客户端类**（需要配置、认证、错误处理）
   - ✅ `GoogleSearchService` - 需要 API Key、Engine ID
   - ✅ `WikipediaService` - 需要 API 配置
   - ✅ `FileSearchService` - 需要平台适配（macOS、Linux）

2. **复杂的业务逻辑**（需要统一接口、错误处理、重试）
   - ✅ 多个实现需要统一接口
   - ✅ 需要复杂的错误处理和重试逻辑
   - ✅ 需要缓存、限流等中间层功能

3. **可被多个地方复用**
   - ✅ 可以被 Tools、API 路由、其他服务使用
   - ✅ 需要独立测试和维护

### 可以直接使用的情况

1. **简单的库调用**（直接调用即可）
   - ✅ `whisper` - 简单的函数调用，不需要复杂配置
   - ✅ `ffmpeg` - 命令行工具，直接调用即可
   - ✅ `yt-dlp` - Python 库，直接调用即可

2. **工具类库**（本身就是工具，不是服务）
   - ✅ `browser-use` - 本身就是工具库，提供 Agent 和 Tools
   - ✅ `planning-with-files` - 规划工具，直接使用

3. **单一用途**（只被一个 Tool 使用）
   - ✅ 如果只被一个 Tool 使用，封装成 Service 可能过度设计

## 推荐策略

### 策略 1：按复杂度判断（推荐）

**封装成 Services：**
- API 客户端（需要配置、认证）
- 复杂的业务逻辑（需要统一接口、错误处理）
- 可被多个地方复用

**直接使用：**
- 简单的库调用（函数调用、命令行工具）
- 工具类库（本身就是工具）
- 单一用途（只被一个 Tool 使用）

### 策略 2：统一封装（更规范但可能过度设计）

**所有 externals 都封装成 Services：**
- 优点：统一接口、易于测试、易于替换
- 缺点：增加抽象层、可能过度设计

## 具体建议

### 当前 externals 的处理建议

| Externals | 当前方式 | 建议 | 理由 |
|-----------|---------|------|------|
| `browser-use` | 直接使用 | ✅ 保持 | 本身就是工具库，提供 Agent 和 Tools |
| `whisper` | 直接使用 | ✅ 保持 | 简单的函数调用，不需要复杂配置 |
| `yt-dlp` | 直接使用 | ✅ 保持 | Python 库，直接调用即可 |
| `you-get` | 直接使用 | ✅ 保持 | 命令行工具，直接调用即可 |
| `bili23-downloader` | 直接使用 | ✅ 保持 | 命令行工具，直接调用即可 |
| `ffmpeg` | 直接使用 | ✅ 保持 | 命令行工具，直接调用即可 |
| `planning-with-files` | 直接使用 | ✅ 保持 | 规划工具，直接使用 |

### 如果需要封装的情况

如果某个 externals 库需要：
1. **复杂的配置管理**（多个环境变量、配置文件）
2. **统一的错误处理和重试逻辑**
3. **被多个地方复用**（Tools、API、其他服务）
4. **需要中间层功能**（缓存、限流、监控）

那么可以考虑封装成 Service。

### 示例：何时需要封装

**场景 1：yt-dlp 需要统一配置和错误处理**

如果 `yt-dlp` 需要：
- 统一的下载配置（代理、cookies、格式选择）
- 统一的错误处理和重试
- 被多个地方使用（Tool、API、后台任务）

可以创建 `VideoDownloadService`：
```python
# backend/services/video_download_service/
class VideoDownloadService:
    """视频下载服务 - 封装 yt-dlp、you-get、bili23-downloader"""
    
    def __init__(self):
        self.proxy = os.getenv("VIDEO_DOWNLOAD_PROXY")
        self.cookies = self._load_cookies()
        self.retry_config = self._load_retry_config()
    
    async def download(self, url: str, **kwargs):
        """统一的下载接口"""
        # 统一的错误处理和重试逻辑
        ...
```

**场景 2：whisper 需要模型管理和缓存**

如果 `whisper` 需要：
- 模型下载和管理
- 结果缓存
- 被多个地方使用

可以创建 `WhisperService`：
```python
# backend/services/whisper_service/
class WhisperService:
    """Whisper 语音转文字服务"""
    
    def __init__(self):
        self.model_cache = ModelCache()
        self.result_cache = ResultCache()
    
    async def transcribe(self, audio_path: str, **kwargs):
        """统一的转录接口"""
        ...
```

## 总结

### 当前策略（推荐）

**保持现状**：
- ✅ 简单的库调用直接使用（whisper、ffmpeg、yt-dlp）
- ✅ 工具类库直接使用（browser-use）
- ✅ API 客户端封装成 Services（google_search_service、wikipedia_service）

### 何时需要封装

**考虑封装成 Service 当：**
1. 需要复杂的配置管理
2. 需要统一的错误处理和重试
3. 被多个地方复用
4. 需要中间层功能（缓存、限流、监控）

**保持直接使用当：**
1. 简单的函数调用或命令行工具
2. 本身就是工具库
3. 只被一个 Tool 使用

### 架构建议

```
externals/                    # 第三方库（原始代码）
  ├── browser-use/           # 工具库，直接使用
  ├── whisper/               # 简单库，直接使用
  └── yt-dlp/                # 简单库，直接使用

services/                     # 服务层（封装）
  ├── google_search_service/ # API 客户端，封装
  ├── wikipedia_service/     # API 客户端，封装
  └── file_search_service/   # 平台适配，封装

core/tools/                   # 工具层（使用 Services 或直接使用 externals）
  └── builtin/
      ├── browser_tool.py    # 直接使用 browser-use
      ├── whisper_tool.py    # 直接使用 whisper
      ├── video_downloader_tool.py  # 直接使用 yt-dlp
      └── google_search_tool.py     # 使用 GoogleSearchService
```

**原则：**
- **Services** = 需要封装的情况（API 客户端、复杂业务逻辑、可复用）
- **直接使用** = 简单库调用、工具类库、单一用途

