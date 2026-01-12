#!/bin/bash
# 安装 Jupyter 相关依赖
# 这个脚本会安装 jupyter-client 和 ipykernel

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

# 检查是否已安装
if python -c "import jupyter_client, ipykernel" 2>/dev/null; then
    echo -e "${GREEN}✅ Jupyter 依赖已安装${NC}"
else
    # 安装 Jupyter 依赖
    echo -e "${YELLOW}📦 安装 Jupyter 相关依赖...${NC}"
    # 安装 jupyter-client 和 ipykernel
    pip install --quiet jupyter-client>=8.6.0 ipykernel>=6.25.0 2>&1 | grep -v "ERROR:" || true
fi

# 验证安装
echo -e "${YELLOW}🔍 验证 Jupyter 安装...${NC}"
python << 'PYEOF'
import sys
try:
    import jupyter_client
    import ipykernel
    print("✅ Jupyter 客户端和 IPython kernel 已正确安装")
    print(f"   jupyter-client 版本: {jupyter_client.__version__}")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)
PYEOF

# 注册 IPython kernel（可选，但建议执行）
echo -e "${YELLOW}📝 注册 IPython kernel...${NC}"
python -m ipykernel install --user --name python3 --display-name "Python 3" 2>&1 | grep -v "ERROR:" || {
    echo -e "${YELLOW}⚠️  Kernel 注册失败，但不影响使用（kernel 会在运行时自动创建）${NC}"
}

echo -e "${GREEN}✅ Jupyter 安装完成${NC}"

