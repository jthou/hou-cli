#!/bin/bash
# 编译 FFmpeg（如果需要）
# 这个脚本会检查 FFmpeg 是否已编译，如果没有则自动编译

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FFMPEG_DIR="$PROJECT_ROOT/backend/externals/ffmpeg"
FFMPEG_BUILD_BIN="$FFMPEG_DIR/build/bin/ffmpeg"

# 检查 FFmpeg 是否需要重新编译
NEED_REBUILD=false
if [ -f "$FFMPEG_BUILD_BIN" ]; then
    # 检查源码是否已更新
    cd "$FFMPEG_DIR"
    CURRENT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "")
    BUILD_HASH=$(cat build/.git_hash 2>/dev/null || echo "")
    
    if [ -n "$CURRENT_HASH" ] && [ "$CURRENT_HASH" != "$BUILD_HASH" ]; then
        echo -e "${YELLOW}🔄 FFmpeg 源码已更新，需要重新编译${NC}"
        echo "   当前版本: $CURRENT_HASH"
        echo "   构建版本: $BUILD_HASH"
        NEED_REBUILD=true
    else
        echo -e "${GREEN}✅ FFmpeg 已编译且为最新版本${NC}"
        exit 0
    fi
    cd "$PROJECT_ROOT"
else
    NEED_REBUILD=true
fi

# 检查 FFmpeg 目录是否存在
if [ ! -d "$FFMPEG_DIR" ] || [ ! -f "$FFMPEG_DIR/configure" ]; then
    echo -e "${YELLOW}⚠️  FFmpeg 目录不存在，尝试初始化 git submodules...${NC}"
    cd "$PROJECT_ROOT"
    if [ -f ".gitmodules" ]; then
        git submodule update --init --recursive backend/externals/ffmpeg 2>/dev/null || {
            echo -e "${RED}❌ 无法初始化 FFmpeg submodule${NC}"
            exit 1
        }
    else
        echo -e "${YELLOW}⚠️  FFmpeg 目录不存在且无法初始化 submodule，跳过编译${NC}"
        exit 0
    fi
fi

# 开始编译
echo -e "${YELLOW}🔨 开始编译 FFmpeg（这可能需要一些时间）...${NC}"
cd "$FFMPEG_DIR"

# 检查 nasm（x86 汇编优化需要）
HAS_NASM=false
if command -v nasm &> /dev/null; then
    NASM_VERSION=$(nasm -v 2>&1 | head -1)
    echo "   检测到 nasm: $NASM_VERSION"
    HAS_NASM=true
else
    echo "   ⚠️  未找到 nasm，将使用 --disable-x86asm（性能可能略低）"
    echo "   💡 提示: 如果需要更好的性能，可以安装 nasm: sudo apt install nasm"
fi

# 如果需要重新编译，先清理
if [ "$NEED_REBUILD" = true ] && [ -f "config.mak" ]; then
    echo "   清理旧的编译文件..."
    make clean 2>/dev/null || true
fi

# 检查是否已配置
if [ ! -f "config.mak" ] || [ "$NEED_REBUILD" = true ]; then
    echo "   配置 FFmpeg..."
    CONFIGURE_OPTS="--prefix=$(pwd)/build --enable-shared --disable-static --enable-gpl --enable-version3 --enable-nonfree"
    if [ "$HAS_NASM" = false ]; then
        CONFIGURE_OPTS="$CONFIGURE_OPTS --disable-x86asm"
    fi
    
    if ! ./configure $CONFIGURE_OPTS 2>&1 | tee /tmp/ffmpeg_configure.log | grep -v "ERROR:"; then
        echo -e "${RED}❌ FFmpeg 配置失败，请查看 /tmp/ffmpeg_configure.log${NC}"
        cd "$PROJECT_ROOT"
        exit 1
    fi
    echo -e "${GREEN}✅ FFmpeg 配置成功${NC}"
fi

# 编译（使用多核）
# 检测 CPU 核心数（兼容 macOS 和 Linux）
if command -v nproc &> /dev/null; then
    CORES=$(nproc)
elif command -v sysctl &> /dev/null; then
    CORES=$(sysctl -n hw.ncpu)
else
    CORES=4  # 默认值
fi
echo "   编译 FFmpeg（使用 $CORES 个核心）..."
if ! make -j$CORES 2>&1 | tee /tmp/ffmpeg_make.log | grep -v "ERROR:"; then
    echo -e "${RED}❌ FFmpeg 编译失败，请查看 /tmp/ffmpeg_make.log${NC}"
    cd "$PROJECT_ROOT"
    exit 1
fi

# 安装
echo "   安装 FFmpeg..."
if ! make install 2>&1 | grep -v "ERROR:"; then
    echo -e "${YELLOW}⚠️  FFmpeg 安装可能有问题${NC}"
fi

cd "$PROJECT_ROOT"

# 验证编译结果
if [ -f "$FFMPEG_BUILD_BIN" ]; then
    echo -e "${GREEN}✅ FFmpeg 编译完成${NC}"
    "$FFMPEG_BUILD_BIN" -version | head -1
    
    # 保存构建版本信息
    cd "$FFMPEG_DIR"
    git rev-parse HEAD > build/.git_hash 2>/dev/null || true
    cd "$PROJECT_ROOT"
else
    echo -e "${RED}❌ FFmpeg 编译失败，二进制文件不存在${NC}"
    exit 1
fi

