# 知识库管理设计文档

## 概述

本文档说明知识库管理系统的设计，包括文件存储、知识提炼、知识入库和向量搜索等功能。系统以知识库整理和使用为核心能力。

## 核心功能

1. **临时文件存储**：处理过程中的临时文件管理
2. **知识提炼存档**：从原始文件中提炼知识并归档
3. **知识入库**：将处理后的知识存入向量数据库
4. **向量搜索**：基于向量相似度的知识检索

## 架构设计

```
用户上传文件/输入
    ↓
文件存储管理
    ├── 临时文件区域 (temp/)
    └── 原始文件存储
    ↓
知识提炼处理
    ├── 文本提取
    ├── 分块处理
    ├── 知识提炼 (LLM)
    └── 元数据提取
    ↓
知识存档
    ├── 存档区域 (archive/)
    ├── 结构化存储
    └── 版本管理
    ↓
向量化处理
    ├── 文本嵌入
    ├── 向量生成
    └── 索引构建
    ↓
向量数据库
    ├── 向量存储
    ├── 元数据关联
    └── 索引管理
    ↓
向量搜索服务
    ├── 相似度搜索
    ├── 混合搜索
    └── 结果排序
```

## 目录结构

```
data/                          # 数据存储根目录
├── temp/                      # 临时文件区域
│   ├── uploads/              # 用户上传的临时文件
│   ├── processing/           # 处理中的文件
│   └── cache/                # 缓存文件
│
├── archive/                   # 知识存档区域
│   ├── documents/            # 原始文档
│   ├── extracted/            # 提取的文本
│   ├── refined/              # 提炼后的知识
│   └── metadata/             # 元数据文件
│
├── vectors/                   # 向量数据库
│   ├── chroma/               # Chroma 数据库文件
│   ├── indices/              # 向量索引
│   └── embeddings/           # 嵌入向量缓存
│
└── metadata/                 # 元数据存储
    ├── knowledge_index.json  # 知识索引
    ├── file_registry.json    # 文件注册表
    └── search_history.json   # 搜索历史
```

## 实现细节

### 1. 文件存储管理

```python
# backend/knowledge/storage.py
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import uuid
from datetime import datetime
from shared.platform_utils import get_app_data_dir

class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data"
        self.temp_dir = self.data_dir / "temp"
        self.archive_dir = self.data_dir / "archive"
        
        # 创建目录
        self._init_directories()
    
    def _init_directories(self):
        """初始化目录结构"""
        dirs = [
            self.temp_dir / "uploads",
            self.temp_dir / "processing",
            self.temp_dir / "cache",
            self.archive_dir / "documents",
            self.archive_dir / "extracted",
            self.archive_dir / "refined",
            self.archive_dir / "metadata",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def save_temp_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = "unknown"
    ) -> Path:
        """
        保存临时文件
        
        Returns:
            临时文件路径
        """
        file_id = str(uuid.uuid4())
        file_ext = Path(filename).suffix
        temp_file = self.temp_dir / "uploads" / f"{file_id}{file_ext}"
        
        temp_file.write_bytes(file_content)
        
        # 记录元数据
        metadata = {
            "file_id": file_id,
            "original_filename": filename,
            "file_type": file_type,
            "saved_at": datetime.now().isoformat(),
            "path": str(temp_file)
        }
        self._save_file_metadata(file_id, metadata)
        
        return temp_file
    
    def move_to_processing(self, file_id: str) -> Path:
        """将文件移动到处理中目录"""
        temp_file = self._get_temp_file(file_id)
        processing_file = self.temp_dir / "processing" / temp_file.name
        
        shutil.move(str(temp_file), str(processing_file))
        return processing_file
    
    def archive_file(
        self,
        file_id: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        归档文件到知识库
        
        Args:
            file_id: 文件ID
            category: 分类
            metadata: 附加元数据
        
        Returns:
            归档文件路径
        """
        processing_file = self.temp_dir / "processing" / f"{file_id}*"
        processing_files = list(self.temp_dir.glob(f"processing/{file_id}*"))
        
        if not processing_files:
            raise FileNotFoundError(f"File {file_id} not found in processing")
        
        source_file = processing_files[0]
        
        # 创建归档目录
        archive_path = self.archive_dir / "documents" / category
        archive_path.mkdir(parents=True, exist_ok=True)
        
        # 移动文件
        dest_file = archive_path / source_file.name
        shutil.move(str(source_file), str(dest_file))
        
        # 保存归档元数据
        archive_metadata = {
            "file_id": file_id,
            "original_filename": source_file.name,
            "category": category,
            "archived_at": datetime.now().isoformat(),
            "path": str(dest_file),
            **(metadata or {})
        }
        self._save_archive_metadata(file_id, archive_metadata)
        
        return dest_file
    
    def cleanup_temp_files(self, older_than_days: int = 7):
        """清理旧的临时文件"""
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
        
        for temp_file in self.temp_dir.rglob("*"):
            if temp_file.is_file():
                if temp_file.stat().st_mtime < cutoff_time:
                    temp_file.unlink()
    
    def _get_temp_file(self, file_id: str) -> Path:
        """获取临时文件路径"""
        temp_files = list(self.temp_dir.glob(f"uploads/{file_id}*"))
        if not temp_files:
            raise FileNotFoundError(f"Temp file {file_id} not found")
        return temp_files[0]
    
    def _save_file_metadata(self, file_id: str, metadata: Dict):
        """保存文件元数据"""
        metadata_file = self.data_dir / "metadata" / f"{file_id}.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        import json
        metadata_file.write_text(json.dumps(metadata, indent=2))
    
    def _save_archive_metadata(self, file_id: str, metadata: Dict):
        """保存归档元数据"""
        metadata_file = self.archive_dir / "metadata" / f"{file_id}.json"
        import json
        metadata_file.write_text(json.dumps(metadata, indent=2))
```

