# 视频摘要技能 - 时间戳提取和剪裁支持

## 概述

为了支持视频自动剪裁编辑，摘要生成过程中需要提取并保留原字幕文件的时间戳信息，建立摘要关键点与视频时间位置的映射关系。

## 设计目标

1. **时间戳保留**：摘要中的每个关键点都关联到原始视频的时间位置
2. **剪裁基础**：提供结构化的时间戳数据，便于后续视频剪裁
3. **精确定位**：支持精确到秒的时间戳定位
4. **多段支持**：支持一个关键点对应多个时间段

## 时间戳数据结构（纯文本格式，容错率高）

### 1. 字幕段落时间戳（纯文本格式）

```
=== SUBTITLE_DATA ===
SEGMENT_COUNT: 100
TOTAL_LENGTH: 5000

=== SEGMENTS ===
1|00:00:00,000 --> 00:00:05,400|这是第一段字幕内容
2|00:00:05,400 --> 00:00:10,800|这是第二段字幕内容
...

=== TIMESTAMP_INDEX ===
1|00:00:00,000|00:00:05,400|0.000|5.400|5.400|这是第一段字幕内容
2|00:00:05,400|00:00:10,800|5.400|10.800|5.400|这是第二段字幕内容
...
格式：索引|开始时间|结束时间|开始秒数|结束秒数|时长|文本预览
```

### 2. 摘要关键点时间戳映射（纯文本格式）

```
=== TIMESTAMP_MAPPING ===
TOTAL_KEY_POINTS: 3

=== KEY_POINTS ===
1|[00:05:30]|00:05:30|00:08:15|330.000|495.000|165.000|10,11,12|视频介绍了 Python 异步编程
2|[00:08:15]|00:08:15|00:12:00|495.000|720.000|225.000|13,14,15|包括 async/await 语法
3|[00:12:00]|00:12:00|00:15:00|720.000|900.000|180.000|18,19,20|实际应用案例

格式：序号|时间戳|开始时间|结束时间|开始秒数|结束秒数|时长|段落索引|关键点文本
```

### 3. 摘要文本（带时间戳标注）

```
视频介绍了 Python 异步编程 [00:05:30]，包括 async/await 语法 [00:08:15] 和实际应用 [00:12:00]。
每个关键点后都标注了对应的时间戳，格式为 [HH:MM:SS]。
```

## 实现方案

### 1. 时间戳提取（在读取字幕时）

```python
def parse_srt_with_timestamps(file_path: str) -> dict:
    """解析 SRT 文件，提取时间戳信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    segments = []
    timestamp_index = {}
    
    for match in matches:
        index, timestamp, text = match
        text = text.strip()
        
        # 解析时间戳
        start_time, end_time = timestamp.split(' --> ')
        start_seconds = timestamp_to_seconds(start_time)
        end_seconds = timestamp_to_seconds(end_time)
        
        segment = {
            'index': int(index),
            'timestamp': timestamp,
            'start_time': start_time,
            'end_time': end_time,
            'start_seconds': start_seconds,
            'end_seconds': end_seconds,
            'duration': end_seconds - start_seconds,
            'text': text
        }
        
        segments.append(segment)
        timestamp_index[int(index)] = segment
    
    return {
        'segments': segments,
        'full_text': ' '.join([s['text'] for s in segments]),
        'segment_count': len(segments),
        'timestamp_index': timestamp_index
    }

def timestamp_to_seconds(timestamp: str) -> float:
    """将时间戳转换为秒数"""
    h, m, s_ms = timestamp.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
```

### 2. 摘要生成时包含时间戳

#### 2.1 Prompt 设计

```python
prompt = f"""基于以下视频字幕内容，生成一个 {summary_length} 字的摘要。

要求：
1. 概括视频的核心内容
2. 突出关键观点
3. 语言简洁明了
4. **重要**：在摘要中为每个关键点标注对应的时间戳（格式：[HH:MM:SS]）
5. 时间戳应准确对应字幕中的时间位置

字幕内容（带时间戳）：
{format_segments_with_timestamps(segments)}

输出格式要求：
- 每个关键点后标注时间戳，例如："视频介绍了 Python 异步编程 [00:05:30]"
- 如果某个观点跨越多个时间段，标注主要时间段或时间范围
- 时间戳格式：[HH:MM:SS] 或 [MM:SS] 或 [HH:MM:SS-HH:MM:SS]
"""
```

