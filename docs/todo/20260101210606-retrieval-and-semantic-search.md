# TODO: 检索功能和语义搜索实现

## 任务概述

实现检索功能和语义搜索，包括 KeywordRetrievalEngine 完善、长期记忆语义搜索（Vector Store: Chroma）、向量嵌入生成和语义搜索集成。

**创建时间**: 2025-01-01  
**优先级**: P1（中优先级）  
**预计工时**: 3-4 天  
**状态**: ⏳ 待开始

**前置任务**: 
- [ ] TODO: 上下文存储核心功能实现（20260101210602）
- [ ] TODO: 长期记忆基础实现（20260101210603）

**关联文档**:
- [主设计文档](../../design/01-context-storage-and-compression-design.md)
- [长期记忆技术选型](../../design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md)

---

## 一、任务范围

### 1.1 核心功能清单

根据设计文档"阶段 5: 检索功能和语义搜索（P1）"，需要实现：

- [ ] **KeywordRetrievalEngine 完善**
  - 完善关键词检索算法
  - 支持更复杂的匹配（如部分匹配、模糊匹配）
  - 性能优化（如需要）

- [ ] **检索功能测试**
  - 关键词检索测试
  - 检索准确性测试
  - 性能测试

- [ ] **长期记忆语义搜索（Vector Store: Chroma）**
  - Chroma 向量存储集成
  - 向量嵌入生成（需要 embedding 模型）
  - 语义搜索实现
  - 元数据过滤支持

- [ ] **向量嵌入生成**
  - 集成 embedding 模型（如 OpenAI embeddings, Ollama embeddings）
  - 文本向量化
  - 批量向量化（性能优化）

- [ ] **语义搜索集成**
  - 与 FileLongTermMemory 集成
  - 创建 VectorLongTermMemory
  - 支持向量搜索和关键词搜索混合

---

## 二、实现步骤

### 2.1 阶段 1: KeywordRetrievalEngine 完善（0.5天）

#### 步骤 1.1: 完善关键词检索
- [ ] 优化 `backend/core/context/retrieval/keyword.py`
- [ ] 改进匹配算法：
  - 支持部分匹配
  - 支持大小写不敏感
  - 支持多词匹配评分
- [ ] 性能优化（如需要）

#### 步骤 1.2: 单元测试
- [ ] 完善 `backend/core/context/retrieval/tests/test_keyword.py`
- [ ] 测试各种匹配场景
- [ ] 测试性能

**验收标准**:
- [ ] KeywordRetrievalEngine 完善
- [ ] 所有测试通过

---

### 2.2 阶段 2: Chroma 向量存储集成（1天）

#### 步骤 2.1: 安装和配置 Chroma
- [ ] 添加 `chromadb` 到 `requirements.txt`
- [ ] 创建 `backend/core/context/long_term_memory/vector_store.py`
- [ ] 实现 `ChromaVectorStore` 类：
  - 初始化 Chroma 客户端（PersistentClient）
  - 创建或获取 collection
  - 配置持久化目录

#### 步骤 2.2: 实现向量存储操作
- [ ] 实现 `add_memory()` 方法：
  - 添加向量、文档、元数据
- [ ] 实现 `search()` 方法：
  - 向量相似度搜索
  - 支持元数据过滤
  - 支持 top_k 参数
- [ ] 实现 `delete_memory()` 方法
- [ ] 实现 `update_memory()` 方法

#### 步骤 2.3: 单元测试
- [ ] 创建 `backend/core/context/long_term_memory/tests/test_vector_store.py`
- [ ] 测试添加向量
- [ ] 测试向量搜索
- [ ] 测试元数据过滤
- [ ] 测试删除和更新

**验收标准**:
- [ ] ChromaVectorStore 实现完成
- [ ] 所有单元测试通过
- [ ] 向量存储正常工作

---

### 2.3 阶段 3: 向量嵌入生成（1天）

#### 步骤 3.1: 选择 Embedding 模型
- [ ] 评估可选方案：
  - OpenAI embeddings（需要 API Key）
  - Ollama embeddings（本地，需要 Ollama）
  - sentence-transformers（本地，需要模型文件）
- [ ] 推荐方案：Ollama（本地，零 API 成本）或 sentence-transformers

#### 步骤 3.2: 实现 Embedding 服务
- [ ] 创建 `backend/services/embeddings/` 目录
- [ ] 创建 `embedding_service.py`：
  - 定义 EmbeddingService 接口
  - 实现 OllamaEmbeddingService（如选择 Ollama）
  - 或实现 SentenceTransformerEmbeddingService（如选择 sentence-transformers）
- [ ] 实现 `embed_query()` 方法（单个文本）
- [ ] 实现 `embed_batch()` 方法（批量文本，性能优化）

#### 步骤 3.3: 单元测试
- [ ] 创建 `backend/services/embeddings/tests/test_embedding_service.py`
- [ ] 测试向量生成
- [ ] 测试批量向量生成
- [ ] 测试向量维度

**验收标准**:
- [ ] Embedding 服务实现完成
- [ ] 所有单元测试通过
- [ ] 向量维度正确

