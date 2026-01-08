#!/bin/bash
# 运行测试脚本，临时清除 PYTHONPATH 以避免 ROS 插件干扰

cd "$(dirname "$0")"
source venv/bin/activate

# 临时清除 PYTHONPATH
unset PYTHONPATH

# 运行 pytest
python -m pytest "$@"
