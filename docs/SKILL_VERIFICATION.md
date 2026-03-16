# 写作技能验证指南

## 一、单元测试

```bash
cd /System/Volumes/Data/justin/prod/hou-cli
pytest backend/core/agent/tests/test_skill_verification.py -v
```

验证项：
- `article_writing` 仅匹配 4 个写作技能
- `work_assistant` 不匹配任何技能
- `general_chat` 使用全部技能
- 写作技能已正确注册

## 二、API 验证

### 1. 写作助手（article_writing）

创建写作会话并发送消息，需传 `context_type: article_writing`：

```bash
# 1. 创建写作会话
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"type": "article_writing"}}'

# 2. 发送消息（替换 SESSION_ID）
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我生成一篇关于 AI 写作的大纲",
    "session_id": "SESSION_ID",
    "context_type": "article_writing"
  }'
```

预期：匹配 `article_outline` 技能，流式返回大纲内容，无重复输出。

### 2. 工作助手（work_assistant）

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "下载这个视频 https://example.com/video.mp4",
    "session_id": "SESSION_ID",
    "context_type": "work_assistant"
  }'
```

预期：不匹配任何技能，直接走 LLM 对话（工作助手身份）。

### 3. 通用对话（general_chat）

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "下载这个视频 https://example.com/video.mp4",
    "session_id": "SESSION_ID",
    "context_type": "general_chat"
  }'
```

预期：可匹配 `video_downloader` 等全部技能。

## 三、前端验证

1. **写作助手**：打开写作页面 → 新建会话 → 输入「帮我生成大纲」→ 应触发 `article_outline`
2. **工作助手**：打开工作助手 → 输入任意问题 → 不触发技能，仅 LLM 回答
3. **通用对话**：打开通用对话 → 输入「下载视频 xxx」→ 可触发视频技能

## 四、技能触发关键词（供 LLM 匹配参考）

| 技能 | 典型用户表述 |
|------|--------------|
| article_outline | 生成大纲、写提纲、列大纲 |
| article_write | 根据大纲撰写、写正文、扩写 |
| article_style_apply | 润色、模仿风格、按写作画像修改 |
| writing_profile_summary | 总结写作画像、分析我的风格 |

## 五、调试日志

启用 DEBUG 时，流式响应中会包含 `__DEBUG__` 消息，可查看：
- `技能匹配`：是否匹配到技能及技能名
- `技能注册`：各技能注册状态
