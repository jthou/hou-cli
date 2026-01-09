#!/bin/bash
# Local-File-Organizer 安装脚本

set -e

echo "=========================================="
echo "Local-File-Organizer 安装脚本"
echo "=========================================="

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  警告：未检测到虚拟环境"
    echo "请先激活虚拟环境：source venv/bin/activate"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 选择安装方式
echo ""
echo "请选择安装方式："
echo "1) 从 GitHub 安装（需要网络连接）"
echo "2) 作为 Git 子模块添加"
echo "3) 直接克隆到本地"
read -p "请输入选项 (1-3): " install_method

case $install_method in
    1)
        echo ""
        echo "正在从 GitHub 安装..."
        pip install git+https://github.com/QiuYannnn/Local-File-Organizer.git
        echo "✅ 安装完成"
        ;;
    2)
        echo ""
        echo "正在添加 Git 子模块..."
        git submodule add https://github.com/QiuYannnn/Local-File-Organizer.git backend/externals/local-file-organizer
        git submodule update --init --recursive backend/externals/local-file-organizer
        echo "✅ 子模块添加完成"
        echo ""
        echo "⚠️  注意：还需要安装 Local-File-Organizer 的依赖"
        echo "请执行：cd backend/externals/local-file-organizer && pip install -r requirements.txt"
        ;;
    3)
        echo ""
        echo "正在克隆到本地..."
        git clone https://github.com/QiuYannnn/Local-File-Organizer.git backend/externals/local-file-organizer
        echo "✅ 克隆完成"
        echo ""
        echo "⚠️  注意：还需要安装 Local-File-Organizer 的依赖"
        echo "请执行：cd backend/externals/local-file-organizer && pip install -r requirements.txt"
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 询问是否安装 Nexa SDK
echo ""
echo "Local-File-Organizer 需要 Nexa SDK"
read -p "是否安装 Nexa SDK？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "请选择 Nexa SDK 版本："
    echo "1) CPU 版本"
    echo "2) GPU 版本（macOS Metal）"
    read -p "请输入选项 (1-2): " sdk_version
    
    case $sdk_version in
        1)
            echo ""
            echo "正在安装 Nexa SDK (CPU)..."
            pip install nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/cpu --extra-index-url https://pypi.org/simple --no-cache-dir
            echo "✅ Nexa SDK (CPU) 安装完成"
            ;;
        2)
            echo ""
            echo "正在安装 Nexa SDK (GPU/Metal)..."
            CMAKE_ARGS="-DGGML_METAL=ON -DSD_METAL=ON" pip install nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/metal --extra-index-url https://pypi.org/simple --no-cache-dir
            echo "✅ Nexa SDK (GPU/Metal) 安装完成"
            ;;
        *)
            echo "❌ 无效选项，跳过 Nexa SDK 安装"
            ;;
    esac
fi

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 重启应用以加载文件整理工具"
echo "2. 查看日志确认工具已注册：'File organizer tool registered successfully'"
echo "3. 运行测试：pytest backend/core/agent/tools/tests/test_file_organizer_tool.py -v"
echo ""
echo "详细文档：docs/tools/file-organizer-setup.md"

