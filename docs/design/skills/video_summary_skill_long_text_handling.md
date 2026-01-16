# 视频摘要技能 - 长文本处理策略

## 问题描述

当视频时长较长时，生成的字幕文件可能包含大量文本（数万到数十万字符），超过 LLM 的上下文窗口限制（如 DeepSeek 的 32K tokens），导致无法一次性处理。

## 解决方案

采用**分块处理 + 层次化摘要**策略，自动处理超长文本。

## 处理流程

### 1. 文本长度检测

```python
def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量（1 token ≈ 4 字符）"""
    return len(text) // 4

max_text_length = 80000  # 80K 字符 ≈ 20K tokens
estimated_tokens = estimate_tokens(subtitle_text)

if estimated_tokens > max_text_length:
    # 需要分块处理
    needs_chunking = True
else:
    # 可以直接处理
    needs_chunking = False
```

### 2. 智能分块策略

#### 2.1 按段落分块（推荐）

**优势**：保持语义完整性，不会在句子中间截断

```python
def chunk_text_by_segments(segments: list, max_tokens_per_chunk: int) -> list:
    """按段落分块文本，确保每个块不超过 max_tokens"""
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for segment in segments:
        segment_text = segment['text']
        segment_tokens = estimate_tokens(segment_text)
        
        # 如果当前块加上新段落会超过限制，开始新块
        if current_tokens + segment_tokens > max_tokens_per_chunk and current_chunk:
            chunks.append({
                'segments': current_chunk,
                'text': ' '.join([s['text'] for s in current_chunk]),
                'start_index': current_chunk[0]['index'],
                'end_index': current_chunk[-1]['index'],
                'start_timestamp': current_chunk[0]['timestamp'].split(' --> ')[0],
                'end_timestamp': current_chunk[-1]['timestamp'].split(' --> ')[1]
            })
            current_chunk = []
            current_tokens = 0
        
        current_chunk.append(segment)
        current_tokens += segment_tokens
    
    # 添加最后一个块
    if current_chunk:
        chunks.append({...})
    
    return chunks
```

#### 2.2 分块大小计算

```python
# LLM 上下文窗口配置
llm_context_window = 32000  # DeepSeek 默认
llm_output_tokens = 2000    # 预留输出
llm_prompt_tokens = 1000    # 预留 prompt

# 实际可用输入 token
available_input_tokens = llm_context_window - llm_output_tokens - llm_prompt_tokens
# = 32000 - 2000 - 1000 = 29000 tokens

# 每个分块的最大 token 数（保守估计，留出余量）
max_tokens_per_chunk = 15000  # 约 60K 字符
```

### 3. 层次化摘要生成

#### 3.1 短文本（直接处理）

```
字幕文本（≤ 80K 字符）
    ↓
LLM 生成摘要
    ↓
最终摘要
```

#### 3.2 长文本（分块处理）

```
字幕文本（> 80K 字符）
    ↓
分块（N 个块，每块 ≤ 15K tokens）
    ↓
┌─────────────────────────────────┐
│ 块 1 → LLM → 摘要片段 1         │
│ 块 2 → LLM → 摘要片段 2         │
│ 块 3 → LLM → 摘要片段 3         │
│ ...                             │
│ 块 N → LLM → 摘要片段 N         │
└─────────────────────────────────┘
    ↓
合并所有摘要片段
    ↓
LLM 生成最终摘要
    ↓
最终摘要
```

### 4. 层次化文章生成

#### 4.1 短文本（直接处理）

```
最终摘要 + 完整字幕文本
    ↓
LLM 生成文章
    ↓
最终文章
```

#### 4.2 长文本（分块处理）

```
最终摘要 + 分块内容
    ↓
┌─────────────────────────────────┐
│ 摘要 + 块 1 → LLM → 文章片段 1   │
│ 摘要 + 块 2 → LLM → 文章片段 2   │
│ 摘要 + 块 3 → LLM → 文章片段 3   │
│ ...                             │
│ 摘要 + 块 N → LLM → 文章片段 N   │
└─────────────────────────────────┘
    ↓
合并所有文章片段
    ↓
LLM 生成最终文章
    ↓
最终文章
```

## 实现细节

### 1. 分块信息结构

