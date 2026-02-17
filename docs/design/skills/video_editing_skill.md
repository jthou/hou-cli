# 视频编辑技能设计文档

## 文档信息

- **版本**: 1.0.0
- **创建日期**: 2026-01-12
- **状态**: 设计阶段
- **优先级**: P1

## 概述

### 背景

基于 FFmpeg 工具，构建完整的视频编辑技能，支持视频剪辑、合并、转场、字幕添加等常见视频编辑操作。该技能将多个 FFmpeg 操作组合成面向任务的视频编辑能力。

### 设计目标

1. **任务导向**：用户只需描述编辑需求，无需了解 FFmpeg 技术细节
2. **功能完整**：覆盖常见视频编辑场景（剪辑、合并、转场、字幕等）
3. **易于扩展**：支持自定义编辑操作和复杂工作流
4. **错误处理**：完善的错误处理和降级策略

### 核心价值

- **简化操作**：用户说"帮我剪辑这个视频的 5-10 分钟片段"，而非"使用 ffmpeg cut 操作"
- **工作流自动化**：复杂的多步骤编辑操作自动执行
- **结果一致性**：统一的输出格式和错误处理

---

## 功能范围

### 1. 视频剪辑（Video Cutting）

**功能描述**：从视频中提取指定时间段的内容

**支持的操作**：
- 单片段剪辑：提取一个时间段
- 多片段剪辑：提取多个时间段并合并
- 智能剪辑：基于字幕时间戳自动剪辑

**使用场景**：
- "帮我提取视频的 5-10 分钟"
- "提取视频中所有提到 'Python' 的片段"
- "根据字幕文件自动剪辑关键片段"

### 2. 视频合并（Video Merging）

**功能描述**：将多个视频文件合并成一个

**支持的操作**：
- 顺序合并：按顺序拼接多个视频
- 并行合并：画中画效果（需要复杂 FFmpeg 命令）
- 带转场合并：合并时添加转场效果

**使用场景**：
- "把这些视频按顺序合并"
- "合并视频并添加淡入淡出效果"

### 3. 转场效果（Transitions）

**功能描述**：在视频片段之间添加转场效果

**支持的效果**：
- 淡入淡出（fade）
- 交叉溶解（crossfade）
- 滑动（slide）
- 缩放（zoom）
- 旋转（rotate）

**使用场景**：
- "在视频片段之间添加淡入淡出效果"
- "使用交叉溶解连接两个视频"

### 4. 字幕添加（Subtitle Overlay）

**功能描述**：在视频上叠加字幕

**支持的操作**：
- SRT 字幕叠加：将 SRT 字幕文件叠加到视频
- 硬字幕：字幕嵌入视频流（不可关闭）
- 软字幕：字幕作为独立轨道（可关闭）
- 字幕样式：字体、大小、颜色、位置等

**使用场景**：
- "给视频添加字幕文件"
- "在视频底部添加白色字幕，字体大小 24"

### 5. 视频编辑（Video Editing）

**功能描述**：综合编辑操作，包含多个步骤

**支持的操作**：
- 剪辑 + 合并
- 剪辑 + 转场 + 合并
- 剪辑 + 字幕 + 合并
- 完整编辑流程：剪辑 → 转场 → 字幕 → 合并

**使用场景**：
- "帮我剪辑视频的关键片段，添加转场和字幕，然后合并"
- "根据摘要中的时间戳自动剪辑视频并生成最终版本"

---

## 技能定义

### 技能名称

- **主技能**：`video_editing`
- **子技能**：
  - `video_cut` - 视频剪辑
  - `video_merge` - 视频合并
  - `video_transition` - 转场效果
  - `video_subtitle_overlay` - 字幕叠加
  - `video_edit_complete` - 完整编辑流程

### 工具依赖

**必需工具**：
- `ffmpeg` - 视频处理核心工具

**可选工具**：
- `whisper` - 用于生成字幕（如果用户需要自动生成字幕）
- `code_executor` - 用于复杂的时间戳解析和逻辑处理

---

## 详细设计

### 1. 视频剪辑技能（video_cut）

#### 1.1 参数定义