#### 2.2 格式化字幕段落（带时间戳）

```python
def format_segments_with_timestamps(segments: list) -> str:
    """格式化字幕段落，包含时间戳信息"""
    formatted = []
    for seg in segments:
        # 简化时间戳格式（去掉毫秒）
        start_simple = seg['start_time'].split(',')[0]
        end_simple = seg['end_time'].split(',')[0]
        formatted.append(f"[{start_simple}-{end_simple}] {seg['text']}")
    return "\n".join(formatted)
```

### 3. 时间戳映射提取（从摘要中）

```python
def extract_timestamps_from_summary(summary: str, timestamp_index: dict) -> list:
    """从摘要文本中提取时间戳，并映射到原始字幕段落"""
    import re
    
    # 匹配时间戳格式：[HH:MM:SS] 或 [MM:SS] 或 [HH:MM:SS-HH:MM:SS]
    timestamp_pattern = r'\[(\d{1,2}):(\d{2}):(\d{2})(?:-(\d{1,2}):(\d{2}):(\d{2}))?\]'
    matches = re.finditer(timestamp_pattern, summary)
    
    key_points = []
    for match in matches:
        # 提取时间戳
        start_h, start_m, start_s = map(int, match.groups()[:3])
        start_seconds = start_h * 3600 + start_m * 60 + start_s
        
        # 查找对应的字幕段落
        matching_segments = find_segments_by_time(
            timestamp_index,
            start_seconds,
            end_seconds if match.groups()[3] else start_seconds + 30  # 默认 30 秒
        )
        
        # 提取关键点文本（时间戳前后的内容）
        point_text = extract_point_text(summary, match.start(), match.end())
        
        key_points.append({
            'point': point_text,
            'timestamp': match.group(),
            'start_seconds': start_seconds,
            'end_seconds': end_seconds if match.groups()[3] else start_seconds + 30,
            'segment_indices': [s['index'] for s in matching_segments],
            'confidence': calculate_confidence(point_text, matching_segments)
        })
    
    return key_points

def find_segments_by_time(timestamp_index: dict, start_seconds: float, end_seconds: float) -> list:
    """根据时间范围查找对应的字幕段落"""
    matching_segments = []
    for seg in timestamp_index.values():
        # 检查时间段是否重叠
        if not (seg['end_seconds'] < start_seconds or seg['start_seconds'] > end_seconds):
            matching_segments.append(seg)
    return matching_segments
```

### 4. 结构化摘要输出

```python
def generate_structured_summary(
    summary_text: str,
    timestamp_index: dict,
    subtitle_segments: list
) -> dict:
    """生成结构化的摘要，包含时间戳映射"""
    
    # 提取时间戳
    key_points = extract_timestamps_from_summary(summary_text, timestamp_index)
    
    return {
        'text': summary_text,
        'key_points': key_points,
        'timestamp_mapping': {
            point['point']: {
                'timestamp': point['timestamp'],
                'start_seconds': point['start_seconds'],
                'end_seconds': point['end_seconds'],
                'segments': point['segment_indices']
            }
            for point in key_points
        },
        'total_duration': max(seg['end_seconds'] for seg in subtitle_segments),
        'coverage': calculate_coverage(key_points, subtitle_segments)
    }
```

## 视频剪裁应用

### 1. 基于关键点剪裁

```python
def cut_video_by_key_points(
    video_path: str,
    summary_with_timestamps: dict,
    key_point_names: list
) -> list:
    """根据摘要关键点剪裁视频"""
    cuts = []
    for point_name in key_point_names:
        if point_name in summary_with_timestamps['timestamp_mapping']:
            mapping = summary_with_timestamps['timestamp_mapping'][point_name]
            cuts.append({
                'start': mapping['start_seconds'],
                'end': mapping['end_seconds'],
                'duration': mapping['end_seconds'] - mapping['start_seconds'],
                'description': point_name
            })
    return cuts
```

