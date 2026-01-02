# TODO-008: 上下文检索和恢复机制实现

## 任务概述

实现上下文检索和恢复机制，允许用户查找、预览和恢复历史会话上下文。包括命令模式支持（类似 Cursor Agent 的 `/commands` 格式）。

**优先级**: P0（高优先级）  
**预计工时**: 3-4 天  
**创建时间**: 2025-01-02  
**状态**: ⏳ 待开始

**关联文档**:
- [设计文档](../../docs/design/01-context-retrieval-and-restoration-design.md)
- [上下文存储设计](../../docs/design/01-context-storage-and-compression-design.md)

---

## 需求分析

### 用户场景

1. **查找历史对话**
   - 用户："前面咱们聊了啥？"
   - 系统：列出最近的会话，或搜索包含关键词的会话

2. **恢复历史会话**
   - 用户："继续之前的对话"
   - 系统：显示最近的会话列表，用户选择后恢复上下文

3. **搜索特定话题**
   - 用户："找一下关于 Python 的对话"
   - 系统：搜索所有会话中包含 "Python" 的消息，返回相关会话

4. **查看会话详情**
   - 用户："显示会话详情"
   - 系统：显示会话的完整消息列表

---

## 任务分解

### 阶段 1: ContextManager 扩展（P0）- 预计 1 天

#### 任务 1.1: 扩展 ContextManager 添加会话检索方法

**文件**: `backend/core/context/manager.py`

**实现步骤**:

1. **添加 `search_sessions()` 方法**
   - 支持按关键词搜索（搜索消息内容）
   - 支持按时间范围筛选
   - 支持数量限制
   - 返回按更新时间倒序的会话列表

2. **添加 `get_session_preview()` 方法**
   - 获取会话预览信息
   - 包含：预览文本、消息数量、创建时间、更新时间
   - 预览文本使用第一条用户消息

3. **添加 `restore_session()` 方法**
   - 验证会话是否存在
   - 返回会话 ID（用于继续对话）

**验收标准**:
- [ ] `search_sessions()` 方法实现完整
- [ ] `get_session_preview()` 方法实现完整
- [ ] `restore_session()` 方法实现完整
- [ ] 单元测试覆盖（至少 80%）

---

#### 任务 1.2: 实现 ContextRetrievalService

**文件**: `backend/core/context/retrieval_service.py`（新建）

**实现步骤**:

1. **创建 ContextRetrievalService 类**
   - 依赖 ContextManager
   - 提供高级检索接口

2. **实现 `list_recent_sessions()` 方法**
   - 列出最近的会话（带预览）
   - 返回格式化的会话信息

3. **实现 `search_sessions_by_keyword()` 方法**
   - 按关键词搜索会话
   - 返回匹配的会话列表（带预览）

4. **实现 `get_session_summary()` 方法**
   - 生成会话摘要
   - 包含第一条消息和消息数量

**验收标准**:
- [ ] ContextRetrievalService 类实现完整
- [ ] 所有方法都有单元测试
- [ ] 代码覆盖率 > 80%

---

### 阶段 2: 后端 API 集成（P0）- 预计 0.5 天

#### 任务 2.1: 扩展后端 API 路由

**文件**: `backend/api/routes.py`

**实现步骤**:

1. **添加会话列表 API**
   - `GET /api/sessions/list?limit=10`
   - 返回最近的会话列表

2. **添加会话搜索 API**
   - `GET /api/sessions/search?keyword=xxx&limit=10`
   - 返回匹配的会话列表

3. **添加会话恢复 API**
   - `POST /api/sessions/{session_id}/restore`
   - 恢复指定会话

4. **添加会话预览 API**
   - `GET /api/sessions/{session_id}/preview`
   - 返回会话预览信息

5. **添加会话消息列表 API**
   - `GET /api/sessions/{session_id}/messages`
   - 返回会话的完整消息列表

**验收标准**:
- [ ] 所有 API 端点实现完整
- [ ] API 文档更新
- [ ] 错误处理完善

---

#### 任务 2.2: 集成到 Orchestrator

**文件**: `backend/core/agent/orchestrator.py`

**实现步骤**:

1. **在 Orchestrator 中集成 ContextRetrievalService**
   - 创建 ContextRetrievalService 实例
   - 提供访问接口

2. **更新 API 路由使用 Orchestrator**
   - 通过 Orchestrator 访问 ContextRetrievalService

**验收标准**:
- [ ] Orchestrator 集成完成
- [ ] API 路由正常工作

---

### 阶段 3: 命令模式实现（P0）- 预计 1.5 天

#### 任务 3.1: 实现交互式命令输入（支持命令提示）

**文件**: `frontend/ui/command_input.py`（新建）

**实现步骤**:

1. **创建 CommandInput 类**
   - 检测用户输入 `/` 时显示命令提示菜单
   - 支持命令自动补全（Tab 键）
   - 使用 `prompt_toolkit` 或 `readline` 实现交互式输入

2. **实现命令提示显示**
   - 当输入 `/` 时，立即显示命令菜单
   - 显示所有可用命令和说明
   - 支持继续输入命令

3. **实现命令补全**
   - Tab 键自动补全命令
   - 支持命令参数提示

**验收标准**:
- [ ] 输入 `/` 时显示命令提示菜单
- [ ] 支持 Tab 键自动补全
- [ ] 交互体验流畅

---

#### 任务 3.2: 实现命令处理器

**文件**: `frontend/ui/command_handler.py`（新建）

**实现步骤**:

1. **创建 CommandHandler 类**
   - 检测 `/` 开头的命令
   - 解析命令和参数
   - 路由到对应的处理函数

2. **实现命令处理函数**
   - `/list` - 列出会话
   - `/search` - 搜索会话
   - `/restore` - 恢复会话
   - `/show` - 显示会话详情
   - `/delete` - 删除会话
   - `/summary` - 生成会话摘要
   - `/clear` - 清除当前会话
   - `/switch` - 切换会话
   - `/help` - 显示帮助

3. **实现命令格式化显示**
   - 会话列表表格显示
   - 搜索结果表格显示
   - 帮助信息格式化

**验收标准**:
- [ ] CommandHandler 类实现完整
- [ ] 所有命令都有处理函数
- [ ] 命令解析正确
- [ ] 错误处理完善

---

#### 任务 3.3: 集成命令模式到交互式对话

**文件**: `frontend/main.py`

**实现步骤**:

1. **集成 CommandInput 到交互式模式**
   - 使用 CommandInput.input_with_hint() 替代 console.input()
   - 支持命令提示功能

2. **在交互式模式中集成命令处理**
   - 检测用户输入是否以 `/` 开头
   - 如果是命令，调用 CommandHandler
   - 如果不是命令，继续正常对话流程

3. **实现会话状态管理**
   - 跟踪当前会话 ID
   - 支持会话切换
   - 支持会话恢复

**验收标准**:
- [ ] 命令提示在交互式对话中工作
- [ ] 命令模式在交互式对话中工作
- [ ] 正常对话流程不受影响
- [ ] 会话状态管理正确

---

### 阶段 4: 前端 CLI 独立命令（P1）- 预计 0.5 天

#### 任务 4.1: 实现 CLI 独立命令

**文件**: `frontend/main.py`

**实现步骤**:

1. **实现 `list` 命令**
   - 列出最近的会话
   - 使用 Rich Table 显示
   - 包含：序号、时间、预览、消息数

2. **实现 `search` 命令**
   - 搜索会话
   - 显示搜索结果表格

3. **实现 `restore` 命令**
   - 恢复会话（支持交互式选择）
   - 显示会话历史
   - 进入交互式对话模式

4. **实现 `show` 命令**
   - 显示会话详情
   - 显示完整消息列表

5. **实现 `delete` 命令**
   - 删除指定会话
   - 确认提示

6. **实现 `summary` 命令**
   - 生成并显示会话摘要

**验收标准**:
- [ ] 所有 CLI 命令实现完整
- [ ] 交互式界面友好
- [ ] 错误处理完善

---

#### 任务 4.2: 扩展 IPC Client

**文件**: `frontend/client/ipc_client.py`

**实现步骤**:

