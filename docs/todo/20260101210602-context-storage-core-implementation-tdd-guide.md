# 上下文存储核心功能实现 - TDD 指南

## 概述

本文档说明如何通过 **TDD (Test-Driven Development)** 方式实现上下文存储核心功能，包括测试编写、验证和实现流程。

**TDD 流程**:
1. 🔴 **Red**: 先写测试，测试失败（当前阶段）
2. 🟢 **Green**: 实现功能，让测试通过
3. 🔵 **Refactor**: 重构代码，保持测试通过

**测试框架**: pytest

---

## 一、TDD 验证流程

### 1.1 基本流程

```bash
# 1. 编写测试（Red 阶段）
# 2. 运行测试，确认失败
pytest backend/core/context/tests/test_models.py -v

# 3. 实现功能（Green 阶段）
# 4. 运行测试，确认通过
pytest backend/core/context/tests/test_models.py -v

# 5. 重构代码（Refactor 阶段）
# 6. 运行测试，确认仍然通过
pytest backend/core/context/tests/test_models.py -v
```

### 1.2 验证测试是否有效

**关键原则**: 测试必须先失败，然后才能通过

**验证方法**:
1. 编写测试
2. 运行测试 → **必须失败**（因为功能未实现）
3. 实现最小功能
4. 运行测试 → **必须通过**
5. 如果测试一开始就通过，说明测试无效

---

## 二、阶段 1: 数据模型 TDD

### 2.1 测试文件结构

```
backend/core/context/tests/
├── __init__.py
└── test_models.py
```

### 2.2 测试用例（先写测试）

#### 测试 1: Message 数据模型

```python
# backend/core/context/tests/test_models.py
import pytest
from datetime import datetime
from backend.core.context.models import Message, MessageRole

class TestMessage:
    """Message 数据模型测试"""
    
    def test_message_creation(self):
        """测试创建 Message"""
        message = Message(
            role=MessageRole.USER,
            content="测试消息",
            message_id="msg_123"
        )
        
        assert message.role == MessageRole.USER
        assert message.content == "测试消息"
        assert message.message_id == "msg_123"
        assert isinstance(message.timestamp, datetime)
    
    def test_message_to_dict(self):
        """测试 Message 序列化"""
        message = Message(
            role=MessageRole.USER,
            content="测试消息",
            message_id="msg_123"
        )
        
        data = message.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "测试消息"
        assert data["message_id"] == "msg_123"
        assert "timestamp" in data
    
    def test_message_from_dict(self):
        """测试 Message 反序列化"""
        data = {
            "role": "user",
            "content": "测试消息",
            "message_id": "msg_123",
            "timestamp": "2025-01-01T12:00:00",
            "metadata": {}
        }
        
        message = Message.from_dict(data)
        
        assert message.role == MessageRole.USER
        assert message.content == "测试消息"
        assert message.message_id == "msg_123"
    
    def test_message_role_enum(self):
        """测试 MessageRole 枚举"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"
```

#### 测试 2: Session 数据模型

```python
class TestSession:
    """Session 数据模型测试"""
    
    def test_session_creation(self):
        """测试创建 Session"""
        session = Session(
            session_id="session_123",
            metadata={"key": "value"}
        )
        
        assert session.session_id == "session_123"
        assert session.metadata == {"key": "value"}
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_session_to_dict(self):
        """测试 Session 序列化"""
        session = Session(session_id="session_123")
        
        data = session.to_dict()
        
        assert data["session_id"] == "session_123"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_session_from_dict(self):
        """测试 Session 反序列化"""
        data = {
            "session_id": "session_123",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00",
            "metadata": {}
        }
        
        session = Session.from_dict(data)
        
        assert session.session_id == "session_123"
```

### 2.3 TDD 验证步骤

#### 步骤 1: 编写测试（Red 阶段）

```bash
# 创建测试文件
mkdir -p backend/core/context/tests
touch backend/core/context/tests/__init__.py
touch backend/core/context/tests/test_models.py

# 编写测试（如上所示）
```

#### 步骤 2: 运行测试，确认失败

```bash
# 运行测试（应该失败，因为 models.py 还不存在）
pytest backend/core/context/tests/test_models.py -v

# 预期输出：
# FAILED - ModuleNotFoundError: No module named 'backend.core.context.models'
```

