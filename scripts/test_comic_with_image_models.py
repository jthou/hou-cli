#!/usr/bin/env python3
"""
使用专业图像生成模型的漫画生成测试
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def test_comic_with_image_models():
    """使用专业图像生成模型测试漫画生成"""
    print("=== 使用专业图像生成模型的漫画测试 ===\n")

    # 检查API密钥
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('BAILIAN_API_KEY')

    if not dashscope_key:
        print("错误: 没有配置 DASHSCOPE_API_KEY 或 BAILIAN_API_KEY")
        return False

    print(f"✓ 检测到图像API密钥")

    # 检查端口4000是否在运行
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 4000))
    if result != 0:
        print("❌ LiteLLM代理未在端口4000运行")
        sock.close()
        return False
    else:
        print("✓ LiteLLM代理在端口4000运行")
    sock.close()

    # 准备测试内容
    test_content = """# 测试漫画
## 场景1
一只可爱的小猫坐在窗边。

## 场景2
小猫决定去花园里探险。

## 场景3
小猫遇到了一只蝴蝶。
"""

    # 尝试使用不同的图像生成模型
    image_models = [
        "Qwen-Image-Max",      # 高质量图像生成
        "Qwen-Image-2.0-Pro",  # 专业图像生成
        "Qwen-Image-Plus",     # 增强图像生成
        "Z-Image-Turbo",       # 快速图像生成
    ]

    print(f"漫画内容: {len(test_content)} 字符")
    print(f"尝试的图像生成模型: {', '.join(image_models)}")

    # 导入漫画技能
    from backend.core.agent.skills.comic.skill import ComicSkill

    # 保存原始环境变量
    orig_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_anthropic_base = os.environ.get('ANTHROPIC_BASE_URL')
    orig_anthropic_model = os.environ.get('ANTHROPIC_MODEL')

    try:
        # 配置环境使用LiteLLM代理
        os.environ['ANTHROPIC_API_KEY'] = 'sk-litellm-comic'
        os.environ['ANTHROPIC_BASE_URL'] = 'http://localhost:4000'

        skill = ComicSkill()

        # 尝试使用不同的图像生成模型
        for model in image_models:
            print(f"\n--- 测试模型: {model} ---")

            # 设置当前模型
            os.environ['ANTHROPIC_MODEL'] = model
            print(f"使用模型: {model}")

            # 创建输出目录
            output_dir = ROOT / "outputs" / f"comic-test-{model.lower().replace('-', '')}"
            output_dir.mkdir(parents=True, exist_ok=True)

            try:
                result = await skill.execute({
                    "source": test_content,
                    "art": "ligne-claire",
                    "tone": "warm",
                    "output_dir": str(output_dir),
                    "llm_model": model
                })

                print(f"执行结果: {'✅ 成功' if result.success else '❌ 失败'}")

                if result.success and result.data:
                    pdf_files = result.data.get("pdf_files", [])
                    print(f"生成的PDF文件: {len(pdf_files)} 个")

                    # 检查文件是否存在且有合理大小
                    for pdf_path in pdf_files:
                        pdf_file = Path(pdf_path)
                        if pdf_file.exists():
                            size = pdf_file.stat().st_size
                            print(f"  - {pdf_file.name}: {size:,} 字节")

                            # 检查是否为真正的PDF
                            with open(pdf_file, 'rb') as f:
                                header = f.read(8)
                                if header.startswith(b'%PDF-'):
                                    print(f"    ✓ 真正的PDF文件")
                                else:
                                    print(f"    ⚠ 可能不是真正的PDF")
                        else:
                            print(f"  - 文件不存在: {pdf_path}")

                    if len(pdf_files) > 0:
                        print(f"🎉 模型 {model} 可能成功生成了漫画！")
                        return True  # 成功了就返回
                else:
                    print(f"  错误: {result.error[:100] if result.error else '未知错误'}")

            except Exception as e:
                print(f"  异常: {e}")
                continue  # 尝试下一个模型

        print("\n尝试了所有图像生成模型，但都没有成功生成漫画。")
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
    print("使用专业图像生成模型的漫画测试")
    print("=" * 50)
    print("这次将使用您推荐的百炼专业图像生成模型:")
    print("- Qwen-Image-Max: 高质量图像生成")
    print("- Qwen-Image-2.0-Pro: 专业图像生成")
    print("- Qwen-Image-Plus: 增强图像生成")
    print("- Z-Image-Turbo: 快速图像生成")
    print("=" * 50)

    success = await test_comic_with_image_models()

    print(f"\n{'🎉 漫画生成测试完成!' if success else '⚠️  漫画生成测试未完全成功'}")

    if success:
        print("漫画功能应该已经修复了！")
    else:
        print("可能需要进一步调试或检查API权限。")

if __name__ == "__main__":
    asyncio.run(main())