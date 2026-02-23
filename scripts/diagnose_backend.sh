#!/bin/bash
# 后端服务诊断脚本

echo "🔍 后端服务诊断"
echo "================"
echo ""

# 1. 检查端口文件
echo "1. 检查端口文件..."
PORT_FILE="$HOME/Library/Application Support/hou-cli/port.txt"
if [ -f "$PORT_FILE" ]; then
    PORT=$(cat "$PORT_FILE")
    echo "   ✅ 端口文件存在: $PORT_FILE"
    echo "   📌 端口号: $PORT"
else
    echo "   ❌ 端口文件不存在: $PORT_FILE"
fi
echo ""

# 2. 检查后端进程
echo "2. 检查后端进程..."
BACKEND_PIDS=$(ps aux | grep -E "python.*backend\.main|uvicorn" | grep -v grep | awk '{print $2}')
if [ -z "$BACKEND_PIDS" ]; then
    echo "   ❌ 未找到后端进程"
else
    echo "   ✅ 找到后端进程:"
    ps aux | grep -E "python.*backend\.main|uvicorn" | grep -v grep
fi
echo ""

# 3. 检查端口监听
if [ -f "$PORT_FILE" ]; then
    PORT=$(cat "$PORT_FILE")
    echo "3. 检查端口 $PORT 监听状态..."
    if lsof -ti:$PORT > /dev/null 2>&1; then
        echo "   ✅ 端口 $PORT 正在监听"
        lsof -ti:$PORT | while read pid; do
            echo "   📌 进程 PID: $pid"
            ps -p $pid -o command= 2>/dev/null || echo "   ⚠️  进程不存在"
        done
    else
        echo "   ❌ 端口 $PORT 未在监听"
    fi
    echo ""
fi

# 4. 健康检查
if [ -f "$PORT_FILE" ]; then
    PORT=$(cat "$PORT_FILE")
    echo "4. 健康检查 (http://127.0.0.1:$PORT/health)..."
    if command -v curl > /dev/null 2>&1; then
        RESPONSE=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:$PORT/health" 2>/dev/null)
        HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
        BODY=$(echo "$RESPONSE" | head -n -1)
        if [ "$HTTP_CODE" = "200" ]; then
            echo "   ✅ 健康检查通过 (HTTP $HTTP_CODE)"
            echo "   📄 响应: $BODY"
        else
            echo "   ❌ 健康检查失败 (HTTP $HTTP_CODE)"
            echo "   📄 响应: $BODY"
        fi
    else
        echo "   ⚠️  curl 未安装，跳过健康检查"
    fi
    echo ""
fi

# 5. 检查日志
echo "5. 检查后端日志..."
LOG_FILE="$HOME/Library/Application Support/hou-cli/logs/backend.log"
if [ -f "$LOG_FILE" ]; then
    echo "   ✅ 日志文件存在: $LOG_FILE"
    echo "   📄 最后10行:"
    tail -10 "$LOG_FILE" | sed 's/^/      /'
else
    echo "   ❌ 日志文件不存在: $LOG_FILE"
fi
echo ""

# 6. 检查启动日志
echo "6. 检查启动日志..."
STARTUP_LOG="$HOME/Library/Application Support/hou-cli/logs/backend_startup.log"
if [ -f "$STARTUP_LOG" ]; then
    echo "   ✅ 启动日志存在: $STARTUP_LOG"
    echo "   📄 最后20行:"
    tail -20 "$STARTUP_LOG" | sed 's/^/      /'
else
    echo "   ⚠️  启动日志不存在: $STARTUP_LOG"
fi
echo ""

echo "诊断完成！"

