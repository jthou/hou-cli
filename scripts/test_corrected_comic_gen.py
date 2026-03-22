#!/usr/bin/env python3
"""
修正版漫画生成脚本 - 确保正确的API密钥配置和图像生成
"""

import asyncio
import os
import tempfile
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def test_correct_comic_generation():
    """使用正确配置进行漫画生成测试"""
    print("=== 修正版漫画生成测试 ===\n")

    # 检查API密钥 - 确保图像API密钥配置正确
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('BAILIAN_API_KEY')

    if not dashscope_key:
        print("错误: 没有配置 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY")
        return False

    print(f"✓ 检测到图像API密钥 (长度: {len(dashscope_key)})")

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

    # 确保.baoyu-skills/.env文件存在且包含图像API密钥
    baoyu_env_path = ROOT / ".baoyu-skills" / ".env"
    if not baoyu_env_path.exists():
        print(f"❌ {baoyu_env_path} 不存在")
        # 创建文件
        baoyu_env_path.parent.mkdir(parents=True, exist_ok=True)
        baoyu_env_path.write_text(f"DASHSCOPE_API_KEY={dashscope_key}\n")
        print(f"✓ 已创建 {baoyu_env_path}")
    else:
        content = baoyu_env_path.read_text()
        if 'DASHSCOPE_API_KEY' not in content and 'BAILIAN_API_KEY' not in content:
            with open(baoyu_env_path, 'a') as f:
                f.write(f"DASHSCOPE_API_KEY={dashscope_key}\n")
            print(f"✓ 已向 {baoyu_env_path} 添加图像API密钥")

    # 准备测试数据 - 简短的漫画内容以加快测试
    test_content = """# 简单漫画测试
## 场景1
一只小猫看着窗外。

## 场景2
小猫决定出去玩耍。

## 场景3
小猫开心地在花园里奔跑。
"""

    print(f"漫画内容: {len(test_content)} 字符")

    # 创建输出目录
    output_dir = ROOT / "outputs" / "corrected-comic-test"
    output_dir.mkdir(parents=True, exist_ok=True)
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

        print("\n开始执行漫画生成（这次应该调用真正的图像生成）...")
        print("注意：由于这是真实的图像生成，可能需要几分钟时间")

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

            # 检查生成的文件
            pdf_files = list(output_dir.glob("*.pdf"))
            png_files = list(output_dir.glob("*.png"))

            print(f"\n生成的文件统计:")
            print(f"PDF文件: {len(pdf_files)} 个")
            print(f"PNG文件: {len(png_files)} 个")

            total_png_size = 0
            total_pdf_size = 0

            for pdf in pdf_files:
                stat = pdf.stat()
                total_pdf_size += stat.st_size
                print(f"  - {pdf.name} ({stat.st_size:,} 字节)")

                # 检查是否为真正的PDF
                with open(pdf, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF-'):
                        print(f"    ✓ 真正的PDF文件")
                    else:
                        print(f"    ⚠ 可能不是真正的PDF文件")

            for png in png_files:
                stat = png.stat()
                total_png_size += stat.st_size
                print(f"  - {png.name} ({stat.st_size:,} 字节)")

                # 检查是否为真正的PNG
                with open(png, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'\x89PNG\r\n\x1a\n'):
                        print(f"    ✓ 真正的PNG文件")
                    else:
                        print(f"    ⚠ 可能不是真正的PNG文件")

            print(f"\n总PDF大小: {total_pdf_size:,} 字节")
            print(f"总PNG大小: {total_png_size:,} 字节")

            if total_png_size > 10000:  # 如果PNG文件总大小超过10KB，可能是真正的图像
                print(f"✓ 看起来成功生成了真正的图像文件！")
            else:
                print(f"⚠ 图像文件总大小较小，可能仍然生成的是占位符")
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
    print("修正版漫画生成功能测试")
    print("=" * 60)
    print("这次测试将会:")
    print("1. 确保.baoyu-skills/.env包含图像API密钥")
    print("2. 使用真实图像生成API")
    print("3. 验证生成的是真正的PDF和PNG文件")
    print("=" * 60)

    success = await test_correct_comic_generation()

    print("\n" + "=" * 60)
    if success:
        print("🎉 漫画生成功能测试完成!")
        print("请检查生成的文件是否为真正的图像文件")
    else:
        print("⚠️  漫画生成功能测试失败")

        print("\n可能的问题:")
        print("- API密钥可能没有图像生成功能权限")
        print("- 百炼/DashScope服务暂时不可用")
        print("- 图像生成模型配置不正确")
        print("- LiteLLM代理配置有问题")

if __name__ == "__main__":
    asyncio.run(main())