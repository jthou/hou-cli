# 外部依赖自动化安装

## 概述

本项目**不再使用 Git 子模块**。外部依赖通过 **pip**（`requirements.txt`）和 **系统 FFmpeg** 安装，并集成到 `make install` / `make install-dev`。

## 自动化流程

### `make install` 流程

1. **安装 Python 依赖**
   - 安装 `requirements.txt`（含 browser-use、yt-dlp、you-get、openai-whisper 等）

2. **FFmpeg**（`scripts/install_ffmpeg.sh`）
   - 若未安装则通过系统包安装（macOS: brew, Linux: apt）

3. **其他脚本**（按需）
   - 安装 browser-use、Whisper、视频下载工具等（也可通过 `pip install -r requirements.txt` 一并安装）

### `make install-dev` 流程

与 `make install` 相同，并额外安装开发依赖（如 `requirements-dev.txt`）、可选预下载 Whisper 模型等。

## 脚本说明

### `scripts/install_ffmpeg.sh`

安装**系统 FFmpeg**（不再从源码编译）。

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- 若已安装则跳过

### `scripts/install_browser_use.sh`

`pip install browser-use`，并验证导入。

### `scripts/install_whisper.sh`

`pip install openai-whisper`，可选 `--download-models` 预下载模型。

### `scripts/install_video_downloaders.sh`

`pip install yt-dlp you-get`。

## 依赖列表（pip + 系统）

| 依赖 | 安装方式 | 说明 |
|------|----------|------|
| browser-use | pip | `requirements.txt` |
| yt-dlp | pip | `requirements.txt` |
| you-get | pip | `requirements.txt` |
| openai-whisper | pip | `requirements.txt` |
| FFmpeg | 系统 | `scripts/install_ffmpeg.sh` 或手动 brew/apt |

## 使用示例

### 首次安装

```bash
pip install -r requirements.txt
bash scripts/install_ffmpeg.sh   # 若系统未装 FFmpeg
```

### 验证

```bash
ffmpeg -version
python -c "import whisper, yt_dlp, you_get; from browser_use import Agent; print('OK')"
```

## 相关文档

- [backend/externals/README.md](../../backend/externals/README.md) - 依赖说明
- [backend/externals/SETUP.md](../../backend/externals/SETUP.md) - 环境准备
