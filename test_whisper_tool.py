#!/usr/bin/env python3
"""测试 WhisperTool"""
import sys
sys.path.insert(0, '.')
from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
from pathlib import Path

# 测试工具执行（使用小音频文件）
audio_file = Path.home() / 'Downloads' / '罗永浩-萤石_audio_test_30s.m4a'

if not audio_file.exists():
    print(f"❌ 测试音频文件不存在: {audio_file}")
    sys.exit(1)

print("🧪 测试 WhisperTool 执行...")
print("=" * 60)

tool = WhisperTool()

# 测试执行
result = tool.execute(
    audio_file=str(audio_file),
    language="zh",
    model="tiny",
    output_format="json"
)

if result.success:
    print("✅ 转录成功！")
    print("")
    print("📊 结果摘要：")
    if result.data and 'summary' in result.data:
        print(result.data['summary'])
    else:
        text = result.data.get('text', '') if result.data else ''
        print(f"文本: {text[:100]}...")
        if result.data:
            print(f"语言: {result.data.get('language', 'unknown')}")
            print(f"段落数: {result.data.get('segments_count', 0)}")
            print(f"输出文件: {result.data.get('output_file', 'N/A')}")
else:
    print(f"❌ 转录失败: {result.error}")



