# 上下文检索和恢复机制设计

## 概述

设计一个完整的上下文检索和调用机制，允许用户查找、预览和恢复历史会话上下文。

**设计目标**:
- ✅ **可检索性**: 支持按时间、关键词、内容搜索历史会话
- ✅ **可预览性**: 提供会话摘要和预览，帮助用户快速识别
- ✅ **可恢复性**: 支持从历史会话中恢复上下文，继续对话
- ✅ **用户友好**: 提供简洁的 CLI 命令和交互式界面

**创建时间**: 2025-01-02  
**状态**: 设计阶段  
**优先级**: P0（高优先级）

---

## 一、需求分析

### 1.1 用户场景

**场景 1: 查找历史对话**
- 用户："前面咱们聊了啥？"
- 系统：列出最近的会话，或搜索包含关键词的会话

**场景 2: 恢复历史会话**
- 用户："继续之前的对话"
- 系统：显示最近的会话列表，用户选择后恢复上下文

**场景 3: 搜索特定话题**
- 用户："找一下关于 Python 的对话"
- 系统：搜索所有会话中包含 "Python" 的消息，返回相关会话

**场景 4: 查看会话详情**
- 用户："显示会话详情"
- 系统：显示会话的完整消息列表

### 1.2 功能需求

1. **会话检索**
   - 按时间范围筛选（今天、本周、本月）
   - 按关键词搜索（搜索消息内容）
   - 按会话元数据筛选（如果有）

2. **会话预览**
   - 会话摘要（第一条消息或自动生成摘要）
   - 会话统计（消息数量、最后更新时间）
   - 会话列表显示（时间、摘要、统计）

3. **会话恢复**
   - 选择会话并恢复上下文
   - 继续对话（使用恢复的会话 ID）
   - 会话切换（在不同会话间切换）

4. **命令模式**（类似 Cursor Agent）
   - `/list` - 列出最近的会话
   - `/search <keyword>` - 搜索会话
   - `/restore [session_id]` - 恢复会话
   - `/show <session_id>` - 显示会话详情
   - `/delete <session_id>` - 删除会话
   - `/summary <session_id>` - 生成会话摘要
   - `/help` - 显示帮助信息
   - `/clear` - 清除当前会话
   - `/switch <session_id>` - 切换到指定会话

5. **前端集成**
   - 命令模式支持（交互式模式中识别 `/` 开头的命令）
   - CLI 独立命令（`list`, `search`, `restore`, `show`）
   - 交互式选择界面
   - 会话列表显示

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              ContextRetrievalService                     │
│                  (会话检索服务)                          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Session      │  │ Session      │  │ Session      │  │
│  │ Search       │  │ Preview      │  │ Restore      │  │
│  │ (搜索)       │  │ (预览)       │  │ (恢复)       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              ContextManager                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Storage      │  │ Retrieval    │  │ LongTerm     │  │
│  │ Backend      │  │ Engine       │  │ Memory       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

1. **ContextRetrievalService**: 会话检索服务（新增）
   - 会话搜索和筛选
   - 会话预览和摘要生成
   - 会话恢复管理

2. **ContextManager**: 上下文管理器（扩展）
   - 添加会话搜索方法
   - 添加会话摘要生成方法
   - 添加会话恢复方法

3. **前端 CLI**: 命令行接口（新增）
   - `list` 命令：列出会话
   - `search` 命令：搜索会话
   - `restore` 命令：恢复会话
   - `show` 命令：显示会话详情

---

## 三、API 设计

### 3.1 ContextManager 扩展方法

```python
class ContextManager:
    """上下文管理器（统一接口）"""
    
    # 现有方法...
    
    def search_sessions(
        self,
        query: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Session]:
        """
        搜索会话
        
        Args:
            query: 搜索关键词（搜索消息内容）
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            会话列表（按更新时间倒序）
        """
        pass
    
    def get_session_preview(
        self,
        session_id: str,
        max_preview_length: int = 100
    ) -> Dict[str, Any]:
        """
        获取会话预览
        
        Args:
            session_id: 会话 ID
            max_preview_length: 预览文本最大长度
            
        Returns:
            预览信息（摘要、消息数量、最后更新时间等）
        """
        pass
    
    def restore_session(
        self,
        session_id: str
    ) -> str:
        """
        恢复会话（返回会话 ID，用于继续对话）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话 ID（如果会话存在）
            
        Raises:
            ValueError: 如果会话不存在
        """
        pass
```

