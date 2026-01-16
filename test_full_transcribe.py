#!/usr/bin/env python3
"""测试完整转录过程"""
import sys
import os
sys.path.insert(0, '.')
import whisper

print("🔍 测试 5: 完整转录过程（使用最小参数）")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

audio_file = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_test_30s.m4a'

try:
    print("加载模型...")
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    print("")
    print("开始完整转录（使用最小参数）...")
    print("   参数：")
    print("   - language: zh")
    print("   - word_timestamps: True")
    print("   - fp16: False")
    print("   - temperature: 0.0 (确定性)")
    print("   - best_of: 1 (最快)")
    print("   - beam_size: 1 (贪心解码)")
    print("")
    
    result = model.transcribe(
        audio_file,
        language="zh",
        word_timestamps=True,
        verbose=False,
        fp16=False,
        temperature=0.0,
        best_of=1,
        beam_size=1
    )
    
    print("✅ 转录成功！")
    print("")
    print(f"转录文本: {result['text']}")
    print(f"段落数: {len(result['segments'])}")
    
    # 显示时间戳
    print("")
    print("⏱️  时间戳信息：")
    for i, seg in enumerate(result['segments'], 1):
        start = seg['start']
        end = seg['end']
        start_min = int(start // 60)
        start_sec = int(start % 60)
        end_min = int(end // 60)
        end_sec = int(end % 60)
        print(f"   {i}. [{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}] {seg['text']}")
    
except Exception as e:
    print(f"❌ 转录失败: {e}")
    import traceback
    traceback.print_exc()
    print("")
    print("💡 如果这里失败，说明问题在完整的转录循环中")



