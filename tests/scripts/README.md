# 测试脚本目录

本目录包含用于快速验证和手动测试的脚本。

## 说明

这些脚本不是标准的 pytest 测试，而是用于：
- 快速验证功能
- 手动测试和调试
- 开发过程中的临时测试

## 文件分类

### Browser 相关脚本
- `test_browser_*.py` - BrowserTool 相关的快速测试脚本
- `run_browser_*.py` - 浏览器自动化运行脚本
- `open_browser_*.py` - 浏览器打开测试脚本

### Whisper 相关脚本
- `test_whisper_tool.py` - WhisperTool 快速测试脚本
- `test_word_timestamps.py` - 单词时间戳测试脚本
- `test_decoder_manual.py` - 解码器手动测试脚本

### FFmpeg 相关脚本
- `extract_full_audio.py` - 提取完整音频脚本
- `show_transcription_stats.py` - 显示转录统计脚本
- `transcribe_full_video.py` - 转录完整视频脚本

## 注意

这些脚本可能包含硬编码的路径或配置，主要用于开发和调试。
如果需要运行这些脚本，请确保：
1. 环境变量已正确配置
2. 依赖已安装
3. 测试文件路径存在

## 标准测试位置

标准的 pytest 测试文件位于：
- `backend/core/agent/tools/tests/` - Tools 单元测试
- `backend/services/*/tests/` - Services 单元测试
- `tests/integration/` - 集成测试

