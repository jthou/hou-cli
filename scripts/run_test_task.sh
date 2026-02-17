#!/bin/bash
# 执行测试任务并监控前后端

cd "$(dirname "$0")/.."
source venv/bin/activate

# 设置环境变量
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600  # 10分钟超时

# 测试任务
TASK="下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。"

echo "=========================================="
echo "测试任务执行"
echo "=========================================="
echo "任务: $TASK"
echo "后端端口: 6080"
echo "超时设置: 600秒"
echo "=========================================="
echo ""

# 检查后端是否运行
if ! curl -s http://127.0.0.1:6080/health > /dev/null 2>&1; then
    echo "❌ 后端服务未运行，请先启动后端："
    echo "   export BACKEND_PORT=6080 && python -m backend.main"
    exit 1
fi

echo "✅ 后端服务已就绪"
echo ""

# 在另一个终端窗口显示后端日志（提示用户）
echo "提示：可以在另一个终端运行以下命令监控后端日志："
echo "  tail -f /tmp/hou-cli-backend.log"
echo "  或者："
echo "  tail -f ~/Library/Application\ Support/hou-cli/logs/backend.log"
echo ""
echo "开始执行任务..."
echo ""

# 执行任务（使用正确的参数格式：message 作为位置参数）
python -m frontend.main chat "$TASK"

echo ""
echo "=========================================="
echo "任务执行完成"
echo "=========================================="
echo ""
echo "查看后端日志："
echo "  tail -100 /tmp/hou-cli-backend.log"
echo "  或"
echo "  tail -100 ~/Library/Application\ Support/hou-cli/logs/backend.log"
echo ""




