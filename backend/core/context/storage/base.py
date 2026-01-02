"""存储后端接口"""
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.core.context.models import Message, Session


class StorageBackend(ABC):
    """存储后端接口"""
    
    @abstractmethod
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        pass
    
    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        pass
    
    @abstractmethod
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        pass
    
    @abstractmethod
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        pass
    
    @abstractmethod
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        pass
    
    @abstractmethod
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        pass

