#!/bin/bash
# Tools 测试运行脚本 - 解决 ROS 插件冲突

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检测并使用虚拟环境（如果存在）
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    echo "✅ 检测到虚拟环境，使用 venv/bin/python"
    PYTHON_CMD="venv/bin/python"
elif [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    echo "✅ 检测到虚拟环境，使用 .venv/bin/python"
    PYTHON_CMD=".venv/bin/python"
else
    echo "⚠️  未检测到虚拟环境，使用系统 python3"
    echo "   建议：创建虚拟环境: python3 -m venv venv && source venv/bin/activate"
    PYTHON_CMD="python3"
fi

# 临时移除 ROS 相关环境变量（如果存在）
if [ -n "$ROS_DISTRO" ]; then
    unset ROS_DISTRO
fi

# 从 PYTHONPATH 中移除 ROS 路径（更彻底的方法）
CLEAN_PYTHONPATH=""
IFS=':' read -ra ADDR <<< "$PYTHONPATH"
for i in "${ADDR[@]}"; do
    if [[ ! "$i" =~ ros ]] && [[ ! "$i" =~ /opt/ros ]]; then
        if [ -z "$CLEAN_PYTHONPATH" ]; then
            CLEAN_PYTHONPATH="$i"
        else
            CLEAN_PYTHONPATH="$CLEAN_PYTHONPATH:$i"
        fi
    fi
done

# 设置清理后的 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$CLEAN_PYTHONPATH"

# 使用 Python 包装脚本运行 pytest，在导入 pytest 之前移除 ROS 路径
$PYTHON_CMD << 'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

# 在导入 pytest 之前，从 sys.path 中移除 ROS 路径
ros_paths_to_remove = []
for path in sys.path[:]:
    path_lower = path.lower()
    if 'ros' in path_lower and ('opt' in path_lower or 'site-packages' in path_lower):
        if 'launch_testing' in path_lower or 'colcon' in path_lower or 'ament' in path_lower:
            ros_paths_to_remove.append(path)

for path in ros_paths_to_remove:
    if path in sys.path:
        sys.path.remove(path)
        print(f"已移除 ROS 路径: {path}", file=sys.stderr)

# 现在导入 pytest
import pytest

# 运行 pytest
if __name__ == "__main__":
    import sys
    pytest_args = [
        "backend/core/agent/tools/tests/",
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
PYTHON_SCRIPT

