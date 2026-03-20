"""三级记忆体系数据模型

设计文档：docs/design/01-three-level-memory-and-context-design.md
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MemoryLayer(str, Enum):
    """记忆层级"""
    SHORT = "short"    # 短期：daily log
    SESSION = "session"  # 近端：当前会话
    LONG = "long"      # 长期：MEMORY.md


@dataclass
class MemoryResult:
    """跨层检索结果"""
    content: str
    layer: MemoryLayer
    source_id: Optional[str] = None  # memory_id 或 session_id
    score: float = 0.0