```yaml
parameters:
  - name: input_file
    type: string
    description: 输入视频文件路径
    required: true
  - name: output_file
    type: string
    description: 输出视频文件路径
    required: true
  - name: segments
    type: array
    description: 要提取的时间段列表
    required: true
    items:
      type: object
      properties:
        start_time: string  # 格式：HH:MM:SS 或 秒数
        end_time: string   # 格式：HH:MM:SS 或 秒数
        duration: string    # 可选，时长（如果提供 end_time 则不需要）
  - name: merge_segments
    type: boolean
    description: 是否将多个片段合并成一个视频（默认：true）
    required: false
    default: true
  - name: video_codec
    type: string
    description: 视频编码器（默认：copy，快速但不精确）
    required: false
    default: copy
    enum: [copy, libx264, libx265]
  - name: audio_codec
    type: string
    description: 音频编码器（默认：copy）
    required: false
    default: copy
    enum: [copy, aac, mp3]
```

#### 1.2 工作流

```yaml
workflow:
  steps:
    # 步骤 1: 分析输入视频
    - name: probe_video
      tool: ffmpeg
      operation: probe
      inputs:
        input_file: ${input.input_file}
      outputs:
        video_info: ${result.data}
        duration: ${result.data.format.duration}
    
    # 步骤 2: 验证时间段
    - name: validate_segments
      tool: code_executor
      inputs:
        code: |
          def parse_time(time_str):
              """解析时间字符串为秒数"""
              if ':' in time_str:
                  parts = time_str.split(':')
                  if len(parts) == 3:
                      h, m, s = map(float, parts)
                      return h * 3600 + m * 60 + s
                  elif len(parts) == 2:
                      m, s = map(float, parts)
                      return m * 60 + s
              else:
                  return float(time_str)
          
          video_duration = float("${steps[0].duration}")
          segments = ${input.segments}
          
          validated_segments = []
          for seg in segments:
              start = parse_time(seg['start_time'])
              if 'end_time' in seg:
                  end = parse_time(seg['end_time'])
              elif 'duration' in seg:
                  end = start + parse_time(seg['duration'])
              else:
                  raise ValueError("必须提供 end_time 或 duration")
              
              # 验证时间段
              if start < 0:
                  start = 0
              if end > video_duration:
                  end = video_duration
              if start >= end:
                  continue  # 跳过无效片段
              
              validated_segments.append({
                  'start_time': start,
                  'end_time': end,
                  'duration': end - start,
                  'start_time_str': f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{start%60:06.3f}",
                  'end_time_str': f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{end%60:06.3f}"
              })
          
          print(f"VALIDATED_SEGMENTS: {len(validated_segments)}")
          for i, seg in enumerate(validated_segments):
              print(f"SEGMENT_{i}: {seg['start_time_str']} -> {seg['end_time_str']} ({seg['duration']:.3f}s)")
      outputs:
        validated_segments: ${result.stdout}
    
    # 步骤 3: 剪辑各个片段
    - name: cut_segments
      type: loop
      loop_over: ${steps[1].validated_segments}
      loop_item: segment
      tool: ffmpeg
      operation: cut
      inputs:
        input_file: ${input.input_file}
        output_file: ${temp_dir}/segment_${loop_index}.mp4
        start_time: ${segment.start_time_str}
        duration: ${segment.duration}
        video_codec: ${input.video_codec | default('copy')}
        audio_codec: ${input.audio_codec | default('copy')}
      outputs:
        segment_files: ${result.output_file}
    
    # 步骤 4: 合并片段（如果需要）
    - name: merge_segments
      type: conditional
      condition: ${input.merge_segments | default(true) and len(${steps[1].validated_segments}) > 1}
      tool: ffmpeg
      operation: merge
      inputs:
        input_files: ${steps[2].segment_files}
        output_file: ${input.output_file}
      outputs:
        final_video: ${result.output_file}
      else:
        # 如果只有一个片段，直接重命名
        tool: code_executor
        inputs:
          code: |
            import shutil
            from pathlib import Path
            
            segment_file = Path("${steps[2].segment_files[0]}")
            output_file = Path("${input.output_file}")
            shutil.move(str(segment_file), str(output_file))
            print(f"OUTPUT_FILE: {output_file}")
        outputs:
          final_video: ${result.stdout}
```

#### 1.3 使用示例

```python
# 用户输入："帮我提取视频的 5-10 分钟和 20-25 分钟，然后合并"
skill.execute(
    input_file="/path/to/video.mp4",
    output_file="/path/to/output.mp4",
    segments=[
        {"start_time": "00:05:00", "end_time": "00:10:00"},
        {"start_time": "00:20:00", "end_time": "00:25:00"}
    ],
    merge_segments=True
)
```

