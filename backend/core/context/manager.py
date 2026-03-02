"""上下文管理器（统一接口）"""
from typing import Any, Dict, List, Optional, Tuple
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
            # 如果未指定 storage_dir，使用项目配置目录
            if storage_dir is None:
                from shared.platform_utils import get_app_data_dir
                storage_dir = get_app_data_dir() / "contexts"
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
            max_messages: 最大消息数（None 表示不限制）
            max_tokens: 最大 token 数（None 表示不限制）
            
        Returns:
            LLM 格式的消息列表
        """
        # 如果 max_messages 和 max_tokens 都为 None，则不压缩，获取完整历史
        if max_messages is None and max_tokens is None:
            messages = self.get_messages(session_id, compressed=False)
        else:
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
        """清除会话内容（消息、文章草稿及文章版本历史），会话记录保留。"""
        ast = self._get_article_storage()
        if ast:
            ast.clear_session(session_id)
        return self.storage.clear_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        """删除会话（移除记录、目录及该会话的文章版本历史）。"""
        ast = self._get_article_storage()
        if ast:
            ast.clear_session(session_id)
        if hasattr(self.storage, "delete_session"):
            return self.storage.delete_session(session_id)
        return self.storage.clear_session(session_id)

    def _get_article_storage(self):
        """懒加载文章版本存储（SQLite），用于当前文章 + 修改历史。"""
        if getattr(self, "_article_storage", None) is not None:
            return self._article_storage
        try:
            from backend.core.context.article_storage import ArticleRevisionStorage
            self._article_storage = ArticleRevisionStorage()
            return self._article_storage
        except Exception:
            self._article_storage = False
            return None

    def get_current_article(self, session_id: str) -> Optional[str]:
        """获取会话的当前文章草稿（写文章右侧输出），用于注入对话上下文。优先从版本库取，无则回退到原存储。"""
        ast = self._get_article_storage()
        if ast:
            current = ast.get_current(session_id)
            if current is not None:
                return current
        if hasattr(self.storage, "get_session_article"):
            return self.storage.get_session_article(session_id)
        return None

    def set_current_article(
        self,
        session_id: str,
        content: str,
        source: str = "user",
    ) -> bool:
        """
        保存会话的当前文章草稿；对话中会多次作为上下文使用。
        source: 'user'（用户点击写入/手动编辑）| 'agent'（助手输出自动写入）。
        会写入版本历史，并同步到原存储（如有）。
        """
        ok = False
        ast = self._get_article_storage()
        if ast:
            ok = ast.set_current(session_id, content or "", source)
        if hasattr(self.storage, "set_session_article"):
            ok = self.storage.set_session_article(session_id, content or "") or ok
        return ok

    def list_article_revisions(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Tuple[int, str, str, str]]:
        """列出该会话的文章修改历史，(id, content, source, created_at)。"""
        ast = self._get_article_storage()
        if not ast:
            return []
        return ast.list_revisions(session_id, limit=limit, offset=offset)

    def restore_article_revision(self, revision_id: int, session_id: str) -> Optional[str]:
        """将指定版本恢复为当前文章，返回恢复后的 content。"""
        ast = self._get_article_storage()
        if not ast:
            return None
        content = ast.restore_revision(revision_id, session_id)
        if content is not None and hasattr(self.storage, "set_session_article"):
            self.storage.set_session_article(session_id, content)
        return content

    def get_mw_source_titles(self, session_id: str) -> List[str]:
        """获取会话的参考 MediaWiki 页面标题列表（写文章用）。"""
        if hasattr(self.storage, "get_session_mw_sources"):
            return self.storage.get_session_mw_sources(session_id)
        return []

    def set_mw_source_titles(self, session_id: str, titles: List[str]) -> bool:
        """设置会话的参考 MediaWiki 页面标题列表。"""
        if hasattr(self.storage, "set_session_mw_sources"):
            return self.storage.set_session_mw_sources(session_id, titles)
        return False

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.storage.get_session(session_id)

    def update_session_metadata(self, session_id: str, metadata_updates: Dict[str, Any]) -> bool:
        """更新会话元数据（如 title）；updates 会合并进现有 metadata。"""
        if hasattr(self.storage, "update_session_metadata"):
            return self.storage.update_session_metadata(session_id, metadata_updates)
        return False

    def list_sessions(
        self,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        offset: int = 0,
    ) -> List[Session]:
        """列出会话；sort=updated_at|created_at，order=asc|desc，offset/limit 分页。"""
        if hasattr(self.storage, "list_sessions"):
            return self.storage.list_sessions(
                limit=limit,
                sort=sort or "updated_at",
                order=order or "desc",
                offset=offset,
            )
        return self.storage.list_sessions(limit)
    
    def get_session_preview(
        self,
        session_id: str,
        max_preview_length: int = 100
    ) -> Dict[str, Any]:
        """
        获取会话预览
        
        Args:
            session_id: 会话 ID
            max_preview_length: 预览文本最大长度
            
        Returns:
            预览信息（摘要、消息数量、最后更新时间等）
        """
        session = self.storage.get_session(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 获取消息列表
        messages = self.storage.get_messages(session_id)
        
        # 生成预览文本：优先首条用户消息；若过短（<15 字）则用首条助手回复前 100 字
        preview_text = ""
        if messages:
            first_user_msg = next(
                (msg for msg in messages if msg.role == MessageRole.USER),
                None
            )
            if first_user_msg:
                preview_text = (first_user_msg.content or "").strip()
                if len(preview_text) > max_preview_length:
                    preview_text = preview_text[:max_preview_length] + "..."
            if len(preview_text.strip()) < 15:
                first_assistant = next(
                    (msg for msg in messages if msg.role == MessageRole.ASSISTANT),
                    None
                )
                if first_assistant and (first_assistant.content or "").strip():
                    fallback = (first_assistant.content or "").strip()
                    if len(fallback) > 100:
                        fallback = fallback[:100] + "..."
                    preview_text = fallback or preview_text
        
        return {
            "session_id": session_id,
            "preview": preview_text,
            "message_count": len(messages),
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "metadata": session.metadata
        }
    
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

