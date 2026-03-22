#!/usr/bin/env python3
"""
使用真实图像生成的漫画测试
"""

import asyncio
import os
import tempfile
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def test_real_comic_generation():
    """使用真实图像生成进行漫画测试"""
    print("=== 真实漫画生成测试 ===\n")

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
    test_content = """# 测试漫画 - 小猫历险记
## 场景1
在一个阳光明媚的早晨，小猫花花决定去花园探险。

## 场景2
花花遇到了一只美丽的蝴蝶，想要抓住它。

## 场景3
经过一番追逐，花花和蝴蝶成为了朋友。

## 场景4
从此以后，花花每天都会在花园里和蝴蝶玩耍。
"""

    print(f"漫画内容: {len(test_content)} 字符")

    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp(prefix="comic_real_test_"))
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

        print("\n开始执行漫画生成（这将需要较长时间，因为涉及真实的图像生成）...")

        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",  # 简洁画风
            "tone": "warm",         # 温暖基调
            "output_dir": str(output_dir),
            "llm_model": "qwen3-max"
        })

        print(f"\n执行结果: {'✅ 成功' if result.success else '❌ 失败'}")

        if result.success:
            print(f"数据: {result.data}")

            # 检查生成的文件
            pdf_files = list(output_dir.glob("*.pdf"))
            png_files = list(output_dir.glob("*.png"))

            print(f"PDF文件: {len(pdf_files)} 个")
            print(f"PNG文件: {len(png_files)} 个")

            if pdf_files:
                for pdf in pdf_files:
                    stat = pdf.stat()
                    print(f"  - {pdf.name} ({stat.st_size} 字节)")

                    # 检查PDF是否有效（简单的检查）
                    if stat.st_size > 1000:  # 至少1KB才可能是真正的PDF
                        print(f"    ✓ 可能是有效的PDF文件")
                    else:
                        print(f"    ⚠ 文件太小，可能无效")

            if png_files:
                for png in png_files:
                    stat = png.stat()
                    print(f"  - {png.name} ({stat.st_size} 字节)")

                    # 检查PNG是否有效
                    if stat.st_size > 100:  # 至少100字节才可能是真正的PNG
                        print(f"    ✓ 可能是有效的PNG文件")
                    else:
                        print(f"    ⚠ 文件太小，可能无效")
        else:
            print(f"❌ 错误: {result.error}")

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
    print("真实漫画生成功能测试")
    print("=" * 50)

    success = await test_real_comic_generation()

    print("\n" + "=" * 50)
    if success:
        print("🎉 漫画生成功能测试完成!")
        print("如果生成了有效大小的PDF/PNG文件，则漫画生成功能工作正常")
    else:
        print("⚠️  漫画生成功能测试失败")

if __name__ == "__main__":
    asyncio.run(main())