### 2. 视频合并技能（video_merge）

#### 2.1 参数定义

```yaml
parameters:
  - name: input_files
    type: array
    description: 要合并的视频文件列表
    required: true
  - name: output_file
    type: string
    description: 输出视频文件路径
    required: true
  - name: transition_type
    type: string
    description: 转场类型（none/fade/crossfade，默认：none）
    required: false
    default: none
    enum: [none, fade, crossfade, slide, zoom]
  - name: transition_duration
    type: number
    description: 转场持续时间（秒，默认：1.0）
    required: false
    default: 1.0
  - name: video_codec
    type: string
    description: 视频编码器（默认：libx264，合并需要重新编码）
    required: false
    default: libx264
  - name: audio_codec
    type: string
    description: 音频编码器（默认：aac）
    required: false
    default: aac
```

#### 2.2 工作流

```yaml
workflow:
  steps:
    # 步骤 1: 检查输入文件
    - name: check_input_files
      tool: code_executor
      inputs:
        code: |
          from pathlib import Path
          
          input_files = ${input.input_files}
          missing_files = []
          valid_files = []
          
          for file_path in input_files:
              path = Path(file_path)
              if not path.exists():
                  missing_files.append(file_path)
              else:
                  valid_files.append(str(path.absolute()))
          
          if missing_files:
              raise FileNotFoundError(f"文件不存在: {missing_files}")
          
          print(f"VALID_FILES: {len(valid_files)}")
          for f in valid_files:
              print(f"FILE: {f}")
      outputs:
        valid_files: ${result.stdout}
    
    # 步骤 2: 分析所有视频（获取分辨率、帧率等）
    - name: probe_all_videos
      type: loop
      loop_over: ${steps[0].valid_files}
      loop_item: video_file
      tool: ffmpeg
      operation: probe
      inputs:
        input_file: ${video_file}
      outputs:
        video_infos: ${result.data}
    
    # 步骤 3: 统一视频参数（如果需要）
    - name: normalize_videos
      type: conditional
      condition: ${input.transition_type != 'none'}
      # 如果使用转场，需要统一分辨率、帧率等
      tool: code_executor
      inputs:
        code: |
          # 分析所有视频的参数，确定统一的目标参数
          video_infos = ${steps[1].video_infos}
          # ... 统一参数逻辑 ...
      outputs:
        target_params: ${result.stdout}
    
    # 步骤 4: 应用转场效果（如果需要）
    - name: apply_transitions
      type: conditional
      condition: ${input.transition_type != 'none'}
      tool: ffmpeg
      operation: custom
      inputs:
        custom_args: |
          # 根据转场类型生成 FFmpeg 复杂滤镜命令
          # 例如：fade 转场使用 xfade 滤镜
          # ... 转场命令生成逻辑 ...
      outputs:
        transitioned_files: ${result.output_file}
    
    # 步骤 5: 合并视频
    - name: merge_videos
      tool: ffmpeg
      operation: merge
      inputs:
        input_files: ${steps[3].transitioned_files | default(${steps[0].valid_files})}
        output_file: ${input.output_file}
        video_codec: ${input.video_codec}
        audio_codec: ${input.audio_codec}
      outputs:
        merged_video: ${result.output_file}
```

### 3. 转场效果技能（video_transition）

#### 3.1 转场类型实现

**淡入淡出（Fade）**：
```bash
# 使用 xfade 滤镜
ffmpeg -i video1.mp4 -i video2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=10[v]" \
  -map "[v]" output.mp4
```

**交叉溶解（Crossfade）**：
```bash
# 使用 xfade 滤镜的 fade 模式
ffmpeg -i video1.mp4 -i video2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=10[v]" \
  -map "[v]" output.mp4
```

**滑动（Slide）**：
```bash
# 使用 xfade 滤镜的 slideleft/slideright 模式
ffmpeg -i video1.mp4 -i video2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=slideleft:duration=1:offset=10[v]" \
  -map "[v]" output.mp4
```

### 4. 字幕叠加技能（video_subtitle_overlay）

#### 4.1 参数定义

