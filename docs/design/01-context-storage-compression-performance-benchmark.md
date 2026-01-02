# 压缩策略性能基准

## 概述

本文档记录上下文压缩策略的性能基准数据，用于性能回归测试和优化参考。

**创建时间**: 2025-01-02  
**测试环境**: macOS, Python 3.12.2  
**测试工具**: pytest

---

## 一、性能基准数据

### 1.1 执行时间（秒）

| 压缩策略 | 100 条消息 | 1000 条消息 | 10000 条消息 |
|---------|-----------|------------|-------------|
| **TimeWindowCompression** | < 0.0001s | < 0.0001s | < 0.0001s |
| **TokenLimitCompression** | 0.0001s | 0.0008s | 0.0072s |
| **ImportanceScoringCompression** | 0.0004s | 0.0035s | 0.0352s |

### 1.2 性能分析

**TimeWindowCompression**:
- ✅ **最快**: 简单的时间窗口截断，O(1) 复杂度
- ✅ **适用场景**: 只需要保留最近消息的场景

**TokenLimitCompression**:
- ✅ **较快**: 需要计算 token 数，O(n) 复杂度
- ✅ **适用场景**: 需要控制 token 数量的场景

**ImportanceScoringCompression**:
- ⚠️ **较慢**: 需要计算每条消息的重要性分数，O(n²) 复杂度
- ✅ **适用场景**: 需要保留重要消息的场景

### 1.3 性能回归阈值

**性能回归测试阈值**（不应超过以下值）：

| 压缩策略 | 100 条消息 | 1000 条消息 | 10000 条消息 |
|---------|-----------|------------|-------------|
| **TimeWindowCompression** | 0.001s | 0.001s | 0.001s |
| **TokenLimitCompression** | 0.01s | 0.01s | 0.1s |
| **ImportanceScoringCompression** | 0.01s | 0.05s | 0.5s |

---

## 二、压缩效果基准

### 2.1 压缩率

**测试场景**: 100 条消息，每条约 25 tokens

| 压缩策略 | 限制条件 | 压缩后消息数 | 压缩率 |
|---------|---------|-------------|--------|
| **TimeWindowCompression** | max_messages=10 | 10 | 90% |
| **TokenLimitCompression** | max_tokens=250 | 9 | 91% |
| **ImportanceScoringCompression** | max_messages=10 | 10 | 90% |

### 2.2 重要消息保留率

**测试场景**: 100 条消息，其中 10 条包含关键词（"问题"）

| 压缩策略 | 限制条件 | 重要消息保留率 |
|---------|---------|---------------|
| **TimeWindowCompression** | max_messages=20 | ~20% (按时间顺序) |
| **TokenLimitCompression** | max_tokens=500 | ~20% (按时间顺序) |
| **ImportanceScoringCompression** | max_messages=20 | **100%** (按重要性) |

**结论**: ImportanceScoringCompression 在保留重要消息方面表现最佳。

---

## 三、使用建议

### 3.1 策略选择

**选择 TimeWindowCompression 当**:
- 只需要保留最近的消息
- 性能要求极高
- 消息重要性差异不大

**选择 TokenLimitCompression 当**:
- 需要精确控制 token 数量
- 系统消息需要优先保留
- 性能要求较高

**选择 ImportanceScoringCompression 当**:
- 需要保留重要消息（包含关键词、系统消息等）
- 消息重要性差异较大
- 可以接受稍慢的性能

### 3.2 性能优化建议

1. **ImportanceScoringCompression 优化**:
   - 如果消息数量很大（> 10000），考虑先使用 TimeWindowCompression 预过滤
   - 可以缓存重要性分数，避免重复计算

2. **TokenLimitCompression 优化**:
   - 如果使用精确的 tokenizer（如 tiktoken），考虑缓存 token 计算结果

3. **混合策略**:
   - 可以先使用 ImportanceScoringCompression 选择重要消息
   - 然后使用 TokenLimitCompression 控制 token 数量

---

## 四、性能回归测试

性能回归测试已集成到 `backend/core/context/compression/tests/test_performance.py`。

**运行性能测试**:
```bash
pytest backend/core/context/compression/tests/test_performance.py -v -s
```

**测试内容**:
- ✅ 不同数据量下的执行时间
- ✅ 压缩效果验证
- ✅ 重要消息保留验证
- ✅ 压缩质量验证

---

## 五、更新记录

| 日期 | 版本 | 变更说明 |
|------|------|---------|
| 2025-01-02 | 1.0 | 初始性能基准数据 |

---

**创建时间**: 2025-01-02  
**版本**: 1.0  
**状态**: 基准数据已记录

