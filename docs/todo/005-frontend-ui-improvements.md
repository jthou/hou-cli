# TODO-005: 前端 UI 改进 - 与 Cursor Agent 风格对齐

## 问题分析

### 当前实现的问题

#### 1. 流式输出重复显示问题 ⚠️
**位置**: `frontend/ui/stream_handler.py` 第 102-144 行

**问题**:
- 流式输出时先显示 dim 文本预览
- 流式结束后重新渲染完整内容
- 导致内容显示两次（一次预览，一次渲染）

**代码**:
```python
# 流式时实时显示 chunk（作为纯文本预览）
if show_incomplete:
    console.print(chunk, end="", style="dim")

# 流式结束，渲染完整内容
renderer = self.factory.get_renderer(full_content)
rendered = renderer.render(full_content)
console.print(rendered)  # 这里会重复显示
```

**影响**: 用户体验不佳，内容重复显示

#### 2. Agent 前缀不够简洁 ⚠️
**位置**: `frontend/main.py` 第 32 行

**当前**:
```python
console.print("[bold cyan]Agent: [/bold cyan]", end="")
```

**问题**: 
- Cursor Agent 通常使用更简洁的提示符（如 `>` 或 `▸`）
- 或者不显示前缀，直接显示内容

#### 3. 会话 ID 显示 ⚠️
**位置**: `frontend/main.py` 第 85 行

**当前**:
```python
console.print(f"[dim]会话 ID: {session_id}[/dim]\n")
```

**问题**:
- Cursor Agent 通常不显示会话 ID（对用户不友好）
- 会话 ID 是技术细节，不应该暴露给用户

#### 4. Banner 过于复杂 ⚠️
**位置**: `frontend/ui/banner.py`

**问题**:
- ASCII 艺术字可能过于花哨
- Cursor Agent 通常使用更简洁的启动画面
- 或者不显示 banner，直接进入交互

#### 5. 非流式响应使用 Panel ⚠️
**位置**: `frontend/main.py` 第 77, 101 行

**当前**:
```python
console.print(ChatPanel(response))
```

**问题**:
- Cursor Agent 通常不使用 Panel 包装回复
- 直接显示内容，更简洁

#### 6. 错误提示不够友好 ⚠️
**位置**: `frontend/main.py` 多处

**当前**:
```python
console.print(f"[bold red]错误: {e}[/bold red]")
```

**问题**:
- 错误信息可能不够详细
- 缺少建议的解决方案

---

## Cursor Agent 风格特点

### 1. 简洁的提示符
- 用户输入: 通常使用 `>` 或 `▸` 作为提示符
- Agent 回复: 不显示前缀，直接显示内容

### 2. 流式输出
- 实时显示，不重复
- 支持 Markdown 实时渲染
- 代码块有语法高亮

### 3. 简洁的界面
- 不显示技术细节（如会话 ID）
- 不使用过多的 Panel 和边框
- 直接显示内容

### 4. 清晰的视觉区分
- 用户输入和 Agent 回复有明显的视觉区分
- 使用颜色区分不同类型的内容

---

## 改进方案

### 优先级 P0（必须修复）

#### 1. 修复流式输出重复显示问题

**方案 A: 使用 Live 组件（推荐）**
```python
from rich.live import Live
from rich.console import Group

async def render_stream(self, stream, console):
    full_content = ""
    with Live(console=console, refresh_per_second=10) as live:
        async for chunk in stream:
            full_content += chunk
            renderer = self.factory.get_renderer(full_content)
            rendered = renderer.render(full_content)
            live.update(rendered)
    
    # 流式结束后，最终渲染一次
    renderer = self.factory.get_renderer(full_content)
    rendered = renderer.render(full_content)
    console.print(rendered)
```

**方案 B: 只显示一次（简单）**
```python
async def render_stream(self, stream, console):
    full_content = ""
    async for chunk in stream:
        full_content += chunk
        # 不实时显示，只收集
    
    # 流式结束后，一次性渲染
    renderer = self.factory.get_renderer(full_content)
    rendered = renderer.render(full_content)
    console.print(rendered)
```

