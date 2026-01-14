#!/bin/bash
# 安装 browser-use（从本地源码）
# browser-use 是 submodule，需要安装到 venv

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROWSER_USE_DIR="$PROJECT_ROOT/backend/externals/browser-use"

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

# 检查 browser-use 目录是否存在
if [ ! -d "$BROWSER_USE_DIR" ] || [ ! -f "$BROWSER_USE_DIR/pyproject.toml" ]; then
    echo -e "${YELLOW}⚠️  browser-use 目录不存在，尝试初始化 git submodules...${NC}"
    cd "$PROJECT_ROOT"
    if [ -f ".gitmodules" ]; then
        git submodule update --init --recursive backend/externals/browser-use 2>/dev/null || {
            echo -e "${RED}❌ 无法初始化 browser-use submodule${NC}"
            exit 1
        }
    else
        echo -e "${RED}❌ browser-use 目录不存在且无法初始化 submodule${NC}"
        exit 1
    fi
fi

# 安装 browser-use
echo -e "${YELLOW}📦 安装 browser-use（从本地源码）...${NC}"
if pip install -e "$BROWSER_USE_DIR" --quiet 2>&1 | grep -v "ERROR:" | grep -v "WARNING:"; then
    echo -e "${GREEN}✅ browser-use 已安装${NC}"
else
    # 即使有警告也继续
    echo -e "${GREEN}✅ browser-use 安装完成（可能有警告，但不影响使用）${NC}"
fi

# 验证安装
echo -e "${YELLOW}🔍 验证 browser-use 安装...${NC}"
python << 'PYEOF'
import sys
try:
    import browser_use
    print("✅ browser-use 已正确安装")
    print(f"   版本: {getattr(browser_use, '__version__', 'unknown')}")
except ImportError as e:
    print(f"❌ browser-use 导入失败: {e}")
    sys.exit(1)
PYEOF

echo -e "${GREEN}✅ browser-use 安装完成${NC}"

