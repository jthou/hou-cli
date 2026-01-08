#!/bin/bash
# 启动后端服务

cd "$(dirname "$0")/.."
source venv/bin/activate

# 自动检查并安装 browser-use 依赖
bash scripts/check_browser_deps.sh

# 启动后端
python -m backend.main