1. **添加会话相关方法**
   - `list_sessions(limit)`
   - `search_sessions(keyword, limit)`
   - `restore_session(session_id)`
   - `get_session_preview(session_id)`
   - `get_session_messages(session_id)`
   - `delete_session(session_id)`
   - `generate_session_summary(session_id)`
   - `clear_session(session_id)`

**验收标准**:
- [ ] IPC Client 方法实现完整
- [ ] 错误处理完善

---

### 阶段 5: 集成测试和文档（P1）- 预计 0.5 天

#### 任务 4.1: 集成测试

**文件**: `backend/core/context/tests/test_retrieval_service.py`（新建）

**实现步骤**:

1. **端到端测试**
   - 测试列出会话
   - 测试搜索会话
   - 测试恢复会话
   - 测试获取会话预览

2. **错误处理测试**
   - 测试会话不存在的情况
   - 测试空搜索结果

**验收标准**:
- [ ] 集成测试覆盖主要场景
- [ ] 所有测试通过

---

#### 任务 5.2: 文档更新

**文件**: `backend/core/context/README.md`, `docs/design/04-getting-started.md`

**实现步骤**:

1. **更新 README**
   - 添加会话检索使用示例
   - 添加会话恢复使用示例

2. **更新使用指南**
   - 添加 CLI 命令说明
   - 添加使用示例

**验收标准**:
- [ ] 文档更新完整
- [ ] 示例代码可运行

---

## 实现计划

### 阶段 1: ContextManager 扩展（1 天）

1. ⏳ 任务 1.1: 扩展 ContextManager 添加会话检索方法
2. ⏳ 任务 1.2: 实现 ContextRetrievalService

### 阶段 2: 后端 API 集成（0.5 天）

3. ⏳ 任务 2.1: 扩展后端 API 路由
4. ⏳ 任务 2.2: 集成到 Orchestrator

### 阶段 3: 命令模式实现（1.5 天）

5. ⏳ 任务 3.1: 实现交互式命令输入（支持命令提示）
6. ⏳ 任务 3.2: 实现命令处理器
7. ⏳ 任务 3.3: 集成命令模式到交互式对话

### 阶段 4: 前端 CLI 独立命令（0.5 天）

7. ⏳ 任务 4.1: 实现 CLI 独立命令
8. ⏳ 任务 4.2: 扩展 IPC Client

### 阶段 5: 集成测试和文档（0.5 天）

9. ⏳ 任务 5.1: 集成测试
10. ⏳ 任务 5.2: 文档更新

---

## 详细实现步骤

### 步骤 1: ContextManager 扩展

**文件**: `backend/core/context/manager.py`

添加以下方法：

```python
def search_sessions(
    self,
    query: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[Session]:
    """搜索会话"""
    # 实现见设计文档

def get_session_preview(
    self,
    session_id: str,
    max_preview_length: int = 100
) -> Dict[str, Any]:
    """获取会话预览"""
    # 实现见设计文档

def restore_session(
    self,
    session_id: str
) -> str:
    """恢复会话"""
    # 实现见设计文档
```

---

### 步骤 2: ContextRetrievalService 实现

**文件**: `backend/core/context/retrieval_service.py`（新建）

完整实现见设计文档。

---

### 步骤 3: 后端 API 路由扩展

**文件**: `backend/api/routes.py`

添加以下路由：

```python
@router.get("/sessions/list")
async def list_sessions(limit: int = 10):
    """列出最近的会话"""
    # 实现

@router.get("/sessions/search")
async def search_sessions(keyword: str, limit: int = 10):
    """搜索会话"""
    # 实现

@router.post("/sessions/{session_id}/restore")
async def restore_session(session_id: str):
    """恢复会话"""
    # 实现

@router.get("/sessions/{session_id}/preview")
async def get_session_preview(session_id: str):
    """获取会话预览"""
    # 实现

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取会话消息列表"""
    # 实现
```

---

### 步骤 3: 交互式命令输入实现

**文件**: `frontend/ui/command_input.py`（新建）

创建 CommandInput 类，实现命令提示功能。

**依赖**: 需要安装 `prompt_toolkit` 库（可选，提供更好的交互体验）

