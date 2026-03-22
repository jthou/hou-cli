#!/usr/bin/env python3
"""
使用修正后的模型进行漫画生成测试
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def test_comic_with_correct_models():
    """使用正确的百炼模型进行漫画生成"""
    print("=== 使用正确模型的漫画生成测试 ===\n")

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
    test_content = """# 小猫探险记
## 场景1
一只名叫小白的猫咪坐在窗台上，望着外面的花园。

## 场景2
小白决定跳下去探索花园，看到了美丽的花朵。

## 场景3
小白遇到了一只友善的小鸟，它们成为了朋友。
"""

    # 试试百炼上支持多模态的模型
    models = [
        "qwen3-max",        # 主推的多模态模型
        "qwen-plus-2025-12-01",  # 支持多模态的增强版
    ]

    print(f"漫画内容: {len(test_content)} 字符")
    print(f"尝试的多模态模型: {', '.join(models)}")

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

        # 尝试使用正确的模型
        for model in models:
            print(f"\n--- 测试模型: {model} ---")

            # 设置当前模型
            os.environ['ANTHROPIC_MODEL'] = model
            print(f"使用模型: {model}")

            # 创建输出目录
            output_dir = ROOT / "outputs" / f"comic-final-test-{model.replace('-', '')}"
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

                                    # 读取PDF内容的一小部分来确认
                                    f.seek(0)
                                    content = f.read(100)
                                    if b'/XObject' in content or b'/Image' in content:
                                        print(f"    🎉 包含图像内容！")

                                    print(f"    🎉 漫画生成成功！")
                                    return True  # 成功了就返回
                                else:
                                    print(f"    ⚠ 可能不是真正的PDF")
                        else:
                            print(f"  - 文件不存在: {pdf_path}")

                    if len(pdf_files) > 0:
                        print(f"🎉 模型 {model} 可能成功生成了漫画！")
                        return True  # 成功了就返回
                else:
                    print(f"  错误: {result.error[:200] if result.error else '无错误信息'}")

            except Exception as e:
                print(f"  异常: {e}")
                import traceback
                traceback.print_exc()
                continue  # 尝试下一个模型

        print("\n尝试了所有多模态模型，但都没有成功生成漫画。")
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
    print("使用正确模型的漫画生成测试")
    print("=" * 50)
    print("这次将使用百炼支持多模态的模型:")
    print("- qwen3-max: 百炼主推的多模态模型")
    print("- qwen-plus-2025-12-01: 支持多模态的增强版")
    print("=" * 50)

    success = await test_comic_with_correct_models()

    print(f"\n{'🎉 漫画生成测试完成!' if success else '⚠️  漫画生成测试未完全成功'}")

    if success:
        print("漫画功能应该已经成功生成了！")
    else:
        print("可能需要进一步检查API权限或模型配置。")

if __name__ == "__main__":
    asyncio.run(main())