---
name: hou-bailian-cursor-step
description: 约定 Cursor Agent 何时通过 MCP 调用百炼单步（文本/VL/文生图/文生视频/TTS/短 ASR 等）及组参；须配合 `hou-bailian-chat` MCP，本 Skill 不提供模型端点或密钥。
---

# 百炼单步（Cursor MCP）使用约定

## 能力边界

- **本 Skill 只描述流程与约定**，不内置 API、不替代你在 `~/.cursor/mcp.json`（或项目 `.cursor/mcp.json`）里配置的 MCP 服务器；**合并模板**以仓库 `config/cursor/mcp.json.example` 为准。
- **实际推理**由已配置的 **`hou-bailian-chat`** MCP 工具完成（仓库脚本 `scripts/mcp_bailian_chat_server.py`）。
- **公众号 / 写作助手编排长文**仍用 **`hou-bailian-article`** 的 `hou_article_writing`，不要用本 MCP 硬撑整篇编排。

## 何时让 Agent 调百炼（单步 MCP）

在对话中**偶尔**走百炼，适用于（示例）：

| 场景 | 建议 |
|------|------|
| 长材料摘要、结构化提取 | `hou_bailian_complete`，system 写清输出格式 |
| 中译英 / 英译中、术语表 | 同上，`temperature` 可略低（如 0.3） |
| 单轮专用指令（审计清单、分类标签） | system 放规则，user 放待处理正文 |
| 主模型上下文不够或你希望固定走 Qwen 百炼 | 显式调用工具，而非默认假设「已自动走百炼」 |
| 读图 / 截图 OCR / 多图问答 | **`hou_bailian_complete_vision`** + VL 模型 id + 公网图 URL 或 `data:image/...;base64,...` |
| 文生图 | **`hou_bailian_text_to_image`** | `wan2.6-t2i`、`qwen-image-max-2025-12-30` 等 |
| 文生视频（异步，可能较久） | **`hou_bailian_text_to_video`** | `wan2.6-t2v`、`wan2.6-i2v`（图生视频需按官方再传参，当前工具以文生为主） |
| 语音合成（TTS） | **`hou_bailian_tts`** | 默认 `qwen3-tts-flash-2025-11-27`；音色 `voice` 见官方文档 |
| 短音频转写（ASR） | **`hou_bailian_speech_to_text`** | 默认 `qwen3-asr-flash-2025-09-08`；音频须 **公网 URL** 或较小体积的 **`data:audio/*;base64,...`** |

**不必**用百炼：简单闲聊、已用主模型能稳定完成的短答、与本仓库无关且未配置 MCP 的环境。

## 模型怎么选（文本共用一个入口）

**百炼文本对话**共用一个工具 **`hou_bailian_complete`**，通过 **`model`** 切换。权威列表：**`hou_bailian_list_models`**（`filter_prefix` 示例：`qwen3`、`vl`、`kimi`、`deepseek`、`wan`、`tts`、`asr`）。

| 需求 | 工具 | `model` 示例（以 list_models 为准） |
|------|------|--------------------------------------|
| 通用文本、长上下文 | `hou_bailian_complete` | `qwen3-max`、`qwen3.6-plus` |
| 百炼上的 Kimi | `hou_bailian_complete` | `kimi-k2-thinking` 等（见注册表） |
| DeepSeek 走百炼线路 | `hou_bailian_complete` | `bailian-deepseek-chat`、`deepseek-v3.2` 等 |
| 视觉 / 多模态 | **`hou_bailian_complete_vision`** | `qwen3-vl-plus-2025-12-19`、`qwen-vl-max-2025-08-13` 等 |

**非百炼**（如 OpenAI/Claude 走 Turbo 网关）不在本 MCP 范围内，会被拒绝。

**长音频 / 实时 ASR**：`qwen3-asr-flash-filetrans`、实时 WebSocket 等请走阿里云官方文档或后续专用封装；本 MCP 的 **`hou_bailian_speech_to_text`** 面向兼容模式 **`input_audio` + 短音频** 场景。

## MCP 工具与参数（组参约定）

配置好 MCP 后，**先读工具 schema**，再调用。

1. **`hou_bailian_complete`**（纯文本）  
   - **必填**：`user_prompt`  
   - **常用可选**：`system_prompt`（默认空）、`model`（默认 `qwen3-max`）、`temperature`（0～2，默认 0.7）、`max_tokens`（需要上限时传入）  
   - **模型**：须解析为百炼线路；**换模型只改 `model`**，无需新工具。  
   - **不确定模型 id**：`hou_bailian_list_models` + `filter_prefix`。

2. **`hou_bailian_complete_vision`**（图 + 文）  
   - **必填**：`user_prompt`、`image_urls`（一条或多条：每条为 **http(s) 可访问图片 URL**，或 **`data:image/<mime>;base64,...`**）  
   - **可选**：`system_prompt`、`model`（默认 `qwen3-vl-plus-2025-12-19`）、`temperature`、`max_tokens`、`max_images`（默认 8，上限 16）  
   - 图须可被 DashScope 拉取或内联于 data URL；**不要用 `file://`**。

3. **`hou_bailian_list_models`**：`filter_prefix`、`max_items`（列表可能截断，以返回 JSON 为准）。

4. **`hou_bailian_ping`**：`live=false` 仅看密钥与 `base_url`；`live=true` 会发一次极小请求验证链路（有费用/额度概念时注意）。

5. **`hou_bailian_text_to_image`**：`prompt`、`model`（默认 `wan2.6-t2i`）、`size`、`reference_image_urls`（可选）。文件默认在 **`~/hou-cli/outputs/bailian_mcp_image/`**。

6. **`hou_bailian_text_to_video`**：`prompt`、`model`（默认 `wan2.6-t2v`）、`size`、`duration`、`prompt_extend`、`watermark`、`shot_type`（可选）、`max_wait_sec`（默认 600）。成功则 **`~/hou-cli/outputs/bailian_mcp_video/*.mp4`**；**超时**则返回 JSON 内含 **`task_id`**，可到控制台或 `GET .../tasks/{id}` 继续查。

7. **`hou_bailian_tts`**：`text`、`voice`（默认 `Cherry`）、`language_type`（默认 `Auto`）、`model`、`instructions`（指令控制模型用）。输出 **`~/hou-cli/outputs/bailian_mcp_tts/*.wav`**。

8. **`hou_bailian_speech_to_text`**：`audio_url` **或** `audio_data_uri`（二选一）、`system_context`（可选）、`model`。公网音频 URL 最稳妥；base64 注意体积极限（见工具说明）。

## 环境与密钥（与仓库一致）

- 密钥：`BAILIAN_API_KEY` 或 `DASHSCOPE_API_KEY`（见仓库 `env.example`）。  
- **勿**把密钥写进 Skill、用户可见日志或对话引用块。  
- MCP 进程的 **`cwd` 应为 hou-cli 仓库根**，以便加载 `.env`。

## 与 `hou_article_writing` 的分工

- **`hou_bailian_complete` / `hou_bailian_complete_vision` / 文生图/视频/TTS/ASR 工具**：单步媒体或对话，不与写作编排混用。  
- **`hou_article_writing`**：写作编排（参考块、改稿、热点摘要进公众号等），与 Web 写作助手同源。

若用户要「按固定 Skill 写整篇公众号」，走 **article MCP**；若只要「把下面这段翻译成英文」，走 **chat MCP**。