```yaml
parameters:
  - name: input_file
    type: string
    description: 输入视频文件路径
    required: true
  - name: output_file
    type: string
    description: 输出视频文件路径
    required: true
  - name: subtitle_file
    type: string
    description: SRT 字幕文件路径
    required: true
  - name: subtitle_style
    type: object
    description: 字幕样式配置
    required: false
    properties:
      font_name: string      # 字体名称（默认：Arial）
      font_size: integer     # 字体大小（默认：24）
      font_color: string     # 字体颜色（默认：white）
      background_color: string  # 背景颜色（默认：black）
      position: string       # 位置（bottom/top，默认：bottom）
      margin_v: integer      # 垂直边距（默认：20）
  - name: hard_subtitle
    type: boolean
    description: 是否硬字幕（嵌入视频流，默认：true）
    required: false
    default: true
```

#### 4.2 工作流

```yaml
workflow:
  steps:
    # 步骤 1: 验证字幕文件
    - name: validate_subtitle
      tool: code_executor
      inputs:
        code: |
          from pathlib import Path
          
          subtitle_file = Path("${input.subtitle_file}")
          if not subtitle_file.exists():
              raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")
          
          # 验证 SRT 格式
          with open(subtitle_file, 'r', encoding='utf-8') as f:
              content = f.read()
          
          # 简单的格式检查
          if '-->' not in content:
              raise ValueError("字幕文件格式不正确（不是 SRT 格式）")
          
          print(f"SUBTITLE_FILE: {subtitle_file}")
      outputs:
        subtitle_valid: ${result.stdout}
    
    # 步骤 2: 生成字幕样式配置
    - name: generate_subtitle_style
      tool: code_executor
      inputs:
        code: |
          style = ${input.subtitle_style | default({})}
          
          # 默认样式
          font_name = style.get('font_name', 'Arial')
          font_size = style.get('font_size', 24)
          font_color = style.get('font_color', 'white')
          bg_color = style.get('background_color', 'black')
          position = style.get('position', 'bottom')
          margin_v = style.get('margin_v', 20)
          
          # 生成 FFmpeg subtitles 滤镜参数
          subtitle_filter = f"subtitles='${input.subtitle_file}':force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H{font_color},BackColour=&H{bg_color},MarginV={margin_v}'"
          
          print(f"SUBTITLE_FILTER: {subtitle_filter}")
      outputs:
        subtitle_filter: ${result.stdout}
    
    # 步骤 3: 叠加字幕
    - name: overlay_subtitle
      tool: ffmpeg
      operation: custom
      inputs:
        custom_args: |
          -i "${input.input_file}" \
          -vf "${steps[1].subtitle_filter}" \
          -c:v libx264 \
          -c:a copy \
          -y "${input.output_file}"
      outputs:
        output_video: ${result.output_file}
```

### 5. 完整编辑流程技能（video_edit_complete）

#### 5.1 参数定义

```yaml
parameters:
  - name: input_file
    type: string
    description: 输入视频文件路径
    required: true
  - name: output_file
    type: string
    description: 输出视频文件路径
    required: true
  - name: edit_plan
    type: object
    description: 编辑计划
    required: true
    properties:
      segments: array        # 要剪辑的片段
      transitions: array      # 转场配置（可选）
      subtitle_file: string   # 字幕文件（可选）
      subtitle_style: object # 字幕样式（可选）
  - name: auto_generate_subtitle
    type: boolean
    description: 是否自动生成字幕（默认：false）
    required: false
    default: false
```

#### 5.2 工作流

