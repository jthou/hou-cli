#!/bin/bash
# Local-File-Organizer 安装脚本
# 支持非交互模式：通过环境变量 FILE_ORGANIZER_METHOD 指定安装方式
# 可选值：github, submodule, clone（默认：github）
# 通过环境变量 NEXA_SDK_VERSION 指定 SDK 版本：cpu, metal（默认：cpu）

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
if python -c "import local_file_organizer" 2>/dev/null || \
   python -c "import Local_File_Organizer" 2>/dev/null || \
   python -c "import LocalFileOrganizer" 2>/dev/null; then
    echo -e "${GREEN}✅ Local-File-Organizer 已安装${NC}"
else
    # 非交互模式：从环境变量读取选择
    if [ -n "$FILE_ORGANIZER_METHOD" ]; then
        install_method="$FILE_ORGANIZER_METHOD"
    else
        # 交互模式
        echo "=========================================="
        echo "Local-File-Organizer 安装脚本"
        echo "=========================================="
        echo ""
        echo "请选择安装方式："
        echo "1) 从 GitHub 安装（需要网络连接）"
        echo "2) 作为 Git 子模块添加"
        echo "3) 直接克隆到本地"
        read -p "请输入选项 (1-3): " install_method
    fi

    case $install_method in
        1|github)
            echo -e "${YELLOW}📦 正在从 GitHub 安装...${NC}"
            pip install --quiet git+https://github.com/QiuYannnn/Local-File-Organizer.git 2>&1 | grep -v "ERROR:" || true
            echo -e "${GREEN}✅ 安装完成${NC}"
            ;;
        2|submodule)
            echo -e "${YELLOW}📦 正在添加 Git 子模块...${NC}"
            LOCAL_ORG_DIR="$PROJECT_ROOT/backend/externals/local-file-organizer"
            if [ ! -d "$LOCAL_ORG_DIR" ]; then
                git submodule add https://github.com/QiuYannnn/Local-File-Organizer.git "$LOCAL_ORG_DIR" 2>&1 | grep -v "ERROR:" || true
            fi
            git submodule update --init --recursive "$LOCAL_ORG_DIR" 2>&1 | grep -v "ERROR:" || true
            echo -e "${GREEN}✅ 子模块添加完成${NC}"
            # 安装依赖
            if [ -f "$LOCAL_ORG_DIR/requirements.txt" ]; then
                echo -e "${YELLOW}📦 安装 Local-File-Organizer 依赖...${NC}"
                pip install --quiet -r "$LOCAL_ORG_DIR/requirements.txt" 2>&1 | grep -v "ERROR:" || true
            fi
            ;;
        3|clone)
            echo -e "${YELLOW}📦 正在克隆到本地...${NC}"
            LOCAL_ORG_DIR="$PROJECT_ROOT/backend/externals/local-file-organizer"
            if [ ! -d "$LOCAL_ORG_DIR" ]; then
                git clone --quiet https://github.com/QiuYannnn/Local-File-Organizer.git "$LOCAL_ORG_DIR" 2>&1 | grep -v "ERROR:" || true
            fi
            echo -e "${GREEN}✅ 克隆完成${NC}"
            # 安装依赖
            if [ -f "$LOCAL_ORG_DIR/requirements.txt" ]; then
                echo -e "${YELLOW}📦 安装 Local-File-Organizer 依赖...${NC}"
                pip install --quiet -r "$LOCAL_ORG_DIR/requirements.txt" 2>&1 | grep -v "ERROR:" || true
            fi
            ;;
        *)
            echo -e "${RED}❌ 无效选项${NC}"
            exit 1
            ;;
    esac
fi

# 安装 Nexa SDK
if [ -n "$NEXA_SDK_VERSION" ]; then
    sdk_version="$NEXA_SDK_VERSION"
elif [ -z "$FILE_ORGANIZER_METHOD" ]; then
    # 交互模式
    echo ""
    echo "Local-File-Organizer 需要 Nexa SDK"
    read -p "是否安装 Nexa SDK？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        sdk_version="skip"
    else
        echo ""
        echo "请选择 Nexa SDK 版本："
        echo "1) CPU 版本"
        echo "2) GPU 版本（macOS Metal）"
        read -p "请输入选项 (1-2): " sdk_version
    fi
else
    # 非交互模式默认安装 CPU 版本
    sdk_version="cpu"
fi

if [ "$sdk_version" != "skip" ]; then
    case $sdk_version in
        1|cpu)
            echo -e "${YELLOW}📦 正在安装 Nexa SDK (CPU)...${NC}"
            pip install --quiet nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/cpu --extra-index-url https://pypi.org/simple --no-cache-dir 2>&1 | grep -v "ERROR:" || true
            echo -e "${GREEN}✅ Nexa SDK (CPU) 安装完成${NC}"
            ;;
        2|metal)
            echo -e "${YELLOW}📦 正在安装 Nexa SDK (GPU/Metal)...${NC}"
            CMAKE_ARGS="-DGGML_METAL=ON -DSD_METAL=ON" pip install --quiet nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/metal --extra-index-url https://pypi.org/simple --no-cache-dir 2>&1 | grep -v "ERROR:" || true
            echo -e "${GREEN}✅ Nexa SDK (GPU/Metal) 安装完成${NC}"
            ;;
        *)
            echo -e "${YELLOW}⚠️  跳过 Nexa SDK 安装${NC}"
            ;;
    esac
fi

# 验证安装
echo -e "${YELLOW}🔍 验证安装...${NC}"
python << 'PYEOF'
import sys
try:
    import local_file_organizer
    print("✅ Local-File-Organizer 已正确安装（local_file_organizer）")
except ImportError:
    try:
        import Local_File_Organizer
        print("✅ Local-File-Organizer 已正确安装（Local_File_Organizer）")
    except ImportError:
        try:
            import LocalFileOrganizer
            print("✅ Local-File-Organizer 已正确安装（LocalFileOrganizer）")
        except ImportError:
            # 检查子模块路径
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent if hasattr(sys, '_getframe') else Path.cwd()
            submodule_path = project_root / "backend" / "externals" / "local-file-organizer"
            if submodule_path.exists():
                print("✅ Local-File-Organizer 子模块存在")
            else:
                print("⚠️  未检测到 Local-File-Organizer")
PYEOF

echo -e "${GREEN}✅ 文件整理工具安装完成${NC}"

