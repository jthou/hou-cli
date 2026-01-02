"""关键词检索引擎（基础版本）"""
from typing import List
from backend.core.context.retrieval.base import RetrievalEngine
from backend.core.context.models import Message


class KeywordRetrievalEngine(RetrievalEngine):
    """关键词检索引擎（最基础版本，仅支持简单关键词匹配）"""
    
    def search(
        self,
        messages: List[Message],
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """搜索相关消息"""
        query_words = set(query.lower().split())
        scored_messages = []
        
        for msg in messages:
            content_words = set(msg.content.lower().split())
            score = len(query_words & content_words)
            if score > 0:
                scored_messages.append((score, msg))
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        return [msg for _, msg in scored_messages[:top_k]]

