# 鲁棒的文件路径和表达式处理方案

## 问题背景

复杂的文件名和文件路径处理一直是系统的痛点：
- 文件名包含空格、中文、特殊字符（如 `【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4`）
- 文件路径提取不完整（只有文件名，缺少目录）
- 表达式求值时 `None` 值导致语法错误（如 `None.srt`）
- 多个处理函数逻辑不一致
- 嵌套变量引用处理不当

## 解决方案

### 1. PathExtractor（统一的路径提取工具）

**位置**: `backend/core/agent/utils/path_utils.py`

**核心功能**:
- 从文本中提取所有文件路径（支持多个文件）
- 支持包含空格、中文、特殊字符的文件名
- 支持目录路径提取（如 `/home/robo/Downloads 目录下`）
- 自动规范化路径（移除多余引号、扩展 ~ 路径等）
- 验证路径格式和有效性

**设计原则**:
1. **多策略提取**: 先查找目录路径，再提取文件名，最后组合
2. **鲁棒性**: 处理各种边界情况（空字符串、None、特殊字符等）
3. **规范化**: 统一路径格式，移除多余引号
4. **验证**: 检查路径格式和有效性

**使用示例**:
```python
from backend.core.agent.utils.path_utils import PathExtractor

text = "/home/robo/Downloads 目录下 【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4"
paths = PathExtractor.extract_paths(text)
# 返回: ['/home/robo/Downloads/【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4']
```

### 2. ExpressionEvaluator（统一的表达式求值工具）

**位置**: `backend/core/agent/utils/expression_utils.py`

**核心功能**:
- 统一的变量替换（`${steps[N].field}`, `${input.field}`, `${config.field}`）
- 避免 `None` 值导致的语法错误（返回空字符串而不是 `'None'`）
- 支持嵌套变量引用（优先替换最内层变量）
- 支持 `file_exists()` 函数调用
- 支持路径拼接（如 `${steps[0].video_path}.srt`）

**设计原则**:
1. **递归替换**: 优先替换最内层的变量引用，以正确处理嵌套情况
2. **函数调用保护**: 如果变量表达式包含函数调用，保留原样，在后续步骤中处理
3. **路径拼接处理**: 先处理路径拼接（如 `'path'.ext`），再处理函数调用
4. **None 值处理**: `None` 值返回空字符串，避免语法错误

**处理流程**:
1. 替换所有嵌套的变量引用（优先最内层）
2. 处理路径拼接（`'path'.ext` -> `'path.ext'`）
3. 处理 `file_exists()` 函数调用中的路径拼接
4. 安全地求值表达式

**使用示例**:
```python
from backend.core.agent.utils.expression_utils import ExpressionEvaluator

context = {
    'step_results': [{'video_path': '/path/to/video.mp4'}],
    'input': {},
    'config': {}
}

evaluator = ExpressionEvaluator(context)
result = evaluator.evaluate("${file_exists(${steps[0].video_path}.srt)}")
# 返回: True 或 False
```

## 集成位置

1. **orchestrator.py**: 使用 `PathExtractor.extract_paths()` 提取技能参数
2. **executor.py**: 使用 `ExpressionEvaluator` 求值表达式（保留旧实现作为后备）

## 解决的问题

✅ **文件路径提取不完整**: 现在能够正确提取完整路径（包括目录）  
✅ **表达式求值时 None 值导致语法错误**: `None` 值返回空字符串，避免 `None.srt` 这样的语法错误  
✅ **多个处理函数逻辑不一致**: 统一使用 `PathExtractor` 和 `ExpressionEvaluator`  
✅ **嵌套变量引用处理不当**: 优先替换最内层变量，正确处理嵌套情况  
✅ **路径拼接时的引号处理问题**: 统一处理路径拼接，确保引号正确

## 测试验证

### 路径提取测试
```python
# 测试1: 包含空格和中文的文件名
text = "/home/robo/Downloads 目录下 【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4"
paths = PathExtractor.extract_paths(text)
# 预期: ['/home/robo/Downloads/【正片】MiniMax 创始人闫俊杰×罗永浩！大山并非无法翻越[00].mp4']

# 测试2: 多个文件
text = "/home/robo/Downloads 目录下 file1.mp4 file2.mp4"
paths = PathExtractor.extract_paths(text)
# 预期: ['/home/robo/Downloads/file1.mp4', '/home/robo/Downloads/file2.mp4']
```

### 表达式求值测试
```python
# 测试1: 嵌套变量引用
expr = "${file_exists(${steps[0].video_path}.srt)}"
# 预期: 正确替换变量并求值

# 测试2: None 值处理
expr = "${steps[0].nonexistent_field}.srt"
# 预期: 返回空字符串，不产生语法错误

# 测试3: 路径拼接
expr = "${steps[0].video_path}.srt"
# 预期: 正确拼接路径
```

## 为什么这个方案是鲁棒的？

1. **统一性**: 所有路径提取和表达式求值都使用统一的工具，避免逻辑不一致
2. **多策略**: 路径提取使用多种策略，确保在各种情况下都能正确提取
3. **错误处理**: 完善的错误处理机制，避免 `None` 值导致的语法错误
4. **递归处理**: 正确处理嵌套变量引用，优先替换最内层变量
5. **函数调用保护**: 正确处理函数调用中的变量引用，避免误替换
6. **路径规范化**: 统一规范化路径格式，移除多余引号，扩展 ~ 路径
7. **验证机制**: 验证路径格式和有效性，确保提取的路径是有效的

## 未来改进建议

1. **添加单元测试**: 为 `PathExtractor` 和 `ExpressionEvaluator` 添加全面的单元测试
2. **性能优化**: 如果路径提取成为性能瓶颈，可以考虑优化正则表达式
3. **扩展支持**: 支持更多文件类型和路径格式
4. **错误恢复**: 如果路径提取失败，提供更详细的错误信息和恢复建议

