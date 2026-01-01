# TODO: 高级压缩策略实现

## 任务概述

实现高级压缩策略：TokenLimitCompression 和 ImportanceScoringCompression，支持基于 token 限制和重要性评分的消息压缩。

**创建时间**: 2025-01-01  
**优先级**: P1（中优先级）  
**预计工时**: 2-3 天  
**状态**: ⏳ 待开始

**前置任务**: 
- [ ] TODO: 上下文存储核心功能实现（20260101210602）

**关联文档**:
- [主设计文档](../../design/01-context-storage-and-compression-design.md)

---

## 一、任务范围

### 1.1 核心功能清单

根据设计文档"阶段 4: 高级压缩（P1）"，需要实现：

- [ ] **TokenLimitCompression 实现**
  - Token 计算（默认：1 token ≈ 4 字符）
  - 支持自定义 tokenizer
  - 压缩策略：优先保留系统消息，然后从后往前保留
  - 支持 max_tokens 和 max_messages 参数

- [ ] **ImportanceScoringCompression 实现**
  - 重要性评分算法：
    - 系统消息：+10.0
    - 最近 5 条消息：+5.0
    - 包含关键词：+2.0
    - 用户消息：+1.0
  - 按分数排序选择消息
  - 按时间顺序重新排序
  - 支持 max_tokens 和 max_messages 参数

- [ ] **压缩策略性能测试**
  - 性能对比测试
  - 压缩效果测试
  - 边界情况测试

---

## 二、实现步骤

### 2.1 阶段 1: TokenLimitCompression（1天）

#### 步骤 1.1: 实现 Token 计算
- [ ] 创建 `backend/core/context/compression/token_limit.py`
- [ ] 实现 `_default_tokenizer()` 方法（1 token ≈ 4 字符）
- [ ] 支持自定义 tokenizer（通过构造函数传入）

#### 步骤 1.2: 实现压缩逻辑
- [ ] 实现 `compress()` 方法：
  - 如果只有 max_messages，使用时间窗口压缩
  - 如果只有 max_tokens，计算总 token 数
  - 如果总 token 数 <= max_tokens，返回全部消息
  - 否则：
    1. 优先保留系统消息（不超过 max_tokens）
    2. 从后往前保留其他消息（不超过 max_tokens）
    3. 按时间顺序重新排序

#### 步骤 1.3: 单元测试
- [ ] 创建 `backend/core/context/compression/tests/test_token_limit.py`
- [ ] 测试 token 计算
- [ ] 测试系统消息优先保留
- [ ] 测试从后往前保留
- [ ] 测试边界情况（空消息、单条消息、全部保留）

**验收标准**:
- [ ] TokenLimitCompression 实现完成
- [ ] 所有单元测试通过
- [ ] 压缩逻辑正确

---

### 2.2 阶段 2: ImportanceScoringCompression（1天）

#### 步骤 2.1: 实现重要性评分算法
- [ ] 创建 `backend/core/context/compression/importance.py`
- [ ] 实现 `_calculate_importance()` 方法：
  - 系统消息：+10.0
  - 最近 5 条消息：+5.0
  - 包含关键词（"错误", "问题", "重要", "关键", "失败", "异常"）：+2.0
  - 用户消息：+1.0

#### 步骤 2.2: 实现压缩逻辑
- [ ] 实现 `compress()` 方法：
  - 计算每条消息的重要性分数
  - 按分数排序（降序）
  - 选择最重要的消息，直到达到限制（max_tokens 或 max_messages）
  - 按时间顺序重新排序

#### 步骤 2.3: 单元测试
- [ ] 创建 `backend/core/context/compression/tests/test_importance.py`
- [ ] 测试重要性评分计算
- [ ] 测试按分数选择消息
- [ ] 测试时间顺序重新排序
- [ ] 测试边界情况

**验收标准**:
- [ ] ImportanceScoringCompression 实现完成
- [ ] 所有单元测试通过
- [ ] 评分算法正确
- [ ] 压缩逻辑正确

---

### 2.3 阶段 3: 性能测试（0.5天）

#### 步骤 3.1: 创建性能测试
- [ ] 创建 `backend/core/context/compression/tests/test_performance.py`
- [ ] 测试不同压缩策略的性能：
  - TimeWindowCompression
  - TokenLimitCompression
  - ImportanceScoringCompression
- [ ] 测试不同数据量下的性能（100, 1000, 10000 条消息）

#### 步骤 3.2: 压缩效果测试
- [ ] 测试压缩后的消息数量
- [ ] 测试压缩后的 token 数量
- [ ] 测试重要消息是否被保留

**验收标准**:
- [ ] 性能测试完成
- [ ] 压缩效果测试完成
- [ ] 测试结果记录在文档中

---

## 三、技术细节

### 3.1 Token 计算

**默认方法**: `1 token ≈ 4 字符`

**自定义 tokenizer**: 支持传入自定义函数

```python
def custom_tokenizer(text: str) -> int:
    # 使用 tiktoken 或其他库
    return len(encoding.encode(text))
```

### 3.2 重要性评分

**评分规则**:
- 系统消息：+10.0（最高优先级）
- 最近 5 条消息：+5.0（时间相关性）
- 包含关键词：+2.0（内容重要性）
- 用户消息：+1.0（用户输入优先）

**关键词列表**: ["错误", "问题", "重要", "关键", "失败", "异常"]

---

## 四、测试要求

### 4.1 单元测试

- [ ] TokenLimitCompression 测试
- [ ] ImportanceScoringCompression 测试
- [ ] 边界情况测试

### 4.2 性能测试

- [ ] 压缩性能对比
- [ ] 压缩效果对比

### 4.3 测试覆盖率

**目标**: > 80%

---

## 五、验收标准

- [ ] TokenLimitCompression 实现完成
- [ ] ImportanceScoringCompression 实现完成
- [ ] 所有单元测试通过
- [ ] 性能测试完成
- [ ] 测试覆盖率 > 80%
- [ ] 文档完整

---

## 六、注意事项

### 6.1 Token 计算准确性

- ⚠️ 默认方法（1 token ≈ 4 字符）是估算，不精确
- ⚠️ 如果需要精确计算，可以使用 tiktoken 库（需要额外依赖）
- ⚠️ 当前阶段使用估算方法即可

### 6.2 重要性评分

- ⚠️ 关键词列表可以根据实际使用情况调整
- ⚠️ 评分权重可以根据实际效果调整

### 6.3 性能考虑

- ⚠️ ImportanceScoringCompression 需要计算所有消息的分数，可能较慢
- ⚠️ 如果消息数量很大，考虑优化（后续阶段）

---

## 七、后续任务

完成本任务后，可以继续：

- [ ] TODO: 检索功能和语义搜索（阶段 5，P1）
- [ ] TODO: 扩展功能（阶段 6，P3）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0  
**状态**: ⏳ 待开始

