#!/bin/bash
# 启动后端服务

cd "$(dirname "$0")/.."
source venv/bin/activate
python -m backend.main






