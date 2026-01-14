# 外部依赖自动化安装

## 概述

本项目的外部依赖（externals）现在已集成到 `make install` 和 `make install-dev` 中，会自动完成更新、编译和安装。

## 自动化流程

### `make install` 流程

1. **更新外部依赖** (`scripts/update_externals.sh`)
   - 初始化所有 git submodules
   - 更新所有 submodules 到最新版本

2. **安装 Python 依赖**
   - 安装 `requirements.txt`
   - 安装项目本身

3. **编译 FFmpeg** (`scripts/install_ffmpeg.sh`)
   - 检查是否需要重新编译（基于 git hash）
   - 自动配置和编译
   - 安装到 `backend/externals/ffmpeg/build/bin/`

4. **安装其他工具**
   - 检查浏览器依赖
   - 安装 Whisper
   - 安装 Jupyter
   - 安装视频下载工具（yt-dlp, you-get）
   - 安装 browser-use

### `make install-dev` 流程

与 `make install` 相同，但额外包括：
- 安装开发依赖 (`requirements-dev.txt`)
- 预下载 Whisper 模型
- 注册 Jupyter kernel

## 脚本说明

### `scripts/update_externals.sh`

更新所有 git submodules 到最新版本。

**功能**：
- 初始化未初始化的 submodules
- 更新所有 submodules 到远程最新版本
- 显示更新状态

**使用**：
```bash
bash scripts/update_externals.sh
```

### `scripts/install_ffmpeg.sh` (已更新)

编译 FFmpeg（如果需要）。

**改进**：
- ✅ 检查源码是否已更新（基于 git hash）
- ✅ 自动检测是否需要重新编译
- ✅ 保存构建版本信息
- ✅ 兼容 macOS 和 Linux（CPU 核心数检测）

**功能**：
- 检查 FFmpeg 是否已编译
- 比较源码版本和构建版本
- 如果需要，自动清理、配置、编译和安装
- 保存构建版本信息到 `build/.git_hash`

**使用**：
```bash
bash scripts/install_ffmpeg.sh
```

### `scripts/install_browser_use.sh` (新增)

安装 browser-use 到 venv。

**功能**：
- 检查 browser-use 目录是否存在
- 如果不存在，尝试初始化 submodule
- 从本地源码安装到 venv
- 验证安装

**使用**：
```bash
bash scripts/install_browser_use.sh
```

### `scripts/install_video_downloaders.sh` (已更新)

安装视频下载工具（yt-dlp, you-get, browser-use）。

**改进**：
- ✅ 添加了 browser-use 安装

## 外部依赖列表

### Git Submodules

1. **bili23-downloader** (`backend/externals/bili23-downloader`)
   - 用途：Bilibili 视频下载（GUI 应用）
   - 安装：不需要（CLI 模式下使用 yt-dlp）

2. **browser-use** (`backend/externals/browser-use`)
   - 用途：浏览器自动化工具
   - 安装：`pip install -e backend/externals/browser-use`
   - 脚本：`scripts/install_browser_use.sh`

3. **ffmpeg** (`backend/externals/ffmpeg`)
   - 用途：视频/音频处理
   - 安装：需要编译
   - 脚本：`scripts/install_ffmpeg.sh`
   - 输出：`backend/externals/ffmpeg/build/bin/`

4. **whisper** (`backend/externals/whisper`)
   - 用途：语音转文字
   - 安装：`pip install -e backend/externals/whisper`
   - 脚本：`scripts/install_whisper.sh`

5. **you-get** (`backend/externals/you-get`)
   - 用途：视频下载工具
   - 安装：`pip install -e backend/externals/you-get`
   - 脚本：`scripts/install_video_downloaders.sh`

6. **yt-dlp** (`backend/externals/yt-dlp`)
   - 用途：视频下载工具（youtube-dl 的改进版）
   - 安装：`pip install -e backend/externals/yt-dlp`
   - 脚本：`scripts/install_video_downloaders.sh`

## 版本管理

### FFmpeg 版本检查

FFmpeg 使用 git hash 来检查是否需要重新编译：
- 构建版本保存在 `backend/externals/ffmpeg/build/.git_hash`
- 每次编译后自动保存当前源码的 git hash
- 如果源码 hash 与构建 hash 不同，自动重新编译

### Submodule 版本

所有 submodules 的版本由 git submodule 管理：
- 查看状态：`git submodule status`
- 更新到最新：`git submodule update --remote --merge`
- 固定版本：提交 submodule 的特定 commit

## 使用示例

### 首次安装

```bash
# 安装生产依赖（包括所有外部依赖）
make install

# 或安装开发依赖
make install-dev
```

### 更新外部依赖

```bash
# 手动更新所有 submodules
bash scripts/update_externals.sh

# 或使用 make install（会自动更新）
make install
```

### 重新编译 FFmpeg

```bash
# 如果 FFmpeg 源码已更新，会自动重新编译
bash scripts/install_ffmpeg.sh

# 或使用 make install（会自动检查并编译）
make install
```

## 故障排除

### Submodule 未初始化

如果遇到 "目录不存在" 错误：

```bash
# 初始化所有 submodules
git submodule update --init --recursive

# 或使用脚本
bash scripts/update_externals.sh
```

### FFmpeg 编译失败

1. 检查系统依赖：
   ```bash
   # macOS
   brew install nasm
   
   # Linux
   sudo apt install nasm build-essential
   ```

2. 查看编译日志：
   ```bash
   cat /tmp/ffmpeg_configure.log
   cat /tmp/ffmpeg_make.log
   ```

3. 手动清理并重新编译：
   ```bash
   cd backend/externals/ffmpeg
   make distclean
   bash ../../scripts/install_ffmpeg.sh
   ```

### Python 库安装失败

1. 确保虚拟环境已激活：
   ```bash
   source venv/bin/activate
   ```

2. 检查 Python 版本（某些库需要特定版本）：
   ```bash
   python --version
   ```

3. 手动安装：
   ```bash
   pip install -e backend/externals/whisper
   pip install -e backend/externals/you-get
   pip install -e backend/externals/yt-dlp
   pip install -e backend/externals/browser-use
   ```

## 最佳实践

1. **定期更新**：
   - 运行 `make install` 会自动更新所有依赖
   - 或手动运行 `bash scripts/update_externals.sh`

2. **版本控制**：
   - 提交 submodule 的特定版本以确保团队一致性
   - FFmpeg 构建版本会自动保存

3. **清理重建**：
   - 如果遇到问题，使用 `make clean-deps` 清理所有依赖
   - 然后重新运行 `make install`

4. **开发环境**：
   - 使用 `make install-dev` 安装开发依赖
   - 包括预下载的 Whisper 模型

## 相关文档

- [外部依赖环境准备指南](../externals/SETUP.md)
- [FFmpeg 编译说明](../externals/SETUP.md#ffmpeg-编译)
- [Whisper 安装说明](../externals/SETUP.md#whisper-安装)