### 3.2 ContextRetrievalService 接口

```python
class ContextRetrievalService:
    """上下文检索服务"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    def list_recent_sessions(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        列出最近的会话（带预览）
        
        Args:
            limit: 返回数量限制
            
        Returns:
            会话列表（包含预览信息）
        """
        pass
    
    def search_sessions_by_keyword(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按关键词搜索会话
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            相关会话列表（包含预览信息）
        """
        pass
    
    def get_session_summary(
        self,
        session_id: str
    ) -> str:
        """
        获取会话摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话摘要文本
        """
        pass
```

---

## 四、实现设计

### 4.1 ContextManager 扩展实现

**文件**: `backend/core/context/manager.py`

```python
def search_sessions(
    self,
    query: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[Session]:
    """搜索会话"""
    # 获取所有会话
    all_sessions = self.storage.list_sessions()
    
    # 按时间筛选
    if start_time or end_time:
        filtered_sessions = []
        for session in all_sessions:
            if start_time and session.updated_at < start_time:
                continue
            if end_time and session.updated_at > end_time:
                continue
            filtered_sessions.append(session)
        all_sessions = filtered_sessions
    
    # 按关键词搜索
    if query:
        matching_sessions = []
        query_lower = query.lower()
        
        for session in all_sessions:
            # 搜索会话内的消息
            messages = self.storage.get_messages(session.session_id)
            for msg in messages:
                if query_lower in msg.content.lower():
                    matching_sessions.append(session)
                    break
        
        all_sessions = matching_sessions
    
    # 按更新时间排序（最新的在前）
    all_sessions.sort(key=lambda s: s.updated_at, reverse=True)
    
    # 应用限制
    if limit:
        all_sessions = all_sessions[:limit]
    
    return all_sessions

def get_session_preview(
    self,
    session_id: str,
    max_preview_length: int = 100
) -> Dict[str, Any]:
    """获取会话预览"""
    session = self.storage.get_session(session_id)
    if not session:
        raise ValueError(f"会话不存在: {session_id}")
    
    # 获取消息列表
    messages = self.storage.get_messages(session_id)
    
    # 生成预览文本（第一条用户消息）
    preview_text = ""
    if messages:
        first_user_msg = next(
            (msg for msg in messages if msg.role == MessageRole.USER),
            None
        )
        if first_user_msg:
            preview_text = first_user_msg.content
            if len(preview_text) > max_preview_length:
                preview_text = preview_text[:max_preview_length] + "..."
    
    return {
        "session_id": session_id,
        "preview": preview_text,
        "message_count": len(messages),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "metadata": session.metadata
    }

def restore_session(
    self,
    session_id: str
) -> str:
    """恢复会话"""
    session = self.storage.get_session(session_id)
    if not session:
        raise ValueError(f"会话不存在: {session_id}")
    
    # 返回会话 ID（用于继续对话）
    return session_id
```

### 4.2 ContextRetrievalService 实现

**文件**: `backend/core/context/retrieval_service.py`（新建）

```python
"""上下文检索服务"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from backend.core.context.manager import ContextManager


class ContextRetrievalService:
    """上下文检索服务"""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    def list_recent_sessions(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """列出最近的会话（带预览）"""
        sessions = self.context_manager.list_sessions(limit=limit)
        
        result = []
        for session in sessions:
            preview = self.context_manager.get_session_preview(session.session_id)
            result.append(preview)
        
        return result
    
    def search_sessions_by_keyword(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关键词搜索会话"""
        sessions = self.context_manager.search_sessions(query=keyword, limit=limit)
        
        result = []
        for session in sessions:
            preview = self.context_manager.get_session_preview(session.session_id)
            result.append(preview)
        
        return result
    
    def get_session_summary(
        self,
        session_id: str
    ) -> str:
        """获取会话摘要"""
        preview = self.context_manager.get_session_preview(session_id)
        messages = self.context_manager.get_messages(session_id, compressed=False)
        
        # 生成摘要
        if not messages:
            return "空会话"
        
        # 简单摘要：第一条用户消息 + 消息数量
        first_msg = messages[0]
        summary = f"开始: {first_msg.content[:50]}... ({len(messages)} 条消息)"
        
        return summary
```

