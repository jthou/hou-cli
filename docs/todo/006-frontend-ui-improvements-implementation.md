# TODO-006: 前端 UI 改进实现任务

## 任务概述

根据设计文档和前端 UI 改进方案（`005-frontend-ui-improvements.md`），实现与 Cursor Agent 风格对齐的简洁 UI。

**优先级**: P0（高优先级）  
**预计工时**: 1-2 天  
**创建时间**: 2025-01-02  
**状态**: ✅ 已完成

---

## 任务目标

1. ✅ 修复流式输出重复显示问题
2. ✅ 简化 Agent 前缀（移除或使用简洁符号）
3. ✅ 移除会话 ID 显示
4. ✅ 简化 Banner
5. ✅ 简化非流式响应显示（移除 Panel）
6. ✅ 改进错误提示

---

## 任务分解

### 阶段 1: 修复核心问题（P0）🔴

#### 任务 1.1: 修复流式输出重复显示问题

**文件**: `frontend/ui/stream_handler.py`

**当前问题**:
- 流式输出时先显示 dim 文本预览
- 流式结束后重新渲染完整内容
- 导致内容显示两次

**实现方案**: 使用 Rich Live 组件实时更新

**实现步骤**:

1. **导入 Rich Live 组件**
   ```python
   from rich.live import Live
   ```

2. **修改 `StreamRenderer.render_stream` 方法**
   - 移除 `show_incomplete` 参数和预览显示逻辑
   - 使用 Live 组件实时更新渲染内容
   - 流式结束后最终渲染一次

3. **实现代码**:
   ```python
   async def render_stream(
       self,
       stream: AsyncIterator[str],
       console: Console,
   ):
       """渲染流式响应（使用 Live 组件避免重复显示）"""
       full_content = ""
       
       # 使用 Live 组件实时更新
       with Live(console=console, refresh_per_second=10) as live:
           async for chunk in stream:
               full_content += chunk
               # 实时渲染当前内容
               renderer = self.factory.get_renderer(full_content)
               rendered = renderer.render(full_content)
               live.update(rendered)
       
       # 流式结束后，最终渲染一次（确保完整渲染）
       if full_content:
           renderer = self.factory.get_renderer(full_content)
           rendered = renderer.render(full_content)
           console.print(rendered)
   ```

**验收标准**:
- [ ] 流式输出不重复显示
- [ ] 实时更新渲染内容
- [ ] 支持 Markdown 和代码块实时渲染

---

#### 任务 1.2: 简化 Agent 前缀

**文件**: `frontend/main.py`

**当前问题**:
- 第 32 行显示 `Agent: ` 前缀
- 不够简洁

**实现方案**: 移除前缀，直接显示内容

**实现步骤**:

1. **修改 `_stream_chat` 函数**
   - 移除第 32 行的 `console.print("[bold cyan]Agent: [/bold cyan]", end="")`
   - 直接开始渲染流式内容

2. **实现代码**:
   ```python
   async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
       """流式聊天（异步）"""
       # 移除 Agent 前缀，直接显示内容
       try:
           factory = RendererFactory()
           stream_renderer = StreamRenderer(factory)
           
           async def stream_generator():
               async for chunk in client.stream_send(message, session_id=session_id):
                   yield chunk
           
           await stream_renderer.render_stream(stream_generator(), console)
           console.print()  # 换行
           
           return True
       except Exception as e:
           console.print(f"\n[bold red]✗ 错误[/bold red]: {e}")
           return None
   ```

**验收标准**:
- [ ] Agent 回复无前缀
- [ ] 直接显示内容

---

#### 任务 1.3: 移除会话 ID 显示

**文件**: `frontend/main.py`

**当前问题**:
- 第 85 行显示会话 ID
- 对用户不友好

**实现方案**: 移除显示，会话 ID 在后台管理

**实现步骤**:

1. **修改 `chat` 函数**
   - 移除第 85 行的 `console.print(f"[dim]会话 ID: {session_id}[/dim]\n")`
   - 会话 ID 继续在后台使用，但不显示给用户

2. **实现代码**:
   ```python
   # 交互式模式
   show_banner()
   console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
   # 移除会话 ID 显示
   
   while True:
       # ...
   ```

**验收标准**:
- [ ] 不显示会话 ID
- [ ] 会话 ID 在后台正常使用

---

