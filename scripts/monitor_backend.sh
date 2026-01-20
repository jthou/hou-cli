#!/bin/bash
# 监控后端日志

LOG_FILE="/tmp/hou-cli-backend.log"

echo "=========================================="
echo "监控后端日志: $LOG_FILE"
echo "按 Ctrl+C 停止监控"
echo "=========================================="
echo ""

tail -f "$LOG_FILE"

