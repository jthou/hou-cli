# Agent Function Calling Tools

这个目录包含 Agent 使用的 function calling tools。

## 目录结构

```
tools/
├── __init__.py          # 模块初始化
├── base.py              # Tool 基类和接口定义
├── registry.py          # Tool 注册和管理
├── builtin/             # 内置工具
│   ├── __init__.py
│   ├── file_tools.py    # 文件操作工具
│   ├── web_tools.py     # 网络请求工具
│   ├── code_tools.py    # 代码相关工具
│   └── system_tools.py  # 系统操作工具
├── custom/              # 自定义工具（可选）
│   ├── __init__.py
│   └── ...
└── tests/               # 测试
    ├── __init__.py
    └── test_tools.py
```

## 设计原则

1. **模块化**: 每个工具都是独立的函数或类
2. **类型安全**: 使用类型注解定义工具的参数和返回值
3. **可扩展**: 支持注册自定义工具
4. **安全**: 工具执行前进行权限和参数验证

## 使用示例

```python
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.builtin.file_tools import read_file_tool

# 注册工具
registry = ToolRegistry()
registry.register(read_file_tool)

# Agent 使用工具
tools = registry.get_tools_for_llm()  # 获取 LLM 格式的工具定义
result = registry.execute("read_file", {"path": "test.txt"})
```

