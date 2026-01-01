"""上下文管理器（简化版）"""
from typing import Dict, List, Optional
from collections import deque
import uuid

class ContextManager:
    """上下文管理器，管理会话和对话历史"""
    
    def __init__(self, max_history: int = 10):
        """
        初始化上下文管理器
        
        Args:
            max_history: 最大历史消息数量，默认 10 条
        """
        self.max_history = max_history
        # 会话存储：{session_id: deque([message1, message2, ...])}
        self.sessions: Dict[str, deque] = {}
    
    def create_session(self) -> str:
        """
        创建新会话
        
        Returns:
            会话 ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = deque(maxlen=self.max_history)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        添加消息到会话历史
        
        Args:
            session_id: 会话 ID
            role: 角色（'user' 或 'assistant'）
            content: 消息内容
        """
        if session_id not in self.sessions:
            # 如果会话不存在，自动创建
            self.sessions[session_id] = deque(maxlen=self.max_history)
        
        self.sessions[session_id].append({
            "role": role,
            "content": content
        })
    
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            历史消息列表
        """
        if session_id not in self.sessions:
            return []
        
        return list(self.sessions[session_id])
    
    def clear_session(self, session_id: str):
        """
        清除会话历史
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.sessions:
            self.sessions[session_id].clear()
    
    def get_history_for_llm(self, session_id: str) -> List[Dict[str, str]]:
        """
        获取用于 LLM 的历史消息格式
        
        Args:
            session_id: 会话 ID
            
        Returns:
            LLM 格式的消息列表
        """
        return self.get_history(session_id)

