#!/usr/bin/env python3
"""删除 externals 子模块后，验证相关功能依赖是否可用（pip + 系统 FFmpeg）。"""
import sys
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    ok = True

    # 1. FFmpeg（系统 PATH）
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print("  [OK] ffmpeg (系统):", ffmpeg)
    else:
        print("  [--] ffmpeg: 未找到（请 brew install ffmpeg 或 apt install ffmpeg）")
        ok = False

    # 2. whisper（pip: openai-whisper）
    try:
        import whisper  # noqa: F401
        print("  [OK] whisper (openai-whisper)")
    except ImportError as e:
        print("  [--] whisper:", e)
        ok = False

    # 3. yt-dlp（pip）
    try:
        import yt_dlp  # noqa: F401
        print("  [OK] yt-dlp")
    except ImportError as e:
        print("  [--] yt-dlp:", e)
        ok = False

    # 4. you-get（pip）
    try:
        import you_get  # noqa: F401
        print("  [OK] you-get")
    except ImportError as e:
        print("  [--] you-get:", e)
        ok = False

    # 5. browser-use（pip）- 暂时移除，后续再开发，不参与验证
    # try:
    #     from browser_use import Agent, Browser
    #     print("  [OK] browser-use")
    # except ImportError as e:
    #     print("  [--] browser-use:", e)
    #     ok = False
    print("  [--] browser-use: 已暂时移除，跳过")

    # 6. 工具模块能正常加载（不依赖 backend/externals 路径；不加载 browser_tool）
    try:
        from backend.core.agent.tools.builtin.ffmpeg_tool import _get_ffmpeg_path, _find_ffmpeg_binary
        from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
        from backend.core.agent.tools.builtin.video_downloader_tool import YouGetDownloader, YtDlpDownloader
        p = _get_ffmpeg_path()
        b = _find_ffmpeg_binary("ffmpeg")
        print("  [OK] 工具模块加载正常（ffmpeg_path 类型:", type(p).__name__ + ", 系统 ffmpeg:", b is not None, ")")
    except Exception as e:
        print("  [--] 工具模块加载失败:", e)
        ok = False

    print()
    if ok:
        print("验证通过：删除 externals 后依赖（pip + 系统 FFmpeg）可用。")
        return 0
    print("部分依赖未就绪，请执行: pip install -r requirements.txt && scripts/install_ffmpeg.sh")
    return 1

if __name__ == "__main__":
    sys.exit(main())
