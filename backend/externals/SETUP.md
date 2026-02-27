# 外部依赖环境准备指南

本仓库**不再使用 Git 子模块**。依赖通过 **pip**（见 `requirements.txt`）和 **系统 FFmpeg** 安装。

## 系统依赖

### macOS

```bash
xcode-select --install
brew install git make pkg-config
# FFmpeg（必需，用于音视频处理）
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y build-essential git ffmpeg
```

## Python 依赖

在项目根目录：

```bash
pip install -r requirements.txt
```

主要包含：

- **browser-use** — 浏览器自动化
- **yt-dlp**、**you-get** — 视频下载
- **openai-whisper** — 语音转文字

## 可选：分步安装

- FFmpeg（系统）：`scripts/install_ffmpeg.sh`
- Whisper：`scripts/install_whisper.sh`（可选 `--download-models` 预下载模型）
- 视频下载工具：`scripts/install_video_downloaders.sh`
- browser-use：`scripts/install_browser_use.sh`

## 验证

```bash
# FFmpeg
ffmpeg -version

# Python 包
python -c "import whisper; print('Whisper OK')"
python -c "import yt_dlp; print('yt-dlp OK')"
python -c "import you_get; print('you-get OK')"
python -c "from browser_use import Agent; print('browser-use OK')"
```

## 常见问题

- **找不到 ffmpeg**：请系统安装，如 `brew install ffmpeg` 或 `sudo apt install ffmpeg`。
- **Whisper 安装慢**：会下载 PyTorch，可改用国内镜像或先单独安装 `torch`。