```yaml
workflow:
  steps:
    # 步骤 1: 剪辑片段
    - name: cut_segments
      skill: video_cut
      inputs:
        input_file: ${input.input_file}
        output_file: ${temp_dir}/segments.mp4
        segments: ${input.edit_plan.segments}
        merge_segments: false  # 先不合并，需要添加转场
    
    # 步骤 2: 生成字幕（如果需要）
    - name: generate_subtitle
      type: conditional
      condition: ${input.auto_generate_subtitle and not ${input.edit_plan.subtitle_file}}
      tool: whisper
      inputs:
        audio_file: ${input.input_file}
        output_file: ${temp_dir}/subtitle.srt}
      outputs:
        subtitle_file: ${result.output_file}
    
    # 步骤 3: 应用转场（如果需要）
    - name: apply_transitions
      type: conditional
      condition: ${input.edit_plan.transitions}
      skill: video_transition
      inputs:
        input_files: ${steps[0].segment_files}
        transition_config: ${input.edit_plan.transitions}
      outputs:
        transitioned_files: ${result.output_files}
    
    # 步骤 4: 合并视频
    - name: merge_videos
      skill: video_merge
      inputs:
        input_files: ${steps[2].transitioned_files | default(${steps[0].segment_files})}
        output_file: ${temp_dir}/merged.mp4}
        transition_type: none  # 转场已在步骤 3 应用
      outputs:
        merged_video: ${result.output_file}
    
    # 步骤 5: 叠加字幕（如果需要）
    - name: overlay_subtitle
      type: conditional
      condition: ${input.edit_plan.subtitle_file or ${steps[1].subtitle_file}}
      skill: video_subtitle_overlay
      inputs:
        input_file: ${steps[3].merged_video}
        output_file: ${input.output_file}
        subtitle_file: ${input.edit_plan.subtitle_file | default(${steps[1].subtitle_file})}
        subtitle_style: ${input.edit_plan.subtitle_style}
      outputs:
        final_video: ${result.output_file}
      else:
        # 如果没有字幕，直接复制合并后的视频
        tool: code_executor
        inputs:
          code: |
            import shutil
            from pathlib import Path
            
            merged_file = Path("${steps[3].merged_video}")
            output_file = Path("${input.output_file}")
            shutil.copy(str(merged_file), str(output_file))
            print(f"OUTPUT_FILE: {output_file}")
        outputs:
          final_video: ${result.stdout}
```

---

## 智能剪辑功能

### 基于字幕的自动剪辑

**功能描述**：根据字幕文件中的关键词或时间戳自动剪辑视频

**使用场景**：
- "提取视频中所有提到 'Python' 的片段"
- "根据摘要中的时间戳自动剪辑视频"

**实现思路**：
1. 解析字幕文件，找到包含关键词的段落
2. 提取这些段落的时间戳
3. 调用 `video_cut` 技能剪辑这些时间段
4. 可选：合并剪辑后的片段

**工作流**：
```yaml
- name: smart_cut_by_keyword
  tool: code_executor
  inputs:
    code: |
      import re
      from pathlib import Path
      
      subtitle_file = Path("${input.subtitle_file}")
      keyword = "${input.keyword}"
      
      # 解析 SRT 文件
      with open(subtitle_file, 'r', encoding='utf-8') as f:
          content = f.read()
      
      # 找到包含关键词的段落
      pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)'
      matches = re.findall(pattern, content, re.DOTALL)
      
      segments = []
      for match in matches:
          index, timestamp, text = match
          if keyword.lower() in text.lower():
              start_time, end_time = timestamp.split(' --> ')
              segments.append({
                  'start_time': start_time.replace(',', '.'),
                  'end_time': end_time.replace(',', '.')
              })
      
      print(f"FOUND_SEGMENTS: {len(segments)}")
      for seg in segments:
          print(f"SEGMENT: {seg['start_time']} -> {seg['end_time']}")
  outputs:
    segments: ${result.stdout}
```

---

## 错误处理

### 错误类型和处理策略

1. **文件不存在**
   - 错误：输入视频文件或字幕文件不存在
   - 处理：立即失败，返回明确的错误信息

2. **时间段无效**
   - 错误：开始时间 >= 结束时间，或超出视频时长
   - 处理：自动修正或跳过无效片段，继续处理其他片段

3. **转场失败**
   - 错误：转场效果应用失败
   - 处理：降级为无转场合并，继续执行

4. **字幕叠加失败**
   - 错误：字幕文件格式错误或叠加失败
   - 处理：返回无字幕版本，提示用户检查字幕文件

5. **合并失败**
   - 错误：视频合并失败（编码器不支持、分辨率不匹配等）
   - 处理：尝试统一视频参数后重试，或返回部分结果

### 错误处理配置

```yaml
error_handling:
  global:
    on_error: partial
    return_intermediate: true
  steps:
    - step: validate_segments
      on_error: fail
      message: "时间段验证失败"
    - step: cut_segments
      on_error: skip
      continue_on_error: true
      message: "部分片段剪辑失败，继续处理其他片段"
    - step: merge_videos
      on_error: retry
      max_retries: 2
      retry_with_normalize: true
```

---

## 性能优化

### 1. 缓存策略

- **视频分析结果**：缓存 `ffprobe` 的分析结果（24 小时）
- **字幕解析结果**：缓存字幕文件解析结果（24 小时）
- **中间文件**：临时文件在任务完成后自动清理

### 2. 编码优化