```bash
pip install prompt-toolkit
```

**简化版本**（不使用 prompt_toolkit）:
```python
def input_with_hint(self, prompt: str = "▸ ") -> str:
    """带命令提示的输入（简化版本）"""
    user_input = self.console.input(prompt)
    if user_input == '/':
        self._show_command_hint()
        user_input = self.console.input(prompt)
    return user_input
```

### 步骤 4: 命令处理器实现

**文件**: `frontend/ui/command_handler.py`（新建）

创建 CommandHandler 类，实现所有命令处理逻辑。

### 步骤 5: 集成命令模式到交互式对话

**文件**: `frontend/main.py`

在交互式对话循环中集成命令处理和命令提示：

```python
from frontend.ui.command_input import CommandInput
from frontend.ui.command_handler import CommandHandler

# 创建命令输入和处理器
command_input = CommandInput(console)
command_handler = CommandHandler(client, session_id)

while True:
    # 使用带提示的输入
    msg = command_input.input_with_hint("[dim cyan]▸[/dim cyan] ")
    
    if msg.lower() in ['exit', 'quit']:
        break
    if not msg.strip():
        continue
    
    # 检测命令模式
    if msg.startswith('/'):
        result = command_handler.handle_command(msg)
        if result:
            console.print(result)
        continue
    
    # 正常对话流程
    if stream:
        asyncio.run(_stream_chat(client, msg, session_id=session_id))
    else:
        # 非流式响应
        # ...
```

### 步骤 5: 前端 CLI 独立命令实现

**文件**: `frontend/main.py`

添加以下命令：

```python
@cli.command()
@click.option('--limit', default=10, help='显示数量限制')
def list(limit):
    """列出最近的会话"""
    # 实现

@cli.command()
@click.argument('keyword')
@click.option('--limit', default=10, help='显示数量限制')
def search(keyword, limit):
    """搜索会话"""
    # 实现

@cli.command()
@click.argument('session_id', required=False)
def restore(session_id):
    """恢复会话（继续对话）"""
    # 实现

@cli.command()
@click.argument('session_id')
def show(session_id):
    """显示会话详情"""
    # 实现

@cli.command()
@click.argument('session_id')
def delete(session_id):
    """删除会话"""
    # 实现

@cli.command()
@click.argument('session_id')
def summary(session_id):
    """生成会话摘要"""
    # 实现
```

---

## 测试计划

### 单元测试

1. **ContextManager 扩展测试**
   - 测试 `search_sessions()` 方法
   - 测试 `get_session_preview()` 方法
   - 测试 `restore_session()` 方法

2. **ContextRetrievalService 测试**
   - 测试 `list_recent_sessions()` 方法
   - 测试 `search_sessions_by_keyword()` 方法
   - 测试 `get_session_summary()` 方法

### 集成测试

1. **端到端测试**
   - 创建多个会话
   - 测试列出会话
   - 测试搜索会话
   - 测试恢复会话
   - 测试获取会话预览

2. **CLI 命令测试**
   - 测试 `list` 命令
   - 测试 `search` 命令
   - 测试 `restore` 命令
   - 测试 `show` 命令

---

## 验收标准

### 功能验收

- [ ] 可以列出最近的会话
- [ ] 可以按关键词搜索会话
- [ ] 可以恢复历史会话并继续对话
- [ ] 可以查看会话详情
- [ ] CLI 命令使用友好

### 代码质量验收

- [ ] 代码符合项目规范
- [ ] 添加必要的注释
- [ ] 错误处理完善
- [ ] 测试覆盖充分（> 80%）

### 文档验收

- [ ] 更新相关代码注释
- [ ] 更新使用文档
- [ ] 更新 API 文档

---

## 相关文档

- [上下文检索和恢复设计](../../docs/design/01-context-retrieval-and-restoration-design.md)
- [上下文存储设计](../../docs/design/01-context-storage-and-compression-design.md)
- [ContextManager API 文档](../../backend/core/context/README.md)

---

**创建时间**: 2025-01-02  
**优先级**: P0  
**状态**: ⏳ 待开始  
**预计完成时间**: 2025-01-04