### 2. 知识提炼处理

```python
# backend/knowledge/processor.py
from typing import List, Dict, Any
from pathlib import Path
from backend.services.llm_service import LLMService
from backend.knowledge.storage import FileStorageManager
from langchain_text_splitters import RecursiveCharacterTextSplitter

class KnowledgeProcessor:
    """知识提炼处理器"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.storage = FileStorageManager()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def process_file(
        self,
        file_path: Path,
        file_type: str = "pdf"
    ) -> Dict[str, Any]:
        """
        处理文件，提炼知识
        
        Returns:
            {
                "file_id": str,
                "extracted_text": str,
                "chunks": List[str],
                "refined_knowledge": Dict,
                "metadata": Dict
            }
        """
        # 1. 提取文本
        extracted_text = await self._extract_text(file_path, file_type)
        
        # 2. 保存提取的文本
        file_id = self._get_file_id(file_path)
        extracted_file = self.storage.archive_dir / "extracted" / f"{file_id}.txt"
        extracted_file.write_text(extracted_text)
        
        # 3. 文本分块
        chunks = self.text_splitter.split_text(extracted_text)
        
        # 4. 知识提炼
        refined_knowledge = await self._refine_knowledge(extracted_text, chunks)
        
        # 5. 保存提炼后的知识
        refined_file = self.storage.archive_dir / "refined" / f"{file_id}.json"
        import json
        refined_file.write_text(json.dumps(refined_knowledge, indent=2, ensure_ascii=False))
        
        # 6. 提取元数据
        metadata = await self._extract_metadata(extracted_text, refined_knowledge)
        
        return {
            "file_id": file_id,
            "extracted_text": extracted_text,
            "chunks": chunks,
            "refined_knowledge": refined_knowledge,
            "metadata": metadata
        }
    
    async def _extract_text(self, file_path: Path, file_type: str) -> str:
        """提取文本内容"""
        if file_type == "pdf":
            from langchain_community.document_loaders import PDFPlumberLoader
            loader = PDFPlumberLoader(str(file_path))
            docs = loader.load()
            return "\n\n".join([doc.page_content for doc in docs])
        elif file_type == "txt":
            return file_path.read_text(encoding="utf-8")
        elif file_type == "md":
            return file_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def _refine_knowledge(
        self,
        text: str,
        chunks: List[str]
    ) -> Dict[str, Any]:
        """使用 LLM 提炼知识"""
        prompt = f"""请从以下文本中提炼关键知识，包括：
1. 核心概念和定义
2. 重要事实和数据
3. 关键观点和结论
4. 相关实体和关系

文本内容：
{text[:5000]}  # 限制长度

请以结构化格式返回（JSON）：
{{
    "concepts": ["概念1", "概念2"],
    "facts": ["事实1", "事实2"],
    "insights": ["观点1", "观点2"],
    "entities": ["实体1", "实体2"],
    "summary": "摘要"
}}"""
        
        response = await self.llm_service.chat(prompt)
        
        # 解析 JSON 响应
        import json
        try:
            return json.loads(response)
        except:
            # 如果解析失败，返回原始响应
            return {"raw": response}
    
    async def _extract_metadata(
        self,
        text: str,
        refined_knowledge: Dict
    ) -> Dict[str, Any]:
        """提取元数据"""
        return {
            "title": refined_knowledge.get("summary", "")[:100],
            "concepts": refined_knowledge.get("concepts", []),
            "entities": refined_knowledge.get("entities", []),
            "word_count": len(text.split()),
            "chunk_count": len(refined_knowledge.get("chunks", [])),
            "processed_at": datetime.now().isoformat()
        }
    
    def _get_file_id(self, file_path: Path) -> str:
        """从文件路径获取文件ID"""
        # 从文件名或元数据中提取
        return file_path.stem
```