- **快速模式**：使用 `copy` 编码器（不重新编码，速度快）
- **精确模式**：使用 `libx264` 编码器（重新编码，质量高）
- **智能选择**：根据操作类型自动选择编码模式

### 3. 并行处理

- **多片段剪辑**：可以并行剪辑多个片段（如果系统资源允许）
- **转场计算**：转场效果可以预先计算

---

## 使用示例

### 示例 1：简单剪辑

```
用户："帮我提取视频的 5-10 分钟"

执行：
video_cut.execute(
    input_file="video.mp4",
    output_file="output.mp4",
    segments=[{"start_time": "00:05:00", "end_time": "00:10:00"}]
)
```

### 示例 2：多片段剪辑并合并

```
用户："提取视频的 5-10 分钟和 20-25 分钟，然后合并"

执行：
video_cut.execute(
    input_file="video.mp4",
    output_file="output.mp4",
    segments=[
        {"start_time": "00:05:00", "end_time": "00:10:00"},
        {"start_time": "00:20:00", "end_time": "00:25:00"}
    ],
    merge_segments=True
)
```

### 示例 3：添加字幕

```
用户："给视频添加字幕文件"

执行：
video_subtitle_overlay.execute(
    input_file="video.mp4",
    output_file="output.mp4",
    subtitle_file="subtitle.srt",
    subtitle_style={
        "font_size": 24,
        "font_color": "white",
        "position": "bottom"
    }
)
```

### 示例 4：完整编辑流程

```
用户："根据摘要中的时间戳自动剪辑视频，添加转场和字幕，然后合并"

执行：
video_edit_complete.execute(
    input_file="video.mp4",
    output_file="output.mp4",
    edit_plan={
        "segments": [
            {"start_time": "00:05:30", "end_time": "00:08:15"},
            {"start_time": "00:12:00", "end_time": "00:15:30"}
        ],
        "transitions": [
            {"type": "fade", "duration": 1.0}
        ],
        "subtitle_file": "subtitle.srt"
    }
)
```

---

## 实现计划

### 阶段 1：基础功能（1-2 周）

- [ ] 实现 `video_cut` 技能
  - 单片段剪辑
  - 多片段剪辑
  - 时间段验证

- [ ] 实现 `video_merge` 技能
  - 顺序合并
  - 基础转场（淡入淡出）

### 阶段 2：高级功能（2-3 周）

- [ ] 实现 `video_transition` 技能
  - 多种转场效果
  - 转场参数配置

- [ ] 实现 `video_subtitle_overlay` 技能
  - SRT 字幕叠加
  - 字幕样式配置

### 阶段 3：智能功能（2-3 周）

- [ ] 实现智能剪辑
  - 基于关键词的自动剪辑
  - 基于时间戳的自动剪辑

- [ ] 实现 `video_edit_complete` 技能
  - 完整编辑流程
  - 工作流编排

### 阶段 4：优化和完善（1-2 周）

- [ ] 错误处理完善
- [ ] 性能优化
- [ ] 测试和文档

---

## 技术细节

### FFmpeg 命令生成

#### 剪辑命令

```bash
# 快速模式（copy 编码器）
ffmpeg -i input.mp4 -ss 00:05:00 -t 00:05:00 -c copy output.mp4

# 精确模式（重新编码）
ffmpeg -i input.mp4 -ss 00:05:00 -t 00:05:00 -c:v libx264 -c:a aac output.mp4
```

#### 合并命令

```bash
# 使用 concat demuxer（需要相同编码格式）
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4

# filelist.txt 内容：
# file 'segment1.mp4'
# file 'segment2.mp4'
```

#### 转场命令

```bash
# 淡入淡出转场
ffmpeg -i video1.mp4 -i video2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=10[v]" \
  -map "[v]" -c:v libx264 output.mp4
```

#### 字幕叠加命令

```bash
# 硬字幕
ffmpeg -i video.mp4 -vf "subtitles=subtitle.srt:force_style='FontSize=24'" \
  -c:v libx264 -c:a copy output.mp4
```

---

## 参考资源

- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [FFmpeg 滤镜文档](https://ffmpeg.org/ffmpeg-filters.html)
- [视频编辑技能架构设计](../agent-tool-skill-architecture.md)
- [FFmpeg 工具实现](../../../../backend/core/agent/tools/builtin/ffmpeg_tool.py)

---

## 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0.0 | 2026-01-12 | 初始版本，完整设计文档 | System Design Team |

---

**文档结束**








