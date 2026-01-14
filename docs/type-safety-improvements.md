# Type Safety 改进建议

## 问题分析

当前遇到的类型错误：
- `'<' not supported between instances of 'str' and 'int'`
- `step_results` 可能是字符串、字典、列表等不同类型
- 表达式求值时类型不匹配

## Type Hints 的作用

### 1. **静态类型检查（开发时）**

Type hints 配合静态类型检查工具（如 `mypy`, `pyright`）可以在**开发时**发现类型问题：

```python
# 当前代码（没有类型检查）
def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
    step_results = context.get('step_results')  # 类型：Any
    if step_idx < len(step_results):  # 如果 step_results 是字符串，这里会出错
        ...

# 改进后（有类型检查）
from typing import List, Dict, Union, TypedDict

class StepResult(TypedDict):
    download_success: bool
    need_retry: bool
    # ... 其他字段

class ExecutionContext(TypedDict):
    step_results: List[Dict[str, Any]]  # 明确类型
    config: Dict[str, Any]
    input: Dict[str, Any]
    result: Optional[Dict[str, Any]]

def _evaluate_expression(
    self, 
    expression: str, 
    context: ExecutionContext  # 明确的类型
) -> Union[bool, int, float, str, None]:
    step_results: List[Dict[str, Any]] = context.get('step_results', [])
    if not isinstance(step_results, list):  # 运行时检查（仍然需要）
        raise TypeError(f"step_results must be a list, got {type(step_results)}")
    if step_idx < len(step_results):  # 类型检查器知道这是安全的
        ...
```

### 2. **运行时类型检查（仍然需要）**

**重要**：Python 是动态类型语言，type hints **不会在运行时强制类型检查**。

```python
# Type hints 不会阻止这个错误：
def add(a: int, b: int) -> int:
    return a + b

add("1", "2")  # 运行时仍然会执行，返回 "12"（字符串拼接）
```

所以我们需要：
1. **静态类型检查**（开发时）：使用 `mypy` 或 `pyright`
2. **运行时类型检查**（运行时）：使用 `isinstance()` 检查

### 3. **更好的解决方案：Pydantic**

使用 Pydantic 可以在运行时自动验证类型：

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional

class StepResult(BaseModel):
    download_success: bool
    need_retry: bool
    progress: Optional[int] = None

class ExecutionContext(BaseModel):
    step_results: List[StepResult] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    
    @validator('step_results', pre=True)
    def validate_step_results(cls, v):
        if not isinstance(v, list):
            raise TypeError(f"step_results must be a list, got {type(v)}")
        return v

# 使用
try:
    context = ExecutionContext(step_results=[...])  # 自动验证类型
except ValidationError as e:
    # 类型错误会被捕获
    logger.error(f"Invalid context: {e}")
```

## 推荐的改进方案

### 方案 1：增强 Type Hints + 运行时检查（推荐）

```python
from typing import List, Dict, Union, Optional, TypedDict, Literal
from dataclasses import dataclass

# 定义类型
class StepResultDict(TypedDict, total=False):
    download_success: bool
    need_retry: bool
    progress: int
    value: Union[str, int, float, bool]

class ExecutionContext(TypedDict, total=False):
    step_results: List[StepResultDict]
    steps: List[StepResultDict]  # 别名
    config: Dict[str, Any]
    input: Dict[str, Any]
    result: Optional[Dict[str, Any]]

def _evaluate_expression(
    self,
    expression: str,
    context: ExecutionContext
) -> Union[bool, int, float, str, None]:
    """计算表达式，返回类型明确"""
    # 运行时类型检查（仍然需要）
    step_results = context.get('step_results') or context.get('steps')
    if step_results is not None and not isinstance(step_results, (list, tuple)):
        raise TypeError(
            f"step_results must be a list or tuple, got {type(step_results)}"
        )
    
    # 现在类型检查器知道 step_results 是 List
    if step_results and step_idx < len(step_results):
        ...
```

### 方案 2：使用 Pydantic（最安全）

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union

class StepResult(BaseModel):
    """步骤结果模型"""
    download_success: Optional[bool] = None
    need_retry: Optional[bool] = None
    progress: Optional[int] = None
    value: Optional[Union[str, int, float, bool]] = None
    
    class Config:
        extra = "allow"  # 允许额外字段

class ExecutionContext(BaseModel):
    """执行上下文模型"""
    step_results: List[StepResult] = Field(default_factory=list)
    steps: Optional[List[StepResult]] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    
    @validator('step_results', 'steps', pre=True)
    def validate_list(cls, v):
        if v is None:
            return []
        if not isinstance(v, (list, tuple)):
            raise TypeError(f"Expected list or tuple, got {type(v)}")
        return [StepResult(**item) if isinstance(item, dict) else item for item in v]
    
    def get_step_results(self) -> List[StepResult]:
        """获取步骤结果列表"""
        return self.step_results or (self.steps or [])

# 使用
def _evaluate_expression(
    self,
    expression: str,
    context: Union[Dict[str, Any], ExecutionContext]
) -> Union[bool, int, float, str, None]:
    # 转换为 Pydantic 模型（自动验证）
    if isinstance(context, dict):
        ctx = ExecutionContext(**context)
    else:
        ctx = context
    
    # 现在类型是明确的
    step_results = ctx.get_step_results()  # List[StepResult]
    if step_idx < len(step_results):
        step_result = step_results[step_idx]  # StepResult
        value = step_result.download_success  # Optional[bool]
        ...
```

### 方案 3：类型守卫（Type Guards）

```python
from typing import TypeGuard

def is_list_of_dicts(value: Any) -> TypeGuard[List[Dict[str, Any]]]:
    """类型守卫：检查是否是字典列表"""
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)

def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
    step_results = context.get('step_results')
    
    # 类型守卫确保类型安全
    if is_list_of_dicts(step_results):
        # 这里类型检查器知道 step_results 是 List[Dict[str, Any]]
        if step_idx < len(step_results):
            ...
```

## 总结

### Type Hints 能帮助什么：
1. ✅ **开发时发现错误**：静态类型检查器（mypy/pyright）可以在开发时发现类型问题
2. ✅ **IDE 支持**：更好的代码补全和错误提示
3. ✅ **文档作用**：代码更易读，类型更明确
4. ❌ **不能完全防止运行时错误**：Python 是动态类型，运行时仍然需要类型检查

### 最佳实践：
1. **使用 Type Hints**：明确函数参数和返回值的类型
2. **使用 TypedDict**：定义字典的结构
3. **运行时类型检查**：使用 `isinstance()` 验证类型
4. **考虑 Pydantic**：对于复杂的数据结构，使用 Pydantic 自动验证
5. **配置静态类型检查**：在 CI/CD 中运行 `mypy` 或 `pyright`

### 当前问题的根本原因：
- `context` 是 `Dict[str, Any]`，类型太宽泛
- `step_results` 可能是任何类型
- 缺少运行时类型验证

### 建议的改进步骤：
1. 定义 `ExecutionContext` TypedDict
2. 在关键位置添加 `isinstance()` 检查（已经做了）
3. 配置 `mypy` 或 `pyright` 进行静态检查
4. 考虑使用 Pydantic 进行数据验证

