# Browser Tool 模型选择设计文档

## 概述

Browser Tool 支持在 DeepSeek 和 Qwen 之间，以及视觉模型和 chat 模型之间进行灵活选择，以优化不同场景下的性能和成本。

## 当前设计

### 1. 模型选择策略

当前采用**两级选择策略**：

#### 第一级：视觉功能检测
- **输入**: 任务描述（task）
- **输出**: 是否需要视觉功能（use_vision: bool）
- **逻辑**: 
  - 检查环境变量 `BROWSER_TOOL_USE_VISION`
  - 如果未强制启用，分析任务描述中的关键词
  - 返回是否需要视觉功能

#### 第二级：模型选择
- **输入**: use_vision 标志
- **输出**: 使用的模型（DeepSeek 或 Qwen-VL）
- **逻辑**:
  - 如果需要视觉功能 → 使用 Qwen-VL（如果已配置 `BAILIAN_API_KEY` 和 `BROWSER_TOOL_VISION_MODEL`）
  - 如果不需要视觉功能 → 使用 DeepSeek（默认）

### 2. 当前实现流程

```
任务描述 (task)
    ↓
_needs_vision(task)
    ↓
检查 BROWSER_TOOL_USE_VISION
    ├─ true → 返回 True（强制启用视觉）
    └─ false → 分析任务关键词
        ├─ 包含视觉关键词 → 返回 True
        └─ 不包含 → 返回 False
    ↓
use_vision 标志
    ↓
_create_llm(use_vision)
    ├─ use_vision=True
    │   ├─ 检查 BROWSER_TOOL_VISION_MODEL 和 BAILIAN_API_KEY
    │   │   ├─ 已设置 → 使用 Qwen-VL（通过 model_config.py 获取配置）
    │   │   └─ 未设置 → 回退到 DeepSeek（警告）
    │   └─ 使用 Qwen-VL 配置（ChatOpenAI + 百炼平台 API）
    └─ use_vision=False
        └─ 使用 DeepSeek 配置
```

### 3. 视觉关键词检测

**明确的视觉关键词**（高优先级）：
- 中文：截图、图片、图像、视觉、识别、视觉分析、页面截图
- 英文：screenshot, image, visual, recognize

**上下文视觉关键词**（需要排除简单导航）：
- 中文：查看页面、页面内容、页面布局、页面元素、页面结构、页面样式、分析页面
- 英文：see, view

**简单导航模式**（排除，不需要视觉）：
- `打开 www.example.com`
- `访问 example.com`
- `navigate to example.com`

### 4. 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `BAILIAN_API_KEY` | 必需（如果使用视觉模型） | - | 百炼平台 API 密钥 |
| `BAILIAN_BASE_URL` | 可选 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 百炼平台 API 地址 |
| `BROWSER_TOOL_VISION_MODEL` | 可选 | `qwen-vl-max-2025-08-13` | 视觉模型名称 |
| `BROWSER_TOOL_USE_VISION` | 可选 | `false` | 强制启用视觉功能 |
| `DEEPSEEK_API_KEY` | 必需 | - | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | 可选 | `deepseek-chat` | DeepSeek 模型名称 |

## 设计优势

### 1. 自动化
- 根据任务描述自动选择最合适的模型
- 无需手动指定使用哪个模型

### 2. 成本优化
- 普通任务使用 DeepSeek（成本较低）
- 只在需要视觉功能时使用 Qwen-VL（成本较高）

### 3. 灵活性
- 支持环境变量强制启用视觉功能
- 支持回退机制（Qwen 不可用时使用 DeepSeek）

### 4. 向后兼容
- 默认使用 DeepSeek，不影响现有功能
- Qwen 是可选的，不配置也能正常工作

## 当前限制

### 1. 二元选择
- 当前只支持 DeepSeek（chat）和 Qwen-VL（视觉）
- 不支持在多个 chat 模型之间选择（如 deepseek-chat vs deepseek-reasoner）
- 不支持在多个视觉模型之间选择（如 qwen-vl-plus vs qwen-vl-max）

### 2. 关键词检测
- 依赖简单的关键词匹配
- 可能误判某些任务
- 无法理解复杂的任务语义

### 3. 静态配置
- 模型选择在任务执行前确定
- 无法根据执行过程中的反馈动态调整

## 可能的改进方向

### 1. 多模型支持

#### 方案 A: 扩展模型列表
```python
# 支持多个 chat 模型
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASONER_MODEL=deepseek-reasoner
DEEPSEEK_CODER_MODEL=deepseek-coder

# 支持多个视觉模型
QWEN_VL_PLUS_MODEL=qwen-vl-plus
QWEN_VL_MAX_MODEL=qwen-vl-max
```

