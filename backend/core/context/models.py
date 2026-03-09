"""上下文存储数据模型"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """消息数据模型"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建（容错：role 大小写、timestamp 缺失、content 为 None）"""
        raw_role = (data.get("role") or "user")
        role_str = str(raw_role).lower().strip()
        try:
            role = MessageRole(role_str)
        except ValueError:
            role = (
                MessageRole.USER if role_str in ("user", "human")
                else MessageRole.ASSISTANT
            )
        content = data.get("content")
        if content is None:
            content = ""
        content = str(content)
        ts = data.get("timestamp")
        if ts:
            try:
                timestamp = datetime.fromisoformat(
                    str(ts).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
        return cls(
            role=role,
            content=content,
            timestamp=timestamp,
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
            message_id=data.get("message_id")
        )


@dataclass
class Session:
    """会话数据模型"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建（容错：缺失 created_at/updated_at/metadata）"""
        sid = data.get("session_id") or ""
        try:
            created = datetime.fromisoformat(
                str(data.get("created_at", "")).replace("Z", "+00:00")
            ) if data.get("created_at") else datetime.now()
        except (ValueError, TypeError):
            created = datetime.now()
        try:
            updated = datetime.fromisoformat(
                str(data.get("updated_at", "")).replace("Z", "+00:00")
            ) if data.get("updated_at") else datetime.now()
        except (ValueError, TypeError):
            updated = datetime.now()
        meta = data.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        return cls(
            session_id=sid,
            created_at=created,
            updated_at=updated,
            metadata=meta,
        )

