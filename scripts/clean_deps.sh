#!/bin/bash
# 清理所有安装的依赖
# 这个脚本会删除虚拟环境、编译的 FFmpeg、Whisper 模型等

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${YELLOW}🧹 开始清理依赖...${NC}"
echo ""

# 1. 删除虚拟环境
VENV_DIR="$PROJECT_ROOT/venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 删除虚拟环境...${NC}"
    rm -rf "$VENV_DIR"
    echo -e "${GREEN}✅ 虚拟环境已删除${NC}"
else
    echo -e "${YELLOW}⚠️  虚拟环境不存在，跳过${NC}"
fi

# 2. 删除编译的 FFmpeg
FFMPEG_BUILD_DIR="$PROJECT_ROOT/backend/externals/ffmpeg/build"
if [ -d "$FFMPEG_BUILD_DIR" ]; then
    echo -e "${YELLOW}🎬 删除编译的 FFmpeg...${NC}"
    rm -rf "$FFMPEG_BUILD_DIR"
    echo -e "${GREEN}✅ FFmpeg 构建目录已删除${NC}"
else
    echo -e "${YELLOW}⚠️  FFmpeg 构建目录不存在，跳过${NC}"
fi

# 3. 删除 Whisper 模型缓存
# Whisper 模型通常存储在 ~/.cache/whisper 或 XDG_CACHE_HOME/whisper
WHISPER_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/whisper"
if [ -d "$WHISPER_CACHE_DIR" ]; then
    echo -e "${YELLOW}🎤 删除 Whisper 模型缓存...${NC}"
    rm -rf "$WHISPER_CACHE_DIR"
    echo -e "${GREEN}✅ Whisper 模型缓存已删除${NC}"
else
    echo -e "${YELLOW}⚠️  Whisper 模型缓存不存在，跳过${NC}"
fi

# 4. 删除 Jupyter kernel（如果已注册）
if command -v jupyter >/dev/null 2>&1; then
    echo -e "${YELLOW}📓 删除 Jupyter kernel...${NC}"
    jupyter kernelspec list 2>/dev/null | grep -q python3 && \
        jupyter kernelspec remove -f python3 2>/dev/null || true
    echo -e "${GREEN}✅ Jupyter kernel 已删除${NC}"
else
    echo -e "${YELLOW}⚠️  Jupyter 未安装，跳过 kernel 删除${NC}"
fi

# 5. 删除 Playwright 浏览器（如果已安装）
PLAYWRIGHT_BROWSERS_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/ms-playwright"
if [ -d "$PLAYWRIGHT_BROWSERS_DIR" ]; then
    echo -e "${YELLOW}🌐 删除 Playwright 浏览器...${NC}"
    rm -rf "$PLAYWRIGHT_BROWSERS_DIR"
    echo -e "${GREEN}✅ Playwright 浏览器已删除${NC}"
else
    echo -e "${YELLOW}⚠️  Playwright 浏览器不存在，跳过${NC}"
fi

# 6. 删除 Python 缓存文件（__pycache__, *.pyc）
echo -e "${YELLOW}🐍 清理 Python 缓存文件...${NC}"
find "$PROJECT_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✅ Python 缓存文件已清理${NC}"

# 7. 删除构建文件
echo -e "${YELLOW}🔨 清理构建文件...${NC}"
rm -rf "$PROJECT_ROOT/build" 2>/dev/null || true
rm -rf "$PROJECT_ROOT/dist" 2>/dev/null || true
rm -rf "$PROJECT_ROOT"/*.egg-info 2>/dev/null || true
echo -e "${GREEN}✅ 构建文件已清理${NC}"

echo ""
echo -e "${GREEN}✅ 所有依赖清理完成！${NC}"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "   - 运行 'make install' 或 'make install-dev' 重新安装依赖"
echo "   - 虚拟环境需要重新创建：python3 -m venv venv"

