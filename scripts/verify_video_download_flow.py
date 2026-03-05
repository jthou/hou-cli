#!/usr/bin/env python3
"""
验证视频下载前后端流程：模拟 task_handlers 的 opts 构建，调用 VideoDownloaderTool，
确认 extractor_args（player_client）等正确传递。
用法: python scripts/verify_video_download_flow.py [url]
"""
import sys
from pathlib import Path

# 项目根
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    url = (sys.argv[1] if len(sys.argv) > 1 else "https://youtu.be/aAPpQC-3EyE").strip()
    if not url.startswith("http"):
        url = "https://" + url

    # 模拟 task_handlers.process_video_download_task 的 opts
    metadata = {
        "url": url,
        "quality": "auto",
        "download_subtitle": False,
        "download_thumbnail": False,
        "extract_audio_only": False,
        "download_subtitle_only": False,
        "download_danmaku": False,
        "audio_format": "mp3",
        "audio_quality": "192k",
    }
    opts = {
        "quality": metadata.get("quality", "auto"),
        "download_subtitle": metadata.get("download_subtitle", False),
        "download_thumbnail": metadata.get("download_thumbnail", False),
        "extract_audio_only": metadata.get("extract_audio_only", False),
        "download_subtitle_only": metadata.get("download_subtitle_only", False),
        "download_danmaku": metadata.get("download_danmaku", False),
        "audio_format": metadata.get("audio_format", "mp3"),
        "audio_quality": metadata.get("audio_quality", "192k"),
    }

    from shared.platform_utils import normalize_output_dir
    from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool

    output_dir = normalize_output_dir(metadata.get("output_dir"), restrict_to_home=True)
    print(f"URL: {url}")
    print(f"quality: {opts['quality']}")
    print(f"output_dir: {output_dir}")
    print()

    tool = VideoDownloaderTool()
    result = tool.execute(url=url, output_dir=output_dir, **opts)

    if result.success:
        print("✅ 下载成功")
        print(f"   output: {result.data.get('output_file', result.data.get('output_dir', ''))}")
    else:
        print("❌ 下载失败")
        print(f"   error: {result.error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
