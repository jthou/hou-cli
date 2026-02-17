#!/bin/bash
# 测试视频下载和字幕提取任务

cd "$(dirname "$0")/.."
source venv/bin/activate

# 设置环境变量
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

# 使用前端执行任务
python -m frontend.main chat --message "$TASK"

echo ""
echo "=========================================="
echo "任务执行完成"
echo "=========================================="




