# 任务复杂度评估方案分析：分类 vs 打分

## 两种方案对比

### 方案1：基于分类（SIMPLE/MEDIUM/COMPLEX）

**实现方式**：
```python
# 将分数映射到分类
def score_to_complexity(score: float) -> TaskComplexity:
    if score < 0.2:
        return TaskComplexity.SIMPLE
    elif score < 0.5:
        return TaskComplexity.MEDIUM
    else:
        return TaskComplexity.COMPLEX

# 模型选择
complexity = score_to_complexity(score)
if complexity == TaskComplexity.SIMPLE:
    return chat_model
elif complexity == TaskComplexity.MEDIUM:
    # 继续使用快速规则判断
    pass
else:
    return reasoning_model
```

**优点**：
- ✅ **简单清晰**：决策规则明确，易于理解和维护
- ✅ **与现有类型一致**：使用 `TaskComplexity` 枚举，类型安全
- ✅ **易于调试**：可以明确知道任务属于哪个复杂度级别
- ✅ **易于扩展**：后续可以基于分类添加更多逻辑

**缺点**：
- ❌ **边界不精确**：0.19 和 0.21 的分数差异很小，但分类不同
- ❌ **需要定义阈值**：需要确定 SIMPLE-MEDIUM 和 MEDIUM-COMPLEX 的阈值
- ❌ **可能丢失信息**：0.49 和 0.51 都是 MEDIUM，但实际复杂度有差异

### 方案2：基于打分（0-1的分数）

**实现方式**：
```python
# 直接使用分数
analysis = complexity_analyzer.analyze_task(task)
score = analysis["score"]

# 模型选择（使用多个阈值）
if score < 0.2:
    return chat_model  # 简单任务
elif score < 0.5:
    # 中等复杂度，结合任务类型判断
    if has_code_keywords(task):
        return code_model
    else:
        return chat_model
else:
    return reasoning_model  # 复杂任务
```

**优点**：
- ✅ **更精确**：可以利用分数的细微差别
- ✅ **更灵活**：可以设置多个阈值，针对不同场景
- ✅ **信息保留**：保留了完整的复杂度信息
- ✅ **可调优**：可以基于实际效果调整阈值

**缺点**：
- ❌ **不够直观**：需要理解分数含义
- ❌ **阈值选择困难**：需要实验确定最佳阈值
- ❌ **决策逻辑复杂**：可能需要多个条件判断

## 推荐方案：混合方案（分类 + 分数）

**核心思想**：使用分数进行精细判断，但最终映射到分类，结合两者优点。

**实现方式**：
```python
async def _select_model(self, task: str) -> str:
    """使用推理模型智能选择最适合的模型"""
    from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
    from backend.core.agent.models import TaskComplexity
    
    config_manager = get_model_config_manager()
    chat_model = config_manager.get_chat_model()
    code_model = config_manager.get_code_model()
    reasoning_model = config_manager.get_reasoning_model()
    
    # 1. 任务复杂度评估（获取分数和详细信息）
    complexity_analyzer = TaskComplexityAnalyzer()
    analysis = complexity_analyzer.analyze_task(task)
    score = analysis["score"]
    
    # 2. 将分数映射到分类（但保留分数用于精细判断）
    def score_to_complexity(score: float) -> TaskComplexity:
        """将分数映射到复杂度分类"""
        if score < 0.2:
            return TaskComplexity.SIMPLE
        elif score < 0.5:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.COMPLEX
    
    complexity = score_to_complexity(score)
    
    # 3. 基于分类和分数进行模型选择
    if complexity == TaskComplexity.COMPLEX:
        # 复杂任务：优先使用推理模型
        return reasoning_model
    elif complexity == TaskComplexity.SIMPLE:
        # 简单任务：继续使用快速规则判断（可能选择 chat 或 code）
        # 但跳过 LLM 分析，直接返回
        task_lower = task.lower()
        if any(kw in task_lower for kw in code_keywords):
            return code_model
        return chat_model
    else:
        # 中等复杂度：结合分数和任务类型
        # 如果分数接近复杂（>0.4），倾向于推理模型
        if score > 0.4:
            # 检查是否有推理关键词
            if any(kw in task_lower for kw in reasoning_keywords):
                return reasoning_model
        
        # 继续使用快速规则判断
        # ... 现有逻辑 ...
```

**优点**：
- ✅ **结合两者优点**：既有分类的清晰性，又有分数的精确性
- ✅ **灵活判断**：中等复杂度任务可以根据分数和任务类型进行更精细的判断
- ✅ **易于调试**：既有分类又有分数，调试时信息更丰富
- ✅ **可扩展**：后续可以基于分数添加更多逻辑

## 具体实现建议

### 阈值设置

基于 `TaskComplexityAnalyzer` 的默认 `complexity_threshold=0.3`，建议：

