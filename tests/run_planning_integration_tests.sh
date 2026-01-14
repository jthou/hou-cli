#!/bin/bash
# 运行规划功能和任务管理功能集成测试

set -e

echo "=========================================="
echo "运行规划功能和任务管理功能集成测试"
echo "=========================================="
echo ""

# 设置环境变量
export ENABLE_PLANNING=true
export PLANNING_COMPLEXITY_THRESHOLD=0.2
export PLANNING_MIN_TASK_LENGTH=10
export DEEPSEEK_API_KEY=test_key_for_testing

# 运行单元测试
echo "1. 运行单元测试..."
echo "----------------------------------------"
pytest backend/core/agent/tests/test_orchestrator_planning_integration.py \
    backend/core/agent/tests/test_task_manager_integration.py \
    -v --tb=short
echo ""

# 运行集成测试
echo "2. 运行集成测试..."
echo "----------------------------------------"
pytest tests/integration/test_orchestrator_planning_task_integration.py \
    tests/integration/test_api_planning_integration.py \
    -v --tb=short
echo ""

# 运行API测试
echo "3. 运行API测试..."
echo "----------------------------------------"
pytest backend/api/tests/test_stream_api_planning_integration.py \
    backend/api/tests/test_task_api.py \
    -v --tb=short
echo ""

echo "=========================================="
echo "所有测试完成！"
echo "=========================================="

