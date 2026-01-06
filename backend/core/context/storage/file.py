"""文件存储后端"""
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from backend.core.context.storage.base import StorageBackend
from backend.core.context.models import Message, Session


class FileStorageBackend(StorageBackend):
    """文件存储后端"""
    
    def __init__(self, storage_dir: Path = Path("data/contexts")):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self._load_sessions()
    
    def _get_session_dir(self, session_id: str) -> Path:
        """获取会话目录"""
        return self.storage_dir / session_id
    
    def _get_messages_file(self, session_id: str) -> Path:
        """获取消息文件"""
        return self._get_session_dir(session_id) / "messages.json"
    
    def _load_sessions(self):
        """加载会话列表"""
        if self.sessions_file.exists():
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sessions = {
                    s["session_id"]: Session.from_dict(s)
                    for s in data.get("sessions", [])
                }
        else:
            self.sessions = {}
    
    def _save_sessions(self):
        """保存会话列表"""
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump({
                "sessions": [s.to_dict() for s in self.sessions.values()]
            }, f, ensure_ascii=False, indent=2)
    
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        
        messages_file = self._get_messages_file(session_id)
        
        # 加载现有消息
        messages = []
        if messages_file.exists():
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 添加新消息
        if not message.message_id:
            message.message_id = str(uuid.uuid4())
        messages.append(message)
        
        # 保存消息
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump({
                "messages": [m.to_dict() for m in messages]
            }, f, ensure_ascii=False, indent=2)
        
        # 如果会话不存在，自动创建会话
        if session_id not in self.sessions:
            from backend.core.context.models import Session
            session = Session(
                session_id=session_id,
                metadata={}
            )
            self.sessions[session_id] = session
            self._save_sessions()
        else:
            # 更新会话时间
            self.sessions[session_id].updated_at = datetime.now()
            self._save_sessions()
        
        return True
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        messages_file = self._get_messages_file(session_id)
        
        if not messages_file.exists():
            return []
        
        with open(messages_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 应用 offset 和 limit
        if offset > 0:
            messages = messages[offset:]
        if limit:
            messages = messages[:limit]
        
        return messages
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        messages_file = self._get_messages_file(session_id)
        
        if not messages_file.exists():
            return False
        
        with open(messages_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 删除消息
        original_count = len(messages)
        messages = [m for m in messages if m.message_id != message_id]
        
        if len(messages) < original_count:
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": [m.to_dict() for m in messages]
                }, f, ensure_ascii=False, indent=2)
            return True
        
        return False
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
        
        return True
    
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        self.sessions[session.session_id] = session
        self._save_sessions()
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        sessions = list(self.sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        if limit:
            sessions = sessions[:limit]
        return sessions

