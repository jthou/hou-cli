# Rich UI 使用指南

## 概述

本项目使用 [Rich](https://github.com/Textualize/rich) 库来提供终端内的富文本用户界面。Rich 是一个强大的 Python 库，可以在终端中渲染美观的文本、表格、进度条等组件。

## 为什么使用 Rich UI？

### 优势

1. **提升用户体验**
   - 美观的表格和面板
   - 实时进度显示
   - 语法高亮和 Markdown 支持
   - 丰富的颜色和样式

2. **无需前后端分离**
   - 在终端内直接渲染
   - 单进程运行
   - 不需要 HTTP 服务器
   - 不需要 WebSocket 连接

3. **简单易用**
   - Python 原生库
   - 丰富的组件
   - 良好的文档
   - 活跃的社区

## 安装

```bash
pip install rich
```

## 核心概念

### Rich UI 不是 Web 前端

**重要区别**：

| 特性 | Rich UI | Web 前端 |
|------|---------|---------|
| 运行环境 | 终端/控制台 | 浏览器 |
| 渲染方式 | 直接输出 ANSI 转义码 | HTML/CSS/JavaScript |
| 进程模型 | 单进程（Python） | 前后端分离 |
| 通信方式 | 函数调用 | HTTP/WebSocket |
| 部署方式 | 本地安装 | 需要服务器 |

**结论**：Rich UI 是 CLI 工具的用户界面层，不是独立的前端应用。

## 常用组件

### 1. Console - 控制台输出

```python
from rich.console import Console

console = Console()

# 基本输出
console.print("Hello, World!")

# 带样式的输出
console.print("[bold red]错误[/bold red]")
console.print("[green]成功[/green]")
console.print("[yellow]警告[/yellow]")
```

### 2. Panel - 面板容器

**使用场景**：
- Panel 主要用于**特殊场景**，如错误提示、状态显示、重要信息展示
- **普通对话回复不使用 Panel**，直接显示内容，保持简洁风格（参考 Cursor Agent）

```python
from rich.panel import Panel
from rich.console import Console

console = Console()

# 基本面板（用于特殊场景）
console.print(Panel("内容"))

# 带标题的面板
console.print(Panel("内容", title="标题"))

# 带边框样式的面板
console.print(Panel("内容", border_style="green"))

# 自适应宽度
console.print(Panel.fit("内容"))

# 错误提示（推荐使用 Panel）
console.print(Panel(
    "[bold red]错误信息[/bold red]",
    border_style="red",
    title="[bold red]错误[/bold red]"
))
```

### 3. Table - 表格

```python
from rich.table import Table
from rich.console import Console

console = Console()

table = Table(title="数据表")
table.add_column("列1", style="cyan")
table.add_column("列2", style="magenta")
table.add_column("列3", style="green")

table.add_row("值1", "值2", "值3")
table.add_row("值4", "值5", "值6")

console.print(table)
```

### 4. Progress - 进度条

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.console import Console
import time

console = Console()

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    console=console
) as progress:
    task = progress.add_task("处理中...", total=100)
    for i in range(100):
        time.sleep(0.01)
        progress.update(task, advance=1)
```

### 5. Markdown - Markdown 渲染

**基础用法**:

```python
from rich.markdown import Markdown
from rich.console import Console

console = Console()

markdown_text = """
# 标题

这是一个 **粗体** 文本和 *斜体* 文本。

- 列表项 1
- 列表项 2
"""

console.print(Markdown(markdown_text))
```

**项目中的智能渲染模块**:

本项目实现了智能的 Markdown 渲染模块（`frontend/ui/renderer.py`），可以自动识别内容类型并选择合适的渲染器：

```python
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer
from rich.console import Console

console = Console()
factory = RendererFactory()

# 自动识别并渲染内容
content = "# 标题\n\n这是 **粗体** 文本"
renderer = factory.get_renderer(content)
rendered = renderer.render(content)
console.print(rendered)

# 流式渲染（使用 Rich Live 组件避免重复显示）
from rich.live import Live

async def stream_generator():
    yield "# 标题\n\n"
    yield "这是 **粗体** 文本"

# 使用 Live 组件实时更新，避免重复显示
full_content = ""
with Live(console=console, refresh_per_second=10) as live:
    async for chunk in stream_generator():
        full_content += chunk
        renderer = factory.get_renderer(full_content)
        rendered = renderer.render(full_content)
        live.update(rendered)

