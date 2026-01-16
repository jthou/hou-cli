# 增强 LLM 工具决策和选择能力方案

## 当前状态分析

### 1. 工具选择机制

**当前实现**：
- LLM 通过 Function Calling 机制选择工具
- `tool_choice: "auto"` - 让 LLM 自动决定是否调用工具
- 支持多轮工具调用循环（最多 100 轮）
- 工具定义包含：name、description、parameters

**当前问题**：
1. **工具描述不够详细**：只有简单的 description，缺少使用场景、示例、限制说明
2. **工具选择规则硬编码**：在 system_prompt 中硬编码了 browser、google_search、get_weather 的规则
3. **工具注册顺序可能影响 LLM 决策**：工具按注册顺序传递给 LLM，可能存在位置偏差
4. **缺少工具组合策略**：没有指导 LLM 如何组合多个工具完成任务
5. **缺少工具使用反馈**：没有记录工具使用历史，无法学习优化
6. **工具选择提示不够清晰**：system_prompt 中的工具选择指南不够系统化

## 增强方案

### 阶段 0：严格的输入输出参数定义（关键！）

**重要**：由于 LLM 可能会编写代码来调用工具，所有工具都必须有严格的输入输出参数定义。

#### 0.1 扩展 ToolResult，添加输出模式定义

```python
# backend/core/agent/tools/base.py

@dataclass
class ToolOutputSchema:
    """工具输出模式定义"""
    type: str  # "object", "array", "string", "integer", "number", "boolean"
    properties: Optional[Dict[str, Any]] = None  # 当 type="object" 时，定义属性
    items: Optional[Dict[str, Any]] = None  # 当 type="array" 时，定义数组元素类型
    description: str = ""  # 输出格式说明
    example: Optional[Any] = None  # 输出示例

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # 新增：输出模式验证（可选，用于严格验证）
    output_schema: Optional[ToolOutputSchema] = None

class Tool(ABC):
    """Tool 基类，所有工具继承此类"""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[List[ToolParameter]] = None,
        output_schema: Optional[ToolOutputSchema] = None  # 新增：输出模式定义
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.output_schema = output_schema  # 新增
    
    def execute(self, **kwargs) -> ToolResult:
        """执行工具，返回 ToolResult"""
        # 1. 验证输入参数
        validation_error = self.validate_parameters(**kwargs)
        if validation_error:
            return ToolResult(
                success=False,
                error=f"参数验证失败: {validation_error}"
            )
        
        # 2. 执行工具（子类实现）
        result = self._execute(**kwargs)
        
        # 3. 验证输出格式（如果定义了输出模式）
        if self.output_schema and result.success and result.data:
            validation_result = self._validate_output(result.data, self.output_schema)
            if not validation_result[0]:
                return ToolResult(
                    success=False,
                    error=f"输出格式验证失败: {validation_result[1]}"
                )
        
        return result
    
    @abstractmethod
    def _execute(self, **kwargs) -> ToolResult:
        """子类实现：执行工具逻辑"""
        pass
    
    def _validate_output(self, data: Any, schema: ToolOutputSchema) -> tuple[bool, Optional[str]]:
        """验证输出格式是否符合模式定义"""
        # 实现输出格式验证逻辑
        # 返回 (是否有效, 错误信息)
        pass
    
    def get_output_schema_dict(self) -> Optional[Dict[str, Any]]:
        """获取输出模式的 JSON Schema 格式（用于 LLM 理解）"""
        if not self.output_schema:
            return None
        
        schema = {
            "type": self.output_schema.type,
            "description": self.output_schema.description
        }
        
        if self.output_schema.type == "object" and self.output_schema.properties:
            schema["properties"] = self.output_schema.properties
            schema["required"] = list(self.output_schema.properties.keys())
        
        if self.output_schema.type == "array" and self.output_schema.items:
            schema["items"] = self.output_schema.items
        
        if self.output_schema.example:
            schema["example"] = self.output_schema.example
        
        return schema
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 LLM Function Calling）"""
        tool_dict = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            "type": param.type,
                            "description": param.description,
                        }
                        for param in self.parameters
                    },
                    "required": [param.name for param in self.parameters if param.required],
                }
            }
        }
        
        # 添加输出模式说明（用于 LLM 理解）
        output_schema = self.get_output_schema_dict()
        if output_schema:
            # 在 description 中添加输出格式说明
            tool_dict["function"]["description"] += f"\n\n输出格式：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
        
        return tool_dict
```

#### 0.2 为现有工具添加输出模式定义

**示例：file_search 工具**