```python
# 复杂度分类阈值
SIMPLE_THRESHOLD = 0.2   # 简单任务：score < 0.2
MEDIUM_THRESHOLD = 0.5    # 中等任务：0.2 <= score < 0.5
COMPLEX_THRESHOLD = 0.5   # 复杂任务：score >= 0.5

# 或者更精细的三级阈值
SIMPLE_THRESHOLD = 0.2
MEDIUM_LOW_THRESHOLD = 0.35   # 中等偏低
MEDIUM_HIGH_THRESHOLD = 0.5   # 中等偏高
COMPLEX_THRESHOLD = 0.5
```

### 模型选择策略

```python
# 策略1：基于分类的简单策略
if complexity == TaskComplexity.COMPLEX:
    return reasoning_model
elif complexity == TaskComplexity.SIMPLE:
    # 简单任务：快速规则判断
    return quick_rule_selection(task)
else:
    # 中等任务：结合分数和任务类型
    return medium_complexity_selection(task, score)

# 策略2：基于分数的精细策略（用于中等复杂度）
def medium_complexity_selection(task: str, score: float) -> str:
    """中等复杂度任务的模型选择"""
    task_lower = task.lower()
    
    # 如果分数接近复杂（>0.4），且包含推理关键词
    if score > 0.4 and has_reasoning_keywords(task):
        return reasoning_model
    
    # 如果包含代码关键词，使用代码模型
    if has_code_keywords(task):
        return code_model
    
    # 默认使用对话模型
    return chat_model
```

## 最终推荐

**推荐使用混合方案**，原因：

1. **最佳实践**：结合分类的清晰性和分数的精确性
2. **灵活性**：可以根据不同复杂度级别采用不同策略
3. **可维护性**：既有明确的分类，又有详细的分数信息
4. **可扩展性**：后续可以基于分数添加更精细的逻辑

**实施步骤**：

1. 使用 `analyze_task()` 获取分数和详细信息
2. 将分数映射到 `TaskComplexity` 分类
3. 基于分类进行初步判断
4. 对于中等复杂度任务，结合分数进行精细判断
5. 记录分类和分数（用于调试和优化）

## 代码示例

```python
async def _select_model(self, task: str) -> str:
    """使用推理模型智能选择最适合的模型"""
    from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
    from backend.core.agent.models import TaskComplexity
    
    config_manager = get_model_config_manager()
    chat_model = config_manager.get_chat_model()
    code_model = config_manager.get_code_model()
    reasoning_model = config_manager.get_reasoning_model()
    
    # 1. 任务复杂度评估
    complexity_analyzer = TaskComplexityAnalyzer()
    analysis = complexity_analyzer.analyze_task(task)
    score = analysis["score"]
    
    # 2. 将分数映射到分类
    if score < 0.2:
        complexity = TaskComplexity.SIMPLE
    elif score < 0.5:
        complexity = TaskComplexity.MEDIUM
    else:
        complexity = TaskComplexity.COMPLEX
    
    # 3. 基于分类和分数选择模型
    if complexity == TaskComplexity.COMPLEX:
        # 复杂任务：优先使用推理模型
        logger.debug(f"复杂任务 (score={score:.2f})，选择推理模型")
        return reasoning_model
    
    elif complexity == TaskComplexity.SIMPLE:
        # 简单任务：快速规则判断
        task_lower = task.lower()
        code_keywords = ["代码", "code", "编程", "program", "函数", "function", 
                        "脚本", "script", "执行", "execute", "运行", "run", 
                        "ls", "cat", "cd", "mkdir", "rm"]
        
        if any(keyword in task_lower for keyword in code_keywords):
            logger.debug(f"简单任务 (score={score:.2f})，包含代码关键词，选择编程模型")
            return code_model
        logger.debug(f"简单任务 (score={score:.2f})，选择对话模型")
        return chat_model
    
    else:
        # 中等复杂度：结合分数和任务类型
        task_lower = task.lower()
        
        # 如果分数接近复杂（>0.4），且包含推理关键词
        reasoning_keywords = ["分析", "analyze", "推理", "reasoning", "思考", 
                            "think", "策略", "strategy", "计划", "plan", 
                            "解决", "solve", "为什么", "why"]
        
        if score > 0.4 and any(kw in task_lower for kw in reasoning_keywords):
            logger.debug(f"中等复杂度任务 (score={score:.2f})，接近复杂且包含推理关键词，选择推理模型")
            return reasoning_model
        
        # 代码关键词检查
        code_keywords = ["代码", "code", "编程", "program", "函数", "function", 
                        "脚本", "script", "执行", "execute", "运行", "run"]
        
        if any(keyword in task_lower for keyword in code_keywords):
            logger.debug(f"中等复杂度任务 (score={score:.2f})，包含代码关键词，选择编程模型")
            return code_model
        
        # 默认使用对话模型
        logger.debug(f"中等复杂度任务 (score={score:.2f})，选择对话模型")
        return chat_model
```