# 流式结束后，最终渲染一次
renderer = factory.get_renderer(full_content)
rendered = renderer.render(full_content)
console.print(rendered)
```

**特性**:
- 自动识别 Markdown、代码块、纯文本
- 代码块优先检测，避免误判
- 流式响应实时渲染（使用 Rich Live 组件）
- 避免重复显示（流式时实时更新，结束后最终渲染）
- 错误降级处理（Markdown 解析失败时降级到纯文本）

### 6. Syntax - 代码语法高亮

**基础用法**:

```python
from rich.syntax import Syntax
from rich.console import Console

console = Console()

code = """
def hello():
    print("Hello, World!")
"""

syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
console.print(syntax)
```

**项目中的代码块渲染**:

通过 `CodeRenderer` 自动识别和渲染代码块：

```python
from frontend.ui.renderer import CodeRenderer

renderer = CodeRenderer()
code_block = "```python\nprint('hello')\n```"
result = renderer.render(code_block)
console.print(result)
```

### 7. Prompt - 交互式提示

```python
from rich.prompt import Prompt, Confirm

# 文本输入
name = Prompt.ask("请输入你的名字")

# 选择
choice = Prompt.ask("选择", choices=["选项1", "选项2", "选项3"])

# 确认
if Confirm.ask("是否继续？"):
    print("继续")
```

### 8. Live - 实时更新界面

```python
from rich.live import Live
from rich.table import Table
from rich.console import Console
import time

console = Console()

def generate_table():
    table = Table()
    table.add_column("时间")
    table.add_column("状态")
    table.add_row(time.strftime("%H:%M:%S"), "运行中")
    return table

with Live(generate_table(), refresh_per_second=4) as live:
    for _ in range(10):
        time.sleep(1)
        live.update(generate_table())
```

## 在项目中的应用示例

### 示例 1：LLM 问答界面（简洁风格，参考 Cursor Agent）

```python
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from frontend.ui.renderer import RendererFactory

console = Console()
factory = RendererFactory()

# 非流式响应（简洁风格，不使用 Panel）
def ask_question(question: str):
    # 用户输入提示（简洁的提示符）
    console.print(f"[dim cyan]▸[/dim cyan] {question}")
    
    # 显示思考进度（可选）
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("思考中...", total=None)
        response = get_llm_response(question)  # 获取 LLM 响应
        progress.update(task, completed=True)
    
    # 直接渲染内容，不使用 Panel（简洁风格）
    renderer = factory.get_renderer(response)
    rendered = renderer.render(response)
    console.print(rendered)
    console.print()  # 空行分隔

# 流式响应（使用 Rich Live 组件避免重复显示）
async def ask_question_stream(question: str):
    # 用户输入提示（简洁的提示符）
    console.print(f"[dim cyan]▸[/dim cyan] {question}")
    
    # 使用 Live 组件实时更新，避免重复显示
    full_content = ""
    renderer = factory.get_renderer("")
    
    async def stream_generator():
        async for chunk in get_llm_stream(question):
            yield chunk
    
    with Live(console=console, refresh_per_second=10) as live:
        async for chunk in stream_generator():
            full_content += chunk
            renderer = factory.get_renderer(full_content)
            rendered = renderer.render(full_content)
            live.update(rendered)
    
    # 流式结束后，最终渲染一次
    renderer = factory.get_renderer(full_content)
    rendered = renderer.render(full_content)
    console.print(rendered)
    console.print()  # 空行分隔
```

### 示例 2：PDF 处理进度

```python
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel

console = Console()

