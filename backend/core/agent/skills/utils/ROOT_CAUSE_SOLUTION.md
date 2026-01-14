# 根本性解决方案：清晰的输入参数解析系统

## 问题本质

### 核心问题

**代码字符串和表达式字符串的处理逻辑混淆**

- **代码字符串**（如 `code_executor` 的 `code` 参数）：
  - 是多行 Python 代码
  - 应该只替换变量引用，不进行表达式求值
  - 必须保留代码结构

- **表达式字符串**（如条件表达式）：
  - 是简单的表达式
  - 应该进行表达式求值
  - 可以包含逻辑运算符、函数调用等

### 之前的问题

1. **所有字符串都被当作表达式求值** - 导致代码字符串被错误处理
2. **补丁式修复** - 通过 `if key == 'code'` 特殊处理，逻辑分散
3. **难以维护** - 容易遗漏其他类似场景

## 根本性解决方案

### 设计原则

1. **类型驱动（Type-Driven）**
   - 根据参数类型和上下文，自动识别参数的处理方式
   - CODE / EXPRESSION / LITERAL 三种类型

2. **单一职责（Single Responsibility）**
   - `InputResolver`：负责输入参数解析
   - `ExpressionEvaluator`：负责表达式求值
   - `PathExtractor`：负责路径提取

3. **可扩展性（Extensibility）**
   - 可以轻松添加新的输入类型
   - 可以轻松添加新的处理策略

### 架构设计

```
InputResolver (输入解析器)
├── _determine_input_type()  # 确定参数类型（核心逻辑）
│   ├── CODE: code 参数 + code_executor 工具
│   ├── EXPRESSION: 包含 ${...} 的字符串
│   └── LITERAL: 其他情况
├── _resolve_code_string()   # CODE 类型：只替换变量引用
├── _resolve_expression()    # EXPRESSION 类型：表达式求值
└── _get_variable_value()    # 获取变量值（复用 ExpressionEvaluator）
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

## 实现细节

### CODE 类型处理

**目标**：只替换变量引用，保留代码结构

**关键点**：
1. 只替换明确的变量引用（`${input.}`, `${steps[}`, `${config.}`）
2. 如果变量不存在，保留原始变量引用（不替换为空字符串）
3. 检测代码中使用的引号类型，正确转义特殊字符

**示例**：
```python
# 输入
code = 'subtitle_path = "${steps[2].subtitle_path}"'

# 处理过程
# 1. 检测到 ${steps[2].subtitle_path}
# 2. 获取变量值: '/path/to/subtitle.srt'
# 3. 检测引号类型: "
# 4. 转义字符串: /path/to/subtitle.srt
# 5. 替换: subtitle_path = "/path/to/subtitle.srt"

# 输出
resolved_code = 'subtitle_path = "/path/to/subtitle.srt"'
```

### EXPRESSION 类型处理

**目标**：进行表达式求值，返回求值结果

**关键点**：
1. 使用 `ExpressionEvaluator` 进行表达式求值
2. 如果求值失败，保留原始表达式
3. 如果求值返回 `None`，保留原始表达式

**示例**：
```python
# 输入
expression = '${file_exists(${steps[0].video_path}.srt)}'

# 处理过程
# 1. 替换变量: file_exists('/path/to/video.srt')
# 2. 求值: True
# 3. 返回: True

# 输出
resolved_expression = True
```

### LITERAL 类型处理

**目标**：不进行任何处理，直接使用

**示例**：
```python
# 输入
literal = 'simple_string'

# 输出
resolved_literal = 'simple_string'  # 不变
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

## 对比：补丁式修复 vs 根本性解决方案

### 补丁式修复（之前）

```python
def _resolve_inputs(self, inputs, context):
    resolved = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            if key == 'code':  # 特殊处理
                # 100+ 行的特殊处理代码
                ...
            else:
                # 表达式求值
                ...
        else:
            resolved[key] = value
    return resolved
```

**问题**：
- 逻辑分散，难以维护
- 容易遗漏其他类似场景
- 难以扩展

### 根本性解决方案（现在）

```python
def _resolve_inputs(self, inputs, context, tool_name=None):
    resolver = InputResolver(context)
    return resolver.resolve(inputs, tool_name)
```

**优势**：
- 逻辑清晰，易于维护
- 类型驱动，自动识别处理方式
- 易于扩展新的类型和处理策略

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
    TEMPLATE = "template"  # 新增

# 添加新的处理策略
def _resolve_template(self, template: str) -> str:
    # 模板处理逻辑
    pass
```

## 测试验证

### 单元测试结果

```
测试1 - CODE 类型:
原始: subtitle_path = "${steps[2].subtitle_path}"
解析后: subtitle_path = "/path/to/subtitle.srt"
包含变量引用: False ✅

测试2 - EXPRESSION 类型:
原始: ${file_exists(${steps[0].video_path}.srt)}
解析后: False
类型: <class 'bool'> ✅

测试3 - LITERAL 类型:
原始: no_variables_here
解析后: no_variables_here
是否相等: True ✅
```

## 总结

### 根本性解决方案的核心

1. **类型驱动**：根据参数类型和上下文，自动识别处理方式
2. **单一职责**：每个组件只负责一个明确的职责
3. **可扩展性**：可以轻松添加新的类型和处理策略

### 解决的问题

1. ✅ **代码字符串被错误地当作表达式求值** - 通过类型判断解决
2. ✅ **表达式求值返回 `None`** - 通过错误处理解决
3. ✅ **变量引用不存在时被替换为空字符串** - 通过保留原始引用解决
4. ✅ **补丁式修复难以维护** - 通过清晰的架构设计解决

### 设计优势

- **清晰**：逻辑分离，易于理解
- **可维护**：集中管理，易于修改
- **可扩展**：类型驱动，易于扩展
- **鲁棒**：错误处理完善，不易出错

