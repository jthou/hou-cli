# Whisper 工具未调用问题分析

## 问题描述

测试任务："下载视频 https://www.bilibili.com/video/BV1dtroBREij 并拆分出音频，并用whisper转出字幕文件"

测试结果显示：
- ✅ 步骤 '下载视频' 已执行
- ✅ 步骤 '提取音频' 已执行  
- ❌ 步骤 '生成字幕' 未找到

实际工具调用：只调用了 `video_downloader`（2次），没有调用 `whisper` 工具。

## 可能的原因分析

### 1. 工具描述问题

**当前 Whisper 工具描述**：
```
"语音转文字工具，使用 OpenAI Whisper 模型进行高精度语音识别。
支持多种音频格式（mp3, wav, m4a, flac 等），
提供精确的段落级别时间戳（精确到 0.01 秒），
支持多语言识别和自动语言检测。"
```

**问题**：
- ❌ 描述中没有明确提到"字幕"、"字幕文件"、"subtitle"等关键词
- ❌ 虽然参数中有 `output_format` 可以输出 srt 格式，但描述中没有强调这一点
- ❌ 推理模型可能无法将"用whisper转出字幕文件"与"语音转文字工具"关联起来

**建议改进**：
- ✅ 在描述中明确提到"生成字幕文件"、"支持SRT字幕格式"
- ✅ 添加关键词："字幕"、"subtitle"、"字幕文件"、"srt"

### 2. 任务完成判断逻辑问题

**当前判断逻辑**（`autonomous_executor.py:307-310`）：
```python
finished = (
    not tool_calls or
    ("完成" in response_str or "任务完成" in response_str)
)
```

**问题**：
- ❌ `not tool_calls` 意味着如果没有工具调用就认为完成，这可能不对
- ❌ 推理模型可能在响应中说了"完成"，但实际上任务还没完成
- ❌ 没有检查是否所有计划步骤都已完成

**从测试日志看**：
- 第2轮推理模型的 `reasoning_content` 说："看起来视频下载已经开始了，但还没有完成。让我检查一下工具的输出..."
- 但最终判断为 `finished: True`，说明推理模型可能过早判断完成

### 3. 系统提示不够明确

**当前系统提示**（`autonomous_executor.py:349-365`）：
```
"你是一个智能任务执行助手。你的任务是自主使用工具完成用户的任务。

原始任务：{task}

执行计划：
{plan.get('plan', '')}

请按照计划逐步执行任务：
1. 分析当前步骤需要做什么
2. 选择合适的工具
3. 执行工具并获取结果
4. 根据结果决定下一步行动
5. 重复直到任务完成

当任务完成时，请明确说明"任务完成"。"
```

**问题**：
- ❌ 没有强调必须完成所有步骤
- ❌ 没有明确说明如何判断任务完成
- ❌ 没有提醒推理模型检查是否所有计划步骤都已完成

## 解决方案

### 方案1：改进 Whisper 工具描述（推荐）

```python
description=(
    "语音转文字工具，使用 OpenAI Whisper 模型进行高精度语音识别。"
    "支持多种音频格式（mp3, wav, m4a, flac 等），"
    "提供精确的段落级别时间戳（精确到 0.01 秒），"
    "支持多语言识别和自动语言检测。"
    "\n\n"
    "**重要功能**："
    "- 可以生成字幕文件（SRT格式），用于视频字幕制作"
    "- 支持从音频文件生成带时间戳的字幕"
    "- 适用于视频字幕提取、语音转字幕等场景"
    "\n\n"
    "使用场景："
    "- 为视频生成字幕文件"
    "- 从音频提取字幕"
    "- 语音转文字并生成字幕"
)
```

### 方案2：改进任务完成判断逻辑

```python
# 检查是否所有计划步骤都已完成
def _check_all_steps_completed(self, plan: Dict[str, Any], execution_history: List[Dict[str, Any]]) -> bool:
    """检查是否所有计划步骤都已完成"""
    steps = plan.get('steps', [])
    if not steps:
        return False
    
    # 检查是否调用了所有必要的工具
    required_tools = plan.get('estimated_tools', [])
    called_tools = set()
    for history_item in execution_history:
        result = history_item.get("result", {})
        tool_results = result.get("tool_results", [])
        for tr in tool_results:
            called_tools.add(tr.get("tool_name", ""))
    
    # 如果计划中提到了whisper，但没调用，说明未完成
    if "whisper" in required_tools and "whisper" not in called_tools:
        return False
    
    return True

# 在判断完成时使用
finished = (
    not tool_calls and
    self._check_all_steps_completed(plan, self.execution_history) and
    ("完成" in response_str or "任务完成" in response_str)
)
```

### 方案3：改进系统提示

```python
system_content = f"""你是一个智能任务执行助手。你的任务是自主使用工具完成用户的任务。

原始任务：{task}

执行计划：
{plan.get('plan', '')}

执行步骤列表：
{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(plan.get('steps', []))])}

**重要提醒**：
1. 必须完成所有计划步骤，不能遗漏任何步骤
2. 如果计划中提到需要调用某个工具（如whisper），必须调用该工具
3. 只有当所有步骤都完成时，才能说"任务完成"
4. 如果某个步骤失败，需要重试或寻找替代方案

请按照计划逐步执行任务：
1. 分析当前步骤需要做什么
2. 选择合适的工具
3. 执行工具并获取结果
4. 根据结果决定下一步行动
5. 重复直到所有步骤完成

**判断任务完成的标准**：
- 所有计划步骤都已执行
- 所有必要的工具都已调用
- 任务目标已达成

当且仅当所有步骤都完成时，请明确说明"任务完成"。"""
```

## 推荐实施顺序

1. **立即实施**：改进 Whisper 工具描述（方案1）
   - 影响范围小
   - 效果明显
   - 风险低

2. **短期实施**：改进系统提示（方案3）
   - 提高推理模型对任务完成标准的理解
   - 减少过早判断完成的情况

3. **中期实施**：改进任务完成判断逻辑（方案2）
   - 增加步骤完成检查
   - 更准确地判断任务是否真正完成

## 测试验证

改进后需要重新测试，验证：
1. 推理模型是否能识别需要调用whisper工具
2. 是否会在所有步骤完成前过早判断完成
3. 是否能正确完成所有步骤

