#!/bin/bash
# 一键启动前后端（后端后台，前端交互式）

cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 自动激活虚拟环境
source venv/bin/activate

echo "🚀 启动后端服务（后台）..."
python cli.py start

echo ""
echo "🚀 启动前端 CLI..."
echo ""

# 启动前端（交互式）
python -m frontend.main chat


