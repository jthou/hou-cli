#!/usr/bin/env python3
"""
最终的漫画生成尝试
"""

import asyncio
import os
import time
from pathlib import Path
import sys

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def monitor_comic_generation():
    """监控漫画生成过程"""
    print("=== 监控漫画生成过程 ===\n")

    # 准备测试内容
    test_content = """# 小猫探险记
## 场景1
一只名叫小白的猫咪坐在窗台上，望着外面的花园。

## 场景2
小白决定跳下去探索花园，看到了美丽的花朵。

## 场景3
小白遇到了一只友善的小鸟，它们成为了朋友。
"""

    # 写入临时文件
    temp_file = "/tmp/simple_comic_test.md"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print("临时文件已创建:", temp_file)
    print("内容长度:", len(test_content), "字符")

    # 检查端口
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

    # 在后台运行漫画生成命令
    import subprocess
    cmd = [
        "node", "scripts/run_baoyu_comic/run.mjs",
        temp_file,
        "--art", "ligne-claire",
        "--tone", "warm",
        "--model", "qwen3-max"
    ]

    print("运行命令:", " ".join(cmd))

    # 执行命令
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("漫画生成已启动，PID:", process.pid)

    # 持续监控comic目录
    comic_dir = ROOT / "comic"
    start_time = time.time()
    max_wait = 300  # 5分钟最大等待时间

    while time.time() - start_time < max_wait:
        # 检查进程是否还在运行
        if process.poll() is not None:
            print(f"\n进程已结束，退出码: {process.returncode}")
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout[:500] if stdout else "无输出")
            print("STDERR:", stderr[:500] if stderr else "无错误")

            if process.returncode == 0:
                print("✅ 命令执行成功")
            else:
                print("❌ 命令执行失败")
                break

        # 检查comic目录
        if comic_dir.exists():
            print(f"\n✓ 发现comic目录: {comic_dir}")
            files = list(comic_dir.rglob('*'))
            print(f"目录内容: {len(files)} 个项目")
            for file in files[:10]:  # 显示前10个文件
                if file.is_file():
                    size = file.stat().st_size
                    print(f"  - {file.relative_to(comic_dir)}: {size:,} 字节")
                    if file.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
                        print(f"    🎉 发现图像文件: {file.name}")

            # 如果找到了图像文件，就成功了
            image_files = [f for f in files if f.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']]
            if image_files:
                print(f"\n🎉 成功生成了 {len(image_files)} 个图像文件！")
                return True

        time.sleep(5)  # 等待5秒后再次检查

    # 超时
    if process.poll() is None:
        print(f"\n⏰ 超时({max_wait}秒)，终止进程...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    return False

if __name__ == "__main__":
    print("启动漫画生成监控...")
    success = monitor_comic_generation()

    if success:
        print("\n🎉 漫画生成监控完成 - 成功检测到图像文件！")
    else:
        print("\n⚠️  漫画生成监控完成 - 未检测到图像文件")