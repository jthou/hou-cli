#!/bin/bash
# 检查并安装 browser-use 相关依赖

set -e

cd "$(dirname "$0")/.."

# 检查 browser-use 是否已安装
check_browser_use() {
    python3 -c "import browser_use" 2>/dev/null && return 0 || return 1
}

# 检查 playwright 是否已安装
check_playwright() {
    python3 -c "import playwright" 2>/dev/null && return 0 || return 1
}

# 检查 langchain-openai 是否已安装
check_langchain_openai() {
    python3 -c "import langchain_openai" 2>/dev/null && return 0 || return 1
}

# 检查 playwright 浏览器是否已安装
check_playwright_browser() {
    python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>/dev/null && return 0 || return 1
}

# 安装依赖
install_deps() {
    echo "📦 检测到 browser-use 相关依赖未安装，正在自动安装..."
    echo ""
    
    # 检查是否有 requirements.txt
    if [ -f "requirements.txt" ]; then
        echo "📥 从 requirements.txt 安装依赖..."
        # 忽略依赖冲突警告（这些通常不会影响功能）
        pip install -q -r requirements.txt 2>&1 | grep -v "dependency conflicts" || true
    else
        echo "📥 安装 browser-use 和相关依赖..."
        pip install -q browser-use>=0.2.7 langchain-openai>=0.3.21 playwright>=1.40.0 2>&1 | grep -v "dependency conflicts" || true
        pip install -q "langchain>=0.3.25" "langchain-core>=0.3.64" "langchain-ollama>=0.3.3" 2>&1 | grep -v "dependency conflicts" || true
        pip install -q "anyio>=4.9.0" "python-dotenv>=1.0.1" 2>&1 | grep -v "dependency conflicts" || true
    fi
    
    # 验证安装
    if check_browser_use && check_playwright && check_langchain_openai; then
        echo "✅ 依赖安装完成"
    else
        echo "⚠️  依赖安装可能不完整，请检查错误信息"
    fi
    echo ""
}

# 安装 playwright 浏览器
install_playwright_browser() {
    echo "🌐 检测到 playwright 浏览器未安装，正在安装..."
    python3 -m playwright install chromium 2>/dev/null || {
        echo "⚠️  自动安装 playwright 浏览器失败，请手动运行: playwright install chromium"
        return 1
    }
    echo "✅ Playwright 浏览器安装完成"
    echo ""
}

# 主逻辑
main() {
    NEED_INSTALL=false
    VERBOSE=${1:-false}  # 第一个参数控制是否显示详细信息
    
    # 检查依赖
    if ! check_browser_use || ! check_playwright || ! check_langchain_openai; then
        NEED_INSTALL=true
    fi
    
    # 如果需要安装依赖
    if [ "$NEED_INSTALL" = true ]; then
        install_deps
    elif [ "$VERBOSE" = "true" ]; then
        echo "✅ browser-use 相关依赖已安装"
    fi
    
    # 检查 playwright 浏览器
    if ! check_playwright_browser; then
        install_playwright_browser
    elif [ "$VERBOSE" = "true" ]; then
        echo "✅ Playwright 浏览器已安装"
    fi
}

# 如果直接运行此脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

