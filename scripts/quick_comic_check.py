#!/usr/bin/env python3
"""
轻量级漫画生成测试 - 用于验证API配置
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def quick_test():
    """快速测试漫画生成API配置"""
    print("=== 快速漫画API配置测试 ===\n")

    # 检查必要的配置
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('BAILIAN_API_KEY')

    if not dashscope_key:
        print("❌ 未配置 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY")
        return False

    print(f"✓ 发现图像API密钥 (长度: {len(dashscope_key)})")

    # 检查.baoyu-skills/.env文件
    baoyu_env_path = ROOT / ".baoyu-skills" / ".env"
    if baoyu_env_path.exists():
        print("✓ .baoyu-skills/.env 文件存在")
        content = baoyu_env_path.read_text()
        has_image_key = 'DASHSCOPE_API_KEY' in content or 'BAILIAN_API_KEY' in content
        print(f"{'✓' if has_image_key else '⚠'} .baoyu-skills/.env 包含图像API密钥")
    else:
        print("⚠ .baoyu-skills/.env 文件不存在")

    # 检查端口4000是否在运行
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 4000))
    if result == 0:
        print("✓ LiteLLM代理在端口4000运行")
    else:
        print("❌ LiteLLM代理未在端口4000运行")
    sock.close()

    print("\n=== 配置状态总结 ===")
    all_good = all([
        dashscope_key,
        baoyu_env_path.exists(),
        'DASHSCOPE_API_KEY' in baoyu_env_path.read_text() if baoyu_env_path.exists() else False,
        result == 0,  # LiteLLM running
    ])

    if all_good:
        print("🎉 所有配置看起来都已正确设置！")
        print("\n现在可以尝试运行完整的漫画生成了。")
        return True
    else:
        print("⚠ 有些配置可能还需要调整。")
        return False

async def main():
    success = await quick_test()

    if success:
        print("\n" + "="*50)
        print("建议的下一步：")
        print("1. 使用简短的文本进行漫画生成测试")
        print("2. 监控生成过程的日志输出")
        print("3. 检查最终生成的文件是否为真正的图像")

if __name__ == "__main__":
    asyncio.run(main())