**验证**: ✅ 测试失败，说明测试有效

#### 步骤 3: 实现最小功能（Green 阶段）

```python
# backend/core/context/models.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id")
        )

@dataclass
class Session:
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )
```

#### 步骤 4: 运行测试，确认通过

```bash
# 运行测试（应该通过）
pytest backend/core/context/tests/test_models.py -v

# 预期输出：
# test_message_creation PASSED
# test_message_to_dict PASSED
# test_message_from_dict PASSED
# test_message_role_enum PASSED
# test_session_creation PASSED
# test_session_to_dict PASSED
# test_session_from_dict PASSED
```

**验证**: ✅ 测试通过，功能实现正确

---

## 三、阶段 2: 存储后端 TDD

### 3.1 测试用例（先写测试）

```python
# backend/core/context/storage/tests/test_file_storage.py
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.models import Message, MessageRole, Session

class TestFileStorageBackend:
    """FileStorageBackend 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """创建 FileStorageBackend 实例"""
        return FileStorageBackend(storage_dir=temp_dir)
    
    def test_create_session(self, storage):
        """测试创建会话"""
        session = Session(session_id="test_session")
        result = storage.create_session(session)
        
        assert result is True
        assert storage.get_session("test_session") is not None
    
    def test_save_message(self, storage):
        """测试保存消息"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="测试消息"
        )
        
        result = storage.save_message(session_id, message)
        assert result is True
        
        messages = storage.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0].content == "测试消息"
    
    def test_get_messages_with_limit(self, storage):
        """测试获取消息（带 limit）"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        # 添加 5 条消息
        for i in range(5):
            message = Message(
                role=MessageRole.USER,
                content=f"消息{i}"
            )
            storage.save_message(session_id, message)
        
        # 获取前 3 条
        messages = storage.get_messages(session_id, limit=3)
        assert len(messages) == 3
    
    def test_persistence(self, storage, temp_dir):
        """测试数据持久化"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="持久化测试"
        )
        storage.save_message(session_id, message)
        
        # 重新创建 storage（模拟重启）
        new_storage = FileStorageBackend(storage_dir=temp_dir)
        messages = new_storage.get_messages(session_id)
        
        assert len(messages) == 1
        assert messages[0].content == "持久化测试"
```

### 3.2 TDD 验证步骤

#### 步骤 1: 编写测试（Red 阶段）

```bash
# 创建测试文件
mkdir -p backend/core/context/storage/tests
touch backend/core/context/storage/tests/__init__.py
touch backend/core/context/storage/tests/test_file_storage.py

# 编写测试（如上所示）
```

#### 步骤 2: 运行测试，确认失败

```bash
# 运行测试（应该失败）
pytest backend/core/context/storage/tests/test_file_storage.py -v

# 预期输出：
# FAILED - ModuleNotFoundError: No module named 'backend.core.context.storage.file'
```

**验证**: ✅ 测试失败，说明测试有效

#### 步骤 3: 实现最小功能（Green 阶段）

```python
# backend/core/context/storage/file.py
# 实现 FileStorageBackend（最小实现，让测试通过）
```

#### 步骤 4: 运行测试，确认通过

```bash
pytest backend/core/context/storage/tests/test_file_storage.py -v
```

---

## 四、阶段 3: 压缩策略 TDD

### 4.1 测试用例（先写测试）

```python
# backend/core/context/compression/tests/test_time_window.py
import pytest
from backend.core.context.compression.time_window import TimeWindowCompression
from backend.core.context.models import Message, MessageRole

class TestTimeWindowCompression:
    """TimeWindowCompression 测试"""
    
    @pytest.fixture
    def compression(self):
        """创建 TimeWindowCompression 实例"""
        return TimeWindowCompression()
    
    def test_no_compression_when_under_limit(self, compression):
        """测试消息数未超过限制时不压缩"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(5)
        ]
        
        result = compression.compress(messages, max_messages=10)
        
        assert len(result) == 5
        assert result == messages
    
    def test_compress_when_over_limit(self, compression):
        """测试消息数超过限制时压缩"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(15)
        ]
        
        result = compression.compress(messages, max_messages=10)
        
        assert len(result) == 10
        # 应该保留最近 10 条
        assert result[0].content == "消息5"
        assert result[-1].content == "消息14"
    
    def test_empty_messages(self, compression):
        """测试空消息列表"""
        result = compression.compress([], max_messages=10)
        assert len(result) == 0
```