### 4.3 交互式命令输入实现（支持命令提示）

**文件**: `frontend/ui/command_input.py`（新建）

**功能**: 当用户输入 `/` 时，立即显示命令菜单提示。

**实现方式**:
1. 使用自定义输入函数，监听键盘输入
2. 检测到 `/` 字符时，显示命令提示菜单
3. 支持 Tab 键自动补全
4. 支持方向键选择命令（可选）

**实现代码**:

```python
"""交互式命令输入（支持命令提示）"""
import sys
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

class CommandInput:
    """交互式命令输入，支持命令提示"""
    
    def __init__(self, console: Console):
        self.console = console
        self.commands = [
            ("list", "列出最近的会话", "[limit]"),
            ("search", "搜索包含关键词的会话", "<keyword> [limit]"),
            ("restore", "恢复会话（继续对话）", "[session_id]"),
            ("show", "显示会话详情", "<session_id>"),
            ("delete", "删除指定会话", "<session_id>"),
            ("summary", "生成并显示会话摘要", "<session_id>"),
            ("clear", "清除当前会话的所有消息", ""),
            ("switch", "切换到指定会话", "<session_id>"),
            ("help", "显示帮助信息", "[command]"),
        ]
    
    def input_with_hint(self, prompt: str = "▸ ") -> str:
        """带命令提示的输入"""
        try:
            from prompt_toolkit import prompt as pt_prompt
            from prompt_toolkit.completion import WordCompleter
            from prompt_toolkit.history import InMemoryHistory
            
            # 创建命令补全器
            command_words = ['/' + cmd[0] for cmd in self.commands]
            completer = WordCompleter(command_words, ignore_case=True)
            history = InMemoryHistory()
            
            # 自定义提示函数
            def get_prompt_text():
                return prompt
            
            # 使用 prompt_toolkit 实现交互式输入
            # 监听输入，检测到单独的 '/' 时显示提示
            user_input = ""
            while True:
                char = sys.stdin.read(1) if sys.stdin.isatty() else None
                if char == '/':
                    # 显示命令提示
                    self._show_command_hint()
                    # 继续读取完整输入
                    user_input = pt_prompt(
                        get_prompt_text,
                        completer=completer,
                        history=history,
                        complete_while_typing=True,
                    )
                    break
                elif char == '\n':
                    # 回车，返回当前输入
                    break
                else:
                    user_input += char
            
            return user_input
        except ImportError:
            # 如果没有 prompt_toolkit，使用简化版本
            return self._simple_input_with_hint(prompt)
    
    def _simple_input_with_hint(self, prompt: str) -> str:
        """简化版本的命令提示输入"""
        # 使用 readline（标准库，Unix/Linux/macOS）
        try:
            import readline
            
            # 设置命令补全
            def complete(text, state):
                commands = ['/' + cmd[0] for cmd in self.commands]
                matches = [cmd for cmd in commands if cmd.startswith(text)]
                if state < len(matches):
                    return matches[state]
                return None
            
            readline.set_completer(complete)
            readline.parse_and_bind("tab: complete")
            
            # 读取输入
            user_input = input(prompt)
            
            # 如果输入是单独的 '/'，显示提示
            if user_input == '/':
                self._show_command_hint()
                user_input = input(prompt)
            
            return user_input
        except ImportError:
            # 如果没有 readline（Windows），使用最简版本
            user_input = self.console.input(prompt)
            if user_input == '/':
                self._show_command_hint()
                user_input = self.console.input(prompt)
            return user_input
    
    def _show_command_hint(self):
        """显示命令提示菜单"""
        hint_text = Text()
        hint_text.append("可用命令:\n", style="dim")
        
        for cmd, desc, args in self.commands:
            cmd_line = f"  [cyan]/{cmd}[/cyan]"
            if args:
                cmd_line += f" {args}"
            cmd_line += f" - {desc}\n"
            hint_text.append(cmd_line)
        
        hint_text.append("\n[dim]提示: 输入命令后按 Enter 执行，按 Tab 自动补全[/dim]")
        
        self.console.print(Panel(
            hint_text,
            border_style="dim cyan",
            title="[dim cyan]命令提示[/dim cyan]",
            padding=(1, 2)
        ))
```

