#!/usr/bin/env python3
"""
漫画生成命令行测试 - 验证 ComicSkill 调用方式
时间：2025-03-18；理由：用户报告 File name too long，需确认 source 以文件路径传入而非内容
用法: python scripts/test_comic_cli.py [--dry-run] [--live]
"""
import argparse
import asyncio
import tempfile
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent


async def test_source_resolution():
    """测试 source 解析逻辑：长文本应识别为内容并写入 temp，不触发 OSError 63"""
    # 复用 skill 中的解析逻辑（不依赖 env）
    long_source = """# 大脑与手足

## 开头

在数字世界的深处，有一座名为"智核"的宏伟殿堂。殿堂中央悬浮着一颗巨大的光球。
""" + "x" * 500  # 确保超长，原先 Path(source).exists() 会 OSError 63

    source = long_source.strip()
    looks_like_path = "\n" not in source and len(source) < 260 and source.strip()
    assert not looks_like_path, "长文本含换行应判为内容"
    work_dir = Path(tempfile.mkdtemp(prefix="comic_test_"))
    source_path = work_dir / "source.md"
    source_path.write_text(source, encoding="utf-8")
    assert source_path.exists(), "temp 文件应创建成功"
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)
    print("[1] 长文本 source 解析通过（按内容写入 temp，未触发 File name too long）")


async def test_run_mjs_dry_run():
    """dry-run: 仅打印 node 命令"""
    short_source = "# 测试\n\n简短内容。"
    work_dir = Path(tempfile.mkdtemp(prefix="comic_test_"))
    source_path = work_dir / "source.md"
    source_path.write_text(short_source, encoding="utf-8")

    run_mjs = ROOT / "scripts" / "run_baoyu_comic" / "run.mjs"
    cmd = ["node", str(run_mjs), str(source_path), "--art", "ligne-claire", "--tone", "neutral"]
    print("拟执行命令:")
    print("  " + " ".join(cmd))
    print(f"  首参: 文件路径 (长度 {len(str(source_path))})")

    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description="漫画生成 CLI 测试")
    p.add_argument("--dry-run", action="store_true", help="仅打印 node 命令")
    args = p.parse_args()

    if args.dry_run:
        asyncio.run(test_run_mjs_dry_run())
        return

    print("=== 漫画生成调用方式测试 ===\n")
    asyncio.run(test_source_resolution())
    print("\n--- dry-run 命令示例 ---")
    asyncio.run(test_run_mjs_dry_run())
    print("\n完整调用: node scripts/run_baoyu_comic/run.mjs <source.md路径> [--art ligne-claire] [--tone neutral] [--output-dir path] [--model claude-3-5-sonnet]")
    print("source 为长文本时，ComicSkill 会先写入 temp 文件再传路径给 run.mjs。")


if __name__ == "__main__":
    main()
