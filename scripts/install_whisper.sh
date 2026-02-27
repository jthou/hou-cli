#!/bin/bash
# 安装 Whisper（pip 包 openai-whisper，不再使用 backend/externals/whisper 子模块）

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

echo -e "${YELLOW}📦 安装 Whisper（openai-whisper）及依赖...${NC}"
pip install openai-whisper --quiet

echo -e "${YELLOW}🔍 验证...${NC}"
python -c "
try:
    import whisper
    import torch
    print('✅ Whisper 和 PyTorch 已正确安装')
    print(f'   PyTorch: {torch.__version__}')
except ImportError as e:
    print(f'❌ 导入失败: {e}')
    exit(1)
"

if [ "$1" = "--download-models" ]; then
    echo -e "${YELLOW}📥 预下载模型（base, small）...${NC}"
    python -c "
import whisper
for name in ['base', 'small']:
    try:
        whisper.load_model(name)
        print(f'   ✅ {name}')
    except Exception as e:
        print(f'   ⚠️  {name}: {e}')
"
fi

echo -e "${GREEN}✅ Whisper 安装完成${NC}"
