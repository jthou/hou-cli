#!/usr/bin/env python3
"""测试音频解码（不进行转录）"""
import sys
import os
sys.path.insert(0, '.')
import whisper

print("🔍 测试 3: 音频解码（不进行转录）")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

audio_file = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_test_30s.m4a'

try:
    print("加载模型...")
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    print("")
    print("测试音频解码（不进行转录）...")
    import whisper.audio as audio_module
    
    # 直接调用音频加载函数
    audio = audio_module.load_audio(audio_file)
    print(f"✅ 音频加载成功")
    print(f"   音频长度: {len(audio)} 采样点")
    print(f"   采样率: {audio_module.SAMPLE_RATE} Hz")
    print(f"   时长: {len(audio) / audio_module.SAMPLE_RATE:.2f} 秒")
    
    # 测试音频预处理
    print("")
    print("测试音频预处理...")
    mel = audio_module.log_mel_spectrogram(audio)
    print(f"✅ 音频预处理成功")
    print(f"   Mel 频谱形状: {mel.shape}")
    
except Exception as e:
    print(f"❌ 音频处理失败: {e}")
    import traceback
    traceback.print_exc()





