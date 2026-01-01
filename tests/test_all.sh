#!/bin/bash
# 运行所有测试

set -e

echo "=========================================="
echo "运行所有测试"
echo "=========================================="

# 获取脚本所在目录（tests 目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 切换到项目根目录
cd "$SCRIPT_DIR/.."

# 运行 pytest 单元测试
echo ""
echo "1. 运行单元测试..."
pytest backend/ -v

# 运行集成测试（可选，需要后端服务）
echo ""
echo "2. 运行集成测试..."
echo "   提示: 集成测试需要后端服务运行"
echo "   运行: pytest tests/test_integration.py -v"

echo ""
echo "=========================================="
echo "✅ 测试完成！"
echo "=========================================="

