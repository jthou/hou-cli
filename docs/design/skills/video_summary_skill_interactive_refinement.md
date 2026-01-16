# 视频摘要技能 - 交互式摘要调整机制

## 概述

交互式摘要调整机制允许用户根据初始摘要提供反馈，系统根据反馈迭代优化摘要，直到满足用户需求。

## 设计目标

1. **用户导向**：摘要生成应考虑用户的特定需求和关注点
2. **迭代优化**：支持多轮反馈和调整
3. **灵活交互**：用户可以通过自然语言提供反馈
4. **智能理解**：系统能够理解用户的调整意图并相应优化

## 工作流程

### 1. 初始摘要生成

```
用户输入（包含问题/需求）
    ↓
生成初始摘要（考虑用户需求）
    ↓
展示初始摘要给用户
```

### 2. 交互式调整循环

```
用户查看初始摘要
    ↓
用户提供反馈（可选）
    ↓
┌─────────────────────────────┐
│ 反馈类型判断：               │
│ - 完成/满意 → 结束          │
│ - 需要调整 → 继续优化       │
└─────────────────────────────┘
    ↓
根据反馈调整摘要
    ↓
展示调整后的摘要
    ↓
（最多 N 轮，默认 3 轮）
```

## 反馈类型和处理

### 1. 长度调整

**用户反馈示例**：
- "太长了，缩短到 100 字"
- "更详细一些，增加到 500 字"
- "保持当前长度"

**处理策略**：
```python
if "缩短" in feedback or "减少" in feedback:
    target_length = extract_number(feedback) or current_length * 0.7
    adjust_summary_length(target_length)
elif "详细" in feedback or "增加" in feedback:
    target_length = extract_number(feedback) or current_length * 1.5
    adjust_summary_length(target_length)
```

### 2. 内容重点调整

**用户反馈示例**：
- "重点关注技术细节"
- "突出关键观点"
- "更关注实际应用"
- "减少背景介绍"

**处理策略**：
```python
focus_areas = extract_focus_areas(feedback)
# 例如：["技术细节", "关键观点", "实际应用"]

refined_summary = generate_summary_with_focus(
    subtitle_text,
    focus_areas=focus_areas,
    exclude_areas=extract_exclude_areas(feedback)
)
```

### 3. 风格调整

**用户反馈示例**：
- "更简洁一些"
- "更正式一些"
- "用更通俗的语言"
- "增加一些数据支撑"

**处理策略**：
```python
style_preferences = extract_style(feedback)
# 例如：{"tone": "formal", "detail_level": "high", "data_support": True}

refined_summary = generate_summary_with_style(
    subtitle_text,
    style=style_preferences
)
```

### 4. 结构调整

**用户反馈示例**：
- "按时间顺序组织"
- "先讲结论，再讲过程"
- "分几个要点说明"

**处理策略**：
```python
structure_preference = extract_structure(feedback)
# 例如：{"order": "chronological", "format": "bullet_points"}

refined_summary = generate_summary_with_structure(
    subtitle_text,
    structure=structure_preference
)
```

## 实现细节

### 1. 反馈解析

```python
def parse_user_feedback(feedback: str) -> dict:
    """解析用户反馈，提取调整意图"""
    result = {
        'action': 'refine',  # refine, complete, unclear
        'length_adjustment': None,
        'focus_areas': [],
        'exclude_areas': [],
        'style_preferences': {},
        'structure_preferences': {}
    }
    
    # 检查是否完成
    if any(word in feedback.lower() for word in ['完成', '满意', '可以', 'ok', 'done']):
        result['action'] = 'complete'
        return result
    
    # 提取长度调整
    length_match = re.search(r'(\d+)\s*字', feedback)
    if length_match:
        result['length_adjustment'] = int(length_match.group(1))
    
    # 提取关注点
    focus_keywords = ['关注', '重点', '突出', '强调']
    for keyword in focus_keywords:
        if keyword in feedback:
            # 提取关注的具体内容
            focus_content = extract_after_keyword(feedback, keyword)
            result['focus_areas'].append(focus_content)
    
    # 提取排除内容
    exclude_keywords = ['减少', '不要', '忽略', '排除']
    for keyword in exclude_keywords:
        if keyword in feedback:
            exclude_content = extract_after_keyword(feedback, keyword)
            result['exclude_areas'].append(exclude_content)
    
    # 提取风格偏好
    if '简洁' in feedback or '简短' in feedback:
        result['style_preferences']['conciseness'] = 'high'
    if '详细' in feedback or '具体' in feedback:
        result['style_preferences']['detail_level'] = 'high'
    if '正式' in feedback:
        result['style_preferences']['tone'] = 'formal'
    if '通俗' in feedback or '简单' in feedback:
        result['style_preferences']['tone'] = 'casual'
    
    return result
```

### 2. 摘要调整 Prompt

