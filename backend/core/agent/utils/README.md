# 统一的文件路径和表达式处理工具

## 概述

为了解决复杂的文件名和文件路径处理问题，我们设计了一套统一的、鲁棒的工具类：

1. **PathExtractor** - 统一的文件路径提取工具
2. **ExpressionEvaluator** - 统一的表达式求值工具

## PathExtractor（路径提取器）

### 功能

- 从文本中提取所有文件路径（支持多个文件）
- 支持包含空格、中文、特殊字符的文件名
- 支持目录路径提取（如 `/home/robo/Downloads 目录下`）
- 自动规范化路径（移除多余引号、扩展 ~ 路径等）
- 验证路径格式和有效性

### 使用方法

```python
from backend.core.agent.utils.path_utils import PathExtractor

# 提取文件路径
text = "/home/robo/Downloads 目录下 【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4"
paths = PathExtractor.extract_paths(text)
# 返回: ['/home/robo/Downloads/【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4']

# 规范化路径
normalized = PathExtractor.normalize_path("'/path/to/file.mp4'")
# 返回: '/path/to/file.mp4'

# 验证路径
is_valid, error = PathExtractor.validate_path("/path/to/file.mp4", must_exist=True)
```

## ExpressionEvaluator（表达式求值器）

### 功能

- 统一的变量替换（`${steps[N].field}`, `${input.field}`, `${config.field}`）
- 避免 `None` 值导致的语法错误（返回空字符串而不是 `'None'`）
- 支持嵌套变量引用
- 支持 `file_exists()` 函数调用
- 支持路径拼接（如 `${steps[0].video_path}.srt`）

### 使用方法

```python
from backend.core.agent.utils.expression_utils import ExpressionEvaluator

context = {
    'input': {'video_path': '/path/to/video.mp4'},
    'step_results': [{'video_path': '/path/to/video.mp4'}],
    'config': {}
}

evaluator = ExpressionEvaluator(context)

# 求值表达式
result = evaluator.evaluate("${input.video_path}")
# 返回: '/path/to/video.mp4'

result = evaluator.evaluate("${file_exists(${steps[0].video_path}.srt)}")
# 返回: True 或 False
```

## 设计原则

1. **统一性**：所有路径提取和表达式求值都使用统一的工具
2. **鲁棒性**：处理各种边界情况（None 值、空字符串、特殊字符等）
3. **可维护性**：集中管理，易于测试和修改
4. **向后兼容**：保留旧实现作为后备方案

## 解决的问题

1. ✅ 文件路径提取不完整（只有文件名，缺少目录）
2. ✅ 表达式求值时 `None` 值导致语法错误
3. ✅ 多个处理函数逻辑不一致
4. ✅ 嵌套变量引用处理不当
5. ✅ 路径拼接时的引号处理问题

## 使用位置

- `backend/core/agent/orchestrator.py` - 使用 `PathExtractor` 提取技能参数
- `backend/core/agent/skills/executor.py` - 使用 `ExpressionEvaluator` 求值表达式

## 测试建议

建议添加单元测试覆盖以下场景：

1. 包含空格的文件名
2. 包含中文的文件名
3. 包含特殊字符的文件名（如 `[00]`, `×`, `！`）
4. 多个文件路径
5. 相对路径和绝对路径
6. `None` 值的表达式求值
7. 嵌套变量引用
8. `file_exists()` 函数调用

