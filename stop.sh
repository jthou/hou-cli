#!/bin/bash
# 停止后端服务脚本

cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在"
    exit 1
fi

# 激活虚拟环境并停止后端
source venv/bin/activate
python cli.py stop






