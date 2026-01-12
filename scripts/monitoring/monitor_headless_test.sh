#!/bin/bash
# 监控无头模式浏览器自动化测试的进度

echo "============================================================"
echo "无头模式浏览器自动化测试监控"
echo "============================================================"

# 检查测试进程
if ps aux | grep -q "[t]est_browser_headless.py"; then
    echo "✅ 测试正在运行中..."
    echo ""
    echo "进程信息:"
    ps aux | grep "[t]est_browser_headless.py" | grep -v grep
    echo ""
else
    echo "⚠️  测试进程未运行或已完成"
    echo ""
fi

# 查看最新日志
if [ -f /tmp/browser_headless_test.log ]; then
    echo "============================================================"
    echo "最新日志输出（最后 80 行）:"
    echo "============================================================"
    tail -80 /tmp/browser_headless_test.log
    echo ""
else
    echo "⚠️  日志文件不存在: /tmp/browser_headless_test.log"
    echo ""
fi

# 查找提取的内容文件
echo "============================================================"
echo "查找提取的内容文件:"
echo "============================================================"
DATA_DIR=$(find /tmp -name "*browser_use_agent*" -type d 2>/dev/null | sort -r | head -1)
if [ -n "$DATA_DIR" ]; then
    echo "找到测试目录: $DATA_DIR"
    echo ""
    
    # 查找提取的文件
    EXTRACTED_FILES=$(find "$DATA_DIR" -name "extracted_content*.md" -type f 2>/dev/null | sort)
    if [ -n "$EXTRACTED_FILES" ]; then
        echo "找到内容文件:"
        file_count=0
        for file in $EXTRACTED_FILES; do
            file_count=$((file_count + 1))
            echo ""
            echo "文件 $file_count: $file"
            echo "  大小: $(du -h "$file" | cut -f1)"
            echo "  修改时间: $(stat -c %y "$file" 2>/dev/null | cut -d. -f1)"
            echo "  内容预览（前 200 字符）:"
            head -c 200 "$file" 2>/dev/null | sed 's/^/    /'
            echo ""
        done
        echo "总共找到 $file_count 个内容文件"
    else
        echo "⚠️  未找到 extracted_content*.md 文件"
    fi
    
    # 列出所有文件
    echo ""
    echo "数据目录中的所有文件:"
    find "$DATA_DIR" -type f 2>/dev/null | head -20 | sed 's/^/  /'
else
    echo "⚠️  未找到测试目录"
fi

echo ""
echo "============================================================"
echo "监控完成"
echo "============================================================"
echo ""
echo "实时查看日志: tail -f /tmp/browser_headless_test.log"
echo "停止测试: pkill -f test_browser_headless.py"

