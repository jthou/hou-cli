# 三级记忆体系与上下文系统设计文档

**版本**: 1.5  
**日期**: 2025-03-14  
**分支**: feature/three-level-memory-system  
**状态**: 设计阶段（已纳入最终评审）

---

## 一、概述

### 1.1 背景

参考 OpenClaw 等自主智能体的实践，引入三级记忆架构，以 Markdown 为内容存储格式，配合向量/全文索引实现智能记忆管理。同时明确**记忆系统**与**上下文系统**的职责边界与协作方式。

### 1.2 目标

- 实现短期、近端、长期三层记忆
- 记忆内容与记忆系统分离（内容为唯一事实来源）
- 统一记忆管理入口（MemoryManager）
- 与现有 ContextManager 清晰协作

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| 内容优先 | Markdown 为唯一事实来源，索引可重建 |
| 职责分离 | Context 管会话状态，Memory 管跨会话持久化 |
| 单向依赖 | 记忆层不依赖具体存储实现 |
| 可替换 | 存储/索引可独立演进 |

---

## 二、三级记忆架构

### 2.1 层级定义

| 层级 | 存储位置 | 时间范围 | 内容类型 |
|------|----------|----------|----------|
| **短期** | `memory/YYYY-MM-DD.md` | 最近 48h | 日日志，append-only |
| **近端** | `{session_id}/messages.json` | 当前会话 | 完整对话历史 |
| **长期** | `MEMORY.md` | 持久 | 偏好、决策、持久知识 |

### 2.2 存储布局

**与现有架构统一**：以 `get_app_data_dir() / "contexts"` 为根目录（如 `~/.local/share/hou-cli/contexts`），在其下扩展 memory 相关结构，避免目录冲突。

```
get_app_data_dir() / "contexts"   # 现有根目录，保持不变
├── sessions.json                 # 现有
├── MEMORY.md                     # 长期记忆（新增）
├── memory/                       # 短期记忆（新增）
│   ├── 2025-03-14.md
│   └── 2025-03-13.md
└── {session_id}/                 # 现有
    ├── messages.json
    ├── current_article.md
    └── mw_sources.json
```

**长期记忆索引**（可选）：`get_app_data_dir() / "memory"` 下存放 SQLite 索引，与 contexts 分离。

### 2.3 检索层（可选）

- **索引存储**: SQLite（`get_app_data_dir() / "memory" / "{agent_id}.sqlite"`）
- **索引内容**: files 表、chunks 表、FTS5 全文、sqlite-vec 向量
- **检索策略**: BM25 + 向量混合（向量权重 0.7，BM25 0.3）

### 2.4 长期记忆按 session 区分（方案 C）

**设计目标**：长期记忆支持用户级（全局）与会话级（按 session 过滤），单文件存储，检索时可选过滤。

#### 2.4.1 记忆类型

| 类型 | scope | 说明 | 示例 |
|------|-------|------|------|
| **用户级** | 全局 | 偏好、通用知识，跨 session 共享 | 「用户喜欢 dark mode」「项目用 FastAPI」 |
| **会话级** | session_id | 某次对话中的重要结论，检索时可限定 | 「本次讨论决定用方案 B」 |

#### 2.4.2 存储格式（MEMORY.md 块扩展）

在现有块格式中增加 `session_id` 元数据（可选，空表示用户级）：

```
<!-- memory: id | type | created | session_id -->
content
```

- `session_id` 为空或省略 → 用户级记忆
- `session_id` 有值 → 会话级记忆

**向后兼容**：旧块无 `session_id` 字段时，解析为 `session_id=""`，视为用户级。

#### 2.4.3 元数据 Schema

```python
# Memory.metadata 持久化到块头（仅 session_id，其余保持 metadata 字段）
# 块头字段：id | type | created | session_id
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | str | 否 | 空=用户级；有值=会话级 |

#### 2.4.4 写入逻辑

| 写入入口 | session_id 来源 | 行为 |
|----------|-----------------|------|
| memory_write 工具 | 当前 session（由 Orchestrator 注入） | 写入时带 session_id |
| add_message(save_to_memory=True) | 当前 session | 写入时带 session_id |
| 用户直接编辑 MEMORY.md | 无 | 不写 session_id → 用户级 |

**memory_write 工具扩展**：增加可选参数 `scope`：
- `scope=user`（默认）：用户级，不写 session_id
- `scope=session`：会话级，写当前 session_id

#### 2.4.5 检索逻辑

| 方法 | session_id 参数 | 行为 |
|------|-----------------|------|
| search_memories(query, session_id=None) | None | 返回全部（用户级 + 会话级） |
| search_memories(query, session_id=sid) | 有值 | 仅返回用户级 + 该 session 的会话级 |
| get_content_for_llm(query, session_id=sid) | 有值 | 同上，用于当前 session 的上下文注入 |

**优先级**：用户级记忆始终参与检索；会话级按 session_id 过滤。

#### 2.4.6 接口变更

```python
# MarkdownLongTermMemory
# save_memory(memory) 保持不变；session_id 从 memory.metadata.get("session_id") 读取并持久化到块头

