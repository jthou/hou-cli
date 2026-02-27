#!/bin/bash
# 安装系统 FFmpeg（本仓库不再使用 backend/externals/ffmpeg 子模块）
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt install ffmpeg

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✅ FFmpeg 已安装${NC}"
    ffmpeg -version | head -1
    exit 0
fi

echo -e "${YELLOW}正在安装 FFmpeg...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
        brew install ffmpeg
        echo -e "${GREEN}✅ FFmpeg 安装完成${NC}"
    else
        echo -e "${RED}请先安装 Homebrew: https://brew.sh${NC}"
        echo "或手动安装: brew install ffmpeg"
        exit 1
    fi
elif [[ -f /etc/debian_version ]] || command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y ffmpeg
    echo -e "${GREEN}✅ FFmpeg 安装完成${NC}"
else
    echo -e "${YELLOW}请手动安装 FFmpeg：${NC}"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    exit 1
fi
