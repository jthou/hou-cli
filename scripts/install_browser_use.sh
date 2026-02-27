#!/bin/bash
# 安装 browser-use（pip 包）
# 注意：browser 工具已暂时移除，安装后需在 requirements.txt 取消注释并在环境中设置 BROWSER_TOOL_ENABLED=true 方可使用。

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "$VIRTUAL_ENV" ] && [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo -e "${YELLOW}📦 激活项目虚拟环境...${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

echo -e "${YELLOW}📦 安装 browser-use（pip）...${NC}"
pip install "browser-use" --quiet

echo -e "${YELLOW}🔍 验证...${NC}"
python -c "
try:
    from browser_use import Agent, Browser
    print('✅ browser-use 已正确安装')
except ImportError as e:
    print(f'❌ 导入失败: {e}')
    exit(1)
"

echo -e "${GREEN}✅ browser-use 安装完成${NC}"
