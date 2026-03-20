"""MemoryFlushTrigger 单元测试"""
import tempfile
from pathlib import Path

import pytest

from backend.core.memory.flush_trigger import MemoryFlushTrigger
from backend.core.context.manager import ContextManager
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.models import MessageRole


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def context_manager(temp_storage):
    storage = FileStorageBackend(storage_dir=temp_storage)
    return ContextManager(storage_backend=storage)


@pytest.fixture
def trigger():
    return MemoryFlushTrigger(message_threshold=5)


def test_should_flush_true_when_over_threshold(context_manager, trigger):
    """消息数超过阈值且未刷新过则触发"""
    sid = context_manager.create_session()
    for _ in range(6):
        context_manager.add_message(sid, MessageRole.USER, "msg")
    raw = context_manager.get_messages(sid, compressed=False)
    assert trigger.should_flush(context_manager, sid, len(raw)) is True


def test_should_flush_false_after_mark_flushed(context_manager, trigger):
    """标记已刷新后不再触发"""
    sid = context_manager.create_session()
    for _ in range(6):
        context_manager.add_message(sid, MessageRole.USER, "msg")
    trigger.mark_flushed(context_manager, sid)
    raw = context_manager.get_messages(sid, compressed=False)
    assert trigger.should_flush(context_manager, sid, len(raw)) is False


def test_get_flush_prompt():
    t = MemoryFlushTrigger()
    p = t.get_flush_prompt()
    assert "memory_write" in p
    assert "daily" in p or "long" in p
