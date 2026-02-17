# CodeExecutorTool 交互改进方案

## 1. 现状分析

### 1.1 当前实现

**CodeExecutorTool 返回的数据结构**：
```python
ToolResult(
    success=True/False,
    data={
        "output": str,           # 标准输出
        "error": str,            # 错误输出
        "exit_code": int,        # 退出码
        "execution_time": float, # 执行时间（秒）
        "memory_used": float,    # 内存使用（MB）
        "language": str,         # 语言类型
        "explanation": str       # 说明（可选）
    },
    error=str  # 如果失败
)
```

**当前渲染方式**（`stream_handler.py` 的 `_render_tool_info`）：
- 显示工具名称：`🔧 TOOL: execute_code`
- 显示参数：JSON 格式，缩进显示
- 显示结果：如果是字典，转成 JSON，超过 200 字符截断
- 显示错误：红色文本

### 1.2 存在的问题

1. **代码内容不可见**
   - 用户看不到实际执行的代码
   - 只能看到参数 JSON，不够直观

2. **输出格式不友好**
   - 输出被转成 JSON 字符串，可读性差
   - 没有代码高亮
   - 长输出被截断（200 字符），看不到完整内容

3. **信息展示混乱**
   - 输出和错误混在一起
   - 执行统计信息（时间、内存）没有突出显示
   - 没有清晰的信息层次

4. **交互体验差**
   - 无法查看完整输出
   - 无法复制代码
   - 没有执行状态提示

## 2. 改进方案

### 2.1 设计目标

1. **清晰展示代码**：显示执行的代码内容，带语法高亮
2. **友好展示输出**：使用代码块格式，支持长输出
3. **突出关键信息**：执行状态、时间、内存使用
4. **区分输出和错误**：清晰分离标准输出和错误输出
5. **提升可读性**：使用 Rich 组件美化显示

### 2.2 改进后的显示格式

#### 成功执行示例

```
┌─────────────────────────────────────────────────┐
│ 🔧 代码执行: Python                                  │
├─────────────────────────────────────────────────┤
│                                                   │
│ 📝 代码:                                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ print("Hello, World!")                      │ │
│ │ x = 1 + 1                                   │ │
│ │ print(f"结果: {x}")                         │ │
│ └─────────────────────────────────────────────┘ │
│                                                   │
│ ✅ 执行成功                                        │
│                                                   │
│ 📤 输出:                                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ Hello, World!                                │ │
│ │ 结果: 2                                      │ │
│ └─────────────────────────────────────────────┘ │
│                                                   │
│ ⏱️  执行时间: 0.05 秒                             │
│ 💾 内存使用: 12.5 MB                              │
└─────────────────────────────────────────────────┘
```

#### 执行失败示例

```
┌─────────────────────────────────────────────────┐
│ 🔧 代码执行: Python                                  │
├─────────────────────────────────────────────────┤
│                                                   │
│ 📝 代码:                                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ print("Hello")                               │ │
│ │ x = 1 / 0                                    │ │
│ └─────────────────────────────────────────────┘ │
│                                                   │
│ ❌ 执行失败 (退出码: 1)                            │
│                                                   │
│ 📤 输出:                                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ Hello                                        │ │
│ └─────────────────────────────────────────────┘ │
│                                                   │
│ ⚠️  错误:                                         │
│ ┌─────────────────────────────────────────────┐ │
│ │ Traceback (most recent call last):          │ │
│ │   File "<string>", line 2, in <module>      │ │
│ │ ZeroDivisionError: division by zero          │ │
│ └─────────────────────────────────────────────┘ │
│                                                   │
│ ⏱️  执行时间: 0.02 秒                             │
└─────────────────────────────────────────────────┘
```

### 2.3 实现方案

#### 方案 1: 在 `stream_handler.py` 中增强 `_render_tool_info`

**优点**：
- 集中处理，易于维护
- 不影响其他工具

**实现**：
1. 检测工具名称是否为 `execute_code`
2. 如果是，使用专门的渲染函数
3. 提取代码、输出、错误等信息
4. 使用 Rich 组件美化显示

#### 方案 2: 在 `CodeExecutorTool` 中返回格式化数据

**优点**：
- 工具自己控制显示格式
- 更灵活

**缺点**：
- 需要修改工具接口
- 可能影响其他工具

**推荐方案 1**，因为：
- 不改变工具接口
- 集中管理显示逻辑
- 易于扩展其他工具的特殊显示

### 2.4 具体实现

#### 2.4.1 新增 `_render_code_executor` 方法

