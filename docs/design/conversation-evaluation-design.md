# 对话评估功能设计文档

## 概述

本功能实现了在每一轮对话开始时，自动对上一轮对话结果进行评估打分，并将评估结果记录到消息的 metadata 中。

## 功能特性

### 1. 自动评估
- 在每一轮对话开始时，自动检测是否有上一轮完整的对话（user + assistant）
- 如果存在且未评估过，则自动进行评估

### 2. 多维度评估
评估包含以下维度：
- **相关性** (relevance, 25%): 回答是否与用户问题相关
- **准确性** (accuracy, 25%): 回答的信息是否准确、可靠
- **有用性** (helpfulness, 20%): 回答是否对用户有帮助
- **完整性** (completeness, 15%): 回答是否完整，是否回答了用户的所有问题
- **清晰度** (clarity, 15%): 回答是否清晰易懂

### 3. 评分标准
- 每个维度评分范围：0-100 分
- 90-100: 优秀
- 80-89: 良好
- 70-79: 中等
- 60-69: 及格
- 0-59: 不及格

### 4. 数据存储
- 评估结果保存在上一轮 assistant 消息的 `metadata["evaluation"]` 中
- 包含总体分数、各维度分数、评估说明和时间戳

### 5. 前端显示
- 评估结果会在前端以面板形式显示
- 显示总体分数、各维度分数和评估说明
- 根据分数使用不同颜色（绿色/黄色/红色）

## 架构设计

### 核心组件

#### 1. ConversationEvaluator (`backend/core/agent/evaluator.py`)
对话评估器，负责：
- 构建评估 prompt
- 调用 LLM 进行评估
- 解析评估结果
- 规范化评估数据

#### 2. Orchestrator 集成
在 `orchestrator.py` 的 `stream_process` 和 `process` 方法中：
- 获取历史消息后，检查是否有上一轮对话
- 如果存在且未评估，调用评估器进行评估
- 将评估结果保存到消息 metadata
- 发送评估结果到前端（流式模式）

#### 3. 前端显示 (`frontend/ui/stream_handler.py`)
- 解析 `__EVALUATION__:` 消息
- 使用 `_render_evaluation_info` 方法渲染评估结果

## 数据格式

### 评估结果格式

```json
{
    "overall_score": 85,
    "dimension_scores": {
        "relevance": 90,
        "accuracy": 85,
        "helpfulness": 80,
        "completeness": 75,
        "clarity": 90
    },
    "evaluation": "评估说明文字，简要说明各维度的评分理由",
    "timestamp": "2024-01-01T12:00:00"
}
```

### 消息 Metadata 格式

评估结果保存在消息的 metadata 中：

```json
{
    "role": "assistant",
    "content": "助手回复内容",
    "metadata": {
        "evaluation": {
            "overall_score": 85,
            "dimension_scores": {...},
            "evaluation": "评估说明",
            "timestamp": "2024-01-01T12:00:00"
        }
    }
}
```

## 使用方式

### 启用/禁用评估

在 `Orchestrator` 初始化后，可以通过以下方式控制：

```python
orchestrator = Orchestrator()
orchestrator.enable_evaluation = True  # 启用评估（默认）
orchestrator.enable_evaluation = False  # 禁用评估
```

### 查看评估结果

#### 1. 通过消息 Metadata
```python
messages = context_manager.get_messages(session_id)
for msg in messages:
    if msg.role == MessageRole.ASSISTANT:
        evaluation = msg.metadata.get("evaluation")
        if evaluation:
            print(f"分数: {evaluation['overall_score']}/100")
```

#### 2. 前端显示
在流式对话中，评估结果会自动显示在控制台。

## 评估流程

1. **检测上一轮对话**
   - 从历史消息中查找最后一对 user-assistant 消息
   - 检查 assistant 消息是否已有评估结果

2. **执行评估**
   - 构建评估 prompt（包含用户问题、助手回复、上下文）
   - 调用 LLM 进行评估
   - 解析返回的 JSON 格式评估结果

3. **保存结果**
   - 将评估结果保存到 assistant 消息的 metadata
   - 更新消息到存储后端

4. **前端显示**
   - 发送 `__EVALUATION__:` 消息到前端
   - 前端解析并渲染评估结果

## 配置选项

### 评估维度权重

可以在 `ConversationEvaluator.EVALUATION_DIMENSIONS` 中调整：

```python
EVALUATION_DIMENSIONS = {
    "relevance": {"weight": 0.25},  # 可调整权重
    "accuracy": {"weight": 0.25},
    "helpfulness": {"weight": 0.20},
    "completeness": {"weight": 0.15},
    "clarity": {"weight": 0.15}
}
```

### 评估模型

默认使用 `Orchestrator` 的 `llm_service`，可以自定义：

```python
evaluator = ConversationEvaluator(llm_service=custom_llm_service)
```

## 注意事项

1. **性能影响**
   - 评估会增加一次 LLM 调用，可能影响响应速度
   - 建议在需要时启用，不需要时可以禁用

2. **成本考虑**
   - 每次评估都会消耗 LLM API 调用
   - 评估失败不会影响正常对话流程

3. **评估准确性**
   - 评估结果依赖于 LLM 的判断
   - 可能受到模型能力和 prompt 设计的影响

4. **数据持久化**
   - 评估结果保存在消息 metadata 中
   - 使用文件存储或数据库存储时，评估结果会持久化

## 未来扩展

1. **用户反馈集成**
   - 允许用户手动调整评估分数
   - 结合用户反馈优化评估模型

2. **评估历史分析**
   - 统计对话质量趋势
   - 识别需要改进的方面

3. **自定义评估维度**
   - 允许用户自定义评估维度
   - 支持不同场景的评估标准

4. **批量评估**
   - 支持对历史对话进行批量评估
   - 生成评估报告