def search_memories(
    self,
    query: str,
    memory_type: Optional[MemoryType] = None,
    top_k: int = 10,
    session_id: Optional[str] = None,  # 新增：None=全部，有值=用户级+该session
) -> List[Memory]: ...

def get_content_for_llm(
    self,
    query: Optional[str] = None,
    top_k: int = 5,
    session_id: Optional[str] = None,  # 新增
) -> str: ...
```

#### 2.4.7 迁移

- 现有 MEMORY.md 块无 session_id → 解析为用户级，无需迁移
- 新写入的会话级记忆带 session_id，旧解析器忽略未知字段即可

---

## 三、记忆系统与记忆内容分离

### 3.1 概念区分

| 维度 | 记忆系统 (Memory System) | 记忆内容 (Memory Content) |
|------|---------------------------|----------------------------|
| 含义 | 存储、索引、检索、写入策略 | 实际被记住的数据 |
| 关注点 | 怎么存、怎么查 | 存什么、谁写入 |
| 可替换性 | 可换实现 | 与业务强相关 |

### 3.2 分层架构

```
┌─────────────────────────────────────────────────────────┐
│  Memory Content Layer（记忆内容层）                        │
│  - 内容模型（Memory, DailyLogEntry）                       │
│  - 写入策略（何时写入、写入哪一层）                          │
│  - 内容格式（Markdown 结构、元数据 schema）                 │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Memory System Layer（记忆系统层）                         │
│  - ContentStore（存什么格式、存哪）                        │
│  - RetrievalEngine（怎么查）                               │
│  - IndexBackend（怎么建索引）                              │
└─────────────────────────────────────────────────────────┘
```

### 3.3 内容作为唯一事实来源

- **Markdown 文件**：人类可读、可编辑、可审计
- **索引**：从内容派生，可随时重建
- **迁移**：换存储实现时，内容可无损迁移

---

## 四、谁写、何时存、是否删除

### 4.1 写入者

| 写入者 | 适用层级 | 说明 |
|--------|----------|------|
| **系统** | 短期、近端 | 消息自动写入 messages.json；关键事件写入 daily log |
| **LLM** | 短期、长期 | 根据 prompt 判断写什么、写哪里 |
| **用户** | 全部 | 直接编辑 .md，或通过「记住这个」触发 |

### 4.2 写入时机

| 层级 | 时机 | 触发方式 |
|------|------|----------|
| 短期 | 会话开始/结束、重要步骤 | 系统自动 |
| 短期 | 压缩前刷新 | 系统触发 LLM 写入 |
| 近端 | 每条消息 | 系统自动 |
| 长期 | 用户说「记住」 | 用户指令 → LLM |
| 长期 | 压缩前刷新 | 系统触发 LLM |
| 长期 | 模型主动判断 | LLM 工具调用 |

### 4.3 删除策略

| 层级 | 是否需要 | 方式 |
|------|----------|------|
| 短期 | 过期清理 | 保留最近 N 天，其余归档 |
| 近端 | 需要 | 删除/清除会话 |
| 长期 | 需要 | 用户编辑 .md；可选 forget 工具 |

---

## 五、统一记忆管理（MemoryManager）

### 5.1 必要性

- 三层协同：加载、写入、刷新需统一编排
- 单一入口：调用方只需「获取当前上下文」
- 写入路由：决定内容写入 daily log 还是 MEMORY.md
- 压缩前刷新：统一调度

### 5.2 职责

| 职责 | 方法 | 说明 |
|------|------|------|
| 聚合上下文 | `get_context_for_llm()` | 合并三层，返回注入 LLM 的文本 |
| 写入路由 | `write()` | 按 layer 写入对应存储 |
| 压缩前刷新 | `flush_before_compression()` | 触发 LLM 写入持久记忆 |
| 检索 | `search()` | 跨层检索 |
| 删除 | `delete()` | 按层删除 |

### 5.3 接口设计

```python
# backend/core/memory/manager.py