### 2. 生成剪裁脚本

```python
def generate_ffmpeg_cut_script(
    video_path: str,
    cuts: list,
    output_dir: str
) -> str:
    """生成 FFmpeg 剪裁脚本"""
    script = []
    for i, cut in enumerate(cuts, 1):
        output_file = f"{output_dir}/clip_{i:03d}_{cut['description']}.mp4"
        script.append(
            f"ffmpeg -i {video_path} "
            f"-ss {cut['start']} -t {cut['duration']} "
            f"-c copy {output_file}"
        )
    return "\n".join(script)
```

## 输出格式

### 1. 文本摘要（带时间戳）

```
视频内容摘要：

1. Python 异步编程介绍 [00:05:30]
   视频开始介绍 Python 异步编程的基本概念...

2. async/await 语法讲解 [00:08:15]
   详细讲解了 async/await 语法的使用方法...

3. 实际应用案例 [00:12:00]
   通过实际案例演示异步编程的应用场景...
```

### 2. 结构化摘要（纯文本格式，容错率高）

```
=== TIMESTAMP_MAPPING ===
TOTAL_KEY_POINTS: 3

=== KEY_POINTS ===
1|[00:05:30]|00:05:30|00:08:15|330.000|495.000|165.000|10,11,12|视频介绍了 Python 异步编程
2|[00:08:15]|00:08:15|00:12:00|495.000|720.000|225.000|13,14,15|包括 async/await 语法
3|[00:12:00]|00:12:00|00:15:00|720.000|900.000|180.000|18,19,20|实际应用案例

格式说明：
序号|时间戳|开始时间|结束时间|开始秒数|结束秒数|时长|段落索引|关键点文本
```

## 使用场景

### 场景 1：生成带时间戳的摘要

```
用户："帮我分析这个视频并生成摘要"
系统：生成摘要，每个关键点都标注时间戳
输出：
  - 文本摘要（带时间戳）
  - 结构化摘要（JSON，包含时间戳映射）
```

### 场景 2：基于摘要剪裁视频

```
用户："帮我剪出视频中关于技术细节的部分"
系统：
  1. 查找摘要中"技术细节"相关关键点
  2. 提取对应的时间戳
  3. 使用 FFmpeg 剪裁视频片段
  4. 输出剪裁后的视频文件
```

### 场景 3：生成视频高亮片段

```
用户："生成视频的高亮片段集合"
系统：
  1. 从摘要中提取所有关键点
  2. 根据时间戳剪裁每个关键点对应的视频片段
  3. 合并成高亮片段集合
```

## 配置参数

```yaml
timestamp_extraction:
  enabled: true  # 是否提取时间戳
  format: "simple"  # 时间戳格式：simple (HH:MM:SS) 或 detailed (HH:MM:SS.mmm)
  include_segments: true  # 是否包含关联的字幕段落索引
  generate_mapping: true  # 是否生成时间戳映射
  output_format: "text"  # 输出格式：text (纯文本，容错率高，推荐)
```

**为什么使用纯文本格式而不是 JSON？**

1. **容错率高**：纯文本格式即使部分数据损坏，其他部分仍可解析
2. **易于调试**：可以直接查看和编辑，无需 JSON 解析器
3. **兼容性好**：不依赖 JSON 库，减少解析错误
4. **可读性强**：人类可读，便于检查和验证
5. **灵活性**：可以轻松添加新字段，无需修改结构

## 优势

1. **精确定位**：每个关键点都能精确定位到视频时间位置
2. **剪裁基础**：提供完整的时间戳数据，便于视频剪裁
3. **灵活应用**：支持多种剪裁场景（单点、多点、范围）
4. **可追溯性**：摘要内容可以追溯到原始字幕段落
5. **自动化**：为视频自动剪裁编辑提供数据基础

