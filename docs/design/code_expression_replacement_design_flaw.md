# 代码中表达式替换的设计缺陷分析

## 问题描述

在 `code_executor` 工具的代码字符串中替换 `${...}` 表达式时，出现了引号重复的语法错误。

### 错误示例

**原始代码**：
```python
segments_str = """${input.segments}"""
```

**替换后**（错误）：
```python
segments_str = """"[{'start_time': '00:05:00', 'end_time': '00:19:00'}]""""
```

**错误**：`SyntaxError: unterminated string literal`（四引号导致语法错误）

## 根因分析

### 1. **设计缺陷：缺乏上下文感知**

**问题**：
- 替换逻辑没有检测表达式是否在字符串字面量中
- 无论表达式在哪里，都使用相同的格式化策略
- 导致在字符串字面量中重复添加引号

**根本原因**：
- **代码字符串中的表达式替换**和**表达式字符串的求值**是两个不同的场景
- 代码字符串中的表达式替换需要**上下文感知**（检测引号上下文）
- 表达式字符串的求值不需要上下文感知（整个字符串就是表达式）

### 2. **替换逻辑的问题**

**错误的替换逻辑**：
```python
# 对于列表/字典，总是使用 json.dumps（会添加引号）
if isinstance(result, (dict, list)):
    return json.dumps(result, ensure_ascii=False)  # 返回 "[...]"
```

**问题**：
- 当表达式在 `"""${input.segments}"""` 中时，`json.dumps` 返回 `"[...]"`（带引号）
- 替换后变成 `""""[...]""""`（四引号）

### 3. **设计层面的问题**

**问题1：类型混淆**
- `code_executor` 工具的 `code` 参数是**代码字符串**，不是**表达式字符串**
- 代码字符串中的表达式应该**只替换值**，不应该进行表达式求值
- 但当前实现将代码字符串当作表达式字符串处理

**问题2：缺乏上下文分析**
- 代码字符串中的表达式替换需要**解析代码结构**（检测引号上下文）
- 当前实现只是简单的字符串替换，没有上下文分析

**问题3：格式化策略单一**
- 所有表达式使用相同的格式化策略
- 没有根据表达式在代码中的位置（字符串内 vs 字符串外）选择不同的策略

## 解决方案

### 1. **上下文感知的替换逻辑**

**核心思想**：
- 检测表达式是否在字符串字面量中（单引号、双引号、三引号）
- 如果在字符串字面量中：直接替换为值（不添加引号）
- 如果不在字符串字面量中：根据类型格式化（添加引号）

**实现**：
```python
def is_in_string_literal(code: str, pos: int):
    """检测位置 pos 是否在字符串字面量中"""
    # 1. 检测三引号字符串（优先级最高）
    # 2. 检测单引号和双引号字符串
    # 3. 返回 (是否在字符串中, 引号类型)
    ...

def replace_expr_in_code(match):
    """替换代码中的表达式（上下文感知）"""
    expr = match.group(0)
    expr_start = match.start()
    
    # 检测表达式是否在字符串字面量中
    in_string, quote_type = is_in_string_literal(code_value, expr_start)
    
    if in_string:
        # 在字符串字面量中：直接替换为值（不添加引号）
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)  # 不添加引号
        else:
            return str(result)
    else:
        # 不在字符串字面量中：根据类型格式化（添加引号）
        if isinstance(result, str):
            return repr(result)  # 添加引号
        elif isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)  # 添加引号
        else:
            return repr(result)
```

### 2. **正确的替换结果**

**原始代码**：
```python
segments_str = """${input.segments}"""
```

**替换后**（正确）：
```python
segments_str = """[{'start_time': '00:05:00', 'end_time': '00:19:00'}]"""
```

**说明**：
- 表达式在 `"""..."""` 三引号字符串中
- 替换时直接使用 `json.dumps()` 的结果（不添加引号）
- 结果正确：`segments_str` 是一个字符串，内容是 JSON 格式的列表

## 设计原则

### 1. **上下文感知**
- 代码字符串中的表达式替换必须**检测上下文**（是否在字符串字面量中）
- 根据上下文选择不同的替换策略

