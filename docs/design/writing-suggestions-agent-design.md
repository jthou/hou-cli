# 写作补全 / 写作建议 Agent 设计

## 一、目标

在 Markdown 编辑器和 MediaWiki 编辑器中，针对**光标位置**的上下文，由 AI 给出 **1–5 条写作建议**，以浮层形式展示，用户可点击插入。

## 二、能力范围

| 能力 | 说明 | 示例 |
|------|------|------|
| **续写补全** | 根据前文续写下一句/段 | 前文「AI 编程新范式包括…」→ 建议「vibe coding、harness engineering 等」 |
| **改写建议** | 对当前句/段给出更优表述 | 「这个功能很好用」→ 建议「该功能在易用性上表现突出」 |
| **结构建议** | 建议补充小标题、列表等 | 长段落后建议「可拆分为：1. 背景 2. 方法 3. 结论」 |
| **术语/表达** | 同义替换、术语规范 | 「搞」→ 建议「实施」「推进」 |
| **格式建议** | Markdown/Wikitext 语法 | 建议用 `##` 做标题、用列表组织要点 |

## 三、架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  MarkdownEditorPreview / WikitextEditorPreview                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  <textarea> 或 可编辑区域                                 │   │
│  │  "AI 编程新范式包括|"  ← 光标                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  WritingSuggestionsPopover (浮层)                         │   │
│  │  • 建议1: vibe coding、harness engineering 等            │   │
│  │  • 建议2: 从 vibe coding 到 harness engineering          │   │
│  │  • 建议3: …                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /api/writing-suggestions                                  │
│  { text_before, text_after, format, cursor_pos }                 │
│  → { suggestions: string[] }                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  WritingSuggestionsAgent (后端)                                  │
│  - 轻量 LLM 调用（短 prompt、低 max_tokens）                     │
│  - 无工具、无会话，单次请求单次响应                               │
└─────────────────────────────────────────────────────────────────┘
```

## 四、前端设计

### 4.1 可复用组件：`WritingSuggestionsPopover`

- **职责**：展示 1–5 条建议，支持点击插入、键盘上下选择
- **定位**：基于 `textarea` 的 `selectionStart` 计算光标像素坐标，用 `position: absolute` 浮在光标下方
- **触发**：编辑模式下「写作建议」按钮（快捷键已移除）
- **交互**：
  - 点击某条建议 → 在光标处插入该文本
  - 上下键选择、Enter 确认
  - Esc 关闭
  - 加载中显示骨架/loading

### 4.2 与编辑器的集成方式

| 编辑器 | 集成方式 |
|--------|----------|
| **MarkdownEditorPreview** | 将 `<textarea>` 包装为 `WritingSuggestionsEditor`，或通过 `ref` + `onKeyDown` 在父组件中处理 |
| **WikitextEditorPreview** | 同上 |
| **WechatDraftEditor** | 可选，与 Markdown 共用逻辑 |

**推荐**：抽一个 `useWritingSuggestions(textareaRef, value, onInsert)` hook，负责：
- 通过「写作建议」按钮触发
- 获取 `selectionStart/End`，截取 `text_before`、`text_after`
- 调用 API，展示 Popover
- 插入时 `onInsert(insertText)` 回调给父组件

### 4.3 光标坐标计算

```javascript
// 使用 textarea 的 selectionStart 配合 measureText 或 mirror div 估算光标像素位置
// 或使用：https://github.com/component/textarea-caret-position
import textareaCaretPosition from 'textarea-caret-position'
const { top, left } = textareaCaretPosition(textareaRef.current, selectionStart)
```

## 五、后端设计

### 5.1 API

```
POST /api/writing-suggestions
Content-Type: application/json

Request:
{
  "text_before": "AI 编程新范式包括",   // 光标前文本，建议 200–500 字
  "text_after": "",                    // 光标后文本，建议 50–100 字
  "format": "markdown" | "wikitext",   // 输出格式
  "max_suggestions": 5                 // 可选，默认 5
}

Response:
{
  "suggestions": [
    "vibe coding、harness engineering 等",
    "从 vibe coding 到 harness engineering",
    "vibe coding 与 harness engineering 等新兴范式"
  ]
}
```

### 5.2 Agent / 服务

- **无会话**：每次请求独立，不依赖历史
- **无工具**：仅 LLM 文本生成
- **轻量**：`max_tokens` 约 100–200，`temperature` 0.3–0.5
- **模型**：可用 `CHAT_MODEL` 或单独配置 `WRITING_SUGGESTIONS_MODEL`

### 5.3 Prompt 模板（示意）

```
你是写作助手。根据用户光标前的文本，给出 1–5 条简短的续写或改写建议。
- 每条建议不超过 30 字，可直接插入
- 输出格式：{format}
- 保持与上下文风格一致

【光标前】
{text_before}

【光标后】
{text_after}

请直接输出 JSON：{"suggestions": ["建议1", "建议2", ...]}
```

## 六、实现阶段

| 阶段 | 内容 | 预估 |
|------|------|------|
| **P0** | 后端 API + 轻量 Agent | 0.5d |
| **P1** | 前端 Popover 组件 + `useWritingSuggestions` hook | 0.5d |
| **P2** | 集成到 MarkdownEditorPreview | 0.25d |
| **P3** | 集成到 WikitextEditorPreview | 0.25d |
| **P4** | 键盘导航、防抖、错误处理 | 0.25d |

## 七、可选增强

- **防抖**：用户停止输入 300–500ms 后再请求，减少无效调用
- **缓存**：相同 `text_before` 短时内复用结果
- **流式**：若希望「边生成边展示」，可改为 SSE，但会增加复杂度
- **上下文**：可选传入 `page_title`、`section_title` 提升建议质量

## 八、依赖

- 前端：可选 `textarea-caret-position` 或自实现光标坐标
- 后端：复用现有 `LLMService`，无新依赖
