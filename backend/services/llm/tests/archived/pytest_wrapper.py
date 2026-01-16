#!/usr/bin/env python3
"""Pytest 包装器 - 在导入 pytest 之前移除 ROS 插件路径"""
import sys
import os
from pathlib import Path

# 在导入任何其他模块之前，移除 ROS 相关路径
ros_paths_to_remove = []
for path in sys.path[:]:  # 使用切片复制，避免迭代时修改
    if 'ros' in path.lower() and ('opt' in path or 'site-packages' in path):
        if 'launch_testing' in path or 'colcon' in path or 'ament' in path:
            ros_paths_to_remove.append(path)

for path in ros_paths_to_remove:
    if path in sys.path:
        sys.path.remove(path)
        print(f"已移除 ROS 路径: {path}", file=sys.stderr)

# 加载 .env 文件
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)

# 现在导入 pytest
import pytest

# 运行 pytest
if __name__ == "__main__":
    # pytest 参数
    pytest_args = [
        "backend/services/llm/tests/",
        "-v",
        "-p", "no:launch_testing",
        "-p", "no:launch_testing_ros_pytest_entrypoint",
        "-p", "no:colcon_core",
        "-p", "no:ament_lint",
        "-p", "no:ament_xmllint",
        "-p", "no:ament_pep257",
        "-p", "no:ament_copyright",
        "-p", "no:ament_flake8",
    ]
    
    # 添加用户提供的参数
    pytest_args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(pytest_args))