```python
# backend/core/agent/tools/builtin/file_search_tool.py

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter, ToolOutputSchema

class FileSearchTool(Tool):
    def __init__(self):
        # 定义输出模式
        output_schema = ToolOutputSchema(
            type="object",
            description="文件搜索结果",
            properties={
                "results": {
                    "type": "array",
                    "description": "搜索结果列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件完整路径"},
                            "name": {"type": "string", "description": "文件名"},
                            "size": {"type": "integer", "description": "文件大小（字节）"},
                            "size_human": {"type": "string", "description": "文件大小（人类可读）"},
                            "modified_time": {"type": "string", "description": "修改时间（ISO 格式）"},
                            "file_type": {"type": "string", "description": "文件类型"}
                        },
                        "required": ["path", "name", "size", "size_human", "modified_time", "file_type"]
                    }
                },
                "total": {"type": "integer", "description": "总结果数"},
                "count": {"type": "integer", "description": "当前返回结果数"},
                "has_more": {"type": "boolean", "description": "是否还有更多结果"},
                "search_time_ms": {"type": "number", "description": "搜索耗时（毫秒）"},
                "search_type": {"type": "string", "description": "搜索类型"},
                "platform": {"type": "string", "description": "平台"},
                "summary": {"type": "string", "description": "结果摘要"}
            },
            example={
                "results": [
                    {
                        "path": "/path/to/file.py",
                        "name": "file.py",
                        "size": 1024,
                        "size_human": "1.0 KB",
                        "modified_time": "2024-01-01T00:00:00",
                        "file_type": "Python"
                    }
                ],
                "total": 1,
                "count": 1,
                "has_more": False,
                "search_time_ms": 10.5,
                "search_type": "filename",
                "platform": "macOS",
                "summary": "找到 1 个文件"
            }
        )
        
        super().__init__(
            name="file_search",
            description="搜索本地文件系统中的文件",
            parameters=[...],
            output_schema=output_schema  # 添加输出模式
        )
    
    def _execute(self, **kwargs) -> ToolResult:
        """执行文件搜索（确保返回格式符合 output_schema）"""
        # ... 执行逻辑 ...
        
        # 确保返回的数据格式符合 output_schema
        return ToolResult(
            success=True,
            data={
                "results": results,  # 必须符合 output_schema 定义
                "total": response.total,
                "count": len(results),
                "has_more": response.has_more,
                "search_time_ms": response.search_time_ms,
                "search_type": response.search_type,
                "platform": response.platform,
                "summary": summary
            }
        )
```

#### 0.3 在 System Prompt 中强调严格的输入输出定义

```python
# backend/core/agent/orchestrator.py

system_prompt = f"""你是一个智能助手，能够帮助用户解决各种问题。

【重要】工具调用规范：

1. **输入参数**：
   - 每个工具都有严格的输入参数定义
   - 必须提供所有必需参数
   - 参数类型必须匹配（string、integer、number、boolean、object、array）
   - 如果参数有枚举值限制，必须使用枚举值之一

2. **输出格式**：
   - 每个工具都有明确的输出格式定义
   - 输出是一个 JSON 对象，包含固定的字段
   - 如果工具执行成功，输出包含 `success: true` 和 `data` 字段
   - 如果工具执行失败，输出包含 `success: false` 和 `error` 字段

3. **代码中调用工具**：
   - 如果你需要编写代码来调用工具，必须严格按照工具的输入输出定义
   - 使用 `tool_registry.get_tool(tool_name)` 获取工具实例
   - 使用 `tool.execute(**kwargs)` 调用工具
   - 检查返回的 `ToolResult.success` 来判断是否成功
   - 从 `ToolResult.data` 中获取结果数据（格式已定义）

4. **工具输出示例**：
   - file_search 工具输出：{{"results": [...], "total": 10, "count": 10, ...}}
   - execute_code 工具输出：{{"output": "...", "error": null, "exit_code": 0}}
   - browser 工具输出：{{"title": "...", "content": "...", "links": [...]}}

{tool_selection_guide}
"""
```

### 阶段 1：增强工具描述和元数据

#### 1.1 扩展 Tool 基类，添加元数据

```python
# backend/core/agent/tools/base.py

@dataclass
class ToolMetadata:
    """工具元数据"""
    category: str  # 工具类别（如 "web", "file", "code", "search"）
    use_cases: List[str]  # 使用场景列表
    examples: List[Dict[str, str]]  # 使用示例 [{"input": "...", "output": "..."}]
    limitations: List[str]  # 限制说明
    best_practices: List[str]  # 最佳实践
    related_tools: List[str]  # 相关工具名称
    cost_estimate: Optional[str] = None  # 成本估算（如 API 调用成本）

class Tool(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[List[ToolParameter]] = None,
        metadata: Optional[ToolMetadata] = None  # 新增
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.metadata = metadata or ToolMetadata(
            category="general",
            use_cases=[],
            examples=[],
            limitations=[],
            best_practices=[],
            related_tools=[]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 LLM Function Calling）"""
        tool_dict = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._build_enhanced_description(),  # 增强描述
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            "type": param.type,
                            "description": param.description,
                        }
                        for param in self.parameters
                    },
                    "required": [param.name for param in self.parameters if param.required],
                }
            }
        }
        return tool_dict
    
    def _build_enhanced_description(self) -> str:
        """构建增强的工具描述"""
        desc = self.description
        
        # 添加使用场景
        if self.metadata.use_cases:
            desc += f"\n\n使用场景：\n" + "\n".join(f"- {uc}" for uc in self.metadata.use_cases)
        
        # 添加示例
        if self.metadata.examples:
            desc += "\n\n使用示例："
            for i, example in enumerate(self.metadata.examples[:3], 1):  # 最多3个示例
                desc += f"\n示例 {i}："
                if "input" in example:
                    desc += f"\n  输入：{example['input']}"
                if "output" in example:
                    desc += f"\n  输出：{example['output']}"
        
        # 添加限制说明
        if self.metadata.limitations:
            desc += "\n\n限制：\n" + "\n".join(f"- {lim}" for lim in self.metadata.limitations)
        
        # 添加最佳实践
        if self.metadata.best_practices:
            desc += "\n\n最佳实践：\n" + "\n".join(f"- {bp}" for bp in self.metadata.best_practices[:2])  # 最多2条
        
        # 添加相关工具
        if self.metadata.related_tools:
            desc += f"\n\n相关工具：{', '.join(self.metadata.related_tools)}"
        
        return desc
```

