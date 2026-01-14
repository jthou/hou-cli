#!/bin/bash
# 安装视频下载工具的依赖（yt-dlp, you-get）
# 这些工具是 submodules，但可能需要安装 Python 依赖

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    # 尝试激活项目根目录下的 venv（如果存在）
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        echo -e "${YELLOW}📦 激活项目虚拟环境...${NC}"
        source "$PROJECT_ROOT/venv/bin/activate"
    else
        echo -e "${YELLOW}⚠️  警告: 未检测到虚拟环境，建议先激活虚拟环境${NC}"
    fi
fi

# 安装 yt-dlp（从本地源码，虽然 dependencies = []，但确保可以导入）
YT_DLP_DIR="$PROJECT_ROOT/backend/externals/yt-dlp"
if [ -d "$YT_DLP_DIR" ] && [ -f "$YT_DLP_DIR/pyproject.toml" ]; then
    echo -e "${YELLOW}📦 安装 yt-dlp（从本地源码）...${NC}"
    # yt-dlp 的 dependencies = []，但安装可以确保它在 Python 路径中
    pip install -e "$YT_DLP_DIR" --quiet 2>&1 | grep -v "ERROR:" || true
    
    # 验证安装
    python << 'PYEOF'
import sys
try:
    import yt_dlp
    print("✅ yt-dlp 已正确安装")
except ImportError as e:
    print(f"❌ yt-dlp 导入失败: {e}")
    sys.exit(1)
PYEOF
else
    echo -e "${YELLOW}⚠️  yt-dlp 目录不存在，跳过安装${NC}"
fi

# 安装 you-get（从本地源码，需要 dukpy 依赖）
YOU_GET_DIR="$PROJECT_ROOT/backend/externals/you-get"
if [ -d "$YOU_GET_DIR" ] && [ -f "$YOU_GET_DIR/setup.py" ]; then
    echo -e "${YELLOW}📦 安装 you-get（从本地源码）...${NC}"
    # you-get 需要 dukpy 依赖
    pip install -e "$YOU_GET_DIR" --quiet 2>&1 | grep -v "ERROR:" || true
    
    # 验证安装
    python << 'PYEOF'
import sys
try:
    import you_get
    print("✅ you-get 已正确安装")
except ImportError as e:
    print(f"❌ you-get 导入失败: {e}")
    sys.exit(1)
PYEOF
else
    echo -e "${YELLOW}⚠️  you-get 目录不存在，跳过安装${NC}"
fi

# 安装 browser-use（用于浏览器 cookies 提取）
BROWSER_USE_DIR="$PROJECT_ROOT/backend/externals/browser-use"
if [ -d "$BROWSER_USE_DIR" ] && [ -f "$BROWSER_USE_DIR/pyproject.toml" ]; then
    echo -e "${YELLOW}📦 安装 browser-use（从本地源码）...${NC}"
    pip install -e "$BROWSER_USE_DIR" --quiet 2>&1 | grep -v "ERROR:" | grep -v "WARNING:" || true
    echo -e "${GREEN}✅ browser-use 已安装${NC}"
fi

# bili23-downloader 是 GUI 应用，不需要安装（CLI 模式下会使用 yt-dlp）

echo -e "${GREEN}✅ 视频下载工具依赖安装完成${NC}"

