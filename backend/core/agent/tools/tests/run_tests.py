#!/usr/bin/env python3
"""
Tools 测试运行脚本 - 解决 ROS 插件冲突

使用方法：
    python3 backend/core/agent/tools/tests/run_tests.py
    或
    python3 backend/core/agent/tools/tests/run_tests.py -k "test_tool_initialization"
"""
import sys
import os
from pathlib import Path

# 在导入 pytest 之前，从 sys.path 中移除 ROS 路径
# 需要更彻底地移除，包括所有包含 ROS 的路径
ros_paths_to_remove = []
for path in sys.path[:]:
    path_lower = str(path).lower()
    # 检查是否是 ROS 相关路径
    if ('/opt/ros' in path_lower or 
        'ros' in path_lower and ('site-packages' in path_lower or 'dist-packages' in path_lower)):
        # 检查是否包含 ROS 相关插件
        if any(keyword in path_lower for keyword in ['launch_testing', 'colcon', 'ament', 'ros']):
            ros_paths_to_remove.append(path)

# 移除 ROS 路径
for path in ros_paths_to_remove:
    if path in sys.path:
        sys.path.remove(path)
        print(f"已移除 ROS 路径: {path}", file=sys.stderr)

# 同时从环境变量中移除
if 'PYTHONPATH' in os.environ:
    pythonpath_parts = os.environ['PYTHONPATH'].split(':')
    cleaned_parts = [p for p in pythonpath_parts if not any(
        keyword in p.lower() for keyword in ['/opt/ros', 'ros'] if keyword in p.lower()
    )]
    os.environ['PYTHONPATH'] = ':'.join(cleaned_parts)

# 添加项目根目录到路径
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 切换到项目根目录
os.chdir(project_root)

from shared.load_env import load_env
load_env(project_root)

# 现在导入 pytest
import pytest

# 运行 pytest
if __name__ == "__main__":
    # 使用绝对路径
    tests_dir = current_file.parent
    pytest_args = [
        str(tests_dir),
        "-v",
        "-p", "no:launch_testing",
        "-p", "no:launch_testing_ros_pytest_entrypoint",
        "-p", "no:colcon_core",
        "-p", "no:ament_lint",
        "-p", "no:ament_xmllint",
        "-p", "no:ament_pep257",
        "-p", "no:ament_copyright",
        "-p", "no:ament_flake8",
        "--ignore-glob=**/launch_testing_ros_pytest_entrypoint.py",
    ]
    
    # 添加用户提供的参数
    pytest_args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(pytest_args))

