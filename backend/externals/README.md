# 外部依赖说明（已改为 pip + 系统安装）

本目录不再使用 Git 子模块。所有相关依赖通过 **pip** 和 **系统包** 安装。

## 依赖一览

| 功能           | 安装方式              | 说明 |
|----------------|-----------------------|------|
| 浏览器自动化   | （暂时移除，后续再开发） | 需时取消 requirements 注释并设置 `BROWSER_TOOL_ENABLED=true` |
| 视频下载       | `pip install yt-dlp you-get` | 见 `requirements.txt` |
| 音视频处理     | 系统安装 FFmpeg       | macOS: `brew install ffmpeg`，Linux: `apt install ffmpeg` |
| 语音转文字     | `pip install openai-whisper` | 见 `requirements.txt` |

## 快速安装

```bash
# 项目根目录下
pip install -r requirements.txt

# FFmpeg（系统）
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

也可使用脚本（会激活 venv 并安装）：

- `scripts/install_ffmpeg.sh` — 安装系统 FFmpeg
- `scripts/install_browser_use.sh` — pip 安装 browser-use
- `scripts/install_whisper.sh` — pip 安装 openai-whisper
- `scripts/install_video_downloaders.sh` — pip 安装 yt-dlp、you-get

更多说明见 [SETUP.md](./SETUP.md)。
