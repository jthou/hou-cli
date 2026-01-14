# 长文本处理策略

## 概述

当视频字幕文件超过 LLM 上下文窗口时，需要采用分块处理策略。本文档详细说明长文本处理的实现方案。

## 问题描述

### 挑战

1. **上下文窗口限制**
   - 大多数 LLM 的上下文窗口有限（如 32K tokens）
   - 长视频字幕可能超过这个限制

2. **语义完整性**
   - 简单的文本分块可能破坏语义完整性
   - 需要保持段落和句子的完整性

3. **处理效率**
   - 分块处理会增加 LLM 调用次数
   - 需要平衡质量和效率

## 解决方案

### 1. 自动检测

```python
def check_text_length(text: str, max_length: int = 80000) -> bool:
    """检查文本是否需要分块"""
    return len(text) > max_length
```

### 2. 智能分块

**策略**：按字幕段落分块，保持语义完整性

```python
def chunk_text_by_segments(segments: list, max_tokens_per_chunk: int) -> list:
    """按段落分块文本，确保每个块不超过 max_tokens"""
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for segment in segments:
        segment_tokens = estimate_tokens(segment['text'])
        
        # 如果当前块加上新段落会超过限制，开始新块
        if current_tokens + segment_tokens > max_tokens_per_chunk and current_chunk:
            chunks.append({
                'segments': current_chunk,
                'text': ' '.join([s['text'] for s in current_chunk]),
                'start_timestamp': current_chunk[0]['timestamp'],
                'end_timestamp': current_chunk[-1]['timestamp']
            })
            current_chunk = []
            current_tokens = 0
        
        current_chunk.append(segment)
        current_tokens += segment_tokens
    
    # 添加最后一个块
    if current_chunk:
        chunks.append({
            'segments': current_chunk,
            'text': ' '.join([s['text'] for s in current_chunk]),
            'start_timestamp': current_chunk[0]['timestamp'],
            'end_timestamp': current_chunk[-1]['timestamp']
        })
    
    return chunks
```

### 3. 层次化处理

**摘要生成**：
```
长文本（> 80K 字符）
  ↓
分块（按段落，每块 ≤ 15K tokens）
  ↓
每块独立生成摘要片段
  ↓
合并所有摘要片段 → 最终摘要
```

**文章生成**：
```
最终摘要 + 分块内容
  ↓
每块基于摘要和片段内容生成文章片段
  ↓
合并所有文章片段 → 最终文章
```

## 配置参数

```yaml
long_text_handling:
  max_text_length: 80000        # 文本长度阈值（字符）
  max_tokens_per_chunk: 15000   # 每个分块的最大 token 数
  llm_context_window: 32000     # LLM 上下文窗口大小
  llm_output_tokens: 2000       # 预留给 LLM 输出的 token 数
  llm_prompt_tokens: 1000       # 预留给 LLM prompt 的 token 数
```

## Token 估算

```python
def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量（1 token ≈ 4 字符）"""
    return len(text) // 4
```

## 错误处理

1. **分块处理失败**：跳过该分块，继续处理其他分块
2. **合并失败**：返回分块结果的简单拼接作为降级方案
3. **部分结果返回**：即使部分分块失败，也返回已成功处理的部分

## 性能优化

1. **缓存机制**：缓存已处理的分块结果
2. **并行处理**：未来可以并行处理多个分块（需要 LLM 支持）

## 使用示例

```python
# 检查是否需要分块
if len(subtitle_text) > max_text_length:
    # 分块处理
    chunks = chunk_text_by_segments(segments, max_tokens_per_chunk)
    
    # 每块生成摘要
    chunk_summaries = []
    for chunk in chunks:
        summary = await generate_chunk_summary(chunk)
        chunk_summaries.append(summary)
    
    # 合并摘要
    final_summary = await merge_summaries(chunk_summaries)
else:
    # 直接生成摘要
    final_summary = await generate_summary(subtitle_text)
```




