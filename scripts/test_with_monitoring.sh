#!/bin/bash
# 测试任务并监控前后端信息

cd "$(dirname "$0")/.."
source venv/bin/activate

# 设置环境变量
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600  # 10分钟超时

# 测试任务
TASK="下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。"

echo "=========================================="
echo "测试任务：$TASK"
echo "=========================================="
echo ""
echo "开始执行任务..."
echo ""

# 在后台监控后端日志
echo "监控后端日志（按 Ctrl+C 停止）..."
tail -f /tmp/hou-cli-backend.log &
TAIL_PID=$!

# 执行任务
echo "执行前端任务..."
python -m frontend.main chat --message "$TASK"

# 停止监控
kill $TAIL_PID 2>/dev/null

echo ""
echo "=========================================="
echo "任务执行完成"
echo "=========================================="
echo ""
echo "查看后端完整日志："
echo "  tail -100 /tmp/hou-cli-backend.log"
echo ""