#### 1.2 为现有工具添加元数据

**示例：browser 工具**

```python
# backend/core/agent/tools/builtin/browser_tool.py

from backend.core.agent.tools.base import Tool, ToolMetadata

class BrowserTool(Tool):
    def __init__(self):
        metadata = ToolMetadata(
            category="web",
            use_cases=[
                "访问网站并获取网页内容",
                "查看网页的文本、链接、图片等信息",
                "提取网页中的特定信息",
                "浏览需要 JavaScript 渲染的动态网页"
            ],
            examples=[
                {
                    "input": "打开 https://www.example.com 并查看页面标题",
                    "output": "页面标题：Example Domain\n页面内容：..."
                },
                {
                    "input": "访问 https://news.example.com 并提取所有新闻标题",
                    "output": "找到 10 条新闻标题：..."
                }
            ],
            limitations=[
                "需要网络连接",
                "某些网站可能有反爬虫机制",
                "JavaScript 渲染可能需要较长时间"
            ],
            best_practices=[
                "对于需要登录的网站，先检查是否需要认证",
                "对于大量数据，考虑分页获取",
                "注意网站的 robots.txt 和使用条款"
            ],
            related_tools=["google_search", "wikipedia"]
        )
        
        super().__init__(
            name="browser",
            description="访问网站并获取网页内容，支持 JavaScript 渲染的动态网页",
            parameters=[...],
            metadata=metadata
        )
```

### 阶段 1.5：消除工具顺序偏差（重要！）

**问题**：工具注册顺序和硬编码规则可能会影响 LLM 的选择：
1. `get_tools_for_llm()` 返回的工具列表保持注册顺序
2. system_prompt 中有硬编码的工具选择规则（如 "必须使用 browser"）
3. 这些规则限制了 LLM 的自由决策能力

**核心原则**：LLM 应该根据**任务需求**和**工具描述**来选择工具，而不是依赖位置或硬编码规则。

#### 1.5.1 按类别分组（推荐，但不暗示优先级）

按类别分组可以帮助 LLM 更好地理解工具结构，但**不暗示优先级**：

```python
# backend/core/agent/tools/registry.py

def get_tools_for_llm(self, grouped: bool = True) -> List[dict]:
    """
    获取 LLM 格式的工具定义（用于 Function Calling）
    
    Args:
        grouped: 是否按类别分组（推荐，让 LLM 更容易理解工具结构）
    
    Returns:
        OpenAI Function Calling 格式的工具定义列表
    """
    tools = list(self._tools.values())
    
    if grouped:
        # 按类别分组（仅用于组织，不暗示优先级）
        tools_by_category = {}
        for tool in tools:
            category = getattr(tool.metadata, 'category', 'general') if hasattr(tool, 'metadata') else 'general'
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
        
        # 按类别顺序排列（仅用于组织，类别内保持稳定顺序）
        category_order = ['code', 'file', 'web', 'search', 'media', 'system', 'general']
        result = []
        for category in category_order:
            if category in tools_by_category:
                # 类别内保持稳定顺序（不随机打乱，也不暗示优先级）
                result.extend([tool.to_dict() for tool in tools_by_category[category]])
        
        # 添加未分类的工具
        for category, category_tools in tools_by_category.items():
            if category not in category_order:
                result.extend([tool.to_dict() for tool in category_tools])
        
        return result
    else:
        return [tool.to_dict() for tool in tools]
```

**注意**：
- 类别分组只是为了**组织工具**，让 LLM 更容易理解工具结构
- **不暗示任何优先级**，LLM 应该根据工具描述选择，而不是位置
- 类别内保持稳定顺序，避免随机性带来的不确定性

#### 1.5.2 移除硬编码的优先级规则

