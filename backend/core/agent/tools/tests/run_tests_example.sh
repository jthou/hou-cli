#!/bin/bash
# Tools 测试运行示例脚本

echo "=========================================="
echo "Tools 测试运行指南"
echo "=========================================="
echo ""

# 检查 pytest
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest 未安装"
    echo "   安装命令: pip install pytest"
    exit 1
fi

echo "✅ pytest 已安装: $(pytest --version)"
echo ""

# 检查 .env 文件
if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
else
    echo "⚠️  .env 文件不存在（某些测试可能需要配置）"
    echo "   创建命令: cp env.example .env"
fi
echo ""

echo "=========================================="
echo "推荐测试顺序"
echo "=========================================="
echo ""

echo "1. 运行基础测试（不需要 API Key）"
echo "   pytest backend/core/agent/tools/tests/ -v -k 'test_tool_initialization'"
echo ""

echo "2. 测试 WikipediaTool（公开 API，不需要配置）"
echo "   pytest backend/core/agent/tools/tests/test_wikipedia_tool.py -v"
echo ""

echo "3. 测试 FileSearchTool（本地文件系统）"
echo "   pytest backend/core/agent/tools/tests/test_file_search_tool.py -v"
echo ""

echo "4. 配置 API Keys 后测试其他工具"
echo "   在 .env 文件中配置相应的 API Keys"
echo "   pytest backend/core/agent/tools/tests/test_google_search_tool.py -v"
echo ""

echo "=========================================="
echo "常用测试命令"
echo "=========================================="
echo ""

echo "# 运行所有工具测试"
echo "pytest backend/core/agent/tools/tests/ -v"
echo ""

echo "# 运行特定工具的测试"
echo "pytest backend/core/agent/tools/tests/test_google_search_tool.py -v"
echo ""

echo "# 只运行单元测试（跳过集成测试）"
echo "pytest backend/core/agent/tools/tests/ -v -m 'not integration'"
echo ""

echo "# 只运行集成测试"
echo "pytest backend/core/agent/tools/tests/ -v -m 'integration'"
echo ""

echo "=========================================="
echo "开始测试？"
echo "=========================================="
echo ""
read -p "运行基础测试 (y/n)? " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "运行基础测试..."
    pytest backend/core/agent/tools/tests/ -v -k "test_tool_initialization" --tb=short
fi

