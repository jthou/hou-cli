"""上下文管理器（统一接口）"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid
from backend.core.context.models import Message, MessageRole, Session
from backend.core.context.storage.base import StorageBackend
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.compression.base import CompressionStrategy
from backend.core.context.compression.time_window import TimeWindowCompression
from backend.core.context.retrieval.base import RetrievalEngine
from backend.core.context.retrieval.keyword import KeywordRetrievalEngine
from backend.core.context.long_term_memory.base import LongTermMemory
from backend.core.context.long_term_memory.models import Memory, MemoryType


class ContextManager:
    """上下文管理器（统一接口）"""
    
    def __init__(
        self,
        storage_backend: Optional[StorageBackend] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        long_term_memory: Optional[LongTermMemory] = None,
        storage_dir: Optional[Path] = None,
        default_max_messages: int = 10,
        default_max_tokens: Optional[int] = None,
        auto_save_to_memory: bool = False
    ):
        """
        初始化上下文管理器
        
        Args:
            storage_backend: 存储后端（默认：FileStorageBackend，持久化）
            compression_strategy: 压缩策略（默认：TimeWindowCompression）
            retrieval_engine: 检索引擎（默认：KeywordRetrievalEngine）
            long_term_memory: 长期记忆（可选）
            storage_dir: 存储目录（仅当使用默认 FileStorageBackend 时有效）
            default_max_messages: 默认最大消息数
            default_max_tokens: 默认最大 token 数
            auto_save_to_memory: 是否自动保存到长期记忆
        """
        # 默认使用 FileStorageBackend（持久化）
        if storage_backend is None:
            storage_dir = storage_dir or Path("data/contexts")
            self.storage = FileStorageBackend(storage_dir=storage_dir)
        else:
            self.storage = storage_backend
        
        self.compression = compression_strategy or TimeWindowCompression()
        self.retrieval = retrieval_engine or KeywordRetrievalEngine()
        self.long_term_memory = long_term_memory
        self.auto_save_to_memory = auto_save_to_memory
        self.default_max_messages = default_max_messages
        self.default_max_tokens = default_max_tokens
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新会话
        
        Args:
            metadata: 会话元数据
            
        Returns:
            会话 ID
        """
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            metadata=metadata or {}
        )
        self.storage.create_session(session)
        return session_id
    
    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        save_to_memory: Optional[bool] = None
    ) -> str:
        """
        添加消息
        
        Args:
            session_id: 会话 ID
            role: 消息角色
            content: 消息内容
            metadata: 消息元数据
            save_to_memory: 是否保存到长期记忆（None 使用 auto_save_to_memory）
            
        Returns:
            消息 ID
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        # 保存到上下文
        self.storage.save_message(session_id, message)
        
        # 可选：保存到长期记忆
        should_save = save_to_memory if save_to_memory is not None else self.auto_save_to_memory
        if should_save and self.long_term_memory and role == MessageRole.USER:
            # 保存用户消息到长期记忆
            memory = Memory(
                memory_id=str(uuid.uuid4()),
                memory_type=MemoryType.CONVERSATION,
                content=content,
                metadata={
                    "session_id": session_id,
                    "role": role.value,
                    **(metadata or {})
                }
            )
            self.long_term_memory.save_memory(memory)
        
        return message.message_id or ""
    
    def get_messages(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None,
        compressed: bool = True
    ) -> List[Message]:
        """
        获取消息列表
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数（None 使用默认值）
            max_tokens: 最大 token 数（None 使用默认值）
            compressed: 是否应用压缩
            
        Returns:
            消息列表
        """
        messages = self.storage.get_messages(session_id)
        
        if not messages:
            return []
        
        # 应用压缩
        if compressed:
            max_msg = max_messages or self.default_max_messages
            max_tok = max_tokens or self.default_max_tokens
            messages = self.compression.compress(messages, max_tok, max_msg)
        
        return messages
    
    def get_messages_for_llm(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        获取用于 LLM 的消息格式
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 格式的消息列表
        """
        messages = self.get_messages(session_id, max_messages, max_tokens)
        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages
        ]
    
    def search_messages(
        self,
        session_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """
        搜索相关消息
        
        Args:
            session_id: 会话 ID
            query: 搜索查询
            top_k: 返回前 K 条消息
            
        Returns:
            相关消息列表
        """
        messages = self.storage.get_messages(session_id)
        return self.retrieval.search(messages, query, top_k)
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        return self.storage.clear_session(session_id)
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.storage.get_session(session_id)
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        return self.storage.list_sessions(limit)
    
    def get_relevant_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5
    ) -> List[Memory]:
        """
        从长期记忆获取相关信息
        
        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤（可选）
            top_k: 返回前 K 条记忆
            
        Returns:
            相关记忆列表
        """
        if not self.long_term_memory:
            return []
        
        return self.long_term_memory.search_memories(query, memory_type, top_k)