**当前问题**：在 system_prompt 中有硬编码的工具选择规则，如：
- "当用户要求'打开'、'访问'、'查看'网站时，**必须使用** browser 工具"
- "当用户要求'搜索'、'查找'网络信息时，**使用** google_search"

这些规则**限制了 LLM 的自由决策能力**，应该移除。

**解决方案**：
1. **移除硬编码规则**：从 system_prompt 中删除所有 "必须使用"、"优先使用" 等规则
2. **增强工具描述**：在工具的描述中说明使用场景，让 LLM 自主判断
3. **明确选择原则**：在 system_prompt 中说明 LLM 应该根据任务和工具描述选择

```python
# backend/core/agent/orchestrator.py

# 移除硬编码规则，改为在工具描述中说明使用场景
system_prompt = f"""你是一个智能助手，能够帮助用户解决各种问题。

【重要】工具选择原则：

1. **根据任务需求选择工具**：
   - 仔细阅读每个工具的描述、使用场景和限制
   - 选择最直接、最合适的工具来完成用户任务
   - 工具列表的顺序**不代表优先级**，不要被位置影响

2. **工具选择标准**：
   - 工具的功能描述是否匹配任务需求
   - 工具的参数是否满足任务要求
   - 工具的限制是否会影响任务执行
   - 工具的输出格式是否满足后续处理需求

3. **自主决策**：
   - 根据任务和工具描述自主选择，不要依赖硬编码规则
   - 如果多个工具都可以完成任务，选择最直接、最合适的
   - 如果工具执行失败，可以尝试其他相关工具

{tool_selection_guide}
"""
```

#### 1.5.3 在工具描述中说明使用场景

**关键**：将硬编码规则转换为工具描述的一部分，让 LLM 在阅读工具描述时自然理解：

```python
# backend/core/agent/tools/builtin/browser_tool.py

class BrowserTool(Tool):
    def __init__(self):
        super().__init__(
            name="browser",
            description=(
                "访问网站并获取网页内容，支持 JavaScript 渲染的动态网页。"
                "\n\n"
                "【使用场景】"
                "\n- 当用户要求'打开'、'访问'、'查看'网站时"
                "\n- 当用户提供具体的网站地址（URL）时"
                "\n- 当需要获取网页的完整内容（包括动态加载的内容）时"
                "\n\n"
                "【与其他工具的区别】"
                "\n- 与 google_search 的区别：browser 用于访问特定网站，google_search 用于搜索网络信息"
                "\n- 如果用户提供的是搜索关键词而不是具体 URL，应该使用 google_search"
            ),
            parameters=[...],
            metadata=ToolMetadata(
                category="web",
                use_cases=[
                    "访问特定网站并获取内容",
                    "查看网页的文本、链接、图片等信息",
                    "提取网页中的特定信息",
                    "浏览需要 JavaScript 渲染的动态网页"
                ],
                ...
            )
        )
```

这样，LLM 在阅读工具描述时就能自然理解使用场景，而不需要硬编码规则。

### 阶段 1.6：选择合适的决策模型（重要！）

**问题**：当前系统使用 `deepseek-chat` 来做工具选择决策，但工具选择决策（编排）需要**推理和编程能力**，而不是简单的对话能力。

**工具选择决策对模型的要求**：
1. **推理能力强**：理解任务需求，分析工具匹配关系，制定执行策略
2. **编程能力强**：理解 LLM 可能编写代码调用工具的场景，理解工具的参数和输出格式
3. **策略制定能力**：能够规划多步骤执行，处理工具组合
4. **问题解决能力**：能够处理异常情况，调整执行计划

**Chat 模型不适合编排的原因**：
- Chat 模型适合**执行**任务，而不是**规划**任务
- 编排任务本质上是**规划型任务**，需要推理能力
- 工具选择需要理解代码调用场景，需要编程能力

#### 1.6.1 推荐的决策模型（按优先级排序）

**第一优先级（推荐）**：推理+编程能力强

1. **`deepseek-reasoner`**（DeepSeek，强烈推荐）
   - ✅ 推理能力强：适合策略制定、多步骤分析、问题解决
   - ✅ 适合编排任务：理解任务结构、依赖关系、执行规划
   - ✅ 理解工具组合：能够协调多个工具的执行
   - ✅ 理解任务分解：能够将复杂任务分解为多个子任务
   - ⚠️ 速度可能较慢
   - ⚠️ 成本可能较高
   - **推荐场景**：工具选择决策、编排任务（默认推荐）

2. **`deepseek-coder`**（DeepSeek）
   - ✅ 编程能力强：理解代码调用工具的场景
   - ✅ 理解工具参数和输出格式：严格理解工具的输入输出定义
   - ✅ 理解代码生成：能够生成调用工具的代码
   - ✅ 速度快
   - ✅ 成本低
   - ⚠️ 推理能力相对较弱（但编程能力可以弥补部分推理需求）
   - **推荐场景**：如果任务主要是代码生成或需要理解代码调用场景