### 3. 向量存储服务

```python
# backend/knowledge/vector_store.py
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from shared.platform_utils import get_app_data_dir

class VectorStore:
    """向量存储服务"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "vectors"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # 初始化向量数据库
        self.vectorstore = Chroma(
            persist_directory=str(self.data_dir / "chroma"),
            embedding_function=self.embeddings
        )
    
    async def add_knowledge(
        self,
        file_id: str,
        chunks: List[str],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        添加知识到向量数据库
        
        Args:
            file_id: 文件ID
            chunks: 文本块列表
            metadata: 元数据
        
        Returns:
            向量ID列表
        """
        # 创建文档对象
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "file_id": file_id,
                    "chunk_index": i,
                    **metadata
                }
            )
            for i, chunk in enumerate(chunks)
        ]
        
        # 添加到向量数据库
        vector_ids = self.vectorstore.add_documents(documents)
        
        return vector_ids
    
    async def add_refined_knowledge(
        self,
        file_id: str,
        refined_knowledge: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """添加提炼后的知识到向量数据库"""
        # 将提炼的知识转换为文本块
        chunks = []
        
        # 概念
        if "concepts" in refined_knowledge:
            for concept in refined_knowledge["concepts"]:
                chunks.append(f"概念：{concept}")
        
        # 事实
        if "facts" in refined_knowledge:
            for fact in refined_knowledge["facts"]:
                chunks.append(f"事实：{fact}")
        
        # 观点
        if "insights" in refined_knowledge:
            for insight in refined_knowledge["insights"]:
                chunks.append(f"观点：{insight}")
        
        # 摘要
        if "summary" in refined_knowledge:
            chunks.append(f"摘要：{refined_knowledge['summary']}")
        
        return await self.add_knowledge(file_id, chunks, metadata)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        # Chroma 的统计信息
        collection = self.vectorstore._collection
        count = collection.count()
        
        return {
            "total_documents": count,
            "collection_name": collection.name
        }
    
    def delete_by_file_id(self, file_id: str):
        """根据文件ID删除向量"""
        # 查询包含该文件ID的所有向量
        results = self.vectorstore.similarity_search(
            query="",  # 空查询，只用于过滤
            k=1000,
            filter={"file_id": file_id}
        )
        
        # 删除这些向量
        # 注意：Chroma 的删除需要向量ID
        # 这里需要根据实际API调整
```

### 4. 向量搜索服务

