#!/usr/bin/env python3
"""转录完整视频"""
import sys
sys.path.insert(0, '.')
from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
from pathlib import Path

# 查找完整的视频文件
video_file = Path.home() / 'Downloads' / '罗永浩-萤石.mp4'
audio_file = Path.home() / 'Downloads' / '罗永浩-萤石_audio.m4a'

# 优先使用音频文件（如果存在），否则使用视频文件
if audio_file.exists():
    input_file = audio_file
    print(f"📁 找到音频文件: {audio_file.name}")
    file_size_mb = audio_file.stat().st_size / 1024 / 1024
    print(f"   文件大小: {file_size_mb:.2f} MB")
elif video_file.exists():
    input_file = video_file
    print(f"📁 找到视频文件: {video_file.name}")
    file_size_mb = video_file.stat().st_size / 1024 / 1024
    print(f"   文件大小: {file_size_mb:.2f} MB")
else:
    print("❌ 未找到视频或音频文件")
    print("   请确认文件存在于 ~/Downloads/ 目录")
    sys.exit(1)

print("")
print("🎙️  开始完整转录...")
print("=" * 60)
print("")
print("⚠️  注意：完整转录可能需要较长时间")
print("   建议使用 'base' 或 'small' 模型以获得更好的准确性")
print("   文件较大，请耐心等待...")
print("")

tool = WhisperTool()

# 使用 base 模型进行完整转录
result = tool.execute(
    audio_file=str(input_file),
    language="zh",
    model="base",  # 使用 base 模型以获得更好的准确性
    output_format="json"
)

if result.success:
    print("")
    print("✅ 转录成功！")
    print("")
    if result.data and 'summary' in result.data:
        print(result.data['summary'])
    else:
        text_len = len(result.data.get('text', '')) if result.data else 0
        segments_count = result.data.get('segments_count', 0) if result.data else 0
        output_file = result.data.get('output_file', 'N/A') if result.data else 'N/A'
        print(f"文本长度: {text_len} 字符")
        print(f"段落数: {segments_count}")
        print(f"输出文件: {output_file}")
else:
    print(f"❌ 转录失败: {result.error}")