3. **`bailian-qwq-plus`**（百炼平台）
   - ✅ 推理能力强：达到 DeepSeek-R1 满血版水平
   - ✅ 支持深度思考
   - ✅ 适合复杂推理任务
   - ⚠️ 速度可能较慢
   - ⚠️ 成本可能较高
   - **推荐场景**：需要最强推理能力时

4. **`bailian-kimi-k2-thinking`**（百炼平台，强烈推荐）
   - ✅ **卓越的编码能力**：月之暗面提供的开源模型，专为编码优化
   - ✅ **卓越的工具调用能力**：理解工具参数和输出格式，适合工具选择决策
   - ✅ **支持思考过程**：能够输出思考过程，推理能力强
   - ✅ **推理+编程结合**：同时具备推理和编程能力，非常适合编排任务
   - **推荐场景**：工具选择决策、编排任务、代码相关任务（强烈推荐）

5. **`bailian-qwen3-coder-plus-2025-09-23`**（百炼平台）
   - ✅ 编程能力强：强大的 Coding Agent 能力
   - ✅ 理解工具调用：理解代码调用工具的场景
   - ✅ 仓库级别理解：能够理解大型代码库
   - ⚠️ 推理能力相对较弱
   - **推荐场景**：需要强编程能力且需要理解代码调用场景时

6. **`deepseek-v3`**（DeepSeek）
   - ✅ 最新模型，能力强
   - ✅ 推理和编程能力都强
   - ⚠️ 成本可能较高
   - **推荐场景**：需要最新最强能力时

**第二优先级（可选）**：推理能力强，但可能缺少编程能力

7. **`deepseek-r1`**（DeepSeek）
   - ✅ 支持思考过程
   - ✅ 推理能力强
   - ⚠️ 速度较慢
   - ⚠️ 成本较高
   - **推荐场景**：需要思考过程的复杂推理

8. **`openai-o3`**（OpenAI，如果成本可接受）
   - ✅ 支持思考过程
   - ✅ 推理能力强
   - ⚠️ 成本高
   - **推荐场景**：需要最强推理能力且成本可接受时

9. **`bailian-deepseek-v3.2`**（百炼平台）
   - ✅ 支持深度思考
   - ✅ 推理能力强
   - ⚠️ 成本可能较高
   - **推荐场景**：需要深度思考的复杂任务

**不推荐用于编排的模型**：
- ❌ `deepseek-chat`：推理能力弱，不适合编排任务（适合执行，不适合规划）
- ❌ `qwen-turbo`：主要是对话模型，推理能力弱
- ❌ `gemini-2.5-flash`：速度快但推理能力相对较弱
- ❌ `claude-3-5-haiku`：速度快但推理能力相对较弱

**为什么 Chat 模型不适合编排**：
- Chat 模型适合**执行**任务（如生成文本、回答问题）
- 编排任务是**规划型任务**，需要：
  - 推理能力：理解任务结构、依赖关系、工具匹配
  - 编程能力：理解代码调用工具的场景、工具参数和输出格式
  - 策略制定：选择最佳执行路径、协调多个工具
- Chat 模型的推理和编程能力都较弱，不适合编排任务

#### 1.6.2 模型选择策略

```python
# backend/core/agent/orchestrator.py

# 环境变量配置
TOOL_SELECTION_MODEL = os.getenv("TOOL_SELECTION_MODEL", "deepseek-reasoner")
# 可选值：
# - deepseek-reasoner（推荐，默认）：推理能力强，适合编排任务
# - bailian-kimi-k2-thinking（强烈推荐）：编码和工具调用能力强，支持思考过程
# - deepseek-coder：编程能力强，适合代码调用场景
# - bailian-qwq-plus：推理能力强，达到 DeepSeek-R1 水平
# - deepseek-v3：最新模型，能力强
# - deepseek-r1：支持思考过程
# - openai-o3：支持思考过程（成本高）

async def _select_model(self, task: str) -> str:
    """
    使用决策模型智能选择最适合的执行模型
    
    Args:
        task: 用户任务
        
    Returns:
        选定的模型名称
    """
    # 使用配置的决策模型进行分析（推荐使用推理模型）
    decision_model = os.getenv("TOOL_SELECTION_MODEL", "deepseek-reasoner")
    
    model_selection_prompt = f"""分析以下任务，决定应该使用哪个模型：

任务：{task}

可选模型：
1. deepseek-chat: 适用于日常对话、文本生成、翻译、信息检索等一般性任务
2. deepseek-reasoner: 适用于需要复杂推理的任务，如数学推理、逻辑分析、策略制定、问题解决等
3. deepseek-coder: 适用于代码生成、代码补全、代码修复、代码审查、编程相关任务，以及简单的命令执行（如 ls、cat、cd 等）

重要提示：
- 如果任务是执行简单的系统命令（如显示文件、查看目录、执行脚本等），应该使用 deepseek-coder
- 如果任务需要复杂的逻辑推理、多步骤分析、策略制定，使用 deepseek-reasoner
- 如果任务只是简单的命令执行，不要使用 deepseek-reasoner，避免过度思考

请只返回模型名称（deepseek-chat、deepseek-reasoner 或 deepseek-coder），不要返回其他内容。"""

    try:
        # 临时切换到决策模型进行分析
        original_model = self.llm_service.model
        self.llm_service.set_model(decision_model)
        
        # 使用决策模型分析
        analysis = await self.llm_service.chat(
            system_prompt="你是一个模型选择助手，根据任务类型选择最合适的模型。",
            user_prompt=model_selection_prompt
        )
        
        # 恢复原模型
        self.llm_service.set_model(original_model)
        
        # 解析返回的模型名称
        analysis = analysis.strip().lower()
        if "deepseek-reasoner" in analysis or "reasoner" in analysis:
            return "deepseek-reasoner"
        elif "deepseek-coder" in analysis or "coder" in analysis:
            return "deepseek-coder"
        else:
            return "deepseek-chat"
            
    except Exception as e:
        logger.warning(f"模型选择失败，使用默认模型: {e}")
        return "deepseek-chat"
```

