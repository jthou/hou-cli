#!/usr/bin/env python3
"""
漫画生成功能验证测试 - 使用百炼模型
"""

import asyncio
import os
import tempfile
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def test_simple_comic_generation():
    """使用百炼模型测试简单的漫画生成"""
    print("=== 百炼模型漫画生成测试 ===\n")

    # 检查API密钥
    if not os.environ.get('BAILIAN_API_KEY') and not os.environ.get('DASHSCOPE_API_KEY'):
        print("错误: 没有配置 BAILIAN_API_KEY 或 DASHSCOPE_API_KEY")
        return False

    print("✓ 检测到 BAILIAN_API_KEY 或 DASHSCOPE_API_KEY")

    # 检查端口4000是否在运行
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 4000))
    if result != 0:
        print("❌ LiteLLM代理未在端口4000运行")
        print("请先启动代理: python scripts/start_litellm_comic_proxy.py")
        sock.close()
        return False
    else:
        print("✓ LiteLLM代理在端口4000运行")
    sock.close()

    # 准备测试数据
    test_content = """# 测试漫画 - 简单故事
## 场景1
从前，有一只小猫。

## 场景2
小猫决定去探险。

## 场景3
它遇到了一只友好的小狗。

## 场景4
它们成为了好朋友。
"""

    print(f"漫画内容: {len(test_content)} 字符")

    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp(prefix="comic_test_"))
    print(f"输出目录: {output_dir}")

    # 导入漫画技能
    from backend.core.agent.skills.comic.skill import ComicSkill

    # 设置环境变量以使用百炼模型
    orig_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_anthropic_base = os.environ.get('ANTHROPIC_BASE_URL')
    orig_anthropic_model = os.environ.get('ANTHROPIC_MODEL')

    try:
        # 配置百炼环境
        os.environ['ANTHROPIC_API_KEY'] = 'sk-litellm-comic'  # 任意值，由LiteLLM代理处理
        os.environ['ANTHROPIC_BASE_URL'] = 'http://localhost:4000'
        os.environ['ANTHROPIC_MODEL'] = 'qwen3-max'

        print(f"使用模型: qwen3-max")
        print(f"API基础URL: http://localhost:4000")

        # 创建技能实例并执行
        skill = ComicSkill()

        print("\n开始执行漫画生成...")
        print("(注意: 这可能需要几分钟，因为涉及API调用和图像生成)")

        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",  # 简洁画风
            "tone": "neutral",      # 中性基调
            "output_dir": str(output_dir),
            "llm_model": "qwen3-max"
        })

        print(f"\n执行结果: {'✅ 成功' if result.success else '❌ 失败'}")

        if result.success:
            print(f"数据: {result.data}")
            if result.data and result.data.get("pdf_files"):
                print(f"✅ 生成了 {len(result.data['pdf_files'])} 个PDF文件")
                for pdf in result.data["pdf_files"]:
                    print(f"  - {pdf}")
            else:
                print("⚠️  执行成功但没有生成PDF文件")
                print("这可能表示API调用成功，但图像生成部分存在问题")
        else:
            print(f"❌ 错误: {result.error}")

            # 特别检查是否是API权限问题
            error_lower = result.error.lower() if result.error else ""
            if "permission" in error_lower or "access" in error_lower:
                print("💡 这可能是API密钥权限问题 - 百炼API可能需要特殊权限才能进行图像生成")
            elif "timeout" in error_lower:
                print("💡 这可能是超时问题 - 检查网络连接或增加超时时间")
            elif "400" in error_lower or "500" in error_lower:
                print("💡 这可能是HTTP错误 - 检查LiteLLM代理配置或模型支持")

        return result.success

    except Exception as e:
        print(f"❌ 执行过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 恢复环境变量
        if orig_anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = orig_anthropic_key
        else:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        if orig_anthropic_base:
            os.environ['ANTHROPIC_BASE_URL'] = orig_anthropic_base
        else:
            os.environ.pop('ANTHROPIC_BASE_URL', None)
        if orig_anthropic_model:
            os.environ['ANTHROPIC_MODEL'] = orig_anthropic_model
        else:
            os.environ.pop('ANTHROPIC_MODEL', None)

async def main():
    print("漫画生成功能验证测试 - 百炼模型")
    print("=" * 50)

    success = await test_simple_comic_generation()

    print("\n" + "=" * 50)
    if success:
        print("🎉 漫画生成功能验证成功!")
        print("✅ 百炼模型可以正常工作")
    else:
        print("⚠️  漫画生成功能验证失败")
        print("可能的原因:")
        print("  1. API密钥权限不足（可能不支持图像生成）")
        print("  2. LiteLLM代理配置问题")
        print("  3. 网络连接问题")
        print("  4. 模型本身不支持漫画生成所需的图像能力")

if __name__ == "__main__":
    asyncio.run(main())