### 4.2 TDD 验证步骤

同阶段 1 和 2 的流程。

---

## 五、阶段 4: ContextManager TDD

### 5.1 测试用例（先写测试）

```python
# backend/core/context/tests/test_manager.py
import pytest
import tempfile
from pathlib import Path
from backend.core.context.manager import ContextManager
from backend.core.context.models import MessageRole

class TestContextManager:
    """ContextManager 测试"""
    
    @pytest.fixture
    def manager(self):
        """创建 ContextManager 实例"""
        return ContextManager()
    
    def test_create_session(self, manager):
        """测试创建会话"""
        session_id = manager.create_session()
        
        assert session_id is not None
        assert len(session_id) > 0
    
    def test_add_and_get_messages(self, manager):
        """测试添加和获取消息"""
        session_id = manager.create_session()
        
        manager.add_message(session_id, MessageRole.USER, "你好")
        manager.add_message(session_id, MessageRole.ASSISTANT, "你好！")
        
        messages = manager.get_messages(session_id)
        assert len(messages) == 2
        assert messages[0].content == "你好"
        assert messages[1].content == "你好！"
    
    def test_get_messages_for_llm(self, manager):
        """测试获取 LLM 格式的消息"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "你好")
        
        llm_messages = manager.get_messages_for_llm(session_id)
        
        assert len(llm_messages) == 1
        assert llm_messages[0]["role"] == "user"
        assert llm_messages[0]["content"] == "你好"
    
    def test_compression(self, manager):
        """测试消息压缩"""
        session_id = manager.create_session()
        
        # 添加 15 条消息
        for i in range(15):
            manager.add_message(session_id, MessageRole.USER, f"消息{i}")
        
        # 获取消息（应该压缩到 10 条）
        messages = manager.get_messages(session_id, max_messages=10)
        assert len(messages) == 10
    
    def test_search_messages(self, manager):
        """测试搜索消息"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "Python 编程")
        manager.add_message(session_id, MessageRole.USER, "Java 开发")
        
        results = manager.search_messages(session_id, "Python")
        
        assert len(results) > 0
        assert any("Python" in msg.content for msg in results)
```

---

## 六、TDD 验证检查清单

### 6.1 每个测试阶段

- [ ] **Red 阶段**: 测试必须失败
  - 运行测试 → 确认失败
  - 如果测试一开始就通过，说明测试无效

- [ ] **Green 阶段**: 实现最小功能
  - 实现能让测试通过的最小代码
  - 运行测试 → 确认通过

- [ ] **Refactor 阶段**: 重构代码
  - 优化代码结构
  - 运行测试 → 确认仍然通过

### 6.2 测试有效性验证

**验证测试是否有效的方法**:

1. **测试必须先失败**:
   ```bash
   # 编写测试后，先运行（应该失败）
   pytest backend/core/context/tests/test_models.py -v
   # 预期: FAILED（因为功能未实现）
   ```

2. **实现功能后必须通过**:
   ```bash
   # 实现功能后，运行测试（应该通过）
   pytest backend/core/context/tests/test_models.py -v
   # 预期: PASSED
   ```

3. **如果测试一开始就通过，说明测试无效**:
   - 检查测试是否真的在测试功能
   - 检查测试是否使用了 Mock 而不是真实实现

---

## 七、运行测试命令

### 7.1 运行单个测试文件

```bash
# 运行数据模型测试
pytest backend/core/context/tests/test_models.py -v

# 运行存储后端测试
pytest backend/core/context/storage/tests/test_file_storage.py -v

# 运行压缩策略测试
pytest backend/core/context/compression/tests/test_time_window.py -v

# 运行 ContextManager 测试
pytest backend/core/context/tests/test_manager.py -v
```

### 7.2 运行所有上下文模块测试

```bash
# 运行所有上下文模块测试
pytest backend/core/context/ -v

# 运行并显示覆盖率
pytest backend/core/context/ --cov=backend.core.context --cov-report=html
```

### 7.3 运行特定测试用例

```bash
# 运行特定测试类
pytest backend/core/context/tests/test_models.py::TestMessage -v

# 运行特定测试方法
pytest backend/core/context/tests/test_models.py::TestMessage::test_message_creation -v
```

