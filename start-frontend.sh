#!/bin/bash
# 启动前端 CLI - 自动激活虚拟环境

cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 自动激活虚拟环境并启动前端
source venv/bin/activate
python -m frontend.main chat






