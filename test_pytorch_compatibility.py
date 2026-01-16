#!/usr/bin/env python3
"""验证 PyTorch 兼容性问题"""
import torch
import sys
import os

print("🔍 测试 1: PyTorch 基本功能")
print("=" * 60)

# 测试基本操作
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
if hasattr(torch.backends, 'mps'):
    print(f"MPS 可用: {torch.backends.mps.is_available()}")

# 测试基本张量操作
try:
    x = torch.randn(3, 3)
    y = torch.randn(3, 3)
    z = x + y
    print("✅ 基本张量操作正常")
except Exception as e:
    print(f"❌ 基本张量操作失败: {e}")
    sys.exit(1)

# 测试矩阵乘法
try:
    result = torch.matmul(x, y)
    print("✅ 矩阵乘法正常")
except Exception as e:
    print(f"❌ 矩阵乘法失败: {e}")
    sys.exit(1)

# 测试卷积操作（Whisper 会用到）
try:
    conv = torch.nn.Conv1d(1, 1, 3)
    input_tensor = torch.randn(1, 1, 10)
    output = conv(input_tensor)
    print("✅ 卷积操作正常")
except Exception as e:
    print(f"❌ 卷积操作失败: {e}")
    sys.exit(1)

print("")
print("✅ PyTorch 基本功能测试通过")
print("")



