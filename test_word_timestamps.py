#!/usr/bin/env python3
"""测试是否是 word_timestamps 导致的问题"""
import sys
import os
sys.path.insert(0, '.')
import whisper

print("🔍 测试: 检查是否是 word_timestamps 导致的问题")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

audio_file = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_test_30s.m4a'

try:
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    print("")
    print("测试 1: 不使用 word_timestamps...")
    try:
        result1 = model.transcribe(
            audio_file,
            language="zh",
            word_timestamps=False,  # 关键：禁用
            verbose=False,
            fp16=False,
            temperature=0.0,
            best_of=1,
            beam_size=1
        )
        print("✅ 成功（不使用 word_timestamps）！")
        print(f"   文本: {result1['text'][:100]}...")
        print(f"   段落数: {len(result1['segments'])}")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        if "segmentation" in str(e).lower() or "139" in str(e):
            print("   → 段错误 - 问题不在 word_timestamps")
    
    print("")
    print("测试 2: 使用 word_timestamps...")
    try:
        result2 = model.transcribe(
            audio_file,
            language="zh",
            word_timestamps=True,  # 启用
            verbose=False,
            fp16=False,
            temperature=0.0,
            best_of=1,
            beam_size=1
        )
        print("✅ 成功（使用 word_timestamps）！")
        print(f"   文本: {result2['text'][:100]}...")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}")
        if "segmentation" in str(e).lower() or "139" in str(e):
            print("   → 段错误 - 问题可能在 word_timestamps 处理中")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()