#### 方案 B: 模型选择策略
```python
def _select_model(self, task: str, use_vision: bool) -> str:
    """根据任务特征选择最合适的模型"""
    if use_vision:
        # 视觉任务：根据复杂度选择
        if "复杂" in task or "详细" in task:
            return "qwen-vl-max"
        else:
            return "qwen-vl-plus"
    else:
        # 普通任务：根据任务类型选择
        if "推理" in task or "分析" in task:
            return "deepseek-reasoner"
        elif "代码" in task or "编程" in task:
            return "deepseek-coder"
        else:
            return "deepseek-chat"
```

### 2. 智能任务分析

#### 方案 A: 使用 LLM 分析任务
```python
def _analyze_task_with_llm(self, task: str) -> dict:
    """使用 LLM 分析任务特征"""
    analysis_prompt = f"""
    分析以下浏览器任务，判断需要什么类型的模型：
    任务: {task}
    
    请返回 JSON:
    {{
        "needs_vision": true/false,
        "complexity": "simple/medium/complex",
        "task_type": "navigation/extraction/interaction/analysis",
        "recommended_model": "deepseek-chat/qwen-vl-max/..."
    }}
    """
    # 使用轻量级模型（如 deepseek-chat）进行分析
    analysis = self._lightweight_llm.analyze(analysis_prompt)
    return json.loads(analysis)
```

#### 方案 B: 规则 + LLM 混合
```python
def _needs_vision(self, task: str) -> bool:
    """混合策略：规则 + LLM"""
    # 1. 快速规则检查
    if self._has_strong_vision_keywords(task):
        return True
    
    if self._is_simple_navigation(task):
        return False
    
    # 2. 模糊情况使用 LLM 判断
    return self._llm_judge_vision_needed(task)
```

### 3. 动态模型切换

#### 方案 A: 执行中切换
```python
async def _execute_async(self, **kwargs):
    """支持执行中切换模型"""
    # 初始模型选择
    llm = self._create_llm(use_vision=initial_vision)
    
    # 执行任务
    try:
        result = await agent.run()
    except VisionRequiredError:
        # 如果执行失败且需要视觉，切换到 Qwen
        logger.info("切换到 Qwen-VL 模型")
        llm = self._create_llm(use_vision=True)
        result = await agent.run()
    
    return result
```

#### 方案 B: 混合使用
```python
async def _execute_async(self, **kwargs):
    """混合使用多个模型"""
    # 导航步骤使用 DeepSeek
    navigation_llm = self._create_llm(use_vision=False)
    await agent.navigate(url, llm=navigation_llm)
    
    # 视觉分析步骤使用 Qwen
    vision_llm = self._create_llm(use_vision=True)
    await agent.analyze_page(llm=vision_llm)
```

### 4. 成本感知选择

```python
def _select_model_with_cost_awareness(self, task: str, budget: float) -> str:
    """考虑成本的模型选择"""
    models = {
        "deepseek-chat": {"cost": 0.001, "capability": "basic"},
        "qwen-vl-max": {"cost": 0.01, "capability": "vision"},
    }
    
    # 如果预算有限，优先使用低成本模型
    if budget < 0.01:
        return "deepseek-chat"
    
    # 根据任务需求选择
    if self._needs_vision(task):
        return "qwen-vl-max"
    else:
        return "deepseek-chat"
```

## 推荐改进方案

### 短期（1-2周）

1. **扩展模型配置**
   - 支持配置多个 DeepSeek 模型（chat, reasoner, coder）
   - 支持配置多个 Qwen 模型（vl-plus, vl-max）
   - 添加模型选择策略配置

2. **改进关键词检测**
   - 优化视觉关键词列表
   - 改进简单导航任务识别
   - 添加任务类型检测（导航、提取、交互、分析）

### 中期（1-2月）

1. **LLM 辅助任务分析**
   - 使用轻量级模型分析任务特征
   - 结合规则和 LLM 判断
   - 缓存分析结果

2. **动态模型切换**
   - 支持执行中切换模型
   - 根据执行反馈调整策略

### 长期（3-6月）

1. **智能模型选择**
   - 基于历史数据学习最优模型选择
   - 考虑成本、性能、准确性的平衡
   - 支持自定义选择策略

2. **混合模型使用**
   - 不同步骤使用不同模型
   - 并行使用多个模型并比较结果

## 当前实现代码位置

- **视觉检测**: `backend/core/agent/tools/builtin/browser_tool.py::_needs_vision()`
- **模型创建**: `backend/core/agent/tools/builtin/browser_tool.py::_create_llm()`
- **任务执行**: `backend/core/agent/tools/builtin/browser_tool.py::_execute_async()`

## 总结

当前设计采用**简单而有效**的策略：
- ✅ 自动检测视觉需求
- ✅ 在 DeepSeek 和 Qwen 之间选择
- ✅ 支持强制启用和自动回退
- ⚠️ 不支持多模型细粒度选择
- ⚠️ 依赖关键词匹配，可能不够智能

**建议**: 保持当前简单设计，根据实际使用情况逐步优化。


