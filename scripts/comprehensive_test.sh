#!/bin/bash
# 综合测试脚本 - 验证所有功能是否符合设计

cd "$(dirname "$0")/.."
source venv/bin/activate

# 设置环境变量
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600  # 10分钟超时

# 测试任务
TASK="下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕，也可以从原视频中下载音频，然后提取字幕。"

echo "=========================================="
echo "综合功能测试"
echo "=========================================="
echo "测试任务: $TASK"
echo "后端端口: 6080"
echo "超时设置: 600秒"
echo "自主执行模式: 启用"
echo "=========================================="
echo ""

# 检查后端状态
echo "1. 检查后端服务状态..."
if curl -s http://127.0.0.1:6080/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务运行正常"
else
    echo "   ❌ 后端服务未运行，请先启动后端"
    exit 1
fi

# 检查环境变量
echo ""
echo "2. 检查环境变量配置..."
if [ -z "$BACKEND_PORT" ]; then
    echo "   ⚠️  BACKEND_PORT 未设置"
else
    echo "   ✅ BACKEND_PORT=$BACKEND_PORT"
fi

if [ -z "$ENABLE_AUTONOMOUS_EXECUTION" ]; then
    echo "   ⚠️  ENABLE_AUTONOMOUS_EXECUTION 未设置"
else
    echo "   ✅ ENABLE_AUTONOMOUS_EXECUTION=$ENABLE_AUTONOMOUS_EXECUTION"
fi

if [ -z "$STREAM_TIMEOUT" ]; then
    echo "   ⚠️  STREAM_TIMEOUT 未设置（将使用默认值）"
else
    echo "   ✅ STREAM_TIMEOUT=$STREAM_TIMEOUT"
fi

# 准备日志文件
FRONTEND_LOG="/tmp/hou-cli-frontend-test-$(date +%Y%m%d-%H%M%S).log"
BACKEND_LOG="/tmp/hou-cli-backend-test-$(date +%Y%m%d-%H%M%S).log"

echo ""
echo "3. 准备日志文件..."
echo "   前端日志: $FRONTEND_LOG"
echo "   后端日志: $BACKEND_LOG"

# 获取后端日志文件路径
APP_LOG_DIR="$HOME/Library/Application Support/hou-cli/logs"
APP_BACKEND_LOG="$APP_LOG_DIR/backend.log"
if [ -f "$APP_BACKEND_LOG" ]; then
    echo "   应用日志: $APP_BACKEND_LOG"
    # 记录当前日志位置
    CURRENT_LOG_SIZE=$(wc -l < "$APP_BACKEND_LOG" 2>/dev/null || echo "0")
    echo "   当前日志行数: $CURRENT_LOG_SIZE"
fi

echo ""
echo "4. 开始执行测试任务..."
echo "   （提示：可以在另一个终端运行 'tail -f $APP_BACKEND_LOG' 监控后端日志）"
echo ""

# 记录开始时间
START_TIME=$(date +%s)

# 执行任务并记录输出
python -m frontend.main chat "$TASK" 2>&1 | tee "$FRONTEND_LOG"

# 记录结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "测试执行完成"
echo "=========================================="
echo "执行时长: ${DURATION} 秒"
echo ""

# 分析结果
echo "5. 分析测试结果..."
echo ""

# 检查前端日志中的关键信息
if [ -f "$FRONTEND_LOG" ]; then
    echo "前端日志分析："
    
    # 检查计划输出
    if grep -q "\[计划\]" "$FRONTEND_LOG"; then
        echo "   ✅ 计划输出正常"
    else
        echo "   ❌ 未找到计划输出"
    fi
    
    # 检查轮次输出
    ROUND_COUNT=$(grep -c "\[第.*轮\]" "$FRONTEND_LOG" || echo "0")
    if [ "$ROUND_COUNT" -gt 0 ]; then
        echo "   ✅ 执行轮次: $ROUND_COUNT 轮"
    else
        echo "   ❌ 未找到执行轮次信息"
    fi
    
    # 检查工具调用
    TOOL_CALL_COUNT=$(grep -c "\[工具调用\]" "$FRONTEND_LOG" || echo "0")
    if [ "$TOOL_CALL_COUNT" -gt 0 ]; then
        echo "   ✅ 工具调用次数: $TOOL_CALL_COUNT"
        echo "   工具调用详情:"
        grep "\[工具调用\]" "$FRONTEND_LOG" | sed 's/^/      /'
    else
        echo "   ❌ 未找到工具调用信息"
    fi
    
    # 检查工具结果
    TOOL_RESULT_COUNT=$(grep -c "\[工具结果\]" "$FRONTEND_LOG" || echo "0")
    if [ "$TOOL_RESULT_COUNT" -gt 0 ]; then
        echo "   ✅ 工具结果数量: $TOOL_RESULT_COUNT"
    else
        echo "   ❌ 未找到工具结果信息"
    fi
    
    # 检查状态更新（心跳）
    STATUS_COUNT=$(grep -c "\[状态\]" "$FRONTEND_LOG" || echo "0")
    if [ "$STATUS_COUNT" -gt 0 ]; then
        echo "   ✅ 状态更新（心跳）次数: $STATUS_COUNT"
    else
        echo "   ⚠️  未找到状态更新（可能任务执行时间较短）"
    fi
    
    # 检查任务完成
    if grep -q "✅.*任务完成" "$FRONTEND_LOG"; then
        echo "   ✅ 任务完成标识正常"
    else
        echo "   ⚠️  未找到任务完成标识"
    fi
    
    # 检查超时错误
    if grep -qi "timeout\|超时" "$FRONTEND_LOG"; then
        echo "   ❌ 发现超时错误"
        grep -i "timeout\|超时" "$FRONTEND_LOG" | sed 's/^/      /'
    else
        echo "   ✅ 未发现超时错误"
    fi
    
    # 检查特定工具
    echo ""
    echo "工具执行验证："
    if grep -q "video_downloader\|视频下载" "$FRONTEND_LOG"; then
        echo "   ✅ video_downloader 已调用"
    else
        echo "   ❌ video_downloader 未调用"
    fi
    
    if grep -q "ffmpeg\|音频提取\|提取音频" "$FRONTEND_LOG"; then
        echo "   ✅ ffmpeg 相关操作已执行"
    else
        echo "   ⚠️  ffmpeg 相关操作未找到（可能直接从视频提取字幕）"
    fi
    
    if grep -q "whisper\|字幕\|subtitle" "$FRONTEND_LOG"; then
        echo "   ✅ whisper 字幕生成已调用"
    else
        echo "   ❌ whisper 字幕生成未调用"
    fi
fi

echo ""
echo "6. 日志文件位置："
echo "   前端日志: $FRONTEND_LOG"
if [ -f "$APP_BACKEND_LOG" ]; then
    echo "   后端日志: $APP_BACKEND_LOG"
    echo "   查看后端日志: tail -100 $APP_BACKEND_LOG"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="




