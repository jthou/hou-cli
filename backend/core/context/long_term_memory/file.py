"""基于文件的长期记忆实现"""
import json
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from backend.core.context.long_term_memory.base import LongTermMemory
from backend.core.context.long_term_memory.models import Memory, MemoryType


class FileLongTermMemory(LongTermMemory):
    """基于文件的长期记忆实现"""
    
    def __init__(self, storage_dir: Path = Path("data/long_term_memory")):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memories_dir = self.storage_dir / "memories"
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.index = {
                    memory_id: Memory.from_dict(m)
                    for memory_id, m in data.get("memories", {}).items()
                }
        else:
            self.index = {}
    
    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "memories": {
                    memory_id: memory.to_dict()
                    for memory_id, memory in self.index.items()
                }
            }, f, ensure_ascii=False, indent=2)
    
    def _get_memory_file(self, memory_id: str) -> Path:
        """获取记忆文件路径"""
        return self.memories_dir / f"{memory_id}.json"
    
    def save_memory(self, memory: Memory) -> bool:
        """保存记忆"""
        if not memory.memory_id:
            memory.memory_id = str(uuid.uuid4())
        
        # 保存到文件
        memory_file = self._get_memory_file(memory.memory_id)
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self.index[memory.memory_id] = memory
        self._save_index()
        
        return True
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        if memory_id in self.index:
            memory_file = self._get_memory_file(memory_id)
            if memory_file.exists():
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    memory = Memory.from_dict(data)
                    # 更新访问信息
                    memory.access_count += 1
                    memory.last_accessed = datetime.now()
                    self.save_memory(memory)
                    return memory
        return None
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """搜索记忆（简单关键词匹配）"""
        query_words = set(query.lower().split())
        scored_memories = []
        
        for memory in self.index.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # 关键词匹配
            content_words = set(memory.content.lower().split())
            summary_words = set((memory.summary or "").lower().split())
            tag_words = set([tag.lower() for tag in memory.tags])
            
            score = (
                len(query_words & content_words) * 3 +
                len(query_words & summary_words) * 2 +
                len(query_words & tag_words)
            )
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # 按分数排序
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [memory for _, memory in scored_memories[:top_k]]
    
    def get_memories_by_tags(
        self,
        tags: List[str],
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """根据标签获取记忆"""
        tag_set = set([tag.lower() for tag in tags])
        memories = []
        
        for memory in self.index.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            
            memory_tags = set([tag.lower() for tag in memory.tags])
            if tag_set & memory_tags:
                memories.append(memory)
        
        return memories
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.index:
            memory_file = self._get_memory_file(memory_id)
            if memory_file.exists():
                memory_file.unlink()
            
            del self.index[memory_id]
            self._save_index()
            return True
        
        return False
    
    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        if memory.memory_id in self.index:
            memory.updated_at = datetime.now()
            return self.save_memory(memory)
        return False