### 阶段 2: 改进用户体验（P1）🟡

#### 任务 2.1: 简化 Banner

**文件**: `frontend/ui/banner.py`

**当前问题**:
- ASCII 艺术字过于复杂
- 不够简洁

**实现方案**: 使用简洁的启动画面

**实现步骤**:

1. **修改 `show_banner` 函数**
   - 移除复杂的 ASCII 艺术字
   - 使用简洁的文本提示

2. **实现代码**:
   ```python
   def show_banner():
       """简洁的启动画面（参考 Cursor Agent）"""
       console.print("[bold cyan]hou-cli[/bold cyan] - LLM Agent CLI")
       console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
   ```

**验收标准**:
- [ ] Banner 简洁
- [ ] 包含必要信息（应用名称、退出提示）

---

#### 任务 2.2: 简化非流式响应显示

**文件**: `frontend/main.py`

**当前问题**:
- 第 77, 101 行使用 `ChatPanel` 包装回复
- 不够简洁

**实现方案**: 直接渲染内容，不使用 Panel

**实现步骤**:

1. **修改非流式响应处理**
   - 移除 `ChatPanel` 的使用
   - 使用 `RendererFactory` 直接渲染内容

2. **实现代码**:
   ```python
   # 非流式响应
   response = client.send(message, session_id=session_id)
   # 直接渲染内容，不使用 Panel
   factory = RendererFactory()
   renderer = factory.get_renderer(response)
   rendered = renderer.render(response)
   console.print(rendered)
   console.print()  # 空行分隔
   ```

3. **更新两处使用**:
   - 第 77 行：单次对话的非流式响应
   - 第 101 行：交互式模式的非流式响应

**验收标准**:
- [ ] 非流式响应不使用 Panel
- [ ] 内容正确渲染（Markdown、代码块等）

---

#### 任务 2.3: 改进错误提示

**文件**: `frontend/main.py`

**当前问题**:
- 错误提示不够友好
- 缺少解决建议

**实现方案**: 使用 Panel 显示错误（特殊场景），添加解决建议

**实现步骤**:

1. **创建错误处理函数**
   ```python
   def show_error(error: Exception, context: str = ""):
       """显示友好的错误提示"""
       from rich.panel import Panel
       
       error_msg = str(error)
       suggestion = ""
       
       # 根据错误类型提供建议
       if "ConnectionError" in str(type(error)) or "连接" in error_msg:
           suggestion = "提示: 请检查后端服务是否正常运行"
       elif "DEEPSEEK_API_KEY" in error_msg:
           suggestion = "提示: 请检查 .env 文件中的 DEEPSEEK_API_KEY 配置"
       else:
           suggestion = "提示: 请查看错误信息并重试"
       
       console.print(Panel(
           f"[bold red]✗ 错误[/bold red]: {error_msg}\n"
           f"[dim]{suggestion}[/dim]",
           border_style="red",
           title="[bold red]错误[/bold red]"
       ))
   ```

2. **更新错误处理位置**:
   - 第 50 行：流式聊天错误
   - 第 61-62 行：连接错误
   - 第 79 行：单次对话错误
   - 第 106 行：交互式模式错误

**验收标准**:
- [ ] 错误提示友好
- [ ] 包含解决建议
- [ ] 使用 Panel 突出显示（特殊场景）

---

### 阶段 3: 优化细节（P2）🟢

#### 任务 3.1: 改进用户输入提示

**文件**: `frontend/main.py`

**当前问题**:
- 第 89 行使用 `[bold cyan]你: [/bold cyan]`
- 不够简洁

**实现方案**: 使用简洁的提示符

**实现步骤**:

1. **修改用户输入提示**
   ```python
   # 选项 1: 使用简洁的提示符（推荐）
   msg = console.input("[dim cyan]▸[/dim cyan] ")
   
   # 选项 2: 使用 > 符号
   # msg = console.input("[cyan]>[/cyan] ")
   ```

2. **更新位置**: 第 89 行

**验收标准**:
- [ ] 提示符简洁
- [ ] 视觉清晰

---

## 实现计划

### 阶段 1: 核心问题修复（P0）- 预计 0.5 天

1. ✅ 任务 1.1: 修复流式输出重复显示问题
2. ✅ 任务 1.2: 简化 Agent 前缀
3. ✅ 任务 1.3: 移除会话 ID 显示

