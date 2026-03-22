#!/usr/bin/env python3
"""
最终漫画生成测试 - 一次性完成漫画生成
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

async def final_comic_test():
    """最终的漫画生成测试"""
    print("=== 最终漫画生成测试 ===\n")

    # 导入漫画技能
    from backend.core.agent.skills.comic.skill import ComicSkill

    # 设置环境变量以使用百炼模型
    orig_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_anthropic_base = os.environ.get('ANTHROPIC_BASE_URL')
    orig_anthropic_model = os.environ.get('ANTHROPIC_MODEL')

    # 配置百炼环境
    os.environ['ANTHROPIC_API_KEY'] = 'sk-litellm-comic'
    os.environ['ANTHROPIC_BASE_URL'] = 'http://localhost:4000'
    os.environ['ANTHROPIC_MODEL'] = 'qwen3-max'

    # 创建测试内容
    test_content = """# 小猫的冒险
## 场景1
小猫咪咪看到窗外有只蝴蝶。

## 场景2
咪咪决定去追蝴蝶。

## 场景3
咪咪和蝴蝶成了朋友。
"""

    # 输出目录
    output_dir = ROOT / "outputs" / "final-comic-test"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("开始漫画生成...")
        print("内容:", test_content.replace('\n', ' ')[:100] + "...")

        skill = ComicSkill()

        # 使用更简化的参数进行测试
        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",
            "tone": "warm",
            "output_dir": str(output_dir),
            "llm_model": "qwen3-max"
        })

        print(f"\n执行结果: {'✅ 成功' if result.success else '❌ 失败'}")

        if result.success:
            print(f"结果数据: {result.data}")

            # 验证生成的文件
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"- {file_path.relative_to(output_dir)}: {size} 字节")

                    # 检查文件类型
                    if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.pdf']:
                        with open(file_path, 'rb') as f:
                            header = f.read(16)

                        if file_path.suffix.lower() == '.pdf':
                            is_pdf = header.startswith(b'%PDF-')
                            print(f"  {'✓' if is_pdf else '⚠'} 真正的PDF" if is_pdf else "  ⚠ 文本PDF")
                        elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                            is_img = (header.startswith(b'\x89PNG') or
                                     header.startswith(b'\xff\xd8\xff') or
                                     header.startswith(b'\x89\x50\x4e\x47'))
                            print(f"  {'✓' if is_img else '⚠'} 真正的图像文件" if is_img else "  ⚠ 文本图像文件")
        else:
            print(f"❌ 错误: {result.error}")

        return result.success

    except Exception as e:
        print(f"❌ 异常: {e}")
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
    print("开始最终漫画生成测试...\n")

    success = await final_comic_test()

    print(f"\n{'🎉 测试完成!' if success else '⚠ 测试完成但可能有问题'}")

    if success:
        print("\n如果成功生成了真正的PDF和PNG文件，漫画功能就已修复！")

if __name__ == "__main__":
    asyncio.run(main())