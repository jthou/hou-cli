"""LegacyMemoryAdapter 单元测试"""
import tempfile
from pathlib import Path

import pytest

from backend.core.context.manager import ContextManager
from backend.core.context.storage.file import FileStorageBackend
from backend.core.memory.long_term.markdown_memory import MarkdownLongTermMemory
from backend.core.memory.legacy_adapter import LegacyMemoryAdapter


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
def adapter(context_manager):
    return LegacyMemoryAdapter(context_manager)


def test_search_empty(adapter):
    """无长期记忆时返回空"""
    results = adapter.search("test", top_k=5)
    assert results == []


def test_search_with_memory(context_manager, adapter):
    """有长期记忆时可检索"""
    from backend.core.context.long_term_memory.models import Memory, MemoryType
    mem = Memory(memory_id="x", memory_type=MemoryType.CONVERSATION, content="Python 编程")
    context_manager.long_term_memory.save_memory(mem)
    results = adapter.search("Python", top_k=5)
    assert len(results) >= 1
    assert any("Python" in m.content for m in results)
