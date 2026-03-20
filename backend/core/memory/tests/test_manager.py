"""MemoryManager 单元测试"""
import tempfile
from pathlib import Path

import pytest

from backend.core.context.manager import ContextManager
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.models import MessageRole
from backend.core.memory.manager import MemoryManager
from backend.core.memory.models import MemoryLayer
from backend.core.memory.long_term.markdown_memory import MarkdownLongTermMemory


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
def memory_manager(context_manager):
    return MemoryManager(context_manager=context_manager)


def test_get_context_for_llm_empty(memory_manager):
    """空记忆时返回空字符串"""
    sid = memory_manager.context_manager.create_session()
    ctx = memory_manager.get_context_for_llm(sid)
    assert isinstance(ctx, str)


def test_write_short(memory_manager):
    """写入短期记忆"""
    ok = memory_manager.write("今日完成 X", layer=MemoryLayer.SHORT)
    assert ok is True
    ctx = memory_manager.get_context_for_llm("any", include_layers=(MemoryLayer.SHORT,))
    assert "今日完成 X" in ctx


def test_write_long(memory_manager):
    """写入长期记忆"""
    ok = memory_manager.write("用户偏好：喜欢 dark mode", layer=MemoryLayer.LONG)
    assert ok is True
    # query=None 时返回全部（限制条数）
    ctx = memory_manager.get_context_for_llm(
        "any", query=None, include_layers=(MemoryLayer.LONG,)
    )
    assert "dark mode" in ctx


def test_search_long(memory_manager):
    """跨层检索长期记忆"""
    memory_manager.write("Python 是解释型语言", layer=MemoryLayer.LONG)
    results = memory_manager.search("Python", layers=(MemoryLayer.LONG,), top_k=5)
    assert len(results) >= 1
    assert any("Python" in r.content for r in results)
    assert results[0].layer == MemoryLayer.LONG


def test_should_flush_and_mark(memory_manager):
    """should_flush 与 mark_flushed"""
    sid = memory_manager.context_manager.create_session()
    for _ in range(20):
        memory_manager.context_manager.add_message(sid, MessageRole.USER, "msg")
    raw = memory_manager.context_manager.get_messages(sid, compressed=False)
    assert memory_manager.should_flush(sid, len(raw)) is True
    memory_manager.mark_flushed(sid)
    assert memory_manager.should_flush(sid, len(raw)) is False