class MemoryLayer(str, Enum):
    SHORT = "short"    # daily log
    SESSION = "session"  # 当前会话
    LONG = "long"      # MEMORY.md

class MemoryManager:
    """统一记忆管理：编排短期、近端、长期三层记忆"""

    def __init__(
        self,
        short_term: Optional[ShortTermMemory] = None,
        session: Optional[ContextManager] = None,
        long_term: Optional[LongTermMemory] = None,
        workspace_dir: Optional[Path] = None,
    ): ...

    def get_context_for_llm(
        self,
        session_id: str,
        query: Optional[str] = None,
        include_layers: Tuple[MemoryLayer, ...] = (MemoryLayer.SHORT, MemoryLayer.SESSION, MemoryLayer.LONG),
        short_term_hours: int = 48,
        long_term_top_k: int = 5,
    ) -> str:
        """聚合三层记忆，返回注入 LLM 的上下文文本"""
        ...

    def write(
        self,
        content: str,
        layer: MemoryLayer,
        source: str = "system",
        session_id: Optional[str] = None,
    ) -> bool:
        """写入指定层级"""
        ...

    def flush_before_compression(self, session_id: str) -> bool:
        """压缩前触发：提醒/执行持久记忆写入"""
        ...

    def search(
        self,
        query: str,
        layers: Optional[Tuple[MemoryLayer, ...]] = None,
        top_k: int = 10,
        timeout: float = 30.0,
        callback_on_error: Optional[Callable[[Exception], None]] = None,
    ) -> List[MemoryResult]:
        """跨层检索；超时或异常时调用 callback_on_error"""
        ...

    def delete(self, layer: MemoryLayer, id_or_path: str) -> bool:
        """按层删除"""
        ...
```

### 5.4 监控与可观测性

| 指标 | 说明 | 目标（可选） |
|------|------|--------------|
| 搜索延迟 | 检索耗时 | SLA：P99 < 500ms（无向量时） |
| 存储空间 | memory/、MEMORY.md 占用 | 告警阈值可配置 |
| 检索准确率 | 可选：人工抽样评估 | — |
| 缓存命中率 | 若引入检索缓存 | 目标 > 60% |

**告警机制**：存储失败、检索超时、索引损坏时记录日志并可接入告警。

---

## 六、上下文系统与记忆系统协调

### 6.1 职责划分

| 系统 | 职责 | 输出 |
|------|------|------|
| **ContextManager** | 会话状态、消息、工作区、压缩 | 消息列表、当前文章、会话元数据 |
| **MemoryManager** | 持久记忆的存储、检索、写入 | 相关记忆片段 |

### 6.2 边界

| 维度 | 上下文系统 (Context) | 记忆系统 (Memory) |
|------|----------------------|-------------------|
| 时间范围 | 当前会话、当前轮次 | 跨会话、跨时间 |
| 核心问题 | 「此刻在做什么」 | 「之前记住了什么」 |
| 数据特性 | 易变、按会话组织 | 持久、可检索 |

### 6.3 协作点：构建 LLM 输入

```
                    ┌─────────────────────────────┐
                    │   Orchestrator / 调用方      │
                    └─────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
         ┌─────────────────────┐             ┌─────────────────────┐
         │   ContextManager     │             │   MemoryManager      │
         │   get_messages()     │             │   get_context_for_llm│
         │   get_current_article│             │   或 search()         │
         └─────────────────────┘             └─────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  Prompt = 系统提示 + 记忆块 + 消息历史 + 当前文章  │
                    └─────────────────────────────────────┘
