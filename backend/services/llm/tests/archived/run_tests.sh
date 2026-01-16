#!/bin/bash
# LLM 测试运行脚本 - 避免 ROS 插件冲突

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 临时移除 ROS 相关路径（如果存在）
if [ -n "$ROS_DISTRO" ]; then
    unset ROS_DISTRO
fi

# 运行 pytest，明确禁用 ROS 插件
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

