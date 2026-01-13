#!/bin/bash
# 安装 Whisper 及其依赖
# 这个脚本会安装 Whisper 从本地源码，并预下载常用模型

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="$PROJECT_ROOT/backend/externals/whisper"

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

# 检查 Whisper 目录是否存在
if [ ! -d "$WHISPER_DIR" ] || [ ! -f "$WHISPER_DIR/pyproject.toml" ]; then
    echo -e "${YELLOW}⚠️  Whisper 目录不存在，尝试初始化 git submodules...${NC}"
    cd "$PROJECT_ROOT"
    if [ -f ".gitmodules" ]; then
        git submodule update --init --recursive backend/externals/whisper 2>/dev/null || {
            echo -e "${RED}❌ 无法初始化 Whisper submodule${NC}"
            exit 1
        }
    else
        echo -e "${RED}❌ Whisper 目录不存在且无法初始化 submodule${NC}"
        exit 1
    fi
fi

# 安装 Whisper
echo -e "${YELLOW}📦 安装 Whisper（这可能需要一些时间，下载 PyTorch 等依赖）...${NC}"

# 先安装基础依赖，避免依赖冲突
pip install --quiet setuptools wheel pyyaml 2>&1 | grep -v "ERROR:" || true

# 安装 Whisper（从本地源码）
if pip install -e "$WHISPER_DIR" --quiet 2>&1 | grep -v "ERROR:" | grep -v "WARNING:"; then
    echo -e "${GREEN}✅ Whisper 已安装${NC}"
else
    # 即使有警告也继续
    echo -e "${GREEN}✅ Whisper 安装完成（可能有警告，但不影响使用）${NC}"
fi

# 验证安装
echo -e "${YELLOW}🔍 验证 Whisper 安装...${NC}"
python << 'PYEOF'
import sys
try:
    import whisper
    import torch
    print("✅ Whisper 和 PyTorch 已正确安装")
    print(f"   PyTorch 版本: {torch.__version__}")
    print(f"   Python 路径: {sys.executable}")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)
PYEOF

# 可选：预下载常用模型（base 和 small）
if [ "$1" = "--download-models" ]; then
    echo -e "${YELLOW}📥 预下载 Whisper 模型（base 和 small）...${NC}"
    python << 'PYEOF'
import sys
try:
    import whisper
    models_to_download = ['base', 'small']
    for model_name in models_to_download:
        try:
            print(f"   下载模型: {model_name}...")
            model = whisper.load_model(model_name, download_root=None)
            print(f"   ✅ {model_name} 模型已下载")
        except Exception as e:
            print(f"   ⚠️  {model_name} 模型下载失败: {str(e)[:100]}")
except ImportError:
    print("   ⚠️  Whisper 未安装，跳过模型下载")
PYEOF
fi

echo -e "${GREEN}✅ Whisper 安装完成${NC}"

