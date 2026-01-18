#!/bin/bash
# PDF 解析工具安装脚本
# 支持非交互模式：通过环境变量 PDF_PARSERS 指定要安装的后端
# 可选值：mineru, camelot, logics, all（默认：mineru）

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 检测操作系统类型
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # 检测 Linux 发行版
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# 检查并安装 ghostscript（Camelot 需要）
install_ghostscript() {
    echo -e "${YELLOW}🔍 检查 Ghostscript（Camelot 需要）...${NC}"
    
    # 检查是否已安装
    if command -v gs &> /dev/null; then
        GS_VERSION=$(gs --version 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✅ Ghostscript 已安装: $GS_VERSION${NC}"
        return 0
    fi
    
    # 根据操作系统安装
    OS=$(detect_os)
    case $OS in
        macos)
            echo -e "${YELLOW}📦 正在安装 Ghostscript（使用 Homebrew）...${NC}"
            if command -v brew &> /dev/null; then
                brew install ghostscript || {
                    echo -e "${RED}❌ Ghostscript 安装失败${NC}"
                    echo -e "${YELLOW}💡 提示: 请手动运行: brew install ghostscript${NC}"
                    return 1
                }
                echo -e "${GREEN}✅ Ghostscript 安装完成${NC}"
            else
                echo -e "${YELLOW}⚠️  未找到 Homebrew，请手动安装 Ghostscript${NC}"
                echo -e "   运行: brew install ghostscript"
                return 1
            fi
            ;;
        debian)
            echo -e "${YELLOW}📦 正在安装 Ghostscript（使用 apt）...${NC}"
            if command -v sudo &> /dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y ghostscript || {
                    echo -e "${RED}❌ Ghostscript 安装失败${NC}"
                    echo -e "${YELLOW}💡 提示: 请手动运行: sudo apt-get install ghostscript${NC}"
                    return 1
                }
                echo -e "${GREEN}✅ Ghostscript 安装完成${NC}"
            else
                echo -e "${YELLOW}⚠️  需要 sudo 权限安装 Ghostscript${NC}"
                echo -e "   运行: sudo apt-get install ghostscript"
                return 1
            fi
            ;;
        redhat)
            echo -e "${YELLOW}📦 正在安装 Ghostscript（使用 yum/dnf）...${NC}"
            if command -v sudo &> /dev/null; then
                if command -v dnf &> /dev/null; then
                    sudo dnf install -y ghostscript || {
                        echo -e "${RED}❌ Ghostscript 安装失败${NC}"
                        return 1
                    }
                else
                    sudo yum install -y ghostscript || {
                        echo -e "${RED}❌ Ghostscript 安装失败${NC}"
                        return 1
                    }
                fi
                echo -e "${GREEN}✅ Ghostscript 安装完成${NC}"
            else
                echo -e "${YELLOW}⚠️  需要 sudo 权限安装 Ghostscript${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  未识别的操作系统，请手动安装 Ghostscript${NC}"
            echo -e "   macOS: brew install ghostscript"
            echo -e "   Ubuntu/Debian: sudo apt-get install ghostscript"
            echo -e "   CentOS/RHEL: sudo yum install ghostscript"
            return 1
            ;;
    esac
}

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

# 非交互模式：从环境变量读取选择
if [ -n "$PDF_PARSERS" ]; then
    install_choice="$PDF_PARSERS"
else
    # 交互模式
    echo "=========================================="
    echo "PDF 解析工具安装脚本"
    echo "=========================================="
    echo ""
    echo "请选择要安装的后端："
    echo "1) MinerU（推荐，完全本地化，免费）"
    echo "2) Camelot（表格提取，免费）"
    echo "3) Logics-Parsing（阿里API，需密钥，高质量）"
    echo "4) 全部安装"
    read -p "请输入选项 (1-4): " install_choice
fi

# 根据选择安装
case $install_choice in
    1|mineru)
        echo -e "${YELLOW}📦 正在安装 MinerU...${NC}"
        pip install --quiet mineru 2>&1 | grep -v "ERROR:" || true
        echo -e "${GREEN}✅ MinerU 安装完成${NC}"
        ;;
    2|camelot)
        # 安装 ghostscript（Camelot 需要）
        install_ghostscript || echo -e "${YELLOW}⚠️  Ghostscript 安装失败，Camelot 可能无法正常工作${NC}"
        echo -e "${YELLOW}📦 正在安装 Camelot...${NC}"
        pip install --quiet "camelot-py[cv]" 2>&1 | grep -v "ERROR:" || true
        echo -e "${GREEN}✅ Camelot 安装完成${NC}"
        ;;
    3|logics)
        echo -e "${YELLOW}📦 正在安装 Logics-Parsing...${NC}"
        pip install --quiet logics-parsing 2>&1 | grep -v "ERROR:" || true
        echo -e "${GREEN}✅ Logics-Parsing 安装完成${NC}"
        echo -e "${YELLOW}⚠️  注意：Logics-Parsing 需要API密钥${NC}"
        echo -e "   请设置环境变量：export DASHSCOPE_API_KEY=\"your-api-key\""
        ;;
    4|all)
        # 安装 ghostscript（Camelot 需要）
        install_ghostscript || echo -e "${YELLOW}⚠️  Ghostscript 安装失败，Camelot 可能无法正常工作${NC}"
        echo -e "${YELLOW}📦 正在安装所有后端...${NC}"
        pip install --quiet mineru "camelot-py[cv]" logics-parsing 2>&1 | grep -v "ERROR:" || true
        echo -e "${GREEN}✅ 所有后端安装完成${NC}"
        echo -e "${YELLOW}⚠️  注意：Logics-Parsing 需要API密钥${NC}"
        echo -e "   请设置环境变量：export DASHSCOPE_API_KEY=\"your-api-key\""
        ;;
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

# 验证安装
echo -e "${YELLOW}🔍 验证安装...${NC}"
python << 'PYEOF'
import sys
backends = {}
try:
    import mineru
    backends["mineru"] = True
except ImportError:
    backends["mineru"] = False

try:
    import camelot
    backends["camelot"] = True
except ImportError:
    backends["camelot"] = False

try:
    import logics_parsing
    backends["logics"] = True
except ImportError:
    backends["logics"] = False

installed = [k for k, v in backends.items() if v]
if installed:
    print(f"✅ 已安装的后端: {', '.join(installed)}")
else:
    print("⚠️  未检测到已安装的后端")
PYEOF

echo -e "${GREEN}✅ PDF 解析工具安装完成${NC}"