---

### 2.4 阶段 4: 语义搜索集成（1天）

#### 步骤 4.1: 创建 VectorLongTermMemory
- [ ] 创建 `backend/core/context/long_term_memory/vector.py`
- [ ] 实现 `VectorLongTermMemory` 类：
  - 继承或组合 FileLongTermMemory
  - 集成 ChromaVectorStore
  - 集成 EmbeddingService
- [ ] 实现 `save_memory()` 方法：
  - 保存到 Memory Store
  - 生成向量嵌入
  - 保存到 Vector Store
  - 更新 Index Store
- [ ] 实现 `search_memories()` 方法：
  - 生成查询向量
  - 向量搜索
  - 元数据过滤
  - 返回完整记忆对象

#### 步骤 4.2: 集成到 ContextManager
- [ ] 修改 ContextManager 支持 VectorLongTermMemory
- [ ] 实现混合搜索（向量搜索 + 关键词搜索）
- [ ] 实现搜索结果合并和排序

#### 步骤 4.3: 集成测试
- [ ] 创建 `tests/integration/test_semantic_search.py`
- [ ] 测试端到端语义搜索流程
- [ ] 测试搜索准确性
- [ ] 测试性能

**验收标准**:
- [ ] VectorLongTermMemory 实现完成
- [ ] 语义搜索集成完成
- [ ] 所有集成测试通过

---

### 2.5 阶段 5: 使用示例和文档（0.5天）

#### 步骤 5.1: 创建使用示例
- [ ] 语义搜索使用示例
- [ ] 向量存储使用示例
- [ ] 混合搜索示例

#### 步骤 5.2: 更新文档
- [ ] 更新使用文档
- [ ] 添加配置说明
- [ ] 添加性能优化建议

**验收标准**:
- [ ] 使用示例清晰
- [ ] 文档完整

---

## 三、技术选型

### 3.1 Vector Store

**推荐**: Chroma

**技术栈**: `chromadb` 库

**理由**:
- ✅ 轻量级（单文件数据库）
- ✅ 易用（API 简单）
- ✅ 功能完整（支持元数据过滤、持久化）
- ✅ 项目已有（设计文档中已提到）

**详细技术选型**: 参考 `docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md` 第 2 节

### 3.2 Embedding 模型

**推荐方案 A**: Ollama（本地，推荐）

**技术栈**: `ollama` 库或 HTTP API

**优点**:
- ✅ 本地运行，零 API 成本
- ✅ 隐私保护
- ✅ 无需网络

**缺点**:
- ⚠️ 需要安装 Ollama
- ⚠️ 需要下载模型

**推荐方案 B**: sentence-transformers（本地备选）

**技术栈**: `sentence-transformers` 库

**优点**:
- ✅ 本地运行
- ✅ 无需额外服务

**缺点**:
- ⚠️ 需要下载模型文件
- ⚠️ 内存占用较大

**推荐方案 C**: OpenAI embeddings（云端）

**技术栈**: `openai` 库

**优点**:
- ✅ 无需本地模型
- ✅ 性能好

**缺点**:
- ❌ 需要 API Key
- ❌ 有 API 成本
- ❌ 需要网络

**建议**: 优先使用 Ollama（本地，零成本）

---

## 四、模块结构

```
backend/core/context/long_term_memory/
├── vector.py               # VectorLongTermMemory
└── vector_store.py         # ChromaVectorStore

backend/services/embeddings/
├── __init__.py
├── embedding_service.py   # EmbeddingService 接口和实现
└── tests/
    └── test_embedding_service.py
```

---

## 五、测试要求

### 5.1 单元测试

- [ ] ChromaVectorStore 测试
- [ ] EmbeddingService 测试
- [ ] VectorLongTermMemory 测试

### 5.2 集成测试

- [ ] 语义搜索端到端测试
- [ ] 混合搜索测试
- [ ] 性能测试

### 5.3 测试覆盖率

**目标**: > 80%

---

## 六、验收标准

- [ ] KeywordRetrievalEngine 完善完成
- [ ] ChromaVectorStore 实现完成
- [ ] EmbeddingService 实现完成
- [ ] VectorLongTermMemory 实现完成
- [ ] 语义搜索集成完成
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 使用示例可以正常运行
- [ ] 文档完整

---

## 七、注意事项

### 7.1 依赖管理

- ⚠️ `chromadb` 需要添加到 `requirements.txt`
- ⚠️ Embedding 模型选择需要明确（Ollama 或 sentence-transformers）
- ⚠️ 如果使用 Ollama，需要说明安装和配置步骤

### 7.2 性能考虑

- ⚠️ 向量生成可能较慢，考虑批量处理
- ⚠️ 向量搜索性能取决于数据量
- ⚠️ 如果向量数据量大，考虑索引优化

### 7.3 错误处理

- ⚠️ Chroma 连接错误处理
- ⚠️ Embedding 服务错误处理
- ⚠️ 向量生成失败处理

---

## 八、后续任务

完成本任务后，可以继续：

- [ ] TODO: 扩展功能（阶段 6，P3）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0  
**状态**: ⏳ 待开始

