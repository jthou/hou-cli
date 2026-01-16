#!/usr/bin/env python3
"""测试 Whisper 模型加载"""
import sys
import os
sys.path.insert(0, '.')
import whisper
import torch

print("🔍 测试 2: Whisper 模型加载")
print("=" * 60)

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

try:
    print("加载 tiny 模型...")
    model = whisper.load_model("tiny")
    print("✅ 模型加载成功")
    
    # 检查模型结构
    print(f"模型类型: {type(model)}")
    print(f"模型设备: {next(model.parameters()).device}")
    
    # 测试模型前向传播（不处理音频）
    print("测试模型前向传播（使用随机输入）...")
    dummy_input = torch.randn(1, 80, 3000)  # 模拟音频特征
    try:
        with torch.no_grad():
            # 只测试编码器部分
            encoder = model.encoder
            encoded = encoder(dummy_input)
        print("✅ 模型前向传播正常")
        print(f"   编码输出形状: {encoded.shape}")
    except Exception as e:
        print(f"❌ 模型前向传播失败: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    import traceback
    traceback.print_exc()



