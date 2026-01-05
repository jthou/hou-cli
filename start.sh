#!/bin/bash
# 一键启动脚本 - 自动激活虚拟环境并启动后端（后台）

cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 自动激活虚拟环境
source venv/bin/activate

# 启动后端（后台）
python cli.py start

echo ""
echo "💡 提示:"
echo "   - 后端已在后台运行"
echo "   - 启动前端: ./start-frontend.sh"
echo "   - 停止后端: ./stop.sh"
echo "   - 查看状态: python cli.py status"