### 2. **类型区分**
- **代码字符串**：只替换表达式，保留代码结构
- **表达式字符串**：进行表达式求值，返回求值结果

### 3. **格式化策略**
- **在字符串字面量中**：直接替换为值（不添加引号）
- **不在字符串字面量中**：根据类型格式化（添加引号）

## 测试用例

### 用例1：表达式在三引号字符串中
```python
# 输入
code = 'segments_str = """${input.segments}"""'

# 期望输出
code = 'segments_str = """[{"start_time": "00:05:00", "end_time": "00:19:00"}]"""'
```

### 用例2：表达式在双引号字符串中
```python
# 输入
code = 'path = "${input.input_file}"'

# 期望输出
code = 'path = "/home/robo/video.mp4"'
```

### 用例3：表达式不在字符串中
```python
# 输入
code = 'segments = ${input.segments}'

# 期望输出
code = 'segments = [{"start_time": "00:05:00", "end_time": "00:19:00"}]'
```

## 总结

**设计缺陷**：
1. **缺乏上下文感知**：没有检测表达式是否在字符串字面量中
2. **格式化策略单一**：所有表达式使用相同的格式化策略
3. **类型混淆**：代码字符串和表达式字符串的处理方式混淆
4. **输入参数获取不一致**：`_execute_llm_code_generator_step` 没有正确处理 `inputs` 字段

**解决方案**：
1. 实现上下文感知的替换逻辑
2. 根据表达式在代码中的位置选择不同的格式化策略
3. 明确区分代码字符串和表达式字符串的处理方式
4. 统一从 `inputs` 字段获取参数（与 `_execute_tool_step` 保持一致）

**关键改进**：
- ✅ 检测表达式是否在字符串字面量中
- ✅ 在字符串字面量中：直接替换为值（不添加引号）
- ✅ 不在字符串字面量中：根据类型格式化（添加引号）
- ✅ 从 `inputs` 字段获取 `code` 和 `prompt` 参数（优先 `inputs`，向后兼容 `step`）

## 附加问题：输入参数获取不一致

### 问题描述

多个执行步骤函数直接从 `step` 获取参数，但技能定义中这些参数在 `inputs` 中：

1. **`_execute_llm_code_generator_step`**：
   ```python
   prompt = step.get('prompt', '')
   code = step.get('code', '')
   model = step.get('model', 'bailian-kimi-k2-thinking')
   ```

2. **`_execute_llm_step`**：
   ```python
   prompt = step.get('prompt', '')
   ```

3. **`_execute_loop_step`**：
   ```python
   items = step.get('items')
   item_var = step.get('item_var', 'item')
   ```

但技能定义中，这些参数在 `inputs` 中：
```yaml
- name: cut_segments
  type: code_executor
  inputs:
    code: |
      ...
```

### 根因

**设计不一致**：
- `_execute_tool_step` 使用 `_resolve_inputs(step.get('inputs', {}), ...)` 解析输入参数
- 其他执行步骤函数直接从 `step` 获取参数，没有处理 `inputs` 字段

### 解决方案

统一从 `inputs` 字段获取参数，同时保持向后兼容：

**`_execute_llm_code_generator_step`**：
```python
inputs = step.get('inputs', {})
prompt = step.get('prompt', '') or inputs.get('prompt', '')
code = step.get('code', '') or inputs.get('code', '')
model = inputs.get('model') or step.get('model', 'bailian-kimi-k2-thinking')
```

**`_execute_llm_step`**：
```python
inputs = step.get('inputs', {})
prompt = step.get('prompt', '') or inputs.get('prompt', '')
```

**`_execute_loop_step`**：
```python
inputs = step.get('inputs', {})
items = step.get('items') or inputs.get('items')
item_var = step.get('item_var') or inputs.get('item_var', 'item')
```

### 修复的函数列表

- ✅ `_execute_llm_code_generator_step` - 修复 `prompt`, `code`, `model`
- ✅ `_execute_llm_step` - 修复 `prompt`
- ✅ `_execute_loop_step` - 修复 `items`, `item_var`
- ✅ `_execute_tool_step` - 已正确使用 `_resolve_inputs`（无需修复）


