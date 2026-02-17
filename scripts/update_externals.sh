#!/bin/bash
# 更新所有外部依赖（git submodules）
# 这个脚本会更新所有 submodules 到最新版本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${YELLOW}🔄 更新所有外部依赖（git submodules）...${NC}"

cd "$PROJECT_ROOT"

# 初始化 submodules（如果还没有初始化）
if [ -f ".gitmodules" ]; then
    echo "   初始化 submodules..."
    git submodule init 2>/dev/null || true
    git submodule update --init --recursive 2>/dev/null || true
fi

# 更新所有 submodules 到最新版本
echo "   更新 submodules 到最新版本..."
if git submodule update --remote --merge 2>&1 | grep -E "(更新|更新|Fast-forward|Already up to date)"; then
    echo -e "${GREEN}✅ Submodules 更新完成${NC}"
else
    echo -e "${GREEN}✅ Submodules 更新完成（可能没有更新）${NC}"
fi

# 显示更新状态
echo ""
echo -e "${YELLOW}📊 Submodules 状态：${NC}"
git submodule status

echo -e "${GREEN}✅ 外部依赖更新完成${NC}"








