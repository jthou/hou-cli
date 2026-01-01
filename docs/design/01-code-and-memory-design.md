# 代码能力和长记忆设计文档

## 概述

本文档说明系统的代码读取/编辑能力、文件系统操作、长记忆和上下文管理功能。系统具备强大的代码理解和编辑能力，以及长期记忆和上下文整理能力。

## 核心功能

1. **代码读取能力**：读取和分析代码文件
2. **代码编辑能力**：编辑和修改代码文件
3. **文件结构读取**：读取和分析本地文件系统结构
4. **长记忆系统**：存储和检索长期记忆
5. **上下文管理**：管理和整理对话上下文

## 架构设计

```
用户请求（代码相关）
    ↓
Code Agent / FileSystem Agent
    ├── 读取文件结构
    ├── 读取代码文件
    ├── 分析代码
    └── 编辑代码
    ↓
长记忆系统
    ├── 代码上下文存储
    ├── 项目结构记忆
    └── 编辑历史记录
    ↓
上下文管理器
    ├── 会话上下文整理
    ├── 代码上下文关联
    └── 上下文压缩和摘要
```

## 实现细节

### 1. 代码读取和编辑 Agent

```python
# backend/agent/agents/code_agent.py
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.agent.agents.base_agent import BaseAgent
from backend.memory.code_context import CodeContextManager
from backend.memory.long_term_memory import LongTermMemory
import ast
import difflib

class CodeAgent(BaseAgent):
    """代码读取和编辑 Agent"""
    
    def __init__(self):
        super().__init__(
            name="代码Agent",
            description="专门处理代码读取、分析和编辑",
            capabilities=[
                "读取代码文件",
                "分析代码结构",
                "编辑代码",
                "代码重构",
                "代码审查"
            ]
        )
        self.context_manager = CodeContextManager()
        self.memory = LongTermMemory()
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行代码相关任务"""
        action = task.get("action")
        
        if action == "read":
            return await self.read_code(task)
        elif action == "edit":
            return await self.edit_code(task)
        elif action == "analyze":
            return await self.analyze_code(task)
        elif action == "refactor":
            return await self.refactor_code(task)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def read_code(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        读取代码文件
        
        Args:
            task: {
                "file_path": str,
                "include_metadata": bool = True
            }
        """
        file_path = Path(task["file_path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 读取文件内容
        content = file_path.read_text(encoding="utf-8")
        
        # 分析代码结构
        metadata = {}
        if task.get("include_metadata", True):
            metadata = await self._analyze_code_structure(content, file_path)
        
        # 保存到上下文
        self.context_manager.add_file_context(file_path, content, metadata)
        
        # 保存到长记忆
        await self.memory.save_code_snapshot(
            file_path=str(file_path),
            content=content,
            metadata=metadata
        )
        
        return {
            "file_path": str(file_path),
            "content": content,
            "metadata": metadata,
            "lines": len(content.splitlines())
        }
    
    async def edit_code(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        编辑代码文件
        
        Args:
            task: {
                "file_path": str,
                "edit_type": "replace" | "insert" | "delete" | "refactor",
                "changes": Dict or str,
                "backup": bool = True
            }
        """
        file_path = Path(task["file_path"])
        edit_type = task.get("edit_type", "replace")
        backup = task.get("backup", True)
        
        # 读取原始内容
        original_content = file_path.read_text(encoding="utf-8")
        
        # 生成新内容
        if edit_type == "replace":
            new_content = task["changes"]
        elif edit_type == "insert":
            new_content = await self._insert_code(original_content, task["changes"])
        elif edit_type == "delete":
            new_content = await self._delete_code(original_content, task["changes"])
        elif edit_type == "refactor":
            new_content = await self._refactor_code(original_content, task["changes"])
        else:
            raise ValueError(f"Unknown edit_type: {edit_type}")
        
        # 创建备份
        if backup:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(original_content, encoding="utf-8")
        
        # 写入新内容
        file_path.write_text(new_content, encoding="utf-8")
        
        # 生成差异
        diff = self._generate_diff(original_content, new_content)
        
        # 更新上下文
        self.context_manager.update_file_context(file_path, new_content)
        
        # 保存编辑历史到长记忆
        await self.memory.save_edit_history(
            file_path=str(file_path),
            original_content=original_content,
            new_content=new_content,
            diff=diff,
            edit_type=edit_type
        )
        
        return {
            "file_path": str(file_path),
            "edited": True,
            "diff": diff,
            "backup_path": str(backup_path) if backup else None
        }
    
    async def analyze_code(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析代码"""
        file_path = Path(task["file_path"])
        content = file_path.read_text(encoding="utf-8")
        
        # 使用 LLM 分析代码
        analysis_prompt = f"""请分析以下代码：

文件路径：{file_path}
代码内容：
```python
{content[:5000]}  # 限制长度
```

请提供：
1. 代码功能概述
2. 主要函数和类
3. 代码质量评估
4. 潜在问题
5. 改进建议
"""
        
        analysis = await self.think(analysis_prompt)
        
        # 解析代码结构
        structure = await self._analyze_code_structure(content, file_path)
        
        return {
            "file_path": str(file_path),
            "analysis": analysis,
            "structure": structure
        }
    
    async def _analyze_code_structure(
        self,
        content: str,
        file_path: Path
    ) -> Dict[str, Any]:
        """分析代码结构"""
        structure = {
            "file_type": file_path.suffix,
            "lines": len(content.splitlines()),
            "functions": [],
            "classes": [],
            "imports": []
        }
        
        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        structure["functions"].append({
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args]
                        })
                    elif isinstance(node, ast.ClassDef):
                        structure["classes"].append({
                            "name": node.name,
                            "line": node.lineno,
                            "methods": [
                                n.name for n in node.body
                                if isinstance(n, ast.FunctionDef)
                            ]
                        })
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            structure["imports"].extend([alias.name for alias in node.names])
                        else:
                            structure["imports"].append(node.module or "")
            except SyntaxError:
                pass
        
        return structure
    
    async def _insert_code(
        self,
        original_content: str,
        changes: Dict[str, Any]
    ) -> str:
        """插入代码"""
        lines = original_content.splitlines()
        insert_line = changes.get("line", len(lines))
        code_to_insert = changes.get("code", "")
        
        lines.insert(insert_line, code_to_insert)
        return "\n".join(lines)
    
    async def _delete_code(
        self,
        original_content: str,
        changes: Dict[str, Any]
    ) -> str:
        """删除代码"""
        lines = original_content.splitlines()
        start_line = changes.get("start_line", 0)
        end_line = changes.get("end_line", len(lines))
        
        del lines[start_line:end_line]
        return "\n".join(lines)
    
    async def _refactor_code(
        self,
        original_content: str,
        changes: Dict[str, Any]
    ) -> str:
        """重构代码"""
        refactor_instruction = changes.get("instruction", "")
        
        # 使用 LLM 进行重构
        prompt = f"""请重构以下代码：

重构要求：{refactor_instruction}

原始代码：
```python
{original_content}
```

请返回重构后的完整代码，保持功能不变。"""
        
        refactored = await self.think(prompt)
        
        # 提取代码块
        if "```python" in refactored:
            start = refactored.find("```python") + len("```python")
            end = refactored.find("```", start)
            refactored = refactored[start:end].strip()
        elif "```" in refactored:
            start = refactored.find("```") + 3
            end = refactored.find("```", start)
            refactored = refactored[start:end].strip()
        
        return refactored
    
    def _generate_diff(
        self,
        original: str,
        modified: str
    ) -> str:
        """生成代码差异"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="original",
            tofile="modified",
            lineterm=""
        )
        
        return "".join(diff)
```

### 2. 文件系统操作 Agent

```python
# backend/agent/agents/filesystem_agent.py
from typing import List, Dict, Any
from pathlib import Path
from backend.agent.agents.base_agent import BaseAgent
from backend.memory.long_term_memory import LongTermMemory

class FileSystemAgent(BaseAgent):
    """文件系统操作 Agent"""
    
    def __init__(self):
        super().__init__(
            name="文件系统Agent",
            description="专门处理文件系统操作和文件结构读取",
            capabilities=[
                "读取文件结构",
                "遍历目录",
                "搜索文件",
                "读取文件元数据"
            ]
        )
        self.memory = LongTermMemory()
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行文件系统操作"""
        action = task.get("action")
        
        if action == "list_directory":
            return await self.list_directory(task)
        elif action == "read_structure":
            return await self.read_structure(task)
        elif action == "search_files":
            return await self.search_files(task)
        elif action == "get_file_info":
            return await self.get_file_info(task)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def list_directory(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        列出目录内容
        
        Args:
            task: {
                "path": str,
                "recursive": bool = False,
                "include_hidden": bool = False
            }
        """
        path = Path(task["path"])
        recursive = task.get("recursive", False)
        include_hidden = task.get("include_hidden", False)
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        if path.is_file():
            return {
                "type": "file",
                "path": str(path),
                "name": path.name,
                "size": path.stat().st_size
            }
        
        items = []
        if recursive:
            for item in path.rglob("*"):
                if not include_hidden and item.name.startswith("."):
                    continue
                items.append(self._get_item_info(item))
        else:
            for item in path.iterdir():
                if not include_hidden and item.name.startswith("."):
                    continue
                items.append(self._get_item_info(item))
        
        # 保存到长记忆
        await self.memory.save_directory_structure(
            path=str(path),
            structure=items
        )
        
        return {
            "type": "directory",
            "path": str(path),
            "items": items,
            "count": len(items)
        }
    
    async def read_structure(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        读取项目结构
        
        Args:
            task: {
                "root_path": str,
                "max_depth": int = 3,
                "file_types": List[str] = None
            }
        """
        root_path = Path(task["root_path"])
        max_depth = task.get("max_depth", 3)
        file_types = task.get("file_types")
        
        structure = {
            "root": str(root_path),
            "type": "directory",
            "children": []
        }
        
        def build_tree(path: Path, depth: int = 0):
            if depth > max_depth:
                return None
            
            item_info = self._get_item_info(path)
            
            if path.is_dir():
                children = []
                try:
                    for child in path.iterdir():
                        if child.name.startswith("."):
                            continue
                        if file_types and child.is_file():
                            if not any(child.name.endswith(ft) for ft in file_types):
                                continue
                        child_info = build_tree(child, depth + 1)
                        if child_info:
                            children.append(child_info)
                except PermissionError:
                    pass
                
                item_info["children"] = children
                item_info["child_count"] = len(children)
            
            return item_info
        
        structure["children"] = [
            build_tree(item)
            for item in root_path.iterdir()
            if not item.name.startswith(".")
        ]
        
        # 保存到长记忆
        await self.memory.save_project_structure(
            root_path=str(root_path),
            structure=structure
        )
        
        return structure
    
    async def search_files(
        self,
        task: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        搜索文件
        
        Args:
            task: {
                "root_path": str,
                "pattern": str,  # 文件名模式
                "content_pattern": str = None,  # 内容模式
                "file_types": List[str] = None
            }
        """
        root_path = Path(task["root_path"])
        pattern = task["pattern"]
        content_pattern = task.get("content_pattern")
        file_types = task.get("file_types")
        
        results = []
        
        for file_path in root_path.rglob(pattern):
            if file_types and not any(file_path.name.endswith(ft) for ft in file_types):
                continue
            
            file_info = self._get_item_info(file_path)
            
            # 如果指定了内容模式，搜索文件内容
            if content_pattern and file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if content_pattern.lower() in content.lower():
                        file_info["matches"] = True
                        results.append(file_info)
                except:
                    pass
            else:
                results.append(file_info)
        
        return results
    
    def _get_item_info(self, item: Path) -> Dict[str, Any]:
        """获取文件/目录信息"""
        stat = item.stat()
        return {
            "name": item.name,
            "path": str(item),
            "type": "directory" if item.is_dir() else "file",
            "size": stat.st_size if item.is_file() else 0,
            "modified": stat.st_mtime,
            "extension": item.suffix if item.is_file() else None
        }
    
    async def get_file_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """获取文件详细信息"""
        file_path = Path(task["file_path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        
        info = {
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "extension": file_path.suffix
        }
        
        # 如果是代码文件，添加代码相关信息
        if file_path.suffix in [".py", ".js", ".ts", ".java", ".cpp", ".c"]:
            try:
                content = file_path.read_text(encoding="utf-8")
                info["lines"] = len(content.splitlines())
                info["language"] = file_path.suffix[1:]
            except:
                pass
        
        return info
```

### 3. 长记忆系统

```python
# backend/memory/long_term_memory.py
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from shared.platform_utils import get_app_data_dir
from backend.knowledge.vector_store import VectorStore

class LongTermMemory:
    """长记忆系统"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用向量数据库存储记忆
        self.vector_store = VectorStore()
        
        # 记忆索引
        self.memory_index = self._load_index()
    
    def _load_index(self) -> Dict:
        """加载记忆索引"""
        index_file = self.data_dir / "memory_index.json"
        if index_file.exists():
            return json.loads(index_file.read_text())
        return {
            "code_snapshots": {},
            "edit_history": [],
            "project_structures": {},
            "conversations": []
        }
    
    def _save_index(self):
        """保存记忆索引"""
        index_file = self.data_dir / "memory_index.json"
        index_file.write_text(
            json.dumps(self.memory_index, indent=2, ensure_ascii=False)
        )
    
    async def save_code_snapshot(
        self,
        file_path: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        """保存代码快照"""
        snapshot_id = f"{file_path}_{datetime.now().timestamp()}"
        
        snapshot = {
            "id": snapshot_id,
            "file_path": file_path,
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存到文件
        snapshot_file = self.data_dir / "code_snapshots" / f"{snapshot_id}.json"
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False)
        )
        
        # 添加到索引
        if file_path not in self.memory_index["code_snapshots"]:
            self.memory_index["code_snapshots"][file_path] = []
        self.memory_index["code_snapshots"][file_path].append(snapshot_id)
        self._save_index()
        
        # 存储到向量数据库（用于搜索）
        await self.vector_store.add_documents([{
            "content": content,
            "metadata": {
                "type": "code_snapshot",
                "file_path": file_path,
                "snapshot_id": snapshot_id,
                **metadata
            }
        }])
    
    async def save_edit_history(
        self,
        file_path: str,
        original_content: str,
        new_content: str,
        diff: str,
        edit_type: str
    ):
        """保存编辑历史"""
        edit_record = {
            "id": f"edit_{datetime.now().timestamp()}",
            "file_path": file_path,
            "edit_type": edit_type,
            "diff": diff,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存到文件
        edit_file = self.data_dir / "edit_history" / f"{edit_record['id']}.json"
        edit_file.parent.mkdir(parents=True, exist_ok=True)
        edit_file.write_text(
            json.dumps(edit_record, indent=2, ensure_ascii=False)
        )
        
        # 添加到索引
        self.memory_index["edit_history"].append(edit_record["id"])
        self._save_index()
    
    async def save_directory_structure(
        self,
        path: str,
        structure: List[Dict]
    ):
        """保存目录结构"""
        structure_record = {
            "path": path,
            "structure": structure,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存到文件
        structure_file = self.data_dir / "structures" / f"{Path(path).name}_{datetime.now().timestamp()}.json"
        structure_file.parent.mkdir(parents=True, exist_ok=True)
        structure_file.write_text(
            json.dumps(structure_record, indent=2, ensure_ascii=False)
        )
    
    async def save_project_structure(
        self,
        root_path: str,
        structure: Dict
    ):
        """保存项目结构"""
        self.memory_index["project_structures"][root_path] = {
            "structure": structure,
            "timestamp": datetime.now().isoformat()
        }
        self._save_index()
    
    async def search_code_memory(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索代码记忆"""
        results = await self.vector_store.similarity_search(
            query=query,
            k=k,
            filter={"type": "code_snapshot"}
        )
        return results
    
    def get_code_history(self, file_path: str) -> List[Dict]:
        """获取代码历史"""
        if file_path not in self.memory_index["code_snapshots"]:
            return []
        
        history = []
        for snapshot_id in self.memory_index["code_snapshots"][file_path]:
            snapshot_file = self.data_dir / "code_snapshots" / f"{snapshot_id}.json"
            if snapshot_file.exists():
                history.append(json.loads(snapshot_file.read_text()))
        
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)
    
    def get_edit_history(self, file_path: Optional[str] = None) -> List[Dict]:
        """获取编辑历史"""
        history = []
        for edit_id in self.memory_index["edit_history"]:
            edit_file = self.data_dir / "edit_history" / f"{edit_id}.json"
            if edit_file.exists():
                edit_record = json.loads(edit_file.read_text())
                if file_path is None or edit_record["file_path"] == file_path:
                    history.append(edit_record)
        
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)
```

### 4. 上下文管理器

```python
# backend/memory/context_manager.py
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from collections import deque

class ContextManager:
    """上下文管理器"""
    
    def __init__(self, max_context_length: int = 10000):
        self.max_context_length = max_context_length
        self.contexts = {}
        self.code_contexts = {}
    
    def add_to_context(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """添加到上下文"""
        if session_id not in self.contexts:
            self.contexts[session_id] = deque(maxlen=100)  # 最多保存100条
        
        self.contexts[session_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict]:
        """获取上下文"""
        if session_id not in self.contexts:
            return []
        
        context = list(self.contexts[session_id])
        
        # 如果指定了最大token数，压缩上下文
        if max_tokens:
            context = self._compress_context(context, max_tokens)
        
        return context
    
    def add_file_context(
        self,
        file_path: Path,
        content: str,
        metadata: Dict
    ):
        """添加文件上下文"""
        file_key = str(file_path)
        self.code_contexts[file_key] = {
            "file_path": file_key,
            "content": content,
            "metadata": metadata,
            "last_accessed": datetime.now().isoformat()
        }
    
    def get_file_context(self, file_path: Path) -> Optional[Dict]:
        """获取文件上下文"""
        file_key = str(file_path)
        if file_key in self.code_contexts:
            self.code_contexts[file_key]["last_accessed"] = datetime.now().isoformat()
            return self.code_contexts[file_key]
        return None
    
    def get_related_context(
        self,
        session_id: str,
        query: str,
        k: int = 5
    ) -> List[Dict]:
        """获取相关上下文（基于查询）"""
        context = self.get_context(session_id)
        
        # 简单的关键词匹配
        query_words = set(query.lower().split())
        scored_contexts = []
        
        for ctx in context:
            content_words = set(ctx["content"].lower().split())
            score = len(query_words & content_words)
            if score > 0:
                scored_contexts.append((score, ctx))
        
        # 按分数排序
        scored_contexts.sort(key=lambda x: x[0], reverse=True)
        
        return [ctx for _, ctx in scored_contexts[:k]]
    
    def _compress_context(
        self,
        context: List[Dict],
        max_tokens: int
    ) -> List[Dict]:
        """压缩上下文"""
        # 简单的压缩策略：保留最近的上下文
        # 实际可以使用更复杂的策略，如摘要、重要性评分等
        
        current_length = sum(len(ctx["content"]) for ctx in context)
        
        if current_length <= max_tokens:
            return context
        
        # 保留最近的上下文
        compressed = []
        length = 0
        
        for ctx in reversed(context):
            ctx_length = len(ctx["content"])
            if length + ctx_length <= max_tokens:
                compressed.insert(0, ctx)
                length += ctx_length
            else:
                break
        
        return compressed
    
    def summarize_context(
        self,
        session_id: str
    ) -> str:
        """总结上下文"""
        context = self.get_context(session_id)
        
        if not context:
            return "无上下文"
        
        # 生成摘要
        summary_parts = []
        summary_parts.append(f"会话包含 {len(context)} 条消息")
        
        # 提取关键信息
        files_mentioned = set()
        for ctx in context:
            if "file_path" in ctx.get("metadata", {}):
                files_mentioned.add(ctx["metadata"]["file_path"])
        
        if files_mentioned:
            summary_parts.append(f"涉及文件：{', '.join(list(files_mentioned)[:5])}")
        
        return "\n".join(summary_parts)
    
    def clear_context(self, session_id: str):
        """清除上下文"""
        if session_id in self.contexts:
            del self.contexts[session_id]
```

### 5. 代码上下文缓存

```python
# backend/memory/code_context.py
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from backend.memory.context_manager import ContextManager

class CodeContextManager:
    """代码上下文管理器"""
    
    def __init__(self, cache_ttl_hours: int = 24):
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.context_manager = ContextManager()
        self.code_cache = {}
    
    def add_file_context(
        self,
        file_path: Path,
        content: str,
        metadata: Dict
    ):
        """添加文件上下文"""
        file_key = str(file_path)
        self.code_cache[file_key] = {
            "content": content,
            "metadata": metadata,
            "cached_at": datetime.now()
        }
        
        # 同时添加到通用上下文管理器
        self.context_manager.add_file_context(file_path, content, metadata)
    
    def get_file_context(
        self,
        file_path: Path
    ) -> Optional[Dict]:
        """获取文件上下文（带缓存）"""
        file_key = str(file_path)
        
        if file_key in self.code_cache:
            cached = self.code_cache[file_key]
            
            # 检查缓存是否过期
            if datetime.now() - cached["cached_at"] < self.cache_ttl:
                return cached
        
        # 从上下文管理器获取
        return self.context_manager.get_file_context(file_path)
    
    def update_file_context(
        self,
        file_path: Path,
        new_content: str
    ):
        """更新文件上下文"""
        file_key = str(file_path)
        
        if file_key in self.code_cache:
            self.code_cache[file_key]["content"] = new_content
            self.code_cache[file_key]["cached_at"] = datetime.now()
        
        # 更新上下文管理器
        metadata = self.code_cache.get(file_key, {}).get("metadata", {})
        self.context_manager.add_file_context(file_path, new_content, metadata)
    
    def get_project_context(
        self,
        project_root: Path
    ) -> Dict:
        """获取项目上下文"""
        project_files = []
        
        for file_key, cached in self.code_cache.items():
            file_path = Path(file_key)
            if project_root in file_path.parents or file_path == project_root:
                project_files.append({
                    "path": file_key,
                    "metadata": cached.get("metadata", {})
                })
        
        return {
            "project_root": str(project_root),
            "files": project_files,
            "file_count": len(project_files)
        }
```

## 集成示例

### 代码读取和编辑工作流

```python
# 使用示例
code_agent = CodeAgent()

# 1. 读取代码
result = await code_agent.execute({
    "action": "read",
    "file_path": "src/main.py",
    "include_metadata": True
})

# 2. 分析代码
analysis = await code_agent.execute({
    "action": "analyze",
    "file_path": "src/main.py"
})

# 3. 编辑代码
edit_result = await code_agent.execute({
    "action": "edit",
    "file_path": "src/main.py",
    "edit_type": "refactor",
    "changes": {
        "instruction": "优化函数，提高性能"
    },
    "backup": True
})
```

### 文件结构读取

```python
filesystem_agent = FileSystemAgent()

# 读取项目结构
structure = await filesystem_agent.execute({
    "action": "read_structure",
    "root_path": ".",
    "max_depth": 3,
    "file_types": [".py", ".js", ".ts"]
})
```

### 长记忆检索

```python
memory = LongTermMemory()

# 搜索代码记忆
results = await memory.search_code_memory(
    query="用户认证功能",
    k=5
)

# 获取代码历史
history = memory.get_code_history("src/main.py")
```

## 总结

代码能力和长记忆系统提供了：

- ✅ **代码读取能力**：读取和分析代码文件，提取结构信息
- ✅ **代码编辑能力**：支持多种编辑方式（替换、插入、删除、重构）
- ✅ **文件系统操作**：读取文件结构、遍历目录、搜索文件
- ✅ **长记忆系统**：存储代码快照、编辑历史、项目结构
- ✅ **上下文管理**：管理会话上下文、代码上下文、上下文压缩和摘要
- ✅ **智能检索**：基于向量搜索的代码记忆检索

这个系统使得 Agent 能够理解代码、编辑代码，并记住之前的操作和上下文，提供强大的代码处理能力。