### 阶段 2: 用户体验改进（P1）- 预计 0.5 天

4. ✅ 任务 2.1: 简化 Banner
5. ✅ 任务 2.2: 简化非流式响应显示
6. ✅ 任务 2.3: 改进错误提示

### 阶段 3: 细节优化（P2）- 预计 0.5 天

7. ✅ 任务 3.1: 改进用户输入提示

---

## 详细实现步骤

### 步骤 1: 修复流式输出（任务 1.1）

**文件**: `frontend/ui/stream_handler.py`

1. 导入 `Live` 组件
2. 修改 `render_stream` 方法签名（移除 `show_incomplete` 参数）
3. 实现 Live 组件实时更新逻辑
4. 测试流式输出不重复显示

**代码变更**:
```python
# 修改前
async def render_stream(self, stream, console, show_incomplete=True):
    full_content = ""
    async for chunk in stream:
        full_content += chunk
        if show_incomplete:
            console.print(chunk, end="", style="dim")
    console.print()
    renderer = self.factory.get_renderer(full_content)
    console.print(renderer.render(full_content))

# 修改后
async def render_stream(self, stream, console):
    full_content = ""
    with Live(console=console, refresh_per_second=10) as live:
        async for chunk in stream:
            full_content += chunk
            renderer = self.factory.get_renderer(full_content)
            rendered = renderer.render(full_content)
            live.update(rendered)
    if full_content:
        renderer = self.factory.get_renderer(full_content)
        rendered = renderer.render(full_content)
        console.print(rendered)
```

---

### 步骤 2: 简化 Agent 前缀（任务 1.2）

**文件**: `frontend/main.py`

1. 移除第 32 行的 Agent 前缀
2. 测试流式输出直接显示内容

**代码变更**:
```python
# 修改前
async def _stream_chat(...):
    console.print("[bold cyan]Agent: [/bold cyan]", end="")
    # ...

# 修改后
async def _stream_chat(...):
    # 移除前缀，直接显示内容
    # ...
```

---

### 步骤 3: 移除会话 ID 显示（任务 1.3）

**文件**: `frontend/main.py`

1. 移除第 85 行的会话 ID 显示
2. 确认会话 ID 在后台正常使用

**代码变更**:
```python
# 修改前
show_banner()
console.print("[yellow]输入 'exit' 或 'quit' 退出[/yellow]")
console.print(f"[dim]会话 ID: {session_id}[/dim]\n")

# 修改后
show_banner()
console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
# 会话 ID 在后台使用，不显示给用户
```

---

### 步骤 4: 简化 Banner（任务 2.1）

**文件**: `frontend/ui/banner.py`

1. 修改 `show_banner` 函数
2. 移除复杂的 ASCII 艺术字
3. 使用简洁的文本

**代码变更**:
```python
# 修改前
def show_banner():
    ascii_art = r"""
    ░█░█░█▀▀░█░░░█░░░█▀█░░░░░█░█░█▀█░█░█░░░░░█▀▀░█░░░▀█▀
    ...
    """
    # 复杂的 Panel 和装饰

# 修改后
def show_banner():
    """简洁的启动画面（参考 Cursor Agent）"""
    console.print("[bold cyan]hou-cli[/bold cyan] - LLM Agent CLI")
    console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
```

---

### 步骤 5: 简化非流式响应（任务 2.2）

**文件**: `frontend/main.py`

1. 创建全局 `RendererFactory` 实例（或在使用时创建）
2. 修改第 77 行：移除 `ChatPanel`，使用直接渲染
3. 修改第 101 行：移除 `ChatPanel`，使用直接渲染

**代码变更**:
```python
# 在文件顶部创建全局工厂（可选）
_renderer_factory = RendererFactory()

# 修改前
response = client.send(message, session_id=session_id)
console.print(ChatPanel(response))

# 修改后
response = client.send(message, session_id=session_id)
factory = RendererFactory()  # 或使用全局实例
renderer = factory.get_renderer(response)
rendered = renderer.render(response)
console.print(rendered)
console.print()  # 空行分隔
```

---

### 步骤 6: 改进错误提示（任务 2.3）

**文件**: `frontend/main.py`

1. 创建 `show_error` 辅助函数
2. 更新所有错误处理位置使用新函数

