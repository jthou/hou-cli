# TODO-005: 前端 UI 文档更新计划

## 需要更新的文档清单

根据前端 UI 改进方案（`005-frontend-ui-improvements.md`），以下 `docs/design` 目录下的文档需要更新：

---

## 优先级 P0（必须更新）

### 1. `04-rich-ui-guide.md` ⚠️ **高优先级**

**需要更新的内容**:

#### 1.1 流式渲染示例（第 171-177 行）
**当前**:
```python
# 流式渲染
async def stream_generator():
    yield "# 标题\n\n"
    yield "这是 **粗体** 文本"

stream_renderer = StreamRenderer(factory)
await stream_renderer.render_stream(stream_generator(), console)
```

**需要更新为**:
- 说明使用 Rich Live 组件避免重复显示
- 更新流式渲染的实现方式

#### 1.2 LLM 问答界面示例（第 259-309 行）
**当前**:
```python
# 非流式响应
console.print(ChatPanel(response))

# 流式响应
console.print("[bold green]回答:[/bold green] ", end="")
await stream_renderer.render_stream(stream_generator(), console)
```

**需要更新为**:
- 非流式响应：不使用 Panel，直接显示内容
- 流式响应：不显示前缀，直接显示内容
- 移除 `ChatPanel` 的使用示例

#### 1.3 Panel 使用说明（第 69-88 行）
**当前**: 详细介绍 Panel 的使用

**需要更新为**:
- 说明 Panel 主要用于特殊场景（如错误提示、状态显示）
- 普通对话回复不使用 Panel
- 添加"简洁风格"的最佳实践

**更新位置**:
- 第 69-88 行：Panel 使用说明
- 第 171-177 行：流式渲染示例
- 第 259-309 行：LLM 问答界面示例
- 第 360-398 行：最佳实践部分

---

### 2. `02-streaming-response.md` ⚠️ **高优先级**

**需要更新的内容**:

#### 2.1 前端流式渲染说明（第 112 行）
**当前**:
```
4. ✅ 前端 UI 实时显示流式输出
```

**需要更新为**:
- 说明使用 Rich Live 组件实现实时更新
- 说明避免重复显示的策略
- 添加流式渲染的实现细节

**更新位置**:
- 第 112 行：实现步骤说明
- 可能需要添加新的章节说明前端渲染实现

---

### 3. `00-architecture-design.md` ⚠️ **中优先级**

**需要更新的内容**:

#### 3.1 前端 UI 层描述（第 80-93 行）
**当前**: 描述了前端 UI 层的功能

**需要更新为**:
- 说明简洁的 UI 风格（参考 Cursor Agent）
- 说明不使用过多 Panel 的设计原则
- 说明流式输出的实时渲染方式

#### 3.2 代码示例（第 376-385 行）
**当前**:
```python
from frontend.ui.panels import ChatPanel
console.print(ChatPanel(response))
```

**需要更新为**:
- 移除 `ChatPanel` 的使用
- 使用直接渲染的方式

**更新位置**:
- 第 80-93 行：前端 UI 层描述
- 第 376-385 行：代码示例

---

## 优先级 P1（应该更新）

### 4. `04-getting-started.md` ⚠️ **中优先级**

**需要更新的内容**:

#### 4.1 使用示例（第 71 行）
**当前**:
```
Agent: 处理任务: 你好
```

**需要更新为**:
- 更新为简洁的输出格式
- 移除 "Agent:" 前缀
- 或使用简洁的符号（如 `▸`）

**更新位置**:
- 第 71 行：使用示例

---

### 5. `03-implementation-guide.md` ⚠️ **中优先级**

**需要更新的内容**:

#### 5.1 UI 实现示例（第 275-330 行）
**当前**:
```python
# frontend/ui/panels.py
from rich.panel import Panel

def chat_panel(message: str, role: str = "assistant") -> Panel:
    return Panel(...)

# 使用示例
console.print(chat_panel("响应内容"))
```

**需要更新为**:
- 说明 Panel 主要用于特殊场景
- 普通对话使用直接渲染
- 更新实现示例

**更新位置**:
- 第 275-330 行：UI 实现示例

---

## 优先级 P2（建议更新）

### 6. `04-quick-reference.md` ⚠️ **低优先级**

**需要更新的内容**:

#### 6.1 功能特性说明
**当前**: 可能包含 UI 相关的说明

**需要更新为**:
- 更新 UI 风格说明
- 说明简洁的设计原则

---

## 更新内容总结

### 主要更新点

1. **移除 Panel 的使用**
   - 普通对话回复不使用 Panel
   - Panel 仅用于特殊场景（错误提示、状态显示）

2. **简化流式输出**
   - 使用 Rich Live 组件避免重复显示
   - 不显示 Agent 前缀
   - 直接显示内容

3. **更新代码示例**
   - 所有使用 `ChatPanel` 的示例改为直接渲染
   - 更新流式渲染的实现方式

4. **添加最佳实践**
   - 简洁风格的设计原则
   - 与 Cursor Agent 风格对齐

---

## 更新计划

### 阶段 1: 核心文档更新（P0）
1. ✅ 更新 `04-rich-ui-guide.md`
   - 更新流式渲染示例
   - 更新 LLM 问答界面示例
   - 更新 Panel 使用说明
   - 添加简洁风格最佳实践

2. ✅ 更新 `02-streaming-response.md`
   - 更新前端渲染实现说明
   - 添加避免重复显示的策略

3. ✅ 更新 `00-architecture-design.md`
   - 更新前端 UI 层描述
   - 更新代码示例

### 阶段 2: 辅助文档更新（P1）
4. ⏳ 更新 `04-getting-started.md`
   - 更新使用示例

5. ⏳ 更新 `03-implementation-guide.md`
   - 更新 UI 实现示例

### 阶段 3: 参考文档更新（P2）
6. ⏳ 更新 `04-quick-reference.md`
   - 更新功能特性说明

---

## 更新后的文档结构

### `04-rich-ui-guide.md` 更新后应包含：

1. **简洁风格设计原则**（新增）
   - 参考 Cursor Agent 风格
   - 不使用过多 Panel
   - 直接显示内容

2. **流式渲染最佳实践**（更新）
   - 使用 Rich Live 组件
   - 避免重复显示
   - 实时更新渲染

3. **Panel 使用场景**（更新）
   - 仅用于特殊场景
   - 错误提示
   - 状态显示

4. **代码示例**（更新）
   - 移除 `ChatPanel` 的使用
   - 使用直接渲染
   - 简洁的输出格式

---

## 验收标准

- [ ] `04-rich-ui-guide.md` 已更新，反映简洁风格
- [ ] `02-streaming-response.md` 已更新流式渲染说明
- [ ] `00-architecture-design.md` 已更新代码示例
- [ ] 所有文档中的 `ChatPanel` 示例已移除或更新
- [ ] 添加了简洁风格的最佳实践
- [ ] 文档与代码实现一致

---

**创建时间**: 2025-01-02  
**优先级**: P0  
**状态**: 待更新
