#!/usr/bin/env python3
"""简单的测试运行器 - 避免 ROS 插件冲突"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 在导入 pytest 之前，移除 ROS 插件路径
ros_paths_to_remove = []
for path in sys.path:
    if 'ros' in path.lower() and ('opt' in path or 'site-packages' in path):
        if 'launch_testing' in path or 'colcon' in path:
            ros_paths_to_remove.append(path)

for path in ros_paths_to_remove:
    if path in sys.path:
        sys.path.remove(path)

# 加载 .env 文件
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ 已加载 .env 文件: {env_path}\n")
else:
    load_dotenv()

# 添加项目根目录到路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 现在导入 pytest
import pytest

# 运行测试
if __name__ == "__main__":
    # 禁用 ROS 插件
    pytest_args = [
        "backend/services/llm/tests/",
        "-v",
        "-p", "no:launch_testing",
        "-p", "no:launch_testing_ros_pytest_entrypoint",
        "-p", "no:colcon_core",
    ]
    
    # 添加用户提供的参数
    pytest_args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(pytest_args))

