# 主编编排管道：实现路径与 JSON 契约

## 仓库内代码路径

| 能力 | 位置 |
|------|------|
| 热点 digest 任务 | `backend/infrastructure/execution/task_handlers.py` → `process_ai_hot_news_digest_task` |
| 热点直跑 API | `backend/api/ai_hot_news_routes.py` → `POST /api/ai-hot-news/run` |
| 默认检索查询 | `backend/services/ai_hot_news_digest/queries.py` → `default_ai_hot_news_queries()` |
| 写作系统提示 | `backend/core/agent/system_prompt_templates.py` → `get_article_writing_system_prompt` |
| 参考块与用户消息 | `backend/core/agent/article_writing_message_contract.py`（`【参考n：标题】`、`【用户本次提问】` 与 `referenceUtils.js` 同步） |
| 微信草稿任务 | `TASK_TYPES["wechat_mp_draft"]` → `process_wechat_mp_draft_task` |
| MCP 草稿 | `scripts/mcp_wechat_mp_draft_server.py` |
| 模型注册 | `backend/services/llm/model_registry.py`（`qwen3.6-plus`、`qwen3-max`） |

## `topic_sheet_v1` JSON 示例

```json
{
  "schema": "topic_sheet_v1",
  "meta": {
    "proposition_one_liner": "用一句话概括全文要回答的判断或关系（非「本周很多事」）。",
    "audience": "如：关注智能体落地的技术负责人",
    "tone": "克制专业 | 传播增强",
    "date_basis": "2026-04-12",
    "timezone_note": "Asia/Shanghai 或 UTC，与事实包一致"
  },
  "candidates": [
    {
      "id": "t1",
      "working_title": "用于内部沟通的暂定题（可≠最终 # 标题）",
      "angle": "切口与论证主轴线",
      "why_now": "与素材中日期的关系一句",
      "reader_job": "须可执行或可转述，禁止「提升认知」「把握趋势」；例：读完能判断「是否要把 RAG 检索层与 IAM 审计日志打通」并说出两条依据出处",
      "priority": 1,
      "risk_flags": ["争议叙事需双源", "融资数字以官宣为准"],
      "source_gaps": ["缺二级媒体交叉"],
      "suggested_refs": ["参考资料中应优先嵌入的 2～3 条链接或标题关键词"]
    }
  ],
  "selected_id": "t1"
}
```

## `outline_v1` JSON 示例

```json
{
  "schema": "outline_v1",
  "sections": [
    { "heading": "小节标题须像已发公号（概括事实或判断）", "claim": "本节要证明的一句话" },
    { "heading": "…", "claim": "…" }
  ]
}
```

## 拼入写作助手的参考块（示意）

与 `format_reference_context` 一致：多块时依次为 `【参考1】…【参考2】…`。

- **参考1**：`fact_pack.md` 全文（含参考资料节）。
- **参考2**（可选）：阶段 B 的 `editorial_brief` 纯文本，标题如 `主编 brief`。

用户本次提问示例：

```text
请按选题 t1 与 outline_v1 写成公众号长文，约 2800 字，克制专业档。事实以参考1 为准；参考2 仅作结构与分寸约束，勿写入元叙事。
```

## 模型 ID 备忘

| 阶段 | `model` 字段（百炼） |
|------|----------------------|
| 主编 B | `qwen3.6-plus` / `bailian-qwen3.6-plus` |
| 成稿 C | `qwen3-max` / `bailian-qwen3-max` |