**使用示例**:

```python
# 在交互式对话中使用
command_input = CommandInput(console)

while True:
    msg = command_input.input_with_hint("[dim cyan]▸[/dim cyan] ")
    # 用户输入 '/' 时，会立即显示命令提示菜单
    # 然后用户可以继续输入命令，如 '/list'
```

### 4.4 命令处理器实现

**文件**: `frontend/ui/command_handler.py`（新建）

```python
"""命令处理器（类似 Cursor Agent 的命令模式）"""
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from frontend.client.ipc_client import IPCClient

class CommandHandler:
    """命令处理器"""
    
    def __init__(self, client: IPCClient, current_session_id: Optional[str] = None):
        self.client = client
        self.current_session_id = current_session_id
        self.console = Console()
    
    def handle_command(self, input_text: str) -> Optional[str]:
        """处理命令输入"""
        if not input_text.startswith('/'):
            return None  # 不是命令
        
        # 解析命令
        parts = input_text[1:].strip().split()
        if not parts:
            return self._show_help()
        
        command = parts[0].lower()
        args = parts[1:]
        
        # 路由到对应的命令处理函数
        handlers = {
            'list': self._handle_list,
            'search': self._handle_search,
            'restore': self._handle_restore,
            'show': self._handle_show,
            'delete': self._handle_delete,
            'summary': self._handle_summary,
            'clear': self._handle_clear,
            'switch': self._handle_switch,
            'help': self._handle_help,
        }
        
        handler = handlers.get(command)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                return f"[red]错误: {e}[/red]"
        else:
            return f"[yellow]未知命令: {command}[/yellow]\n输入 /help 查看帮助"
    
    # ... 其他命令处理函数（见之前的实现）
```

### 4.5 前端 CLI 独立命令

**文件**: `frontend/main.py`（扩展）

