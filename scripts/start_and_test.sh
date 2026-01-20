#!/bin/bash
# 启动后端和前端，并执行测试任务

cd "$(dirname "$0")/.."
source venv/bin/activate

# 设置环境变量
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600  # 10分钟超时

echo "=========================================="
echo "启动后端服务（端口: 6080）"
echo "=========================================="

# 清理旧进程
lsof -ti:6080 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

# 启动后端（后台运行）
nohup python -m backend.main > /tmp/hou-cli-backend.log 2>&1 &
BACKEND_PID=$!
echo "后端已启动，PID: $BACKEND_PID"

# 等待后端启动
echo "等待后端启动..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:6080/health > /dev/null 2>&1; then
        echo "✅ 后端服务已就绪"
        break
    fi
    sleep 1
done

# 检查后端是否启动成功
if ! curl -s http://127.0.0.1:6080/health > /dev/null 2>&1; then
    echo "❌ 后端启动失败，请查看日志: /tmp/hou-cli-backend.log"
    tail -20 /tmp/hou-cli-backend.log
    exit 1
fi

echo ""
echo "=========================================="
echo "后端日志位置: /tmp/hou-cli-backend.log"
echo "监控后端日志: tail -f /tmp/hou-cli-backend.log"
echo "=========================================="
echo ""
echo "现在可以运行前端测试任务："
echo "  python -m frontend.main chat --message '下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。'"
echo ""
echo "或者使用交互式模式："
echo "  python -m frontend.main chat"
echo ""

