# 输入参数解析系统设计文档

## 问题背景

### 核心问题

**代码字符串和表达式字符串的处理逻辑混淆**

- **代码字符串**（如 `code_executor` 工具的 `code` 参数）：
  - 是多行 Python 代码
  - 应该只替换变量引用（如 `${steps[2].subtitle_path}`），不进行表达式求值
  - 必须保留代码结构，不能改变代码的语法

- **表达式字符串**（如条件表达式、参数值）：
  - 是简单的表达式（如 `${file_exists(${steps[0].video_path}.srt)}`）
  - 应该进行表达式求值，返回求值结果
  - 可以包含逻辑运算符、函数调用等

### 之前的问题

1. **所有字符串都被当作表达式求值**
   - `_resolve_inputs` 对所有字符串都调用 `_evaluate_expression`
   - 导致代码字符串中的 `' '.join` 被错误替换

2. **补丁式修复**
   - 通过 `if key == 'code'` 特殊处理
   - 逻辑分散，难以维护
   - 容易遗漏其他类似场景

## 设计原则

### 1. 类型驱动（Type-Driven）

根据参数的类型和上下文，自动识别参数的处理方式：

- **CODE 类型**：代码字符串，只替换变量引用
- **EXPRESSION 类型**：表达式字符串，进行表达式求值
- **LITERAL 类型**：字面量，不进行任何处理

### 2. 单一职责（Single Responsibility）

每个组件只负责一个明确的职责：

- `InputResolver`：负责输入参数解析
- `ExpressionEvaluator`：负责表达式求值
- `PathExtractor`：负责路径提取

### 3. 可扩展性（Extensibility）

系统设计支持未来扩展：

- 可以轻松添加新的输入类型
- 可以轻松添加新的处理策略
- 可以轻松添加新的工具特殊处理

## 架构设计

### 核心组件

```
InputResolver (输入解析器)
├── _determine_input_type()  # 确定参数类型
├── _resolve_code_string()   # 解析代码字符串
├── _resolve_expression()    # 解析表达式
└── _get_variable_value()    # 获取变量值
    └── ExpressionEvaluator  # 表达式求值器（复用）
```

### 类型判断规则

```python
def _determine_input_type(key, value, tool_name):
    # 规则1: code 参数 + code_executor/execute_code 工具 = CODE 类型
    if key == 'code' and tool_name in ('code_executor', 'execute_code'):
        return InputType.CODE
    
    # 规则2: 包含 ${...} 的字符串 = EXPRESSION 类型
    if isinstance(value, str) and '${' in value:
        return InputType.EXPRESSION
    
    # 规则3: 其他情况 = LITERAL 类型
    return InputType.LITERAL
```

### 处理流程

```
输入参数 → 类型判断 → 选择处理策略 → 解析结果
    ↓           ↓            ↓            ↓
  inputs    CODE/EXPR/   CODE: 只替换    resolved
            LITERAL       EXPR: 求值
                         LITERAL: 原样
```

## 实现细节

### 1. CODE 类型处理

**目标**：只替换变量引用，保留代码结构

**步骤**：
1. 使用正则表达式匹配 `${...}` 变量引用
2. 只替换明确的变量引用（`${input.}`, `${steps[}`, `${config.}`）
3. 获取变量值，格式化为代码字符串
4. 检测代码中使用的引号类型，正确转义特殊字符
5. 如果变量不存在，保留原始变量引用（不替换为空字符串）

**示例**：
```python
# 输入
code = 'subtitle_path = "${steps[2].subtitle_path}"'

# 处理
# 1. 检测到 ${steps[2].subtitle_path}
# 2. 获取变量值: '/path/to/subtitle.srt'
# 3. 检测引号类型: "
# 4. 转义字符串: /path/to/subtitle.srt
# 5. 替换: subtitle_path = "/path/to/subtitle.srt"
```

### 2. EXPRESSION 类型处理

**目标**：进行表达式求值，返回求值结果