## 问题描述

在 `code_executor` 工具的代码字符串中替换 `${...}` 表达式时，出现了引号重复的语法错误。

### 错误示例

**原始代码**：
```python
segments_str = """${input.segments}"""
```

**替换后**（错误）：
```python
segments_str = """"[{'start_time': '00:05:00', 'end_time': '00:19:00'}]""""
```

**错误**：`SyntaxError: unterminated string literal`（四引号导致语法错误）

## 根因分析

### 1. **设计缺陷：缺乏上下文感知**

**问题**：
- 替换逻辑没有检测表达式是否在字符串字面量中
- 无论表达式在哪里，都使用相同的格式化策略
- 导致在字符串字面量中重复添加引号

**根本原因**：
- **代码字符串中的表达式替换**和**表达式字符串的求值**是两个不同的场景
- 代码字符串中的表达式替换需要**上下文感知**（检测引号上下文）
- 表达式字符串的求值不需要上下文感知（整个字符串就是表达式）

### 2. **替换逻辑的问题**

**错误的替换逻辑**：
```python
# 对于列表/字典，总是使用 json.dumps（会添加引号）
if isinstance(result, (dict, list)):
    return json.dumps(result, ensure_ascii=False)  # 返回 "[...]"
```

**问题**：
- 当表达式在 `"""${input.segments}"""` 中时，`json.dumps` 返回 `"[...]"`（带引号）
- 替换后变成 `""""[...]""""`（四引号）

### 3. **设计层面的问题**

**问题1：类型混淆**
- `code_executor` 工具的 `code` 参数是**代码字符串**，不是**表达式字符串**
- 代码字符串中的表达式应该**只替换值**，不应该进行表达式求值
- 但当前实现将代码字符串当作表达式字符串处理

**问题2：缺乏上下文分析**
- 代码字符串中的表达式替换需要**解析代码结构**（检测引号上下文）
- 当前实现只是简单的字符串替换，没有上下文分析

**问题3：格式化策略单一**
- 所有表达式使用相同的格式化策略
- 没有根据表达式在代码中的位置（字符串内 vs 字符串外）选择不同的策略

## 解决方案

### 1. **上下文感知的替换逻辑**

**核心思想**：
- 检测表达式是否在字符串字面量中（单引号、双引号、三引号）
- 如果在字符串字面量中：直接替换为值（不添加引号）
- 如果不在字符串字面量中：根据类型格式化（添加引号）

**实现**：
```python
def is_in_string_literal(code: str, pos: int):
    """检测位置 pos 是否在字符串字面量中"""
    # 1. 检测三引号字符串（优先级最高）
    # 2. 检测单引号和双引号字符串
    # 3. 返回 (是否在字符串中, 引号类型)
    ...

def replace_expr_in_code(match):
    """替换代码中的表达式（上下文感知）"""
    expr = match.group(0)
    expr_start = match.start()
    
    # 检测表达式是否在字符串字面量中
    in_string, quote_type = is_in_string_literal(code_value, expr_start)
    
    if in_string:
        # 在字符串字面量中：直接替换为值（不添加引号）
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)  # 不添加引号
        else:
            return str(result)
    else:
        # 不在字符串字面量中：根据类型格式化（添加引号）
        if isinstance(result, str):
            return repr(result)  # 添加引号
        elif isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)  # 添加引号
        else:
            return repr(result)
```

### 2. **正确的替换结果**

**原始代码**：
```python
segments_str = """${input.segments}"""
```

**替换后**（正确）：
```python
segments_str = """[{'start_time': '00:05:00', 'end_time': '00:19:00'}]"""
```

**说明**：
- 表达式在 `"""..."""` 三引号字符串中
- 替换时直接使用 `json.dumps()` 的结果（不添加引号）
- 结果正确：`segments_str` 是一个字符串，内容是 JSON 格式的列表

## 设计原则

### 1. **上下文感知**
- 代码字符串中的表达式替换必须**检测上下文**（是否在字符串字面量中）
- 根据上下文选择不同的替换策略