#### 1.6.3 环境变量配置

在 `env.example` 中添加：

```bash
# 工具选择决策模型（可选）
# 说明：用于工具选择决策和编排任务的模型
# 工具选择决策需要推理和编程能力，而不是简单的对话能力
# 可选值：
#   - deepseek-reasoner（推荐，默认）：推理能力强，适合编排任务、策略制定
#   - bailian-kimi-k2-thinking（强烈推荐）：编码和工具调用能力强，支持思考过程
#   - deepseek-coder：编程能力强，适合理解代码调用工具的场景
#   - bailian-qwq-plus（百炼平台）：推理能力强，达到 DeepSeek-R1 水平
#   - deepseek-v3：最新模型，推理和编程能力都强
#   - deepseek-r1：支持思考过程，推理能力强
#   - openai-o3：支持思考过程，推理能力强（成本高）
# 默认值：deepseek-reasoner
# 注意：
#   - 工具选择决策是编排任务，需要推理能力，不推荐使用 chat 模型
#   - 如果任务主要是代码生成或需要理解代码调用场景，可以使用 deepseek-coder
#   - 如果需要最强推理能力，可以使用 bailian-qwq-plus 或 deepseek-r1
#   - 如果成本是主要考虑因素，可以使用 deepseek-coder（速度快、成本低）
TOOL_SELECTION_MODEL=deepseek-reasoner
```

#### 1.6.4 模型选择建议

**编排任务（强烈推荐）**：
- `bailian-kimi-k2-thinking`：编码和工具调用能力强，支持思考过程
  - 卓越的编码能力：理解代码调用工具的场景
  - 卓越的工具调用能力：理解工具参数和输出格式
  - 支持思考过程：推理能力强
  - **最适合工具选择决策和编排任务**

**编排任务（默认推荐）**：
- `deepseek-reasoner`：推理能力强，适合工具选择决策和编排任务
  - 理解任务结构、依赖关系
  - 制定执行策略
  - 协调多个工具

**代码调用场景（推荐）**：
- `deepseek-coder`：编程能力强，理解工具参数和输出格式，速度快、成本低
  - 理解代码调用工具的场景
  - 理解严格的输入输出定义
  - 生成调用工具的代码

**推理+编程结合（最佳）**：
- `bailian-kimi-k2-thinking`：编码和工具调用能力强，支持思考过程（强烈推荐）
- `deepseek-v3`：最新模型，推理和编程能力都强
- `bailian-qwen3-coder-plus-2025-09-23`：编程能力强，适合 Coding Agent 场景

**最强推理能力**：
- `bailian-qwq-plus`：达到 DeepSeek-R1 水平，推理能力强
- `deepseek-r1`：支持思考过程，推理能力强

**不推荐用于编排**：
- ❌ `deepseek-chat`：推理能力弱，不适合编排任务（适合执行，不适合规划）
- ❌ `qwen-turbo`：主要是对话模型，推理能力弱
- ❌ `gemini-2.5-flash`：速度快但推理能力相对较弱

### 阶段 2：优化 System Prompt

#### 2.1 构建动态工具选择指南

