# External Dependencies

This directory contains external libraries that are integrated directly from source code using git submodules.

> 📖 **环境准备指南**：如果是在新机器上设置开发环境，请先查看 [SETUP.md](./SETUP.md) 了解如何初始化 submodule、编译 FFmpeg、安装 Whisper 等完整流程。

## Integrated Libraries

### 1. browser-use
- **Purpose**: Browser automation and web scraping
- **Repository**: https://github.com/browser-use/browser-use
- **Usage**: Used for browser automation tasks

### 2. you-get
- **Purpose**: Universal video downloader (supports multiple platforms)
- **Repository**: https://github.com/soimort/you-get
- **Usage**: Primary video download tool for YouTube, Bilibili, Youku, etc.
- **Priority**: **Primary** - Use this for most video download needs

### 3. yt-dlp
- **Purpose**: Powerful video downloader with advanced subtitle and audio extraction
- **Repository**: https://github.com/yt-dlp/yt-dlp
- **Usage**: Primary tool for YouTube and other platforms, especially for subtitle-only and audio-only downloads
- **Priority**: **Primary** - Use for YouTube and when subtitle/audio extraction is needed

### 4. ffmpeg
- **Purpose**: Complete, cross-platform solution to record, convert and stream audio and video
- **Repository**: https://github.com/FFmpeg/FFmpeg
- **Usage**: Required for audio extraction and video format conversion (used by yt-dlp)
- **Priority**: **Required** - System dependency for video/audio processing

### 5. whisper
- **Purpose**: Speech recognition and transcription tool
- **Repository**: https://github.com/openai/whisper
- **Usage**: Speech-to-text transcription, subtitle generation, audio transcription
- **Priority**: **Optional** - For speech recognition features
- **Installation**: 
  ```bash
  # 从本地源码安装（推荐，使用我们下载的版本）
  pip install -e backend/externals/whisper
  
  # 这会自动安装所有依赖：
  # - PyTorch (深度学习框架)
  # - tiktoken (OpenAI 的快速分词器)
  # - numpy, numba, tqdm, more-itertools 等
  ```
- **Note**: 下载源码只是获取了源代码文件，还需要安装 Python 依赖包才能运行。使用 `pip install -e` 可以从本地源码安装并自动安装所有依赖。

## Managing Submodules

### Initial Setup
```bash
# Clone repository with submodules
git clone --recursive <repo-url>

# Or initialize existing repository
git submodule update --init --recursive
```

### Updating Submodules
```bash
# Update all submodules to latest
git submodule update --remote

# Update specific submodule
git submodule update --remote backend/externals/you-get
```

### Working with Submodules
```bash
# Enter submodule directory
cd backend/externals/you-get

# Make changes and commit
git add .
git commit -m "Your changes"
git push

# Return to main repository and update submodule reference
cd ../../..
git add backend/externals/you-get
git commit -m "Update you-get submodule"
```

## Integration Guidelines

1. **Prefer you-get or yt-dlp** for video download (B 站可优先 you-get 或指定 yt-dlp)
2. **Modify submodule code** if needed, but document changes clearly
3. **Keep submodules updated** to get bug fixes and new features

