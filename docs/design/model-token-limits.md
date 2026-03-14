# 模型 Token 限制参考

各模型的最大上下文（输入）与最大输出 token 数，用于配置 `LLM_MAX_TOKENS` 及输入/输出时的提示与警告。

参考：[llm-context-limits](https://github.com/taylorwilsdon/llm-context-limits)

## 配置说明

- **LLM_MAX_TOKENS**：可选。不设置时**不人为截断**，使用模型 max_output；设置时取 `min(LLM_MAX_TOKENS, 模型 max_output)`
- 截断仅发生在超出模型能力时
- 若输出因达到模型上限被截断，会在响应末尾追加警告

## 各模型限制（概览）

| 提供商 | 模型 | 最大上下文 | 最大输出 |
|--------|------|------------|----------|
| DeepSeek | deepseek-chat, deepseek-coder, deepseek-reasoner | 64K | 8K |
| OpenAI | gpt-5, gpt-5.1, gpt-5.2 | 400K | 128K |
| OpenAI | gpt-4.1 | 1M | 32K |
| OpenAI | gpt-4o | 128K | 16K |
| OpenAI | o3, o3-mini | 200K | 100K |
| Anthropic | Claude 4.5 Opus/Sonnet | 200K | 64K |
| Anthropic | Claude 3.7/3.5 | 200K | 8K |
| Google | gemini-2.5-pro | 1M | 64K |
| Google | gemini-2.5-flash | 1M | 8K |
| 百炼 Qwen | qwen-turbo, qwen-max 等 | 32K | 8K |

完整配置见 `backend/services/llm/model_token_limits.py`。

## 输入/输出警告机制

1. **输入**：若估计 token 数超过模型 max_context 的 90%，会记录 warning 日志
2. **输出**：若 `finish_reason == "length"`，会在响应末尾追加：
   ```
   ⚠️ 输出因达到 token 上限而截断，建议在 .env 中提高 LLM_MAX_TOKENS 或分批提问。
   ```