```python
@cli.command()
@click.option('--limit', default=10, help='显示数量限制')
def list(limit):
    """列出最近的会话"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        show_error(e)
        return
    
    # 调用后端 API 获取会话列表
    sessions = client.list_sessions(limit=limit)
    
    # 显示会话列表
    if not sessions:
        console.print("[dim]没有找到会话[/dim]")
        return
    
    from rich.table import Table
    table = Table(title="最近会话")
    table.add_column("序号", style="cyan")
    table.add_column("时间", style="green")
    table.add_column("预览", style="white")
    table.add_column("消息数", style="yellow")
    
    for i, session in enumerate(sessions, 1):
        table.add_row(
            str(i),
            session["updated_at"].strftime("%Y-%m-%d %H:%M"),
            session["preview"],
            str(session["message_count"])
        )
    
    console.print(table)

@cli.command()
@click.argument('keyword')
@click.option('--limit', default=10, help='显示数量限制')
def search(keyword, limit):
    """搜索会话"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        show_error(e)
        return
    
    # 调用后端 API 搜索会话
    sessions = client.search_sessions(keyword=keyword, limit=limit)
    
    # 显示搜索结果
    if not sessions:
        console.print(f"[dim]没有找到包含 '{keyword}' 的会话[/dim]")
        return
    
    from rich.table import Table
    table = Table(title=f"搜索结果: {keyword}")
    table.add_column("序号", style="cyan")
    table.add_column("时间", style="green")
    table.add_column("预览", style="white")
    table.add_column("消息数", style="yellow")
    
    for i, session in enumerate(sessions, 1):
        table.add_row(
            str(i),
            session["updated_at"].strftime("%Y-%m-%d %H:%M"),
            session["preview"],
            str(session["message_count"])
        )
    
    console.print(table)

@cli.command()
@click.argument('session_id', required=False)
def restore(session_id):
    """恢复会话（继续对话）"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        show_error(e)
        return
    
    # 如果没有提供 session_id，显示会话列表供选择
    if not session_id:
        sessions = client.list_sessions(limit=10)
        if not sessions:
            console.print("[dim]没有找到会话[/dim]")
            return
        
        # 交互式选择
        from rich.prompt import Prompt
        console.print("\n[bold]选择要恢复的会话:[/bold]")
        for i, session in enumerate(sessions, 1):
            console.print(f"  {i}. {session['preview']} ({session['updated_at'].strftime('%Y-%m-%d %H:%M')})")
        
        choice = Prompt.ask("\n请输入序号", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                session_id = sessions[idx]["session_id"]
            else:
                console.print("[red]无效的序号[/red]")
                return
        except ValueError:
            console.print("[red]无效的输入[/red]")
            return
    
    # 恢复会话并进入交互式模式
    try:
        restored = client.restore_session(session_id)
        console.print(f"[green]已恢复会话: {session_id[:8]}...[/green]")
        
        # 显示会话历史
        messages = client.get_session_messages(session_id)
        if messages:
            console.print("\n[bold]会话历史:[/bold]")
            for msg in messages[-5:]:  # 显示最后 5 条
                role = "你" if msg["role"] == "user" else "Agent"
                console.print(f"[dim]{role}:[/dim] {msg['content'][:100]}...")
        
        # 进入交互式模式
        console.print("\n[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
        
        while True:
            msg = console.input("[dim cyan]▸[/dim cyan] ")
            if msg.lower() in ['exit', 'quit']:
                break
            if not msg.strip():
                continue
            
            # 使用恢复的 session_id 继续对话
            asyncio.run(_stream_chat(client, msg, session_id=session_id))
            console.print()
    except Exception as e:
        show_error(e)

@cli.command()
@click.argument('session_id')
def show(session_id):
    """显示会话详情"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        show_error(e)
        return
    
    # 获取会话详情
    try:
        preview = client.get_session_preview(session_id)
        messages = client.get_session_messages(session_id)
        
        # 显示会话信息
        console.print(f"\n[bold]会话 ID:[/bold] {session_id}")
        console.print(f"[bold]创建时间:[/bold] {preview['created_at']}")
        console.print(f"[bold]更新时间:[/bold] {preview['updated_at']}")
        console.print(f"[bold]消息数量:[/bold] {preview['message_count']}")
        
        # 显示消息列表
        if messages:
            console.print("\n[bold]消息列表:[/bold]")
            for i, msg in enumerate(messages, 1):
                role = "你" if msg["role"] == "user" else "Agent"
                console.print(f"\n[{i}] [cyan]{role}:[/cyan] {msg['content']}")
        else:
            console.print("\n[dim]会话为空[/dim]")
    except Exception as e:
        show_error(e)
```

### 4.4 后端 API 路由

**文件**: `backend/api/routes.py`（扩展）

```python
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.core.agent.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()

@router.get("/sessions/list")
async def list_sessions(limit: int = 10):
    """列出最近的会话"""
    retrieval_service = ContextRetrievalService(orchestrator.context_manager)
    sessions = retrieval_service.list_recent_sessions(limit=limit)
    return {"sessions": sessions}

@router.get("/sessions/search")
async def search_sessions(keyword: str, limit: int = 10):
    """搜索会话"""
    retrieval_service = ContextRetrievalService(orchestrator.context_manager)
    sessions = retrieval_service.search_sessions_by_keyword(keyword, limit=limit)
    return {"sessions": sessions}

@router.post("/sessions/{session_id}/restore")
async def restore_session(session_id: str):
    """恢复会话"""
    try:
        orchestrator.context_manager.restore_session(session_id)
        return {"session_id": session_id, "status": "restored"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/sessions/{session_id}/preview")
async def get_session_preview(session_id: str):
    """获取会话预览"""
    try:
        preview = orchestrator.context_manager.get_session_preview(session_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取会话消息列表"""
    messages = orchestrator.context_manager.get_messages(session_id, compressed=False)
    return {
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }
```