```

### 6.4 数据流

| 阶段 | 上下文系统 | 记忆系统 |
|------|------------|----------|
| 会话开始 | 创建/加载 session，加载 messages | 加载 daily log 最近 48h，可选 MEMORY.md |
| 每轮对话 | 追加/获取消息，压缩 | 按 query 检索相关记忆 |
| 构建 prompt | 提供消息历史、当前文章 | 提供检索到的记忆片段 |
| 压缩前 | 触发压缩 | 触发 flush，写入持久记忆 |
| 会话结束 | 更新会话元数据 | 可选：写入 daily log 摘要 |

### 6.5 依赖关系

- **MemoryManager 不依赖 ContextManager 内部实现**
- **ContextManager 不依赖 MemoryManager**
- 两者通过 `session_id` 和调用方（Orchestrator）协调

```python
# Orchestrator 中的协调逻辑
messages = context_manager.get_messages_for_llm(session_id, ...)
article = context_manager.get_current_article(session_id)
memory_block = memory_manager.get_context_for_llm(session_id=session_id, query=user_task, ...)
prompt = build_prompt(system=..., memory=memory_block, messages=messages, article=article)
```

---

## 七、与现有架构的整合与迁移

### 7.1 冗余模块清理

| 模块 | 现状 | 建议 |
|------|------|------|
| `backend/infrastructure/memory/` | 占位实现（long_term_memory.py 仅 TODO，测试已注释） | **删除**，避免与 `backend/core/context/` 功能重叠 |
| `backend/core/context/` | 完整实现（ContextManager、FileLongTermMemory） | 保留，作为近端记忆与兼容层 |

**清理前置**：实施 P1 前执行 `rm -rf backend/infrastructure/memory/`，将三级记忆实现放在 `backend/core/memory/`。

### 7.2 现有架构对照

| 现有组件 | 设计文档对应 | 整合策略 |
|----------|--------------|----------|
| ContextManager | 近端记忆 + 会话管理 | 保留，不修改核心职责 |
| FileLongTermMemory (JSON) | 长期记忆层 | 保留为兼容层；新增 MarkdownLongTermMemory |
| LongTermMemory 接口 | 长期记忆抽象 | 保留；MarkdownLongTermMemory 实现该接口 |
| get_relevant_memories() | MemoryManager.search() | 通过适配器桥接 |
| get_app_data_dir()/contexts | 存储根目录 | 统一使用，在其下扩展 memory/、MEMORY.md |

### 7.3 向后兼容与适配层

**LegacyMemoryAdapter**：过渡期维持对现有 `ContextManager.get_relevant_memories()` 的兼容。

```python
class LegacyMemoryAdapter:
    """适配现有长期记忆接口到新记忆系统"""
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager

    def search(self, query: str, memory_type=None, top_k=10) -> List[Memory]:
        return self.context_manager.get_relevant_memories(query, memory_type, top_k)
```

**MemoryManager 组合方式**：MemoryManager 通过组合现有 ContextManager 实现近端层，无需替换 ContextManager。

**ContextManager 集成（可选）**：过渡期 ContextManager 可接受 `memory_manager` 参数，逐步将长期记忆职责迁移至 MemoryManager：

```python
class ContextManager:
    def __init__(self, memory_manager: Optional[MemoryManager] = None, ...):
        self.memory_manager = memory_manager or self._create_legacy_memory()
        # Phase 1: 保持现有 long_term_memory；Phase 2: 逐步迁移到 memory_manager
