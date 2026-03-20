"""MarkdownLongTermMemory 单元测试"""
import pytest
from pathlib import Path

from backend.core.memory.long_term.markdown_memory import MarkdownLongTermMemory
from backend.core.context.long_term_memory.models import Memory, MemoryType


@pytest.fixture
def temp_memory_file(tmp_path):
    """临时 MEMORY.md 路径"""
    return tmp_path / "MEMORY.md"


@pytest.fixture
def md_memory(temp_memory_file):
    """MarkdownLongTermMemory 实例"""
    return MarkdownLongTermMemory(memory_file=temp_memory_file)


class TestMarkdownLongTermMemory:
    """MarkdownLongTermMemory 测试"""

    def test_save_and_get(self, md_memory, temp_memory_file):
        """保存并获取记忆"""
        mem = Memory(memory_id="test-1", memory_type=MemoryType.PREFERENCE, content="用户偏好 Python")
        ok = md_memory.save_memory(mem)
        assert ok is True
        assert temp_memory_file.exists()
        loaded = md_memory.get_memory("test-1")
        assert loaded is not None
        assert loaded.content == "用户偏好 Python"
        assert loaded.memory_type == MemoryType.PREFERENCE

    def test_search(self, md_memory):
        """关键词搜索"""
        md_memory.save_memory(Memory(memory_id="a", memory_type=MemoryType.KNOWLEDGE, content="项目使用 FastAPI"))
        md_memory.save_memory(Memory(memory_id="b", memory_type=MemoryType.PREFERENCE, content="喜欢用 Python"))
        results = md_memory.search_memories("Python", top_k=5)
        assert len(results) >= 1
        assert any("Python" in m.content for m in results)

    def test_delete(self, md_memory):
        """删除记忆"""
        md_memory.save_memory(Memory(memory_id="del-1", memory_type=MemoryType.CONVERSATION, content="待删除"))
        assert md_memory.get_memory("del-1") is not None
        ok = md_memory.delete_memory("del-1")
        assert ok is True
        assert md_memory.get_memory("del-1") is None

    def test_get_content_for_llm(self, md_memory):
        """获取 LLM 上下文"""
        md_memory.save_memory(Memory(memory_id="x", memory_type=MemoryType.PREFERENCE, content="偏好 Markdown"))
        block = md_memory.get_content_for_llm(query="Markdown", top_k=3)
        assert "偏好 Markdown" in block

    def test_session_id_user_and_session_scope(self, md_memory):
        """用户级与会话级记忆；检索时 session_id 过滤"""
        md_memory.save_memory(
            Memory(memory_id="u1", memory_type=MemoryType.PREFERENCE, content="用户偏好 dark mode", metadata={})
        )
        md_memory.save_memory(
            Memory(
                memory_id="s1",
                memory_type=MemoryType.CONVERSATION,
                content="本次讨论决定用方案 B",
                metadata={"session_id": "sess-abc"},
            )
        )
        md_memory.save_memory(
            Memory(
                memory_id="s2",
                memory_type=MemoryType.CONVERSATION,
                content="另一会话的结论",
                metadata={"session_id": "sess-xyz"},
            )
        )
        # 全部（关键词 dark 或 B 能匹配）
        all_r = md_memory.search_memories("dark B", top_k=10)
        assert len(all_r) >= 2
        # 限定 sess-abc：用户级 + 该 session
        filtered = md_memory.search_memories("dark B", top_k=10, session_id="sess-abc")
        assert any("方案 B" in m.content for m in filtered)
        assert any("dark mode" in m.content for m in filtered)
        # sess-xyz 不应包含「方案 B」
        filtered_xyz = md_memory.search_memories("B", top_k=10, session_id="sess-xyz")
        assert not any("方案 B" in m.content for m in filtered_xyz)

    def test_backward_compat_old_block_format(self, md_memory, temp_memory_file):
        """旧格式 3 字段块仍可解析"""
        temp_memory_file.write_text(
            '<!-- memory: old-1 | conversation | 2025-01-01T00:00:00 -->\n旧格式内容\n\n'
        )
        all_mem = md_memory._load_all()
        assert len(all_mem) == 1
        assert all_mem[0].content == "旧格式内容"
        assert (all_mem[0].metadata or {}).get("session_id", "") == ""
