#!/usr/bin/env python3
"""显示转录统计信息"""
import json
from pathlib import Path

json_file = Path.home() / 'Downloads' / '罗永浩-萤石_audio_transcription.json'

if json_file.exists():
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("📊 转录结果统计：")
    print("=" * 60)
    print(f"总文本长度: {len(data['text'])} 字符")
    print(f"段落数: {len(data['segments'])}")
    
    # 计算总时长
    if data['segments']:
        total_duration = data['segments'][-1]['end']
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        seconds = int(total_duration % 60)
        print(f"总时长: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    # 显示前几个段落
    print("")
    print("📝 前 10 个段落：")
    for i, seg in enumerate(data['segments'][:10], 1):
        start = seg['start']
        end = seg['end']
        start_min = int(start // 60)
        start_sec = int(start % 60)
        end_min = int(end // 60)
        end_sec = int(end % 60)
        print(f"  {i}. [{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}] {seg['text']}")
    
    # 显示最后几个段落
    print("")
    print("📝 最后 5 个段落：")
    for i, seg in enumerate(data['segments'][-5:], len(data['segments']) - 4):
        start = seg['start']
        end = seg['end']
        start_min = int(start // 60)
        start_sec = int(start % 60)
        end_min = int(end // 60)
        end_sec = int(end % 60)
        print(f"  {i}. [{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}] {seg['text']}")
else:
    print("❌ 转录文件不存在")



