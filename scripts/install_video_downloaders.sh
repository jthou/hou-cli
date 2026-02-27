#!/bin/bash
# 安装视频下载工具依赖（yt-dlp, you-get）— 使用 pip，不再使用 externals 子模块

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "$VIRTUAL_ENV" ] && [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo -e "${YELLOW}📦 激活项目虚拟环境...${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

echo -e "${YELLOW}📦 安装 yt-dlp、you-get...${NC}"
pip install yt-dlp you-get --quiet

echo -e "${YELLOW}🔍 验证...${NC}"
python -c "
import sys
try:
    import yt_dlp
    print('✅ yt-dlp 已安装')
except ImportError as e:
    print(f'❌ yt-dlp: {e}')
    sys.exit(1)
try:
    import you_get
    print('✅ you-get 已安装')
except ImportError as e:
    print(f'❌ you-get: {e}')
    sys.exit(1)
"

echo -e "${GREEN}✅ 视频下载工具依赖安装完成${NC}"
