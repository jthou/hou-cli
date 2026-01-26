# 目录配置说明

本文档说明项目中临时目录、下载目录、输出目录的配置和使用规范。

## 📁 目录配置现状

### 当前问题

1. **根目录下的 `downloads/` 目录** ❌
   - 位置：项目根目录 `/downloads/`
   - 问题：不应该在项目根目录创建用户数据目录
   - 影响：污染项目结构，可能被提交到 Git

2. **目录配置不统一**
   - 不同工具使用不同的目录配置方式
   - 缺少统一的目录管理机制

### 当前配置

#### 1. 应用数据目录

**位置**: `shared/platform_utils.py`

```python
def get_app_data_dir() -> Path:
    """获取应用数据目录（跨平台）"""
    # Windows: C:\Users\Username\AppData\Local\hou-cli
    # macOS: /Users/Username/Library/Application Support/hou-cli
    # Linux: /home/username/.local/share/hou-cli
```

**用途**: 存储应用配置、端口文件等

#### 2. 下载目录

**位置**: `shared/platform_utils.py`

```python
def get_default_download_dir() -> Path:
    """获取系统默认下载目录（跨平台）"""
    # 所有平台: ~/Downloads/hou-cli-videos
    return Path.home() / "Downloads" / "hou-cli-videos"
```

**用途**: 视频下载、文件下载等

**问题**: 
- ✅ 使用系统 Downloads 目录的子目录（合理）
- ❌ 但可能有代码直接使用根目录的 `downloads/`

#### 3. 临时目录

**当前使用**: Python 标准库 `tempfile`

```python
import tempfile
temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
```

**问题**: 
- 使用系统临时目录（`/tmp` 或 `%TEMP%`）
- 没有统一的临时目录管理

## 🎯 推荐的目录配置方案

### 方案：统一使用应用数据目录

```
应用数据目录 (get_app_data_dir())
├── cache/          # 缓存目录
│   ├── models/     # 模型缓存
│   └── temp/       # 临时文件
├── downloads/      # 下载目录
│   ├── videos/     # 视频文件
│   ├── audio/      # 音频文件
│   └── files/      # 其他文件
├── output/         # 输出目录
│   ├── transcripts/  # 转录文件
│   ├── subtitles/    # 字幕文件
│   └── reports/     # 报告文件
└── logs/           # 日志目录（可选）
```

### 目录结构

**Windows**:
```
C:\Users\Username\AppData\Local\hou-cli\
├── cache\
├── downloads\
├── output\
└── logs\
```

**macOS**:
```
/Users/Username/Library/Application Support/hou-cli/
├── cache/
├── downloads/
├── output/
└── logs/
```

**Linux**:
```
/home/username/.local/share/hou-cli/
├── cache/
├── downloads/
├── output/
└── logs/
```

## 🔧 实施建议

### 1. 扩展 `shared/platform_utils.py`

添加统一的目录管理函数：

```python
def get_app_data_dir() -> Path:
    """获取应用数据目录（跨平台）"""
    # 现有实现...

def get_cache_dir() -> Path:
    """获取缓存目录"""
    cache_dir = get_app_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_download_dir() -> Path:
    """获取下载目录"""
    download_dir = get_app_data_dir() / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir

def get_output_dir() -> Path:
    """获取输出目录"""
    output_dir = get_app_data_dir() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_temp_dir() -> Path:
    """获取临时目录（应用专用）"""
    temp_dir = get_cache_dir() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
```

### 2. 环境变量支持

在 `env.example` 中添加目录配置：

```bash
# 目录配置（可选）
# 如果不设置，使用系统默认位置
# HOU_CLI_DATA_DIR=~/.local/share/hou-cli  # Linux/macOS
# HOU_CLI_DATA_DIR=%LOCALAPPDATA%\hou-cli  # Windows
# HOU_CLI_DOWNLOAD_DIR=~/Downloads/hou-cli-videos
# HOU_CLI_OUTPUT_DIR=~/Documents/hou-cli-output
# HOU_CLI_CACHE_DIR=~/.cache/hou-cli
# HOU_CLI_TEMP_DIR=~/.cache/hou-cli/temp
```

### 3. 更新工具使用

**视频下载工具**:
```python
from shared.platform_utils import get_download_dir

# 使用统一的下载目录
output_dir = get_download_dir() / "videos"
```

**Whisper 工具**:
```python
from shared.platform_utils import get_output_dir

# 使用统一的输出目录
output_dir = get_output_dir() / "transcripts"
```

**临时文件**:
```python
from shared.platform_utils import get_temp_dir

# 使用统一的临时目录
temp_file = get_temp_dir() / f"temp_{uuid.uuid4()}.txt"
```

## 📋 需要检查的地方

### 1. 根目录 downloads/ 目录

**检查**: 是否有代码直接使用 `./downloads` 或项目根目录的 `downloads/`

**修复**: 
- 移除根目录的 `downloads/` 目录
- 更新所有引用，使用 `get_download_dir()`

### 2. 工具中的目录使用

**需要检查的工具**:
- `video_downloader_tool.py` - 下载目录
- `whisper_tool.py` - 输出目录
- `browser_tool.py` - 下载目录（browser-use 配置）
- `file_organizer_tool.py` - 可能需要临时目录

### 3. 临时文件使用

**检查**: 所有使用 `tempfile` 的地方
- `video_downloader_tool.py` - cookies 临时文件
- `ffmpeg_tool.py` - 临时文件

## 🚀 迁移步骤

### 步骤 1: 扩展 platform_utils.py

添加新的目录管理函数（见上方代码）

### 步骤 2: 更新工具代码

1. 更新 `video_downloader_tool.py`:
   ```python
   # 旧代码
   output_dir = normalize_output_dir(kwargs.get('output_dir'))
   
   # 新代码（如果未指定，使用应用数据目录）
   if 'output_dir' in kwargs:
       output_dir = Path(kwargs['output_dir']).expanduser()
   else:
       output_dir = get_download_dir() / "videos"
   ```

2. 更新 `whisper_tool.py`:
   ```python
   # 如果未指定输出文件，使用应用数据目录
   if not output_file:
       output_dir = get_output_dir() / "transcripts"
       output_path = output_dir / f"{audio_path.stem}_transcription"
   ```

### 步骤 3: 清理根目录

1. 检查根目录 `downloads/` 中的文件
2. 迁移到新的下载目录
3. 将 `downloads/` 添加到 `.gitignore`
4. 删除根目录的 `downloads/` 目录

### 步骤 4: 更新文档

更新相关文档，说明新的目录配置

## 📝 配置优先级

1. **用户指定** - 如果用户通过参数指定了目录，使用用户指定的
2. **环境变量** - 如果设置了环境变量，使用环境变量指定的
3. **系统默认** - 使用应用数据目录的子目录

## 🔍 检查清单

- [ ] 扩展 `shared/platform_utils.py` 添加目录管理函数
- [ ] 检查所有工具中的目录使用
- [ ] 更新 `video_downloader_tool.py` 使用新的下载目录
- [ ] 更新 `whisper_tool.py` 使用新的输出目录
- [ ] 检查并修复根目录 `downloads/` 的使用
- [ ] 更新 `env.example` 添加目录配置选项
- [ ] 将 `downloads/` 添加到 `.gitignore`
- [ ] 迁移根目录 `downloads/` 中的文件
- [ ] 删除根目录的 `downloads/` 目录
- [ ] 更新相关文档

---

**最后更新**: 2026-01-20  
**维护者**: 项目团队


