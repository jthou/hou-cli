#!/bin/bash
# 运行所有测试脚本

set -e

echo "=========================================="
echo "运行所有测试"
echo "=========================================="

# 1. 上下文管理器快速测试
echo ""
echo "1. 上下文管理器测试..."
python tests/test_context_manager_quick.py

# 2. 端到端测试
echo ""
echo "2. 端到端对话测试..."
python tests/integration/test_e2e_chat.py

# 3. 多轮对话测试
echo ""
echo "3. 多轮对话上下文测试..."
python tests/integration/test_multi_turn_chat.py

echo ""
echo "=========================================="
echo "✅ 所有测试完成！"
echo "=========================================="









