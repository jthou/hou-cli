"""长期记忆 - Markdown 文件存储（MEMORY.md）

设计文档：docs/design/01-three-level-memory-and-context-design.md 2.4
存储格式：MEMORY.md 为唯一事实来源，人类可读可编辑
块格式：<!-- memory: id | type | created | session_id -->\ncontent\n
session_id 可选，空表示用户级；旧格式 3 字段向后兼容
"""
import re
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from backend.core.context.long_term_memory.base import LongTermMemory
from backend.core.context.long_term_memory.models import Memory, MemoryType


# 支持 3 字段（旧）或 4 字段（含 session_id）
_BLOCK_PATTERN = re.compile(
    r"<!-- memory: ([^|]+)\|([^|]+)\|([^|]*)(?:\|([^>]*))? -->\n(.*?)(?=\n<!-- memory:|\Z)",
    re.DOTALL,
)


class MarkdownLongTermMemory(LongTermMemory):
    """长期记忆 - 以 MEMORY.md 为唯一事实来源"""

    def __init__(self, memory_file: Optional[Path] = None):
        """
        Args:
            memory_file: MEMORY.md 路径，默认 get_app_data_dir()/contexts/MEMORY.md
        """
        if memory_file is None:
            from shared.platform_utils import get_app_data_dir
            memory_file = get_app_data_dir() / "contexts" / "MEMORY.md"
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[Memory]:
        """解析 MEMORY.md 返回所有 Memory"""
        if not self.memory_file.exists():
            return []
        text = self.memory_file.read_text(encoding="utf-8")
        memories = []
        for m in _BLOCK_PATTERN.finditer(text):
            mem_id = m.group(1).strip()
            mem_type_str = m.group(2).strip()
            created_str = m.group(3).strip()
            session_id = (m.group(4) or "").strip() if m.lastindex >= 4 and m.group(4) is not None else ""
            content = m.group(5).strip()
            try:
                mem_type = MemoryType(mem_type_str)
            except ValueError:
                mem_type = MemoryType.CONVERSATION
            try:
                created = datetime.fromisoformat(created_str) if created_str else datetime.now()
            except ValueError:
                created = datetime.now()
            meta = {"session_id": session_id} if session_id else {}
            memories.append(Memory(
                memory_id=mem_id,
                memory_type=mem_type,
                content=content,
                metadata=meta,
                created_at=created,
                updated_at=created,
            ))
        return memories

    def _save_all(self, memories: List[Memory]) -> bool:
        """将全部 Memory 写回 MEMORY.md"""
        try:
            lines = []
            for mem in memories:
                sid = (mem.metadata or {}).get("session_id", "")
                lines.append(
                    f"<!-- memory: {mem.memory_id} | {mem.memory_type.value} | {mem.created_at.isoformat()} | {sid} -->"
                )
                lines.append(mem.content)
                lines.append("")
            self.memory_file.write_text("\n".join(lines), encoding="utf-8")
            return True
        except (OSError, IOError) as e:
            import logging
            logging.getLogger(__name__).warning("MarkdownLongTermMemory._save_all 失败: %s", e)
            return False

    def save_memory(self, memory: Memory) -> bool:
        """保存记忆（新增或更新）"""
        if not memory.memory_id:
            memory.memory_id = str(uuid.uuid4())
        memories = self._load_all()
        index = next((i for i, m in enumerate(memories) if m.memory_id == memory.memory_id), None)
        if index is not None:
            memory.updated_at = datetime.now()
            memories[index] = memory
        else:
            memory.created_at = memory.created_at or datetime.now()
            memory.updated_at = memory.updated_at or memory.created_at
            memories.append(memory)
        return self._save_all(memories)

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        for m in self._load_all():
            if m.memory_id == memory_id:
                m.access_count += 1
                m.last_accessed = datetime.now()
                self.save_memory(m)
                return m
        return None

    def _match_session(self, mem: Memory, session_id: Optional[str]) -> bool:
        """session_id 过滤：None=全部；有值=用户级+该 session"""
        if session_id is None:
            return True
        mem_sid = (mem.metadata or {}).get("session_id", "")
        return mem_sid == "" or mem_sid == session_id

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10,
        session_id: Optional[str] = None,
    ) -> List[Memory]:
        """搜索记忆（关键词匹配）；session_id 有值时仅返回用户级+该 session"""
        query_words = set(query.lower().split())
        scored = []
        for m in self._load_all():
            if memory_type and m.memory_type != memory_type:
                continue
            if not self._match_session(m, session_id):
                continue
            content_words = set(m.content.lower().split())
            summary_words = set((m.summary or "").lower().split())
            tag_words = set(t.lower() for t in m.tags)
            score = (
                len(query_words & content_words) * 3
                + len(query_words & summary_words) * 2
                + len(query_words & tag_words)
            )
            if score > 0:
                scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def get_memories_by_tags(
        self,
        tags: List[str],
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """根据标签获取记忆"""
        tag_set = set(t.lower() for t in tags)
        return [
            m for m in self._load_all()
            if (memory_type is None or m.memory_type == memory_type)
            and tag_set & set(t.lower() for t in m.tags)
        ]

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        memories = [m for m in self._load_all() if m.memory_id != memory_id]
        if len(memories) == len(self._load_all()):
            return False
        return self._save_all(memories)

    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        if not any(m.memory_id == memory.memory_id for m in self._load_all()):
            return False
        memory.updated_at = datetime.now()
        return self.save_memory(memory)

    def get_content_for_llm(
        self,
        query: Optional[str] = None,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> str:
        """
        获取用于注入 LLM 的长期记忆文本（不含元数据）
        query 为 None 时返回全部（限制条数）；session_id 有值时仅用户级+该 session
        """
        if query:
            memories = self.search_memories(query, top_k=top_k, session_id=session_id)
        else:
            all_mem = self._load_all()
            if session_id is not None:
                all_mem = [m for m in all_mem if self._match_session(m, session_id)]
            memories = all_mem[:top_k]
        if not memories:
            return ""
        parts = [m.content for m in memories]
        return "\n\n".join(parts)