**代码变更**:
```python
# 添加错误处理函数
def show_error(error: Exception, context: str = ""):
    """显示友好的错误提示"""
    from rich.panel import Panel
    
    error_msg = str(error)
    suggestion = ""
    
    # 根据错误类型提供建议
    if "ConnectionError" in str(type(error)) or "连接" in error_msg:
        suggestion = "提示: 请检查后端服务是否正常运行"
    elif "DEEPSEEK_API_KEY" in error_msg:
        suggestion = "提示: 请检查 .env 文件中的 DEEPSEEK_API_KEY 配置"
    else:
        suggestion = "提示: 请查看错误信息并重试"
    
    console.print(Panel(
        f"[bold red]✗ 错误[/bold red]: {error_msg}\n"
        f"[dim]{suggestion}[/dim]",
        border_style="red",
        title="[bold red]错误[/bold red]"
    ))

# 更新错误处理
# 修改前
console.print(f"[bold red]错误: {e}[/bold red]")

# 修改后
show_error(e)
```

---

### 步骤 7: 改进用户输入提示（任务 3.1）

**文件**: `frontend/main.py`

1. 修改第 89 行的用户输入提示

**代码变更**:
```python
# 修改前
msg = console.input("[bold cyan]你: [/bold cyan]")

# 修改后
msg = console.input("[dim cyan]▸[/dim cyan] ")
```

---

## 测试计划

### 单元测试

1. **流式渲染测试**
   - 测试 Live 组件实时更新
   - 测试不重复显示
   - 测试 Markdown 和代码块渲染

2. **错误处理测试**
   - 测试不同错误类型的提示
   - 测试错误 Panel 显示

### 集成测试

1. **端到端流式输出测试**
   - 启动后端和前端
   - 发送消息，验证流式输出不重复
   - 验证内容正确渲染

2. **端到端非流式输出测试**
   - 启动后端和前端
   - 发送消息（`--no-stream`），验证不使用 Panel
   - 验证内容正确渲染

3. **交互式模式测试**
   - 启动交互式模式
   - 验证不显示会话 ID
   - 验证简洁的提示符
   - 验证简洁的 Banner

4. **错误处理测试**
   - 测试后端未启动时的错误提示
   - 测试 API Key 未配置时的错误提示
   - 测试网络错误时的错误提示

### 手动测试清单

- [ ] 流式输出不重复显示
- [ ] Agent 回复无前缀
- [ ] 不显示会话 ID
- [ ] Banner 简洁
- [ ] 非流式响应不使用 Panel
- [ ] 错误提示友好且有建议
- [ ] 用户输入提示简洁
- [ ] 整体风格与 Cursor Agent 一致

---

## 验收标准

### 功能验收

- [ ] 流式输出不重复显示 ✅
- [ ] Agent 回复无前缀或使用简洁符号 ✅
- [ ] 不显示会话 ID ✅
- [ ] Banner 简洁或不显示 ✅
- [ ] 非流式响应不使用 Panel ✅
- [ ] 错误提示友好且有建议 ✅
- [ ] 用户输入提示简洁 ✅
- [ ] 整体风格与 Cursor Agent 一致 ✅

### 代码质量验收

- [ ] 代码符合项目规范
- [ ] 添加必要的注释
- [ ] 错误处理完善
- [ ] 测试覆盖充分

### 文档验收

- [ ] 更新相关代码注释
- [ ] 更新使用文档（如需要）

---

## 相关文档

- [前端 UI 改进方案](./005-frontend-ui-improvements.md)
- [设计文档更新计划](./005-frontend-ui-docs-update-plan.md)
- [Rich UI 使用指南](../design/04-rich-ui-guide.md)
- [流式响应设计](../design/02-streaming-response.md)

---

## 风险评估

### 低风险

- ✅ 修改范围明确
- ✅ 不影响后端逻辑
- ✅ 可以逐步实现和测试

### 注意事项

- ⚠️ 流式输出修改可能影响用户体验，需要充分测试
- ⚠️ 确保向后兼容（如果已有用户使用）

---

## 后续优化（可选）

1. **性能优化**
   - 优化 Live 组件的刷新频率
   - 优化渲染性能

2. **用户体验增强**
   - 添加加载动画
   - 添加进度指示

3. **可配置性**
   - 支持配置 UI 风格
   - 支持自定义提示符

---

**创建时间**: 2025-01-02  
**优先级**: P0  
**状态**: ✅ 已完成  
**完成时间**: 2025-01-02
