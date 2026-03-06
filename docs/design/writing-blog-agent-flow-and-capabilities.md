# writing_blog_agent 完整流程与智能能力投放

## 一、典型研发流程清单

| 序号 | 环节 | 输入 | 输出 | 当前实现 |
|------|------|------|------|----------|
| 1 | 解析用户输入 | task 字符串、context | parsed_input (topic, target_audience, article_type, draft_points, special_requirements) | `_parse_user_input` |
| 2 | 创建文章大纲 | parsed_input | outline (title, introduction, sections, conclusion, call_to_action) | `_create_outline` |
| 3 | 生成详细内容 | outline | article (introduction, sections[], conclusion, call_to_action, metadata) | `_generate_detailed_content` |
| 4 | 优化与润色 | article | optimized_article | `_optimize_article`（当前仅打戳，未真正优化） |
| 5 | MediaWiki 格式化 | optimized_article | mediawiki_content | `_format_for_mediawiki` |

---

## 二、各环节可投放的智能能力及价值

### 环节 1：解析用户输入

| 能力类型 | 能力名称 | 投放方式 | 价值 |
|----------|----------|----------|------|
| **Tool** | `google_search` | 用户主题模糊时，搜索相关热点/趋势 | 提升主题准确性和时效性 |
| **Tool** | `web_fetch` | 用户提供参考 URL 时，抓取页面内容 | 将外部资料纳入解析上下文 |
| **Tool** | `mediawiki` | 用户指定参考页面时，拉取已有文章 | 保持风格一致、避免重复 |
| **MCP** | cursor-ide-browser | 用户说「参考某网站」时，导航并提取 | 多页、需交互场景的信息采集 |
| **Skill** | 写作画像（喜好、表述习惯、范文） | 在 prompt 中注入用户偏好 | 输出更贴合个人风格 |
| **Agent** | chat_agent | 复杂/歧义输入时，多轮澄清 | 减少误解、提高需求准确度 |

### 环节 2：创建文章大纲

| 能力类型 | 能力名称 | 投放方式 | 价值 |
|----------|----------|----------|------|
| **Tool** | `google_search` | 搜索同类文章结构、SEO 标题 | 大纲更符合行业惯例、利于 SEO |
| **Tool** | `mediawiki` | 拉取同主题已有文章大纲 | 保持 wiki 内结构统一 |
| **Tool** | `wikipedia` | 主题涉及百科时，补充结构参考 | 提升专业性和完整性 |
| **Skill** | 大纲模板库 | 按 article_type 选择预设模板 | 加快生成、保证结构规范 |
| **Agent** | code_agent | 若需生成代码示例，预规划代码块 | 技术博客中代码结构更合理 |

### 环节 3：生成详细内容

| 能力类型 | 能力名称 | 投放方式 | 价值 |
|----------|----------|----------|------|
| **Tool** | `web_fetch` | 各 section 撰写时，按需抓取参考页 | 内容有据可查、减少幻觉 |
| **Tool** | `mediawiki` | 引用 wiki 内已有段落/定义 | 复用权威内容、保持一致性 |
| **Tool** | `google_search` | 补充数据、案例、最新信息 | 提高信息密度和时效性 |
| **Tool** | `image_generation` | 需要配图时生成插图 | 图文并茂、提升可读性 |
| **MCP** | cursor-ide-browser | 需要登录/多步操作才能获取的信息 | 突破简单 HTTP 限制 |
| **Skill** | 写作画像 | 每 section 遵循用户表述习惯 | 全文风格统一 |
| **Agent** | pdf_agent | 参考 PDF 文档撰写 | 技术文档、报告类文章 |

### 环节 4：优化与润色

| 能力类型 | 能力名称 | 投放方式 | 价值 |
|----------|----------|----------|------|
| **LLM** | 语法/表达优化 prompt | 检查语法、流畅度、一致性 | 当前 `_optimize_article` 未实现，可补齐 |
| **Tool** | `execute_code` | 运行拼写/语法检查脚本（如 language-tool） | 自动化质量把关 |
| **Skill** | 风格检查（可读性、术语统一） | 注入规则或二次 LLM 校验 | 提升专业度 |
| **Agent** | chat_agent | 模拟目标读者做「试读反馈」 | 更贴近读者体验 |

### 环节 5：MediaWiki 格式化与发布

| 能力类型 | 能力名称 | 投放方式 | 价值 |
|----------|----------|----------|------|
| **Tool** | `mediawiki` | 发布/更新页面、添加分类、链接 | 一键发布到 wiki |
| **Tool** | `gvim` | 在编辑器中打开并支持保存回 wiki | 人工微调后同步 |
| **Skill** | MediaWiki 模板/宏 | 按站点规范插入模板 | 符合站点约定 |
| **Agent** | article_writing_agent | 与写文章流程共用发布逻辑 | 复用已有能力 |

