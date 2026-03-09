#!/bin/bash
# 测试代码助手是否调用执行工具
# 用法: ./scripts/test_code_assistant_tools.sh
# 需确保后端已启动 (默认 8081)

set -e
API="${API:-http://localhost:8081}"
SESSION_ID=""

echo "=== 1. 创建 code_assistant 会话 ==="
resp=$(curl -s -X POST "$API/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"metadata":{"type":"code_assistant"}}')
SESSION_ID=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
if [ -z "$SESSION_ID" ]; then
  echo "创建会话失败: $resp"
  exit 1
fi
echo "session_id: $SESSION_ID"

echo ""
echo "=== 2. 发送「写一段 python 执行看看」请求 ==="
curl -s -X POST "$API/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"写一段 python，执行看看\\n\\nprint(\\\"Hello, world!\\\")\",
    \"session_id\": \"$SESSION_ID\",
    \"context_type\": \"code_assistant\"
  }" | while IFS= read -r line; do
  if [[ "$line" == data:* ]]; then
    content=$(echo "$line" | sed 's/^data: //' | python3 -c "
import sys,json
try:
  d=json.load(sys.stdin)
  c=d.get('content','')
  if c and '__TOOL__' in str(c):
    print('>>> 检测到 __TOOL__ 调用!')
  if c and not c.startswith('__'):
    print(c[:200])
except: pass
" 2>/dev/null || true)
    [ -n "$content" ] && echo "$content"
  fi
done

echo ""
echo "=== 完成 ==="
echo "若看到「检测到 __TOOL__ 调用」则说明工具被正确调用"
echo "若只有文本无 __TOOL__，请检查: 1) 是否在代码助手页面 2) 模型是否支持 tool calling"