### 7.4 测试覆盖率

```bash
# 生成覆盖率报告
pytest backend/core/context/ --cov=backend.core.context --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest backend/core/context/ --cov=backend.core.context --cov-report=html
# 查看: htmlcov/index.html
```

---

## 八、TDD 最佳实践

### 8.1 测试编写原则

1. **测试名称清晰**: 使用描述性的测试名称
   ```python
   # ✅ 好
   def test_message_serialization_round_trip(self):
   
   # ❌ 不好
   def test1(self):
   ```

2. **一个测试一个断言**: 每个测试只测试一个功能点
   ```python
   # ✅ 好
   def test_message_role(self):
       assert message.role == MessageRole.USER
   
   def test_message_content(self):
       assert message.content == "测试"
   
   # ❌ 不好
   def test_message(self):
       assert message.role == MessageRole.USER
       assert message.content == "测试"
       assert message.timestamp is not None
   ```

3. **使用 Fixture**: 使用 pytest fixture 管理测试数据
   ```python
   @pytest.fixture
   def storage(self):
       return FileStorageBackend()
   ```

### 8.2 测试组织

```
backend/core/context/
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # 数据模型测试
│   ├── test_manager.py          # ContextManager 测试
│   └── test_integration.py     # 集成测试
├── storage/
│   └── tests/
│       ├── __init__.py
│       └── test_file_storage.py
└── compression/
    └── tests/
        ├── __init__.py
        └── test_time_window.py
```

---

## 九、TDD 工作流程示例

### 9.1 完整示例：实现 Message 模型

#### 步骤 1: 编写测试（Red）

```python
# test_models.py
def test_message_creation(self):
    message = Message(
        role=MessageRole.USER,
        content="测试"
    )
    assert message.role == MessageRole.USER
```

#### 步骤 2: 运行测试，确认失败

```bash
$ pytest test_models.py::TestMessage::test_message_creation -v
FAILED - ModuleNotFoundError: No module named 'backend.core.context.models'
```

**验证**: ✅ 测试失败，测试有效

#### 步骤 3: 实现最小功能（Green）

```python
# models.py
@dataclass
class Message:
    role: MessageRole
    content: str
```

#### 步骤 4: 运行测试，确认通过

```bash
$ pytest test_models.py::TestMessage::test_message_creation -v
PASSED
```

**验证**: ✅ 测试通过，功能实现正确

#### 步骤 5: 重构（Refactor）

```python
# 优化代码结构，添加更多功能
# 运行测试，确认仍然通过
```

---

## 十、常见问题

### 10.1 测试一开始就通过

**问题**: 测试编写后运行，发现已经通过了

**原因**:
- 功能已经实现
- 测试使用了 Mock 而不是真实实现
- 测试没有真正测试功能

**解决**:
- 检查功能是否已经实现
- 如果已实现，删除测试或更新测试
- 确保测试测试的是真实功能

### 10.2 测试失败但功能正常

**问题**: 功能正常工作，但测试失败

**原因**:
- 测试用例错误
- 测试环境问题
- 测试数据问题

**解决**:
- 检查测试用例逻辑
- 检查测试环境配置
- 检查测试数据

### 10.3 测试覆盖率不足

**问题**: 测试覆盖率 < 80%

**解决**:
- 添加更多测试用例
- 覆盖边界情况
- 覆盖错误处理

---

## 十一、验收标准

### 11.1 TDD 流程验证

- [ ] 每个功能都先写测试（Red 阶段）
- [ ] 测试运行失败（确认测试有效）
- [ ] 实现功能后测试通过（Green 阶段）
- [ ] 重构后测试仍然通过（Refactor 阶段）

### 11.2 测试质量验证

- [ ] 测试覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 测试用例清晰易懂
- [ ] 测试覆盖边界情况
- [ ] 测试覆盖错误处理

---

## 十二、相关文档

- [任务文档](./004-context-storage-core-implementation.md)
- [主设计文档](../../design/01-context-storage-and-compression-design.md)
- [TDD 状态文档](../archived/001-deepseek-integration-tdd-status.md)

---

**创建时间**: 2025-01-01  
**版本**: 1.0  
**状态**: TDD 指南完成

