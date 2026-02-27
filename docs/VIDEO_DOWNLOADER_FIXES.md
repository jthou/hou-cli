# 视频下载工具修复说明

## 问题 1: 音频转换失败（Encoder not found）

### 问题描述

在使用 `video_downloader` 工具提取音频时，yt-dlp 下载成功，但在音频转换阶段失败，错误信息：

```
ERROR: Postprocessing: audio conversion failed: Error opening output files: Encoder not found
```

### 原因分析

1. **FFmpeg 缺少 MP3 编码器**：系统 FFmpeg 在安装时可能未包含 `libmp3lame` 编码器
2. **默认使用 MP3 格式**：yt-dlp 默认尝试将音频转换为 MP3 格式，但 FFmpeg 找不到 MP3 编码器

### 修复方案

**文件**: `backend/core/agent/tools/builtin/video_downloader_tool.py`

**修复内容**:
1. 在音频转换前检查 FFmpeg 是否支持 MP3 编码器（libmp3lame）
2. 如果不支持，自动改用 AAC 格式（更通用，大多数 FFmpeg 版本都支持）
3. 检查顺序：
   - 先检查系统 FFmpeg（`ffmpeg -encoders`）
   - 如果不存在，检查系统 PATH 中的 FFmpeg
   - 如果检查失败，默认使用 AAC 格式

**代码变更**:
```python
# 检查 FFmpeg 是否支持 MP3 编码器
audio_format = options.get('audio_format', 'mp3')
if audio_format.lower() == 'mp3':
    # 检查 MP3 编码器是否可用
    # ... 检查逻辑 ...
    if 'libmp3lame' not in result.stdout:
        logger.warning("FFmpeg 不支持 MP3 编码器（libmp3lame），改用 AAC 格式")
        audio_format = 'aac'
```

### 使用建议

1. **如果需要 MP3 格式**：
   - 安装支持 MP3 的 FFmpeg（包含 libmp3lame）
   - 或使用系统 FFmpeg（如果已安装 libmp3lame）

2. **如果使用 AAC 格式**（推荐）：
   - AAC 格式更通用，兼容性更好
   - 大多数现代播放器都支持 AAC
   - 文件大小和音质与 MP3 相当

## 问题 2: 流式请求超时

### 问题描述

在执行视频下载等长任务时，前端出现超时错误：

```
✗ 连接错误: 流式请求超时
提示: 请检查后端服务是否正常运行，或任务是否过于复杂导致超时
```

### 原因分析

1. **前端 read 超时设置过短**：前端配置的 read 超时为 60 秒（空闲超时）
2. **视频下载任务时间长**：视频下载和音频转换可能需要几分钟时间
3. **后端未持续发送数据**：如果后端在下载过程中没有发送进度更新，前端会认为连接空闲而超时

### 修复方案

**文件**: `frontend/client/stream_receiver.py`

**修复内容**:
1. 将 read 超时从 60 秒增加到 300 秒（5 分钟）
2. 支持通过环境变量 `STREAM_READ_TIMEOUT` 配置超时时间
3. 保持其他超时设置不变（connect: 10秒, write: 10秒, pool: 10秒）

**代码变更**:
```python
# 从环境变量读取 read 超时，默认 300 秒（5 分钟）
read_timeout = float(os.getenv("STREAM_READ_TIMEOUT", "300.0"))
stream_timeout = Timeout(
    connect=10.0,      # 连接超时
    read=read_timeout,  # 读取超时（空闲超时）- 关键：这是空闲超时，不是总超时
    write=10.0,        # 写入超时
    pool=10.0          # 连接池超时
)
```

### 配置说明

**环境变量**:
- `STREAM_READ_TIMEOUT`: 流式请求的 read 超时时间（秒），默认 300 秒（5 分钟）

**超时类型说明**:
- **read 超时是空闲超时**：如果指定时间内没有收到任何数据才超时
- **不是总超时**：只要后端持续发送数据（即使是心跳），就不会超时
- **任务总时间可以很长**：只要后端定期发送进度更新或心跳，前端就不会超时

### 使用建议

1. **对于长任务**（如视频下载）：
   - 确保后端在任务执行过程中定期发送进度更新
   - 可以通过 `STREAM_READ_TIMEOUT` 环境变量增加超时时间

2. **对于超长任务**（超过 5 分钟）：
   ```bash
   # 设置更长的超时时间（例如 10 分钟）
   export STREAM_READ_TIMEOUT=600
   ```

3. **后端进度更新**：
   - 工具应该通过 `progress_callback` 定期发送进度更新
   - 这样前端就不会因为空闲而超时

## 测试验证

### 测试音频转换

```bash
# 测试视频下载并提取音频
python -c "
from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
tool = VideoDownloaderTool()
result = tool.execute(
    url='https://www.bilibili.com/video/BV1knvYBDEjs',
    extract_audio_only=True,
    audio_format='mp3'  # 会自动检测并改用 AAC（如果不支持 MP3）
)
print(result)
"
```

### 测试流式超时

```bash
# 设置超时时间
export STREAM_READ_TIMEOUT=600  # 10 分钟

# 运行前端，测试长任务
# 前端应该不会在 10 分钟内超时（只要后端持续发送数据）
```

## 相关文档

- [视频下载工具使用指南](../tools/video-downloader-usage.md)
- [流式请求超时优化](../archived/optimization/FRONTEND_BACKEND_TIMEOUT_OPTIMIZATION.md)
- [FFmpeg 工具说明](../tools/ffmpeg-tool.md)

---

**最后更新**: 2026-01-20  
**维护者**: 项目团队