```python
def _render_code_executor(self, tool_data: dict, console: Console):
    """专门渲染代码执行工具的结果"""
    tool_args = tool_data.get("args", {})
    result = tool_data.get("result", {})
    success = tool_data.get("success", False)
    error = tool_data.get("error")
    
    # 提取信息
    code = tool_args.get("code", "")
    language = tool_args.get("language", "python")
    explanation = tool_args.get("explanation", "")
    output = result.get("output", "") if result else ""
    error_output = result.get("error", "") if result else ""
    exit_code = result.get("exit_code", 0) if result else 0
    execution_time = result.get("execution_time", 0) if result else 0
    memory_used = result.get("memory_used", 0) if result else 0
    
    # 构建内容
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text
    
    content_parts = []
    
    # 代码部分
    if code:
        code_syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=False,
            word_wrap=True
        )
        content_parts.append(Text("📝 代码:", style="bold"))
        content_parts.append("")
        content_parts.append(code_syntax)
        content_parts.append("")
    
    # 执行状态
    if success:
        status_text = Text("✅ 执行成功", style="bold green")
    else:
        status_text = Text(f"❌ 执行失败 (退出码: {exit_code})", style="bold red")
    content_parts.append(status_text)
    content_parts.append("")
    
    # 输出部分
    if output:
        content_parts.append(Text("📤 输出:", style="bold"))
        content_parts.append("")
        output_panel = Panel(
            output,
            border_style="blue",
            padding=(0, 1)
        )
        content_parts.append(output_panel)
        content_parts.append("")
    
    # 错误部分
    if error_output or error:
        error_content = error_output or error
        content_parts.append(Text("⚠️  错误:", style="bold yellow"))
        content_parts.append("")
        error_panel = Panel(
            error_content,
            border_style="red",
            padding=(0, 1)
        )
        content_parts.append(error_panel)
        content_parts.append("")
    
    # 统计信息
    stats = []
    if execution_time > 0:
        stats.append(f"⏱️  执行时间: {execution_time:.2f} 秒")
    if memory_used > 0:
        stats.append(f"💾 内存使用: {memory_used:.2f} MB")
    if stats:
        content_parts.append(Text("\n".join(stats), style="dim"))
    
    # 渲染面板
    title = f"🔧 代码执行: {language.upper()}"
    if explanation:
        title += f" - {explanation}"
    
    console.print(Panel(
        *content_parts,
        border_style="green" if success else "red",
        title=title,
        padding=(1, 1)
    ))
```

#### 2.4.2 修改 `_render_tool_info` 方法

```python
def _render_tool_info(self, tool_data: dict, console: Console):
    """渲染工具调用信息"""
    tool_name = tool_data.get("name", "unknown")
    
    # 特殊处理代码执行工具
    if tool_name == "execute_code":
        self._render_code_executor(tool_data, console)
        return
    
    # 其他工具使用原有逻辑
    # ... 原有代码 ...
```

### 2.5 长输出处理

#### 方案 A: 截断 + 提示

```python
MAX_OUTPUT_LINES = 50  # 最大显示行数

if output:
    lines = output.split('\n')
    if len(lines) > MAX_OUTPUT_LINES:
        display_lines = lines[:MAX_OUTPUT_LINES]
        display_output = '\n'.join(display_lines)
        display_output += f"\n\n... (输出已截断，共 {len(lines)} 行，显示前 {MAX_OUTPUT_LINES} 行)"
    else:
        display_output = output
```

#### 方案 B: 可折叠面板（Rich 支持）

```python
from rich.console import Group
from rich.panel import Panel

if len(output) > 1000:
    # 使用可折叠面板
    output_panel = Panel(
        output,
        title="点击展开/折叠",
        border_style="blue",
        collapse=True  # Rich 支持
    )
else:
    output_panel = Panel(output, border_style="blue")
```

**推荐方案 A**，因为：
- 简单直接
- 用户可以看到关键信息
- 避免界面过长

### 2.6 代码高亮

使用 Rich 的 `Syntax` 组件：

```python
from rich.syntax import Syntax

code_syntax = Syntax(
    code,
    language,  # "python", "bash", "zsh", "powershell", "batch"
    theme="monokai",  # 或其他主题
    line_numbers=False,  # 不显示行号（代码块较短）
    word_wrap=True  # 自动换行
)
```

### 2.7 语言图标映射

```python
LANGUAGE_ICONS = {
    "python": "🐍",
    "bash": "💻",
    "zsh": "💻",
    "powershell": "⚡",
    "batch": "📜"
}

icon = LANGUAGE_ICONS.get(language, "🔧")
title = f"{icon} 代码执行: {language.upper()}"
```

## 3. 实施计划

### 3.1 第一阶段：基础改进

1. ✅ 添加 `_render_code_executor` 方法
2. ✅ 修改 `_render_tool_info` 检测 `execute_code`
3. ✅ 显示代码内容（带语法高亮）
4. ✅ 清晰分离输出和错误
5. ✅ 显示执行统计信息

### 3.2 第二阶段：优化体验

1. 长输出截断处理
2. 语言图标映射
3. 代码说明显示（如果有）
4. 错误信息格式化（Traceback 高亮）

### 3.3 第三阶段：高级功能（可选）

1. 可折叠面板
2. 输出搜索/过滤
3. 代码复制按钮（如果 Rich 支持）
4. 执行历史记录

## 4. 预期效果

### 4.1 用户体验提升

- ✅ **代码可见**：用户可以看到执行的代码
- ✅ **输出清晰**：使用代码块格式，易于阅读
- ✅ **信息完整**：执行时间、内存使用一目了然
- ✅ **错误明确**：错误信息单独显示，易于定位

### 4.2 可维护性

- ✅ **代码集中**：显示逻辑集中在 `stream_handler.py`
- ✅ **易于扩展**：可以为其他工具添加特殊显示
- ✅ **向后兼容**：不影响其他工具

## 5. 总结

通过改进 `CodeExecutorTool` 的显示格式，可以显著提升用户体验：

1. **清晰展示代码**：用户可以看到执行的代码内容
2. **友好展示输出**：使用代码块格式，支持长输出
3. **突出关键信息**：执行状态、时间、内存使用
4. **区分输出和错误**：清晰分离标准输出和错误输出

改进方案简单易行，不需要修改工具接口，只需要增强前端的渲染逻辑。









