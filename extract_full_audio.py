#!/usr/bin/env python3
"""从完整视频中提取音频"""
import sys
sys.path.insert(0, '.')
from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
from pathlib import Path

print("🎵 重新从完整视频中提取音频...")
print("=" * 60)
print("")
print("⚠️  注意：这将创建新的完整音频文件")
print("   完整提取可能需要较长时间（4小时21分钟的视频）")
print("")

video_file = '/Users/jintinghou/Downloads/罗永浩-萤石.mp4'
output_audio = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_full.m4a'

tool = FFmpegTool()

print("开始提取...")
result = tool.execute(
    operation="extract_audio",
    input_file=video_file,
    output_file=output_audio,
    audio_format="m4a",
    audio_quality="192k"
)

if result.success:
    print("")
    print("✅ 音频提取成功！")
    print(f"   输出文件: {output_audio}")
    
    # 检查新音频文件时长
    print("")
    print("🔍 验证新音频文件时长...")
    probe_result = tool.execute(operation="probe", input_file=output_audio)
    if probe_result.success and probe_result.data:
        audio_info = probe_result.data.get('info', {})
        duration = audio_info.get('format', {}).get('duration', 0)
        if duration:
            hours = int(float(duration) // 3600)
            minutes = int((float(duration) % 3600) // 60)
            seconds = int(float(duration) % 60)
            print(f"   新音频时长: {hours:02d}:{minutes:02d}:{seconds:02d}")
            print(f"   总秒数: {float(duration):.2f} 秒")
            
            # 对比原始视频
            video_sec = 15690.175667
            audio_sec = float(duration)
            if abs(audio_sec - video_sec) < 10:  # 允许10秒误差
                print("")
                print("✅ 音频文件时长与视频一致！")
            else:
                print("")
                print(f"⚠️  时长仍有差异: {abs(audio_sec - video_sec):.2f} 秒")
else:
    print(f"❌ 提取失败: {result.error}")





