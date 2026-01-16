#!/bin/bash
# 使用 pytest 运行测试 - 解决 ROS 插件冲突

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 临时移除 ROS 相关环境变量（如果存在）
if [ -n "$ROS_DISTRO" ]; then
    unset ROS_DISTRO
fi

# 从 PYTHONPATH 中移除 ROS 路径
export PYTHONPATH=$(echo "$PYTHONPATH" | tr ':' '\n' | grep -v ros | tr '\n' ':')

# 运行 pytest，明确禁用 ROS 插件，但保留 pytest-asyncio
python3 -m pytest \
    backend/services/llm/tests/ \
    -v \
    -p no:launch_testing \
    -p no:launch_testing_ros_pytest_entrypoint \
    -p no:colcon_core \
    -p no:ament_lint \
    -p no:ament_xmllint \
    -p no:ament_pep257 \
    -p no:ament_copyright \
    -p no:ament_flake8 \
    --ignore-glob="**/launch_testing_ros_pytest_entrypoint.py" \
    "$@"