```json
{
  "needs_chunking": true,
  "text_length": 150000,
  "estimated_tokens": 37500,
  "chunk_count": 3,
  "chunks": [
    {
      "segments": [...],
      "text": "块 1 的完整文本...",
      "start_index": 1,
      "end_index": 500,
      "start_timestamp": "00:00:00,000",
      "end_timestamp": "00:15:30,000"
    },
    {
      "segments": [...],
      "text": "块 2 的完整文本...",
      "start_index": 501,
      "end_index": 1000,
      "start_timestamp": "00:15:30,000",
      "end_timestamp": "00:30:00,000"
    },
    ...
  ]
}
```

### 2. 错误处理

#### 2.1 分块处理失败

```python
# 如果某个分块处理失败，跳过该分块
for chunk in chunks:
    try:
        chunk_summary = generate_summary_for_chunk(chunk)
        chunk_summaries.append(chunk_summary)
    except Exception as e:
        logger.warning(f"分块 {chunk['start_index']}-{chunk['end_index']} 处理失败: {e}")
        # 跳过该分块，继续处理其他分块
        continue
```

#### 2.2 合并失败

```python
try:
    final_summary = merge_chunk_summaries(chunk_summaries)
except Exception as e:
    logger.warning(f"合并摘要失败: {e}，使用简单拼接")
    # 降级方案：简单拼接所有分块摘要
    final_summary = "\n\n".join(chunk_summaries)
```

### 3. 性能优化

#### 3.1 缓存分块信息

```yaml
cache:
  keys:
    - steps[4].chunk_info  # 缓存分块信息，避免重复计算
  ttl: 86400  # 24 小时
```

#### 3.2 并行处理（未来优化）

```yaml
parallel:
  enabled: true  # 未来版本支持
  # 分块摘要和文章生成可以并行处理
  # 但合并步骤必须串行
```

## 配置参数

```yaml
long_text_handling:
  # 文本长度阈值（字符数）
  max_text_length: 80000  # 80K 字符 ≈ 20K tokens
  
  # 每个分块的最大 token 数
  max_tokens_per_chunk: 15000  # 15K tokens ≈ 60K 字符
  
  # 分块策略
  chunking_strategy: "by_segments"  # 按段落分块
  
  # LLM 上下文窗口配置
  llm_context_window: 32000  # DeepSeek 默认
  llm_output_tokens: 2000    # 预留输出
  llm_prompt_tokens: 1000    # 预留 prompt
```

## 使用示例

### 示例 1：短文本（无需分块）

```
输入：字幕文本 50K 字符（≈ 12.5K tokens）
处理：直接生成摘要和文章
输出：摘要 + 文章
```

### 示例 2：长文本（需要分块）

```
输入：字幕文本 150K 字符（≈ 37.5K tokens）
检测：超过阈值（80K 字符），需要分块
分块：分为 3 个块（每块约 12.5K tokens）
处理：
  1. 每块生成摘要片段
  2. 合并摘要片段 → 最终摘要
  3. 每块基于摘要生成文章片段
  4. 合并文章片段 → 最终文章
输出：摘要 + 文章
```

## 优势

1. **自动处理**：无需用户干预，自动检测并分块
2. **语义完整**：按段落分块，保持语义完整性
3. **层次化处理**：先分块摘要，再整体合并，保证质量
4. **容错性强**：单个分块失败不影响整体处理
5. **可配置**：支持根据不同的 LLM 模型调整参数
6. **性能优化**：支持缓存和未来并行处理

## 注意事项

1. **Token 估算**：使用简单的 1 token ≈ 4 字符估算，实际可能略有偏差
2. **分块边界**：按段落分块可能造成块大小不均匀
3. **合并质量**：分块处理后再合并，质量可能略低于直接处理
4. **处理时间**：分块处理需要多次 LLM 调用，耗时更长
5. **成本考虑**：多次 LLM 调用会增加 API 成本

## 未来优化

1. **精确 Token 计算**：使用实际的 tokenizer 计算 token 数量
2. **分块重叠**：在分块边界添加重叠，保持上下文连贯性
3. **并行处理**：分块摘要和文章生成可以并行处理
4. **自适应分块**：根据内容语义自动调整分块大小
5. **增量处理**：支持增量生成，实时显示进度



