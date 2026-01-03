#!/bin/bash
# 启动前端 CLI

cd "$(dirname "$0")/.."
source venv/bin/activate
python -m frontend.main chat