```python
# backend/core/agent/orchestrator.py

def _build_tool_selection_guide(self) -> str:
    """构建工具选择指南（动态生成）"""
    tools = self.tool_registry.list_tools()
    tool_objects = [self.tool_registry.get_tool(name) for name in tools]
    
    # 按类别分组
    tools_by_category = {}
    for tool in tool_objects:
        category = tool.metadata.category if tool.metadata else "general"
        if category not in tools_by_category:
            tools_by_category[category] = []
        tools_by_category[category].append(tool)
    
    guide = "【工具选择指南】\n\n"
    
    for category, category_tools in tools_by_category.items():
        guide += f"## {category.upper()} 类别工具：\n\n"
        for tool in category_tools:
            guide += f"### {tool.name}\n"
            guide += f"- 描述：{tool.description}\n"
            
            if tool.metadata and tool.metadata.use_cases:
                guide += f"- 适用场景：{', '.join(tool.metadata.use_cases[:2])}\n"
            
            if tool.metadata and tool.metadata.related_tools:
                guide += f"- 相关工具：{', '.join(tool.metadata.related_tools)}\n"
            
            guide += "\n"
    
    guide += """
【工具选择原则】

1. **任务分析**：
   - 首先分析用户任务的核心需求
   - 确定需要什么类型的信息或操作
   - 考虑任务的复杂度和所需步骤

2. **工具匹配**：
   - 根据任务类型选择最合适的工具类别
   - 优先选择直接满足需求的工具
   - 考虑工具的限制和最佳实践

3. **工具组合**：
   - 复杂任务可能需要多个工具协作
   - 先使用搜索/查找工具获取信息，再使用操作工具执行任务
   - 例如：先 file_search 找到文件，再 execute_code 处理文件

4. **多轮迭代**：
   - 如果第一次工具调用结果不完整，继续使用其他工具
   - 根据工具返回的结果调整策略
   - 如果工具调用失败，尝试替代方案

5. **错误处理**：
   - 如果工具调用失败，分析失败原因
   - 尝试使用相关工具或替代方案
   - 如果所有尝试都失败，明确告诉用户无法完成的原因

【工具组合示例】

- 任务："查找并处理某个文件"
  → 1. file_search（查找文件）
  → 2. execute_code（处理文件）

- 任务："搜索某个主题并总结"
  → 1. google_search（搜索信息）
  → 2. 直接总结（不需要额外工具）

- 任务："访问网站并提取数据"
  → 1. browser（访问网站）
  → 2. 直接提取（从返回内容中提取）
"""
    
    return guide
```

#### 2.2 更新 System Prompt

```python
# backend/core/agent/orchestrator.py

async def stream_process(self, task: str, session_id: Optional[str] = None, ...):
    # ... 现有代码 ...
    
    # 构建增强的 system_prompt
    tool_selection_guide = self._build_tool_selection_guide()
    
    system_prompt = f"""你是一个智能助手，能够帮助用户解决各种问题。当用户提供历史对话记录时，请基于历史对话内容来理解和回答当前问题。

重要原则：
- 对于简单的命令执行任务（如显示文件、查看目录、执行脚本等），严格按照用户指令执行，不要添加额外的探索、检查或推理
- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作
- 不要过度思考，不要添加用户没有要求的额外功能

{tool_selection_guide}

【多轮对话策略】

1. **第一轮**：分析任务，选择最合适的工具开始执行
2. **根据结果**：
   - 如果结果完整，直接返回给用户
   - 如果结果不完整，继续使用其他工具补充信息
   - 如果工具调用失败，尝试替代方案
3. **持续迭代**：直到任务完成或明确无法完成
4. **保持上下文**：记住之前的工具调用结果，避免重复调用

【工具调用最佳实践】

- 优先使用最直接的工具（如 file_search 而不是先 list_files 再搜索）
- 如果工具返回大量数据，考虑分页或过滤
- 如果工具调用失败，检查参数是否正确，或尝试相关工具
- 对于需要多步骤的任务，可以连续调用多个工具
"""
```

### 阶段 3：增强工具调用循环

#### 3.1 添加工具调用历史记录

```python
# backend/core/agent/orchestrator.py

class ToolCallHistory:
    """工具调用历史记录"""
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.failed_calls: List[Dict[str, Any]] = []
    
    def record_call(self, tool_name: str, args: Dict, result: ToolResult):
        """记录工具调用"""
        call_info = {
            "tool_name": tool_name,
            "args": args,
            "success": result.success,
            "timestamp": time.time()
        }
        self.calls.append(call_info)
        
        if not result.success:
            call_info["error"] = result.error
            self.failed_calls.append(call_info)
    
    def get_recent_calls(self, tool_name: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """获取最近的工具调用"""
        calls = self.calls[-limit:] if not tool_name else [
            c for c in self.calls if c["tool_name"] == tool_name
        ][-limit:]
        return calls
    
    def has_failed_recently(self, tool_name: str, within_seconds: int = 60) -> bool:
        """检查某个工具是否最近失败过"""
        now = time.time()
        for call in self.failed_calls:
            if call["tool_name"] == tool_name:
                if now - call["timestamp"] < within_seconds:
                    return True
        return False

async def _chat_with_tools_stream(self, ...):
    # ... 现有代码 ...
    
    tool_call_history = ToolCallHistory()  # 新增
    
    max_iterations = 100
    for iteration in range(max_iterations):
        # ... 现有代码 ...
        
        # 检查工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                
                # 检查是否最近失败过（避免重复失败）
                if tool_call_history.has_failed_recently(tool_name):
                    # 提示 LLM 该工具最近失败过，建议使用替代方案
                    yield f"⚠️ 警告：{tool_name} 工具最近调用失败，建议检查参数或使用替代工具。\n"
                
                # ... 执行工具调用 ...
                
                # 记录工具调用历史
                tool_call_history.record_call(tool_name, tool_args, tool_result)
                
                # ... 现有代码 ...
```

