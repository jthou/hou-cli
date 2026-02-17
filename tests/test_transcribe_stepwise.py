#!/usr/bin/env python3
"""测试转录过程（逐步测试）"""
import sys
import os
sys.path.insert(0, '.')
import whisper
import torch

print("🔍 测试 4: 转录过程（逐步测试）")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

audio_file = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_test_30s.m4a'

try:
    print("步骤 1: 加载模型...")
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    print("")
    print("步骤 2: 加载音频...")
    import whisper.audio as audio_module
    audio = audio_module.load_audio(audio_file)
    print(f"✅ 音频加载成功: {len(audio)} 采样点")
    
    print("")
    print("步骤 3: 音频预处理...")
    mel = audio_module.log_mel_spectrogram(audio)
    print(f"✅ 预处理成功: {mel.shape}")
    
    print("")
    print("步骤 4: 模型编码（这一步最容易出错）...")
    # mel 可能已经是 Tensor 或 numpy array
    if isinstance(mel, torch.Tensor):
        mel_tensor = mel.unsqueeze(0)
    else:
        mel_tensor = torch.from_numpy(mel).unsqueeze(0)
    print(f"   输入形状: {mel_tensor.shape}")
    
    with torch.no_grad():
        encoded = model.encoder(mel_tensor)
    print(f"✅ 编码成功: {encoded.shape}")
    
    print("")
    print("步骤 5: 解码器初始化...")
    # 测试解码器
    decoder = model.decoder
    print("✅ 解码器可用")
    
    print("")
    print("⚠️  如果以上步骤都成功，问题可能在解码循环中")
    print("   建议：尝试使用更小的音频片段（10秒）或不同的解码参数")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    print("")
    print("💡 这可以帮助定位问题出现在哪个步骤")

