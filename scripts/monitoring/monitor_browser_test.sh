#!/bin/bash
# 监控浏览器自动化测试的进度

echo "============================================================"
echo "浏览器自动化测试监控"
echo "============================================================"

# 检查测试进程
if ps aux | grep -q "[t]est_browser_automation.py"; then
    echo "✅ 测试正在运行中..."
    echo ""
    echo "进程信息:"
    ps aux | grep "[t]est_browser_automation.py" | grep -v grep
    echo ""
else
    echo "⚠️  测试进程未运行"
    echo ""
fi

# 查看最新日志
if [ -f /tmp/browser_test_full.log ]; then
    echo "============================================================"
    echo "最新日志输出（最后 50 行）:"
    echo "============================================================"
    tail -50 /tmp/browser_test_full.log
    echo ""
else
    echo "⚠️  日志文件不存在: /tmp/browser_test_full.log"
    echo ""
fi

# 查找 DOM 信息文件
echo "============================================================"
echo "查找 DOM 信息文件:"
echo "============================================================"
DOM_DIR=$(find /tmp -name "*browser_use_agent*" -type d 2>/dev/null | sort -r | head -1)
if [ -n "$DOM_DIR" ]; then
    echo "找到测试目录: $DOM_DIR"
    echo ""
    
    # 查找提取的文件
    EXTRACTED_FILES=$(find "$DOM_DIR" -name "extracted_content*.md" -type f 2>/dev/null)
    if [ -n "$EXTRACTED_FILES" ]; then
        echo "找到 DOM 信息文件:"
        for file in $EXTRACTED_FILES; do
            echo "  - $file"
            echo "    大小: $(du -h "$file" | cut -f1)"
            echo "    前 100 字符:"
            head -c 200 "$file" 2>/dev/null | sed 's/^/    /'
            echo ""
        done
    else
        echo "⚠️  未找到 extracted_content*.md 文件"
    fi
    
    # 查找 todo.md
    TODO_FILE=$(find "$DOM_DIR" -name "todo.md" -type f 2>/dev/null | head -1)
    if [ -n "$TODO_FILE" ]; then
        echo "找到任务清单文件: $TODO_FILE"
        echo "内容:"
        cat "$TODO_FILE" | sed 's/^/  /'
        echo ""
    fi
else
    echo "⚠️  未找到测试目录"
fi

echo "============================================================"
echo "监控完成"
echo "============================================================"
echo ""
echo "实时查看日志: tail -f /tmp/browser_test_full.log"
echo "停止测试: pkill -f test_browser_automation.py"