```python
# backend/knowledge/search.py
from typing import List, Dict, Any, Optional
from backend.knowledge.vector_store import VectorStore
from langchain_core.documents import Document

class VectorSearchService:
    """向量搜索服务"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 过滤条件
            score_threshold: 相似度阈值
        
        Returns:
            搜索结果列表
        """
        # 执行向量搜索
        results = self.vector_store.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter
        )
        
        # 格式化结果
        formatted_results = []
        for doc, score in results:
            if score >= score_threshold:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                    "file_id": doc.metadata.get("file_id"),
                    "chunk_index": doc.metadata.get("chunk_index")
                })
        
        return formatted_results
    
    async def hybrid_search(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        混合搜索（向量搜索 + 关键词搜索）
        
        Args:
            query: 查询文本
            k: 返回结果数量
            alpha: 向量搜索权重（0-1）
        """
        # 向量搜索
        vector_results = await self.search(query, k=k*2)
        
        # 关键词搜索（简单实现）
        keyword_results = await self._keyword_search(query, k=k*2)
        
        # 合并和排序结果
        combined_results = self._merge_results(
            vector_results,
            keyword_results,
            alpha
        )
        
        return combined_results[:k]
    
    async def _keyword_search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """关键词搜索（简单实现）"""
        # 这里可以实现更复杂的关键词搜索
        # 例如使用全文索引或 Elasticsearch
        query_terms = query.lower().split()
        
        # 简单的文本匹配
        results = []
        # 实际实现需要遍历所有文档
        return results
    
    def _merge_results(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict],
        alpha: float
    ) -> List[Dict]:
        """合并搜索结果"""
        # 创建结果字典（去重）
        result_dict = {}
        
        # 添加向量搜索结果
        for i, result in enumerate(vector_results):
            key = f"{result['file_id']}_{result['chunk_index']}"
            result_dict[key] = {
                **result,
                "combined_score": result["score"] * alpha
            }
        
        # 添加关键词搜索结果
        for i, result in enumerate(keyword_results):
            key = f"{result['file_id']}_{result['chunk_index']}"
            if key in result_dict:
                result_dict[key]["combined_score"] += (1 - alpha) * result.get("score", 0)
            else:
                result_dict[key] = {
                    **result,
                    "combined_score": (1 - alpha) * result.get("score", 0)
                }
        
        # 按综合分数排序
        return sorted(
            result_dict.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
    
    async def search_by_concept(
        self,
        concept: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """按概念搜索"""
        query = f"概念：{concept}"
        return await self.search(query, k=k)
    
    async def search_by_file(
        self,
        file_id: str,
        query: Optional[str] = None,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """在特定文件中搜索"""
        filter = {"file_id": file_id}
        if query:
            return await self.search(query, k=k, filter=filter)
        else:
            # 返回文件中的所有块
            return await self.search("", k=k, filter=filter)
```

### 5. 知识索引管理

```python
# backend/knowledge/indexer.py
from typing import Dict, List, Any
from pathlib import Path
import json
from datetime import datetime
from shared.platform_utils import get_app_data_dir

class KnowledgeIndexer:
    """知识索引管理器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "metadata"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.data_dir / "knowledge_index.json"
        self.registry_file = self.data_dir / "file_registry.json"
        
        self.index = self._load_index()
        self.registry = self._load_registry()
    
    def _load_index(self) -> Dict:
        """加载知识索引"""
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {
            "files": {},
            "concepts": {},
            "entities": {},
            "last_updated": None
        }
    
    def _load_registry(self) -> Dict:
        """加载文件注册表"""
        if self.registry_file.exists():
            return json.loads(self.registry_file.read_text())
        return {}
    
    def _save_index(self):
        """保存知识索引"""
        self.index["last_updated"] = datetime.now().isoformat()
        self.index_file.write_text(
            json.dumps(self.index, indent=2, ensure_ascii=False)
        )
    
    def _save_registry(self):
        """保存文件注册表"""
        self.registry_file.write_text(
            json.dumps(self.registry, indent=2, ensure_ascii=False)
        )
    
    def register_file(
        self,
        file_id: str,
        file_path: str,
        metadata: Dict[str, Any]
    ):
        """注册文件"""
        self.registry[file_id] = {
            "file_id": file_id,
            "file_path": file_path,
            "registered_at": datetime.now().isoformat(),
            **metadata
        }
        self._save_registry()
    
    def index_knowledge(
        self,
        file_id: str,
        refined_knowledge: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """索引知识"""
        # 索引文件
        self.index["files"][file_id] = {
            "file_id": file_id,
            "title": metadata.get("title", ""),
            "concepts": refined_knowledge.get("concepts", []),
            "entities": refined_knowledge.get("entities", []),
            "summary": refined_knowledge.get("summary", ""),
            "indexed_at": datetime.now().isoformat(),
            **metadata
        }
        
        # 索引概念
        for concept in refined_knowledge.get("concepts", []):
            if concept not in self.index["concepts"]:
                self.index["concepts"][concept] = []
            self.index["concepts"][concept].append(file_id)
        
        # 索引实体
        for entity in refined_knowledge.get("entities", []):
            if entity not in self.index["entities"]:
                self.index["entities"][entity] = []
            self.index["entities"][entity].append(file_id)
        
        self._save_index()
    
    def search_by_concept(self, concept: str) -> List[str]:
        """根据概念查找文件"""
        return self.index["concepts"].get(concept, [])
    
    def search_by_entity(self, entity: str) -> List[str]:
        """根据实体查找文件"""
        return self.index["entities"].get(entity, [])
    
    def get_file_info(self, file_id: str) -> Dict:
        """获取文件信息"""
        return self.index["files"].get(file_id, {})
```