**步骤**：
1. 使用 `ExpressionEvaluator` 进行表达式求值
2. 如果求值失败，保留原始表达式
3. 如果求值返回 `None`，保留原始表达式

**示例**：
```python
# 输入
expression = '${file_exists(${steps[0].video_path}.srt)}'

# 处理
# 1. 替换变量: file_exists('/path/to/video.srt')
# 2. 求值: True
# 3. 返回: True
```

### 3. LITERAL 类型处理

**目标**：不进行任何处理，直接使用

**步骤**：
1. 直接返回原始值

**示例**：
```python
# 输入
literal = 'simple_string'

# 处理
# 1. 直接返回: 'simple_string'
```

## 优势

### 1. 清晰的逻辑分离

- **代码字符串**：只替换变量引用，不进行表达式求值
- **表达式字符串**：进行表达式求值
- **字面量**：不进行任何处理

### 2. 易于维护

- 所有逻辑集中在 `InputResolver` 类中
- 类型判断规则清晰明确
- 易于添加新的类型和处理策略

### 3. 可扩展性

- 可以轻松添加新的输入类型（如 `TEMPLATE`, `SQL`, `SHELL` 等）
- 可以轻松添加新的工具特殊处理
- 可以轻松添加新的变量引用格式

### 4. 错误处理

- 变量不存在时，保留原始变量引用（而不是替换为空字符串）
- 表达式求值失败时，保留原始表达式
- 代码字符串替换后为空时，保留原始代码

## 使用示例

### 在 SkillExecutor 中使用

```python
# 旧方式（补丁式）
def _resolve_inputs(self, inputs, context):
    if key == 'code':
        # 特殊处理...
    else:
        # 表达式求值...

# 新方式（设计清晰）
def _resolve_inputs(self, inputs, context, tool_name=None):
    resolver = InputResolver(context)
    return resolver.resolve(inputs, tool_name)
```

### 扩展新类型

```python
# 添加新的输入类型
class InputType(Enum):
    CODE = "code"
    EXPRESSION = "expression"
    LITERAL = "literal"
    TEMPLATE = "template"  # 新增：模板字符串

# 添加新的处理策略
def _resolve_template(self, template: str) -> str:
    # 模板处理逻辑
    pass
```

## 测试建议

### 单元测试

1. **CODE 类型测试**：
   - 测试变量引用替换
   - 测试变量不存在时的处理
   - 测试引号检测和转义
   - 测试代码字符串替换后为空的情况

2. **EXPRESSION 类型测试**：
   - 测试简单表达式求值
   - 测试复杂表达式求值
   - 测试表达式求值失败时的处理

3. **LITERAL 类型测试**：
   - 测试字面量字符串
   - 测试非字符串类型

### 集成测试

1. **完整工作流测试**：
   - 测试 `code_executor` 工具的代码字符串处理
   - 测试条件表达式的求值
   - 测试参数值的解析

## 迁移指南

### 从旧代码迁移

1. **替换 `_resolve_inputs` 调用**：
   ```python
   # 旧代码
   inputs = self._resolve_inputs(step.get('inputs', {}), context)
   
   # 新代码
   inputs = self._resolve_inputs(step.get('inputs', {}), context, tool_name=actual_tool_name)
   ```

2. **移除特殊处理代码**：
   - 移除 `if key == 'code'` 的特殊处理
   - 移除其他补丁式修复

3. **验证功能**：
   - 运行现有测试
   - 验证工具调用是否正常

## 未来改进

1. **支持更多输入类型**：
   - `TEMPLATE`：模板字符串（如 Jinja2）
   - `SQL`：SQL 查询字符串
   - `SHELL`：Shell 命令字符串

2. **改进类型判断**：
   - 支持显式类型标记（如 `code: |`）
   - 支持工具定义中的类型提示

3. **性能优化**：
   - 缓存表达式求值结果
   - 优化正则表达式匹配

4. **错误处理增强**：
   - 提供更详细的错误信息
   - 支持错误恢复策略

