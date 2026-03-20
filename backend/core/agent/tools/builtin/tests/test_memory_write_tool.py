"""MemoryWriteTool 单元测试"""
import tempfile
from pathlib import Path

import pytest

from backend.core.context.manager import ContextManager
from backend.core.context.storage.file import FileStorageBackend
from backend.core.memory.long_term.markdown_memory import MarkdownLongTermMemory
from backend.core.agent.tools.builtin.memory_write_tool import MemoryWriteTool


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def context_manager(temp_storage):
    storage = FileStorageBackend(storage_dir=temp_storage)
    lt = MarkdownLongTermMemory(memory_file=temp_storage / "MEMORY.md")
    return ContextManager(storage_backend=storage, long_term_memory=lt)


@pytest.fixture
def tool(context_manager):
    return MemoryWriteTool(context_manager)


def test_memory_write_user_scope(tool, context_manager):
    """scope=user 写入用户级记忆，无 session_id"""
    r = tool.execute(content="用户偏好 Python", layer="long", scope="user")
    assert r.success is True
    all_mem = context_manager.long_term_memory.search_memories("Python", top_k=5)
    assert len(all_mem) >= 1
    assert (all_mem[0].metadata or {}).get("session_id", "") == ""


def test_memory_write_session_scope(tool, context_manager):
    """scope=session 且 session_id 时写入会话级记忆"""
    r = tool.execute(content="session conclusion for test", layer="long", scope="session", session_id="sess-123")
    assert r.success is True
    all_mem = context_manager.long_term_memory.search_memories("session", top_k=5)
    assert len(all_mem) >= 1
    assert (all_mem[0].metadata or {}).get("session_id") == "sess-123"
    filtered = context_manager.long_term_memory.search_memories("session", top_k=5, session_id="sess-123")
    assert any("session conclusion" in m.content for m in filtered)