```python
def build_refinement_prompt(
    current_summary: str,
    user_feedback: str,
    subtitle_text: str,
    target_length: int,
    iteration: int
) -> str:
    """构建摘要调整的 Prompt"""
    
    feedback_analysis = parse_user_feedback(user_feedback)
    
    prompt = f"""这是第 {iteration} 轮摘要调整。

原始字幕内容：
{subtitle_text}

当前摘要（第 {iteration - 1} 轮）：
{current_summary}

用户反馈：
{user_feedback}

请根据用户反馈调整摘要，生成新的摘要版本。

要求：
1. 保持摘要长度在 {target_length} 字左右"""
    
    if feedback_analysis['length_adjustment']:
        prompt += f"\n2. 摘要长度应调整为约 {feedback_analysis['length_adjustment']} 字"
    
    if feedback_analysis['focus_areas']:
        prompt += f"\n3. 重点关注以下方面：{', '.join(feedback_analysis['focus_areas'])}"
    
    if feedback_analysis['exclude_areas']:
        prompt += f"\n4. 减少或排除以下内容：{', '.join(feedback_analysis['exclude_areas'])}"
    
    if feedback_analysis['style_preferences']:
        style_desc = describe_style_preferences(feedback_analysis['style_preferences'])
        prompt += f"\n5. 风格要求：{style_desc}"
    
    prompt += "\n6. 保持逻辑连贯性和可读性"
    prompt += "\n7. 如果用户反馈不明确，请做出合理的改进"
    
    return prompt
```

### 3. 交互循环控制

```python
class InteractiveSummaryRefinement:
    """交互式摘要调整管理器"""
    
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.current_summary = None
        self.refinement_history = []
        self.iteration_count = 0
    
    async def refine_summary(
        self,
        initial_summary: str,
        subtitle_text: str,
        llm_service,
        user_feedback_callback
    ) -> str:
        """执行交互式摘要调整"""
        self.current_summary = initial_summary
        self.iteration_count = 0
        
        while self.iteration_count < self.max_iterations:
            # 展示当前摘要
            await self._present_summary(self.current_summary)
            
            # 收集用户反馈
            user_feedback = await user_feedback_callback()
            
            # 检查是否完成
            if self._is_complete(user_feedback):
                break
            
            # 调整摘要
            refined_summary = await self._refine(
                self.current_summary,
                user_feedback,
                subtitle_text,
                llm_service
            )
            
            # 记录历史
            self.refinement_history.append({
                'iteration': self.iteration_count + 1,
                'feedback': user_feedback,
                'summary_before': self.current_summary,
                'summary_after': refined_summary
            })
            
            # 更新当前摘要
            self.current_summary = refined_summary
            self.iteration_count += 1
        
        return self.current_summary
    
    def _is_complete(self, feedback: str) -> bool:
        """检查用户是否满意当前摘要"""
        complete_keywords = ['完成', '满意', '可以', 'ok', 'done', '结束']
        return any(keyword in feedback.lower() for keyword in complete_keywords)
```

## 使用场景

### 场景 1：长度调整

```
用户："帮我分析这个视频"
系统：生成初始摘要（200 字）
用户："太长了，缩短到 100 字"
系统：生成调整后的摘要（100 字）
用户："完成"
```

### 场景 2：内容重点调整

```
用户："分析这个视频，重点关注技术实现"
系统：生成初始摘要（包含技术实现）
用户："更关注实际应用场景"
系统：调整摘要，突出应用场景
用户："完成"
```

### 场景 3：多轮调整

```
用户："帮我生成摘要"
系统：生成初始摘要
用户："更详细一些"
系统：生成更详细的摘要
用户："重点关注前 10 分钟的内容"
系统：调整摘要，突出前 10 分钟
用户："缩短到 150 字"
系统：生成最终摘要（150 字，突出前 10 分钟）
用户："完成"
```

## 配置参数

```yaml
interactive_refinement:
  enabled: true  # 是否启用交互式调整
  max_iterations: 3  # 最大调整轮数
  auto_present: true  # 自动展示摘要
  feedback_timeout: 300  # 等待用户反馈的超时时间（秒）
  save_history: true  # 是否保存调整历史
```

## 优势

1. **用户导向**：摘要更符合用户需求
2. **灵活调整**：支持多种调整类型
3. **迭代优化**：多轮调整逐步优化
4. **自然交互**：用户可以用自然语言提供反馈
5. **历史记录**：保存调整历史，便于追溯

## 注意事项

1. **轮数限制**：避免无限循环，设置最大轮数
2. **超时处理**：如果用户长时间不反馈，自动结束
3. **反馈理解**：需要准确理解用户的调整意图
4. **成本考虑**：多轮调整会增加 LLM 调用次数
5. **用户体验**：需要清晰的提示和进度反馈

## 未来优化

1. **智能建议**：系统主动提供调整建议
2. **可视化对比**：展示调整前后的对比
3. **模板支持**：提供摘要模板供用户选择
4. **批量调整**：支持同时调整多个方面
5. **学习用户偏好**：记录用户偏好，自动应用