---

## 五、任务分解

### 阶段 1: ContextManager 扩展（P0）

**任务 1.1**: 扩展 ContextManager 添加会话检索方法
- [ ] `search_sessions()` 实现
- [ ] `get_session_preview()` 实现
- [ ] `restore_session()` 实现
- [ ] 单元测试

**任务 1.2**: 实现 ContextRetrievalService
- [ ] 创建 `retrieval_service.py`
- [ ] 实现会话列表、搜索、摘要方法
- [ ] 单元测试

### 阶段 2: 后端 API 集成（P0）

**任务 2.1**: 扩展后端 API 路由
- [ ] 添加会话列表 API
- [ ] 添加会话搜索 API
- [ ] 添加会话恢复 API
- [ ] 添加会话预览 API
- [ ] 添加会话消息列表 API

**任务 2.2**: 集成到 Orchestrator
- [ ] 在 Orchestrator 中集成 ContextRetrievalService
- [ ] 更新 API 路由使用 Orchestrator

### 阶段 3: 前端 CLI 命令（P1）

**任务 3.1**: 实现 CLI 命令
- [ ] `list` 命令：列出会话
- [ ] `search` 命令：搜索会话
- [ ] `restore` 命令：恢复会话
- [ ] `show` 命令：显示会话详情

**任务 3.2**: 实现交互式界面
- [ ] 会话列表显示（使用 Rich Table）
- [ ] 交互式会话选择
- [ ] 会话详情显示

### 阶段 4: 集成测试和文档（P1）

**任务 4.1**: 集成测试
- [ ] 端到端测试（列出、搜索、恢复会话）
- [ ] 错误处理测试

**任务 4.2**: 文档更新
- [ ] 更新 README 添加使用示例
- [ ] 更新 API 文档

---

## 六、使用示例

### 6.1 列出最近会话

```bash
# 列出最近 10 个会话
hou-cli list

# 列出最近 5 个会话
hou-cli list --limit 5
```

### 6.2 搜索会话

```bash
# 搜索包含 "Python" 的会话
hou-cli search Python

# 搜索包含 "设计" 的会话
hou-cli search 设计 --limit 5
```

### 6.3 恢复会话

```bash
# 恢复指定会话
hou-cli restore <session_id>

# 交互式选择会话
hou-cli restore
```

### 6.4 显示会话详情

```bash
# 显示会话详情
hou-cli show <session_id>
```

### 6.5 在对话中使用

```python
# 用户："前面咱们聊了啥？"
# 系统：列出最近的会话

# 用户："继续之前的对话"
# 系统：显示会话列表，用户选择后恢复
```

---

## 七、技术选型

### 7.1 会话搜索

- **关键词搜索**: 使用现有的 `KeywordRetrievalEngine`
- **时间筛选**: 使用 Python `datetime` 标准库
- **性能优化**: 对于大量会话，考虑添加索引（未来优化）

### 7.2 会话预览

- **预览文本**: 使用第一条用户消息（简单有效）
- **未来优化**: 可以使用 LLM 生成摘要（需要额外 API 调用）

### 7.3 前端显示

- **表格显示**: 使用 Rich `Table` 组件
- **交互式选择**: 使用 Rich `Prompt` 组件
- **格式化**: 使用 Rich 样式和颜色

---

## 八、相关文档

- [上下文存储设计](./01-context-storage-and-compression-design.md)
- [ContextManager API 文档](../../backend/core/context/README.md)
- [前端 CLI 使用指南](../design/04-getting-started.md)

---

**创建时间**: 2025-01-02  
**最后更新**: 2025-01-02  
**版本**: 1.0  
**状态**: 设计完成，待实现