**推荐**: 方案 A，提供实时反馈

#### 2. 简化 Agent 前缀

**当前**:
```python
console.print("[bold cyan]Agent: [/bold cyan]", end="")
```

**改进**:
```python
# 选项 1: 不显示前缀
# 直接显示内容

# 选项 2: 使用简洁的符号
console.print("[dim]▸[/dim] ", end="")

# 选项 3: 使用颜色区分
console.print("[dim cyan]▸[/dim cyan] ", end="")
```

**推荐**: 选项 1，不显示前缀，直接显示内容

#### 3. 移除会话 ID 显示

**当前**:
```python
console.print(f"[dim]会话 ID: {session_id}[/dim]\n")
```

**改进**:
```python
# 移除这行，不显示会话 ID
# 会话 ID 在后台管理，用户不需要知道
```

### 优先级 P1（应该修复）

#### 4. 简化 Banner

**当前**: 复杂的 ASCII 艺术字

**改进**:
```python
def show_banner():
    """简洁的启动画面"""
    console.print("[bold cyan]hou-cli[/bold cyan] - LLM Agent CLI")
    console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
```

**或者**: 不显示 banner，直接进入交互

#### 5. 简化非流式响应显示

**当前**:
```python
console.print(ChatPanel(response))
```

**改进**:
```python
# 直接显示内容，不使用 Panel
renderer = _renderer_factory.get_renderer(response)
rendered = renderer.render(response)
console.print(rendered)
```

#### 6. 改进错误提示

**当前**:
```python
console.print(f"[bold red]错误: {e}[/bold red]")
```

**改进**:
```python
console.print(f"[bold red]✗ 错误[/bold red]: {e}")
console.print("[dim]提示: 请检查后端服务是否正常运行[/dim]")
```

### 优先级 P2（建议修复）

#### 7. 改进用户输入提示

**当前**:
```python
msg = console.input("[bold cyan]你: [/bold cyan]")
```

**改进**:
```python
# 选项 1: 使用简洁的提示符
msg = console.input("[dim cyan]▸[/dim cyan] ")

# 选项 2: 使用 > 符号
msg = console.input("[cyan]>[/cyan] ")

# 选项 3: 不显示提示符（Cursor Agent 风格）
msg = console.input()
```

**推荐**: 选项 1 或 2，保持简洁

#### 8. 改进流式输出的实时渲染

**当前**: 流式时显示 dim 文本，结束后重新渲染

**改进**: 使用 Rich Live 组件实时更新渲染内容

---

## 实现计划

### 阶段 1: 修复核心问题（P0）
1. ✅ 修复流式输出重复显示问题
2. ✅ 简化 Agent 前缀
3. ✅ 移除会话 ID 显示

### 阶段 2: 改进用户体验（P1）
4. ✅ 简化 Banner
5. ✅ 简化非流式响应显示
6. ✅ 改进错误提示

### 阶段 3: 优化细节（P2）
7. ⏳ 改进用户输入提示
8. ⏳ 改进流式输出的实时渲染

---

## 参考实现

### Cursor Agent 风格示例

```python
# 用户输入
> 你好

# Agent 回复（直接显示，无前缀）
你好！我是你的 AI 助手。

# 流式输出（实时显示，不重复）
正在思考...
```

### 改进后的实现示例

```python
# 用户输入
▸ 你好

# Agent 回复（直接显示，无前缀）
你好！我是你的 AI 助手。

# 流式输出（实时显示，不重复）
正在思考...
```

---

## 验收标准

- [ ] 流式输出不重复显示
- [ ] Agent 回复无前缀或使用简洁符号
- [ ] 不显示会话 ID
- [ ] Banner 简洁或不显示
- [ ] 非流式响应不使用 Panel
- [ ] 错误提示友好且有建议
- [ ] 整体风格与 Cursor Agent 一致

---

**创建时间**: 2025-01-02  
**优先级**: P0  
**状态**: 待实现
