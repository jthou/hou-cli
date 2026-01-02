"""长期记忆数据模型"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型"""
    CONVERSATION = "conversation"  # 对话记忆
    KNOWLEDGE = "knowledge"        # 知识记忆
    PREFERENCE = "preference"      # 用户偏好
    CODE = "code"                  # 代码记忆
    TASK = "task"                  # 任务记忆


@dataclass
class Memory:
    """长期记忆数据模型"""
    memory_id: str
    memory_type: MemoryType
    content: str
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        return cls(
            memory_id=data["memory_id"],
            memory_type=MemoryType(data["memory_type"]),
            content=data["content"],
            summary=data.get("summary"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
        )