---

## 三、当前 article_writing 已配备工具（可复用）

`AGENT_TOOLS["article_writing"]` 当前包含：

- `browser`（若启用）
- `google_search`
- `web_fetch`
- `mediawiki`

writing_blog_agent 通过 `BlogWritingSkill` → `ArticleWritingAgent` 间接使用上述工具，但 **BlogWritingAgent 自身** 的 `execute` 流程（`_parse_user_input` → `_create_outline` → …）**尚未接入任何工具**，仅依赖纯 LLM 调用。

---

## 四、建议改造优先级

| 优先级 | 改造项 | 说明 |
|--------|--------|------|
| P0 | 在 `_parse_user_input` 前/中接入 `web_fetch`、`mediawiki` | 用户提供 URL 或参考页时自动拉取 |
| P0 | 在 `_create_outline` 中接入 `google_search`、`mediawiki` | 大纲更贴合实际、SEO 友好 |
| P1 | 在 `_generate_detailed_content` 各 section 中接入 `web_fetch`、`mediawiki` | 内容有据可查 |
| P1 | 实现 `_optimize_article` 的真实优化逻辑 | 当前仅打戳，无实质优化 |
| P2 | 接入 `image_generation` | 技术博客配图 |
| P2 | 写作画像贯穿全流程 | 已有 ArticleWritingAgent 画像，需在 BlogWritingAgent 中透传 |
| P3 | MCP browser、pdf_agent 等 | 扩展信息源类型 |

---

## 五、实施状况核查（2025-03）

### 5.1 已实施

| 项目 | 状态 | 说明 |
|------|------|------|
| Article writing 主流程 | ✅ | stream_process 使用 get_article_writing_system_prompt + article_writing 工具 |
| article_writing 工具 | ✅ | browser, google_search, web_fetch, mediawiki（AGENT_TOOLS 配置） |
| 写作画像 | ✅ | ArticleWritingAgent 注入 profile_block，写文章页会话使用 |
| BlogWritingSkill | ✅ | 已注册，匹配时调用 ArticleWritingAgent.execute() |
| MediaWiki 参考页 | ✅ | 写文章会话可配置 mw_source_titles，注入 prompt |
| 当前文章草稿 | ✅ | context_manager.set_current_article，支持续写/修改 |

### 5.2 已实施（2025-03 更新）

| 项目 | 状态 | 说明 |
|------|------|------|
| BlogWritingAgent 内工具调用 | ✅ | _parse_user_input 接入 web_fetch、mediawiki |
| _create_outline | ✅ | 接入 google_search、mediawiki search_read |
| _generate_detailed_content | ✅ | 各 section 注入 _reference_content |
| _optimize_article | ✅ | 使用 LLM 进行语法、流畅度、可读性优化 |
| writing_blog_tool | ✅ | 已注册，调用 BlogWritingAgent，支持 reference_url、mediawiki_page |
| _execute_agent(writing_blog_agent) | ✅ | 参数格式修正，返回可读字符串 |

### 5.3 已知问题

| 项目 | 说明 |
|------|------|
| 编排选择器流程 | 仅 process() 使用，stream 走 stream_process，故 writing_blog_agent 实际未被流式入口调用 |
| WorkAssistant vs ArticleWriting | 共用同一 prompt 与工具，仅 ArticleWriting 注入 mw_reference、current_article |

---

## 六、关于「输出未完全」问题

若出现「应该是没有能完全输出」的情况，可能原因包括：

1. **流式响应被截断**：SSE 超时、网络中断、前端 buffer 未完全处理。
2. **LLM max_tokens 限制**：长文章生成时触达上限，需分段生成或提高 `max_tokens`。
3. **工具调用循环达到上限**：`max_iterations` 用尽，未完成全部 section。
4. **JSON 解析失败**：`_parse_user_input`、`_create_outline` 依赖 `re.search(r'\{.*\}', response)`，若 LLM 返回格式不规范会回退到默认结构，可能丢失部分信息。

**排查建议**：

- 检查 `stream_chat_with_tools` 的 `finish_reason` 是否为 `length`。
- 检查 orchestrator 日志中是否有「达到最大工具调用迭代次数」。
- 在 `_generate_detailed_content` 中为每个 section 单独记录 token 使用或分段流式输出。

---

## 七、流程入口对照

| 入口 | 调用链 | 使用的 Agent/工具 |
|------|--------|-------------------|
| 写文章页 `/api/chat/stream` | stream_process | article_writing 工具（LLM 直接调用） |
| 工作助手 `/api/chat/stream` | stream_process | 同上，无 mw/草稿注入 |
| 技能匹配 blog_writing | BlogWritingSkill.execute | ArticleWritingAgent（无工具） |
| 编排选择 writing_blog_agent | process → _execute_agent | BlogWritingAgent（无工具，且参数格式不兼容） |