#### 3.2 优化工具调用循环策略

```python
# backend/core/agent/orchestrator.py

async def _chat_with_tools_stream(self, ...):
    # ... 现有代码 ...
    
    # 添加循环策略提示
    strategy_hints = []
    
    max_iterations = 100
    for iteration in range(max_iterations):
        # ... 现有代码 ...
        
        # 如果已经多次迭代，给 LLM 提示
        if iteration > 10:
            # 检查是否有重复的工具调用
            recent_calls = tool_call_history.get_recent_calls(limit=5)
            tool_names = [c["tool_name"] for c in recent_calls]
            if len(set(tool_names)) < len(tool_names):
                # 有重复调用
                strategy_hints.append(
                    "检测到重复的工具调用，建议尝试不同的方法或工具。"
                )
        
        # 如果多次失败，建议调整策略
        if len(tool_call_history.failed_calls) > 3:
            strategy_hints.append(
                "多个工具调用失败，建议重新分析任务需求或尝试不同的工具组合。"
            )
        
        # 将策略提示添加到 user_prompt
        if strategy_hints:
            enhanced_user_prompt = user_prompt + "\n\n【策略提示】\n" + "\n".join(strategy_hints)
            strategy_hints = []  # 清空提示
        else:
            enhanced_user_prompt = user_prompt
        
        # ... 继续 LLM 调用 ...
```

### 阶段 4：工具使用反馈和学习（可选）

#### 4.1 工具使用统计

```python
# backend/core/agent/tools/registry.py

class ToolUsageStats:
    """工具使用统计"""
    
    def __init__(self):
        self.stats: Dict[str, Dict[str, Any]] = {}
    
    def record_usage(self, tool_name: str, success: bool, duration: float):
        """记录工具使用"""
        if tool_name not in self.stats:
            self.stats[tool_name] = {
                "total_calls": 0,
                "success_calls": 0,
                "failed_calls": 0,
                "avg_duration": 0.0,
                "total_duration": 0.0
            }
        
        stats = self.stats[tool_name]
        stats["total_calls"] += 1
        if success:
            stats["success_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["total_calls"]
    
    def get_success_rate(self, tool_name: str) -> float:
        """获取工具成功率"""
        if tool_name not in self.stats:
            return 1.0
        stats = self.stats[tool_name]
        if stats["total_calls"] == 0:
            return 1.0
        return stats["success_calls"] / stats["total_calls"]
    
    def get_recommended_tools(self, category: str) -> List[str]:
        """获取推荐工具（基于成功率）"""
        # 可以根据统计信息推荐工具
        pass
```

#### 4.2 工具选择建议

```python
# backend/core/agent/orchestrator.py

def _get_tool_recommendations(self, task: str) -> List[str]:
    """根据任务和工具使用统计，推荐工具"""
    # 可以基于任务关键词、工具使用历史等推荐
    # 这是一个可选的高级功能
    pass
```

## 实施优先级

### 高优先级（立即实施）

1. **阶段 1.1**：扩展 Tool 基类，添加元数据支持
2. **阶段 2.1**：构建动态工具选择指南
3. **阶段 2.2**：更新 System Prompt，集成工具选择指南

### 中优先级（后续实施）

4. **阶段 1.2**：为现有工具添加元数据
5. **阶段 3.1**：添加工具调用历史记录
6. **阶段 3.2**：优化工具调用循环策略

### 低优先级（可选）

7. **阶段 4**：工具使用反馈和学习机制

## 预期效果

### 1. 工具选择更准确

- **更详细的工具描述**：LLM 能更好地理解每个工具的用途和限制
- **使用场景和示例**：帮助 LLM 快速判断是否应该使用某个工具
- **工具组合策略**：指导 LLM 如何组合多个工具完成任务

### 2. 工具调用更高效

- **避免重复失败**：记录工具调用历史，避免重复调用最近失败的工具
- **策略调整**：根据工具调用结果动态调整策略
- **错误处理**：更好的错误处理和替代方案

### 3. 系统更智能

- **动态指南**：工具选择指南根据实际注册的工具动态生成
- **上下文感知**：考虑工具使用历史，提供更智能的建议
- **可扩展性**：新工具只需添加元数据，就能自动获得完整的工具选择支持

## 总结

这个增强方案的核心思想是：

1. **增强工具描述**：让 LLM 更清楚地了解每个工具的能力和限制
2. **优化选择策略**：通过动态生成的指南和策略提示，帮助 LLM 做出更好的工具选择
3. **改进调用循环**：记录历史、避免重复失败、动态调整策略
4. **持续学习**（可选）：通过使用统计，不断优化工具推荐

这样可以让 LLM 更自由、更智能地选择和使用工具，通过多轮对话自主完成任务。