## 完整工作流程

### 知识入库流程

```python
# backend/knowledge/knowledge_service.py
from backend.knowledge.storage import FileStorageManager
from backend.knowledge.processor import KnowledgeProcessor
from backend.knowledge.vector_store import VectorStore
from backend.knowledge.search import VectorSearchService
from backend.knowledge.indexer import KnowledgeIndexer

class KnowledgeService:
    """知识库服务（统一入口）"""
    
    def __init__(self):
        self.storage = FileStorageManager()
        self.processor = KnowledgeProcessor()
        self.vector_store = VectorStore()
        self.search_service = VectorSearchService(self.vector_store)
        self.indexer = KnowledgeIndexer()
    
    async def add_file_to_knowledge_base(
        self,
        file_path: Path,
        file_type: str = "pdf",
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        将文件添加到知识库（完整流程）
        
        1. 保存临时文件
        2. 移动到处理中
        3. 提取和提炼知识
        4. 归档文件
        5. 向量化并入库
        6. 建立索引
        """
        # 1. 保存临时文件
        file_content = file_path.read_bytes()
        temp_file = self.storage.save_temp_file(
            file_content,
            file_path.name,
            file_type
        )
        file_id = temp_file.stem.split("_")[0] if "_" in temp_file.stem else temp_file.stem
        
        # 2. 移动到处理中
        processing_file = self.storage.move_to_processing(file_id)
        
        # 3. 处理文件
        result = await self.processor.process_file(processing_file, file_type)
        
        # 4. 归档文件
        archived_file = self.storage.archive_file(
            file_id,
            category,
            result["metadata"]
        )
        
        # 5. 向量化并入库
        vector_ids = await self.vector_store.add_refined_knowledge(
            file_id,
            result["refined_knowledge"],
            result["metadata"]
        )
        
        # 6. 建立索引
        self.indexer.register_file(file_id, str(archived_file), result["metadata"])
        self.indexer.index_knowledge(file_id, result["refined_knowledge"], result["metadata"])
        
        return {
            "file_id": file_id,
            "archived_path": str(archived_file),
            "vector_ids": vector_ids,
            "metadata": result["metadata"]
        }
    
    async def search_knowledge(
        self,
        query: str,
        k: int = 5,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索知识"""
        if use_hybrid:
            return await self.search_service.hybrid_search(query, k=k)
        else:
            return await self.search_service.search(query, k=k)
    
    async def search_by_concept(
        self,
        concept: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """按概念搜索"""
        # 先从索引查找相关文件
        file_ids = self.indexer.search_by_concept(concept)
        
        # 然后在这些文件中搜索
        results = []
        for file_id in file_ids[:5]:  # 限制文件数量
            file_results = await self.search_service.search_by_file(
                file_id,
                query=f"概念：{concept}",
                k=k
            )
            results.extend(file_results)
        
        return results[:k]
```

## API 集成

```python
# backend/api/knowledge_routes.py
from fastapi import APIRouter, UploadFile, File
from backend.knowledge.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
knowledge_service = KnowledgeService()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = "general"
):
    """上传文件到知识库"""
    # 保存上传的文件
    file_content = await file.read()
    file_path = Path(f"/tmp/{file.filename}")
    file_path.write_bytes(file_content)
    
    # 添加到知识库
    result = await knowledge_service.add_file_to_knowledge_base(
        file_path,
        file_type=file.filename.split(".")[-1],
        category=category
    )
    
    return result

@router.post("/search")
async def search_knowledge(query: str, k: int = 5):
    """搜索知识"""
    results = await knowledge_service.search_knowledge(query, k=k)
    return {"results": results}

@router.get("/concepts")
async def list_concepts():
    """列出所有概念"""
    index = knowledge_service.indexer.index
    return {"concepts": list(index["concepts"].keys())}
```

## 总结

知识库管理系统提供了：

- ✅ **文件存储管理**：临时文件和归档文件的完整生命周期管理
- ✅ **知识提炼**：使用 LLM 从原始文件中提炼结构化知识
- ✅ **向量化存储**：将知识转换为向量并存储到向量数据库
- ✅ **向量搜索**：支持相似度搜索和混合搜索
- ✅ **知识索引**：建立概念和实体的索引，支持快速查找
- ✅ **完整工作流**：从文件上传到知识检索的完整流程

这个系统使得项目能够有效地整理、存储和检索知识，成为以知识库为核心的应用。