def process_pdf(file_path: str):
    console.print(f"[yellow]正在处理: {file_path}[/yellow]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        # 模拟处理步骤
        steps = ["加载PDF", "提取文本", "向量化", "生成摘要"]
        for i, step in enumerate(steps):
            task = progress.add_task(step, total=100)
            # 处理逻辑...
            progress.update(task, completed=100)
    
    console.print(Panel("[green]处理完成![/green]", border_style="green"))
```

### 示例 3：数据展示表格

```python
from rich.table import Table
from rich.console import Console

console = Console()

def show_model_info():
    table = Table(title="模型信息", show_header=True, header_style="bold magenta")
    table.add_column("模型名称", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("版本")
    
    table.add_row("deepseek-r1:14b", "✅ 可用", "v1.0")
    table.add_row("nomic-embed-text", "✅ 可用", "v1.0")
    
    console.print(table)
```

## 最佳实践

### 0. UI 设计原则（参考 Cursor Agent）

**核心原则**：

1. **简洁优先**
   - ✅ 不使用过多的装饰元素
   - ✅ 直接显示内容，减少视觉噪音
   - ✅ 保持界面清爽

2. **一致性**
   - ✅ 统一的提示符风格（`▸` 或 `>`）
   - ✅ 统一的颜色使用
   - ✅ 统一的交互方式

3. **清晰性**
   - ✅ 用户输入和 Agent 回复有明显的视觉区分
   - ✅ 错误信息清晰明确
   - ✅ 状态反馈及时

4. **专业性**
   - ✅ 不显示技术细节（如会话 ID、内部状态）
   - ✅ 专注于用户任务
   - ✅ 提供有用的反馈

**具体实践**：

- ✅ **直接显示内容**：普通对话回复不使用 Panel，直接显示内容
- ✅ **简洁的提示符**：使用 `▸` 或 `>` 作为用户输入提示，不使用冗长的前缀
- ✅ **不显示技术细节**：不显示会话 ID 等技术细节
- ✅ **流式输出不重复**：使用 Rich Live 组件避免重复显示
- ✅ **清晰的视觉区分**：用户输入和 Agent 回复有明显的视觉区分

**示例**：
```python
# ✅ 推荐：简洁风格
console.print(f"[dim cyan]▸[/dim cyan] {user_input}")
renderer = factory.get_renderer(response)
console.print(renderer.render(response))

# ❌ 不推荐：使用 Panel 包装普通回复
console.print(Panel(response, title="Agent"))
```

### 1. 统一使用 Console 实例

```python
# 推荐：创建全局 console 实例
from rich.console import Console

console = Console()

# 不推荐：每次都创建新实例
# console = Console()  # 在函数中重复创建
```

### 2. 合理使用颜色和样式

```python
# 推荐：使用语义化的样式
console.print("[error]错误信息[/error]")
console.print("[success]成功信息[/success]")
console.print("[warning]警告信息[/warning]")

# 或者使用标准颜色
console.print("[red]错误[/red]")
console.print("[green]成功[/green]")
console.print("[yellow]警告[/yellow]")
```

### 3. 处理长文本

```python
from rich.text import Text

# 自动换行
console.print("很长的文本...", overflow="fold")

# 截断
console.print("很长的文本...", overflow="ellipsis")
```

### 4. 错误处理

**设计原则**：
- ✅ 错误信息清晰明确
- ✅ 提供解决建议
- ✅ 使用 Panel 突出显示错误（特殊场景）
- ✅ 区分错误类型（网络错误、API 错误、配置错误等）

**基础用法**：
```python
from rich.console import Console
from rich.traceback import install

# 安装 Rich 的 traceback 处理器
install(show_locals=True)

console = Console()

try:
    # 可能出错的代码
    pass
except Exception as e:
    console.print_exception()  # 美观的错误显示
```

**错误提示示例**（使用 Panel，特殊场景）：
```python
from rich.panel import Panel

# 错误提示（使用 Panel 突出显示）
console.print(Panel(
    f"[bold red]✗ 错误[/bold red]: {error_message}\n"
    "[dim]提示: 请检查后端服务是否正常运行[/dim]",
    border_style="red",
    title="[bold red]错误[/bold red]"
))
```

## 性能考虑

1. **避免频繁创建对象**
   ```python
   # 不推荐：在循环中创建
   for i in range(1000):
       table = Table()  # 每次都创建新对象
   
   # 推荐：复用对象
   table = Table()
   for i in range(1000):
       table.add_row(...)
   ```

2. **使用 Live 组件进行实时更新（流式输出推荐）**
   ```python
   # 适合实时更新的场景（如流式输出）
   # 使用 Live 组件可以避免重复显示问题
   full_content = ""
   with Live(console=console, refresh_per_second=10) as live:
       async for chunk in stream:
           full_content += chunk
           rendered = render_content(full_content)
           live.update(rendered)
   
   # 流式结束后，最终渲染一次
   console.print(render_content(full_content))
   ```

3. **大量数据考虑分页**
   ```python
   # 对于大量数据，考虑分页显示
   from rich.pager import Pager
   
   with Pager() as pager:
       pager.print(large_content)
   ```

## 总结

Rich UI 为 CLI 工具提供了强大的终端界面能力，同时保持了单进程架构的简单性。它**不是传统的前后端分离架构**，而是 CLI 工具的用户界面层，直接在终端中渲染，无需网络通信。

## 参考资源

- [Rich 官方文档](https://rich.readthedocs.io/)
- [Rich GitHub 仓库](https://github.com/Textualize/rich)
- [Rich 示例](https://github.com/Textualize/rich/tree/master/examples)

