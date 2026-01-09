#!/bin/bash
# PDF 解析工具安装脚本

set -e

echo "=========================================="
echo "PDF 解析工具安装脚本"
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

echo ""
echo "请选择要安装的后端："
echo "1) MinerU（推荐，完全本地化，免费）"
echo "2) Camelot（表格提取，免费）"
echo "3) Logics-Parsing（阿里API，需密钥，高质量）"
echo "4) 全部安装"
read -p "请输入选项 (1-4): " install_choice

case $install_choice in
    1)
        echo ""
        echo "正在安装 MinerU..."
        pip install mineru
        echo "✅ MinerU 安装完成"
        echo ""
        echo "MinerU 特点："
        echo "  - 完全本地化，无需远程模型"
        echo "  - 免费使用"
        echo "  - 适合学术文献、RAG知识库构建"
        ;;
    2)
        echo ""
        echo "正在安装 Camelot..."
        pip install camelot-py[cv]
        echo "✅ Camelot 安装完成"
        echo ""
        echo "Camelot 特点："
        echo "  - 专业表格提取"
        echo "  - 免费使用"
        echo "  - 适合金融年报等复杂表格"
        ;;
    3)
        echo ""
        echo "正在安装 Logics-Parsing..."
        pip install logics-parsing
        echo "✅ Logics-Parsing 安装完成"
        echo ""
        echo "⚠️  注意：Logics-Parsing 需要API密钥"
        read -p "是否现在配置API密钥？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "请输入 DASHSCOPE_API_KEY: " api_key
            if [ ! -z "$api_key" ]; then
                echo "export DASHSCOPE_API_KEY=\"$api_key\"" >> ~/.bashrc
                echo "export DASHSCOPE_API_KEY=\"$api_key\"" >> ~/.zshrc 2>/dev/null || true
                export DASHSCOPE_API_KEY="$api_key"
                echo "✅ API密钥已配置（已添加到 ~/.bashrc 和 ~/.zshrc）"
                echo "   请运行 source ~/.bashrc 或重新打开终端使配置生效"
            fi
        fi
        echo ""
        echo "Logics-Parsing 特点："
        echo "  - 使用阿里 Qwen2.5-VL 大模型"
        echo "  - 高质量解析"
        echo "  - 30天内100万免费Tokens"
        ;;
    4)
        echo ""
        echo "正在安装所有后端..."
        pip install mineru camelot-py[cv] logics-parsing
        echo "✅ 所有后端安装完成"
        echo ""
        echo "⚠️  注意：Logics-Parsing 需要API密钥"
        echo "   请设置环境变量：export DASHSCOPE_API_KEY=\"your-api-key\""
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 重启应用以加载PDF解析工具"
echo "2. 查看日志确认工具已注册：'PDF parser tool registered successfully'"
echo "3. 测试工具：解析一个PDF文件"
echo ""
echo "详细文档：docs/tools/pdf-parser-setup.md"