```

### 7.4 存储格式迁移

| 阶段 | 操作 |
|------|------|
| 当前 | FileLongTermMemory：`index.json` + `memories/{id}.json` |
| 迁移 | 提供工具将 JSON 记忆转换为 MEMORY.md 条目 |
| 目标 | MarkdownLongTermMemory：`MEMORY.md` 为唯一事实来源 |

**迁移工具**：`scripts/migrate_memory_json_to_markdown.py`（实施时开发）

### 7.5 详细迁移路径与 API 兼容性

**API 兼容性保证**：

| 接口 | 兼容策略 |
|------|----------|
| `get_relevant_memories()` | 保留；内部可委托 MemoryManager 或 LegacyMemoryAdapter |
| `add_message(save_to_memory=True)` | 保留；写入目标可切换为 MarkdownLongTermMemory |
| `LongTermMemory` 接口 | 保留；MarkdownLongTermMemory 实现该接口 |

**数据迁移步骤**：

1. 现有长期记忆（`memories/*.json`）→ 运行迁移工具 → `MEMORY.md` 条目
2. 会话历史（`messages.json`）→ 保持不动，作为近端记忆
3. 新数据 → 按三层架构写入

### 7.6 配置兼容性

保留现有 ContextManager 参数，新增记忆系统配置：

```python
# 现有参数（保留）
ContextManager(
    long_term_memory: Optional[LongTermMemory] = None,  # 可传入 FileLongTermMemory 或 MarkdownLongTermMemory
    auto_save_to_memory: bool = False,
)

# 新配置（记忆系统启用时）
memory:
  enabled: true
  use_legacy_adapter: false  # true 时通过 LegacyMemoryAdapter 使用现有 long_term_memory
```

**配置迁移工具**：提供脚本将旧配置合并到新 memory 配置块，保持向后兼容。

---

## 八、模块结构

### 8.1 目录结构

**说明**：`backend/infrastructure/memory/` 为占位模块，实施时删除；三级记忆实现放在 `backend/core/memory/`。

```
backend/core/
├── context/                    # 保留：会话、消息、文章（近端记忆）
│   ├── manager.py              # ContextManager
│   ├── storage/
│   ├── compression/
│   └── ...
└── memory/                     # 新增：统一记忆管理
    ├── __init__.py
    ├── manager.py              # MemoryManager
    ├── models.py               # MemoryLayer, MemoryResult
    ├── short_term/
    │   └── daily_log.py        # DailyLogMemory
    ├── long_term/
    │   └── markdown.py         # MarkdownLongTermMemory
    └── tests/
```

### 8.2 组件关系

```
                    MemoryManager
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
  ShortTermMemory    ContextManager    LongTermMemory
  (DailyLogMemory)   (复用现有)        (MarkdownLongTermMemory)
        │                 │                 │
        ▼                 ▼                 ▼
  memory/*.md       messages.json     MEMORY.md
```

---

## 九、实施阶段（含评审调整）

**实施优先级**（架构整合评审）：0）清理冗余模块；1）统一存储目录；2）向后兼容接口；3）短期记忆；4）MemoryManager；5）向量检索（可选）。

| 阶段 | 内容 | 预估 | 评审补充 |
|------|------|------|----------|
| **P0** | 现状：ContextManager、FileLongTermMemory、FileStorageBackend 已存在 | — | 作为迁移基线 |
| **P0.5** | 清理 `backend/infrastructure/memory/` 占位模块 | 0.5 天 | 删除冗余，避免技术债务 |
| **P1** | DailyLogMemory + 存储目录统一 + Orchestrator 注入 | 1-2 天 | 加强错误处理与基本监控 |
| **P2** | MarkdownLongTermMemory + 写入工具 + JSON→MD 迁移工具 | 1-2 天 | 保留 FileLongTermMemory 为兼容层 |
| **P3** | MemoryFlushTrigger + 压缩前集成 | 0.5 天 | 细化触发条件（见 9.4） |
| **P4** | MemoryManager 统一编排层 + LegacyMemoryAdapter | 1 天 | 与 ContextManager 组合 |
| **P5** | 向量检索 + 混合检索（可选） | 2-3 天 | 实施前做成本效益分析 |

### 9.2 DailyLogMemory 实现要点

```python
class DailyLogMemory:
    def __init__(self, storage_dir: Path = get_app_data_dir() / "contexts" / "memory"):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def write_daily_entry(self, content: str, date: datetime = None) -> bool:
        """按日期 append 到 YYYY-MM-DD.md"""
        ...

    def get_recent_entries(self, hours: int = 48) -> str:
        """获取最近 N 小时的日志内容"""
        ...
```

### 9.3 测试策略

| 类型 | 说明 |
|------|------|
| 保留现有测试 | 保持对 ContextManager、FileLongTermMemory 的测试 |
| 新增模块测试 | 为 DailyLogMemory、MarkdownLongTermMemory、MemoryManager 编写单元测试 |
| 集成测试 | 验证 MemoryManager 与 ContextManager 的协作、Orchestrator 注入 |

### 9.4 P2 压缩前刷新触发条件（细化）

- **token 阈值**：`context_window - reserve_tokens_floor - soft_threshold_tokens`
- **周期**：每个压缩周期最多触发一次（在 sessions 元数据中记录）
- **静默回合**：系统注入提示，模型回复 `NO_REPLY` 表示无内容需写入
- **工作区可写**：若 `workspaceAccess: "ro"` 则跳过

---

## 十、配置项（建议）

```yaml
# 记忆系统配置
memory:
  enabled: true
  workspace_dir: null  # null 使用 get_app_data_dir()/contexts
  use_legacy_adapter: false  # true 时通过 LegacyMemoryAdapter 使用现有 long_term_memory

  short_term:
    enabled: true
    retention_days: 7
    load_hours: 48

  long_term:
    enabled: true
    file: "MEMORY.md"

  flush:
    enabled: true
    soft_threshold_tokens: 4000
    reserve_tokens_floor: 20000

  # 性能与动态调整（评审补充）
  performance:
    search_timeout: 30.0
    adaptive_search_timeout: false
    max_concurrent_searches: 3
```

---

## 十一、风险与保障

### 11.1 存储一致性与并发访问

| 风险 | 措施 |
|------|------|
| 多组件同时写同一文件 | 文件锁（`fcntl`/`filelock`）或单写者模式 |
| 写入中断导致损坏 | 先写临时文件，再原子重命名 |
| 并发读写的竞态 | 读写锁；或限制为单进程内单写 |

### 11.2 性能与扩展性

| 风险 | 措施 |
|------|------|
| 纯文件 + 全文搜索性能瓶颈 | 引入 SQLite FTS5；数据量 > 10 万条时评估向量索引 |
| 单文件过大 | MEMORY.md 按主题分块；daily log 按天拆分 |
| 扩展阈值 | 明确：chunk 数 > N 或 单文件 > M MB 时触发索引/分片 |

### 11.3 隐私与安全

| 风险 | 措施 |
|------|------|
| 敏感信息落盘 | 可选：敏感字段脱敏、加密存储（需密钥管理） |
| 用户隐私 | 定义敏感信息识别规则；写入前可做过滤/脱敏 |
| 工作区权限 | 确保 workspace 目录权限正确，避免泄露 |

### 11.4 错误处理与恢复

| 场景 | 策略 |
|------|------|
| 存储失败 | 记录日志；返回失败；可选重试（有限次数）；**降级**：写入失败时跳过该条，不阻塞主流程 |
| 检索超时 | `search()` 支持 timeout；超时返回空或部分结果；**降级**：超时后回退到关键词检索 |
| 文件损坏 | 尝试解析；失败时跳过该文件并记录 |
| 并发访问 | 文件锁或单写者模式；**降级**：锁竞争时排队或返回空 |
| 备份与恢复 | 可选：定期备份 memory/、MEMORY.md；提供恢复脚本 |

### 11.5 版本兼容性

| 风险 | 措施 |
|------|------|
| 格式升级不兼容 | 文件头增加版本标识（如 `<!-- memory-format: 1 -->`） |
| 向下兼容 | 旧版本解析时忽略未知字段；新版本可读旧格式 |
| 数据迁移 | 提供迁移脚本；大版本升级时执行 |

### 11.6 重构风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 功能中断 | 灰度发布；先在非生产环境验证 |
| 数据丢失 | 迁移前备份 `contexts/`、`long_term_memory/` |
| 回滚需求 | 保留 FileLongTermMemory 为兼容层；可切回原有实现 |

---

## 十二、参考

- [OpenClaw 记忆文档](https://openclawcn.com/docs/concepts/memory/)
- [OpenClaw 三级记忆实现揭秘](https://bbs.huaweicloud.com/blogs/475004)
- 项目内：`docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md`

---

## 附录：设计评审反馈（2025-03-14）

**第一轮**：架构分层清晰、内容优先原则、职责分离、统一接口、实现路径清晰。已纳入：存储并发、性能扩展、隐私安全、错误恢复、版本兼容、接口超时与回调、配置灵活性、监控指标、P2 触发条件细化、P4 成本效益分析。

**第二轮（架构整合）**：与现有 ContextManager、FileLongTermMemory、get_app_data_dir()/contexts 对齐。已纳入：存储目录统一、LegacyMemoryAdapter、迁移路径、配置兼容、DailyLogMemory 实现要点、实施优先级。

**第三轮（冗余模块）**：`backend/infrastructure/memory/` 为占位实现，与 `backend/core/context/` 功能重叠。已纳入：P0.5 清理冗余模块、ContextManager 接受 memory_manager 参数、重构风险与缓解（灰度、备份、回滚）、测试策略（保留现有、新增模块、集成测试）。

**第四轮（最终版）**：已纳入：详细迁移路径与 API 兼容性（7.5）、存储失败/检索超时/并发降级策略（11.4）、检索延迟 SLA 与缓存目标（5.4）、配置迁移工具（7.6）。风险提示：迁移需仔细规划、大量数据下文件存储性能需验证、多进程/多线程一致性需考虑。

**第四轮（最终版）**：迁移路径、错误处理、监控指标细化。已纳入：7.6 数据迁移策略、7.7 API 兼容性保证、配置迁移工具、5.4 检索延迟 SLA/缓存目标/告警、11.4 存储失败降级与并发访问。
