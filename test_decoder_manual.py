#!/usr/bin/env python3
"""手动测试解码器步骤"""
import sys
import os
sys.path.insert(0, '.')
import whisper
import torch

print("🔍 测试: 手动执行解码步骤")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

audio_file = '/Users/jintinghou/Downloads/罗永浩-萤石_audio_test_30s.m4a'

try:
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    # 加载和预处理音频
    import whisper.audio as audio_module
    audio = audio_module.load_audio(audio_file)
    mel = audio_module.log_mel_spectrogram(audio)
    
    # 转换为 tensor
    if isinstance(mel, torch.Tensor):
        mel_tensor = mel.unsqueeze(0)
    else:
        mel_tensor = torch.from_numpy(mel).unsqueeze(0)
    
    print("")
    print("步骤 1: 编码器...")
    with torch.no_grad():
        encoded = model.encoder(mel_tensor)
    print(f"✅ 编码成功: {encoded.shape}")
    
    print("")
    print("步骤 2: 测试解码器（单个 token）...")
    decoder = model.decoder
    # 创建初始 token
    tokens = torch.tensor([[50258]])  # <|startoftranscript|>
    
    with torch.no_grad():
        # 测试解码器的前向传播
        try:
            # 需要创建位置编码等
            n_audio_ctx = encoded.shape[1]
            kv_cache = None
            offset = 0
            
            # 调用解码器
            decoded = decoder(tokens, encoded, kv_cache=kv_cache, offset=offset)
            print("✅ 解码器单步成功")
            print(f"   输出形状: {decoded.shape}")
        except Exception as e:
            print(f"❌ 解码器单步失败: {e}")
            import traceback
            traceback.print_exc()
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()