### 2. **类型区分**
- **代码字符串**：只替换表达式，保留代码结构
- **表达式字符串**：进行表达式求值，返回求值结果

### 3. **格式化策略**
- **在字符串字面量中**：直接替换为值（不添加引号）
- **不在字符串字面量中**：根据类型格式化（添加引号）

## 测试用例

### 用例1：表达式在三引号字符串中
```python
# 输入
code = 'segments_str = """${input.segments}"""'

# 期望输出
code = 'segments_str = """[{"start_time": "00:05:00", "end_time": "00:19:00"}]"""'
```

### 用例2：表达式在双引号字符串中
```python
# 输入
code = 'path = "${input.input_file}"'

# 期望输出
code = 'path = "/home/robo/video.mp4"'
```

### 用例3：表达式不在字符串中
```python
# 输入
code = 'segments = ${input.segments}'

# 期望输出
code = 'segments = [{"start_time": "00:05:00", "end_time": "00:19:00"}]'
```

## 总结

**设计缺陷**：
1. **缺乏上下文感知**：没有检测表达式是否在字符串字面量中
2. **格式化策略单一**：所有表达式使用相同的格式化策略
3. **类型混淆**：代码字符串和表达式字符串的处理方式混淆
4. **输入参数获取不一致**：`_execute_llm_code_generator_step` 没有正确处理 `inputs` 字段

**解决方案**：
1. 实现上下文感知的替换逻辑
2. 根据表达式在代码中的位置选择不同的格式化策略
3. 明确区分代码字符串和表达式字符串的处理方式
4. 统一从 `inputs` 字段获取参数（与 `_execute_tool_step` 保持一致）

**关键改进**：
- ✅ 检测表达式是否在字符串字面量中
- ✅ 在字符串字面量中：直接替换为值（不添加引号）
- ✅ 不在字符串字面量中：根据类型格式化（添加引号）
- ✅ 从 `inputs` 字段获取 `code` 和 `prompt` 参数（优先 `inputs`，向后兼容 `step`）

## 附加问题：输入参数获取不一致

### 问题描述

多个执行步骤函数直接从 `step` 获取参数，但技能定义中这些参数在 `inputs` 中：

1. **`_execute_llm_code_generator_step`**：
   ```python
   prompt = step.get('prompt', '')
   code = step.get('code', '')
   model = step.get('model', 'bailian-kimi-k2-thinking')
   ```

2. **`_execute_llm_step`**：
   ```python
   prompt = step.get('prompt', '')
   ```

3. **`_execute_loop_step`**：
   ```python
   items = step.get('items')
   item_var = step.get('item_var', 'item')
   ```

但技能定义中，这些参数在 `inputs` 中：
```yaml
- name: cut_segments
  type: code_executor
  inputs:
    code: |
      ...
```

### 根因

**设计不一致**：
- `_execute_tool_step` 使用 `_resolve_inputs(step.get('inputs', {}), ...)` 解析输入参数
- 其他执行步骤函数直接从 `step` 获取参数，没有处理 `inputs` 字段

### 解决方案

统一从 `inputs` 字段获取参数，同时保持向后兼容：

**`_execute_llm_code_generator_step`**：
```python
inputs = step.get('inputs', {})
prompt = step.get('prompt', '') or inputs.get('prompt', '')
code = step.get('code', '') or inputs.get('code', '')
model = inputs.get('model') or step.get('model', 'bailian-kimi-k2-thinking')
```

**`_execute_llm_step`**：
```python
inputs = step.get('inputs', {})
prompt = step.get('prompt', '') or inputs.get('prompt', '')
```

**`_execute_loop_step`**：
```python
inputs = step.get('inputs', {})
items = step.get('items') or inputs.get('items')
item_var = step.get('item_var') or inputs.get('item_var', 'item')
```

### 修复的函数列表

- ✅ `_execute_llm_code_generator_step` - 修复 `prompt`, `code`, `model`
- ✅ `_execute_llm_step` - 修复 `prompt`
- ✅ `_execute_loop_step` - 修复 `items`, `item_var`
- ✅ `_execute_tool_step` - 已正确使用 `_resolve_inputs`（无需修复）
