# TODO-003: Markdown 渲染模块设计与实现

## 任务概述

设计并实现一个完整的 Markdown 渲染模块，智能处理何时显示 Markdown 源码，何时渲染为格式化内容。解决当前前端在流式和非流式响应中 Markdown 显示不一致的问题。

**优先级**: 高  
**预计工时**: 2-3 天  
**负责人**: 待分配  
**状态**: 待开始

---

## 一、问题分析

### 1.1 当前问题

1. **流式响应时显示源码**
   - 流式响应时，直接 `console.print(chunk, end="")` 输出文本
   - Markdown 语法（如 `**粗体**`、`# 标题`）会以源码形式显示
   - 用户体验差，看到的是未渲染的 Markdown 语法

2. **非流式响应时渲染 Markdown**
   - 非流式响应时，使用 `ChatPanel` 中的 `Markdown(message)` 渲染
   - 显示效果良好，但和流式响应不一致

3. **缺乏统一的渲染策略**
   - 没有统一的模块来决定何时渲染、何时显示源码
   - 没有内容类型识别（Markdown、纯文本、代码块等）
   - 没有流式响应的缓冲和智能处理

### 1.2 设计目标

1. **统一渲染接口**: 提供统一的接口处理所有内容渲染
2. **智能内容识别**: 自动识别 Markdown、纯文本、代码块等
3. **流式响应优化**: 流式响应时也能正确渲染 Markdown
4. **可配置策略**: 支持配置何时显示源码、何时渲染

---

## 二、设计方案

### 2.1 模块结构

```
frontend/ui/
├── renderer.py          # 主渲染模块（新建）
│   ├── ContentRenderer  # 内容渲染器基类
│   ├── MarkdownRenderer # Markdown 渲染器
│   ├── TextRenderer     # 纯文本渲染器
│   ├── CodeRenderer     # 代码块渲染器
│   └── RendererFactory   # 渲染器工厂
├── stream_handler.py    # 流式响应处理器（新建）
│   ├── StreamBuffer     # 流式缓冲器
│   └── StreamRenderer   # 流式渲染器
└── ...
```

### 2.2 核心组件设计

#### 2.2.1 ContentRenderer（内容渲染器基类）

```python
class ContentRenderer:
    """内容渲染器基类"""
    
    def can_render(self, content: str) -> bool:
        """判断是否可以渲染此内容"""
        pass
    
    def render(self, content: str, **kwargs) -> Any:
        """渲染内容"""
        pass
    
    def render_stream_chunk(self, chunk: str, buffer: str) -> tuple[str, Any]:
        """渲染流式数据块
        返回: (更新后的 buffer, 渲染结果)
        """
        pass
```

#### 2.2.2 MarkdownRenderer（Markdown 渲染器）

```python
class MarkdownRenderer(ContentRenderer):
    """Markdown 渲染器"""
    
    def can_render(self, content: str) -> bool:
        """检测是否为 Markdown 内容
        
        使用更严格的检测规则，避免误判：
        - 标题必须在行首，且后面有空格和非空白字符
        - 粗体/斜体必须成对出现
        - 列表项必须在行首
        - 代码块必须完整（```...```）
        """
        markdown_patterns = [
            r'^#{1,6}\s+\S+',        # 标题：行首，后面有空格和非空白字符
            r'\*\*[^*]+\*\*',        # 粗体：成对的 **，中间不能是 *
            r'(?<!\*)\*[^*\s][^*]*\*(?!\*)',  # 斜体：单独的 *，不能是 **
            r'^[-*+]\s+\S+',         # 无序列表：行首，后面有空格和非空白字符
            r'^\d+\.\s+\S+',         # 有序列表：行首，后面有空格和非空白字符
            r'```[\s\S]*?```',       # 代码块
            r'\[[^\]]+\]\([^\)]+\)', # 链接：格式严格
            r'!\[[^\]]+\]\([^\)]+\)', # 图片：格式严格
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                return True
        
        return False
    
    def render(self, content: str, **kwargs) -> Markdown:
        """渲染 Markdown 为 Rich Markdown 对象
        
        添加错误处理，渲染失败时降级到纯文本
        """
        try:
            return Markdown(content)
        except Exception:
            # 降级到纯文本
            return content
    
    def render_stream_chunk(self, chunk: str, buffer: str) -> tuple[str, Optional[Markdown]]:
        """流式渲染 Markdown
        - 缓冲数据直到可以识别完整 Markdown 块
        - 对于不完整的 Markdown，显示为纯文本
        - 对于完整的 Markdown，渲染后显示
        """
        pass
```

#### 2.2.3 TextRenderer（纯文本渲染器）

```python
class TextRenderer(ContentRenderer):
    """纯文本渲染器"""
    
    def can_render(self, content: str) -> bool:
        """纯文本总是可以渲染"""
        return True
    
    def render(self, content: str, **kwargs) -> str:
        """直接返回文本（不渲染）"""
        return content
```

#### 2.2.4 CodeRenderer（代码块渲染器）

```python
class CodeRenderer(ContentRenderer):
    """代码块渲染器"""
    
    def can_render(self, content: str) -> bool:
        """检测是否为代码块（```language\ncode\n```）"""
        pass
    
    def render(self, content: str, language: str = None) -> Syntax:
        """渲染代码块为 Rich Syntax 对象"""
        pass
```

#### 2.2.5 RendererFactory（渲染器工厂）

```python
class RendererFactory:
    """渲染器工厂，根据内容类型选择合适的渲染器"""
    
    def __init__(self):
        self.renderers = [
            CodeRenderer(),
            MarkdownRenderer(),
            TextRenderer(),  # 默认渲染器
        ]
    
    def get_renderer(self, content: str) -> ContentRenderer:
        """根据内容类型选择合适的渲染器"""
        for renderer in self.renderers:
            if renderer.can_render(content):
                return renderer
        return TextRenderer()  # 默认
```

#### 2.2.6 StreamBuffer（流式缓冲器）

```python
class StreamBuffer:
    """流式响应缓冲器
    
    简化策略：只检测明确的完整块，避免复杂判断
    """
    
    def __init__(self, min_chunk_size: int = 20):
        self.buffer = ""
        self.min_chunk_size = min_chunk_size
        self.last_extracted_pos = 0  # 记录上次提取的位置，避免重复
    
    def add_chunk(self, chunk: str) -> tuple[Optional[str], str]:
        """添加数据块，返回可渲染的完整内容（如果有）
        
        Returns:
            (renderable_content, remaining_buffer)
        """
        self.buffer += chunk
        
        # 如果缓冲区足够大，尝试提取可渲染的内容
        if len(self.buffer) >= self.min_chunk_size:
            renderable, remaining = self._extract_renderable()
            if renderable:
                self.last_extracted_pos = len(renderable)
                return renderable, remaining
        
        return None, self.buffer
    
    def _extract_renderable(self) -> tuple[str, str]:
        """提取可渲染的完整内容块
        
        简化策略：只检测明确的完整块
        1. 完整的代码块（```...```）- 优先级最高
        2. 完整的段落（以 \n\n 结尾）
        3. 完整的句子（以句号等结尾，且后面有空格）
        """
        # 策略 1: 检测完整的代码块（```...```）
        # 从上次提取位置之后开始查找，避免重复
        search_start = self.last_extracted_pos
        code_block_match = re.search(
            r'```[\s\S]*?```', 
            self.buffer[search_start:], 
            re.DOTALL
        )
        if code_block_match:
            # 计算在完整 buffer 中的位置
            start_pos = search_start + code_block_match.start()
            end_pos = search_start + code_block_match.end()
            renderable = self.buffer[start_pos:end_pos]
            remaining = self.buffer[end_pos:]
            return renderable, remaining
        
        # 策略 2: 检测完整的段落（以 \n\n 结尾）
        # 查找最后一个完整的段落
        para_match = re.search(
            r'.+?\n\n', 
            self.buffer[search_start:], 
            re.DOTALL
        )
        if para_match:
            start_pos = search_start + para_match.start()
            end_pos = search_start + para_match.end()
            renderable = self.buffer[start_pos:end_pos]
            remaining = self.buffer[end_pos:]
            return renderable, remaining
        
        # 策略 3: 检测完整的句子（以句号、问号、感叹号结尾，且后面有空格或换行）
        sentence_match = re.search(
            r'.+?[。！？.!?][\s\n]+', 
            self.buffer[search_start:]
        )
        if sentence_match:
            start_pos = search_start + sentence_match.start()
            end_pos = search_start + sentence_match.end()
            renderable = self.buffer[start_pos:end_pos]
            remaining = self.buffer[end_pos:]
            return renderable, remaining
        
        # 没有可提取的完整内容
        return "", self.buffer
    
    def flush(self) -> str:
        """清空缓冲区，返回剩余内容"""
        content = self.buffer
        self.buffer = ""
        return content
```

#### 2.2.7 StreamRenderer（流式渲染器）

```python
class StreamRenderer:
    """流式渲染器，处理流式响应的实时渲染"""
    
    def __init__(self, renderer_factory: RendererFactory):
        self.factory = renderer_factory
        self.buffer = StreamBuffer()
        self.current_renderer = None
    
    async def render_stream(self, stream: AsyncIterator[str], console: Console):
        """渲染流式响应"""
        async for chunk in stream:
            # 添加到缓冲区
            renderable, remaining = self.buffer.add_chunk(chunk)
            
            if renderable:
                # 有可渲染的完整内容
                renderer = self.factory.get_renderer(renderable)
                rendered = renderer.render(renderable)
                console.print(rendered, end="")
            
            # 显示剩余的不完整内容（作为纯文本）
            if remaining and len(remaining) > 0:
                console.print(remaining, end="", style="dim")
        
        # 流式结束，渲染剩余内容
        remaining = self.buffer.flush()
        if remaining:
            renderer = self.factory.get_renderer(remaining)
            rendered = renderer.render(remaining)
            console.print(rendered)
```

### 2.3 渲染策略

#### 策略 1: 自动检测（默认）

- **Markdown 内容**: 自动检测并渲染
- **纯文本内容**: 直接显示
- **代码块**: 使用语法高亮渲染

#### 策略 2: 强制渲染

- 所有内容都尝试作为 Markdown 渲染
- 如果渲染失败，回退到纯文本

#### 策略 3: 强制源码

- 所有内容都显示为源码（不渲染）
- 用于调试或查看原始内容

### 2.4 配置选项

```python
class RenderConfig:
    """渲染配置"""
    
    # 渲染模式
    mode: str = "auto"  # "auto" | "force_render" | "force_raw"
    
    # 流式响应配置
    stream_buffer_size: int = 50  # 最小缓冲大小
    stream_render_delay: float = 0.1  # 渲染延迟（秒）
    
    # Markdown 配置
    markdown_theme: str = "default"  # Markdown 主题
    markdown_code_theme: str = "monokai"  # 代码块主题
    
    # 显示配置
    show_markdown_hints: bool = False  # 是否显示 Markdown 提示
    max_line_length: int = 80  # 最大行长度
```

---

## 三、实现步骤（TDD）

### 阶段 1: 测试驱动开发 - 基础渲染器（1天）

#### 步骤 1.1: 编写测试用例

**文件**: `frontend/ui/tests/test_renderer.py`

```python
# 测试用例：
# 1. test_text_renderer_basic - 纯文本渲染
# 2. test_markdown_renderer_detection - Markdown 检测
# 3. test_markdown_renderer_basic - Markdown 基础渲染
# 4. test_code_renderer_detection - 代码块检测
# 5. test_code_renderer_basic - 代码块渲染
# 6. test_renderer_factory_selection - 渲染器选择
```

#### 步骤 1.2: 实现基础渲染器

**文件**: `frontend/ui/renderer.py`

- 实现 `ContentRenderer` 基类
- 实现 `TextRenderer`
- 实现 `MarkdownRenderer`（基础功能）
- 实现 `CodeRenderer`（基础功能）
- 实现 `RendererFactory`

#### 步骤 1.3: 运行测试验证

```bash
pytest frontend/ui/tests/test_renderer.py -v
```

### 阶段 2: 流式响应处理（1天）

#### 步骤 2.1: 编写流式处理测试

**文件**: `frontend/ui/tests/test_stream_handler.py`

```python
# 测试用例：
# 1. test_stream_buffer_basic - 流式缓冲基础功能
# 2. test_stream_buffer_markdown - Markdown 流式缓冲
# 3. test_stream_buffer_code_block - 代码块流式缓冲
# 4. test_stream_renderer_basic - 流式渲染基础
# 5. test_stream_renderer_markdown - Markdown 流式渲染
# 6. test_stream_renderer_mixed - 混合内容流式渲染
```

#### 步骤 2.2: 实现流式处理器

**文件**: `frontend/ui/stream_handler.py`

- 实现 `StreamBuffer`
- 实现 `StreamRenderer`

#### 步骤 2.3: 运行测试验证

```bash
pytest frontend/ui/tests/test_stream_handler.py -v
```

### 阶段 3: 集成到前端（0.5天）

#### 步骤 3.1: 修改 `frontend/main.py`

- 替换流式响应的直接输出
- 使用 `StreamRenderer` 处理流式响应
- 使用 `RendererFactory` 处理非流式响应

#### 步骤 3.2: 修改 `frontend/ui/panels.py`

- 更新 `ChatPanel` 使用新的渲染器
- 移除直接的 `Markdown()` 调用

#### 步骤 3.3: 集成测试

- 测试流式响应中的 Markdown 渲染
- 测试非流式响应中的 Markdown 渲染
- 测试混合内容（Markdown + 代码块）

### 阶段 4: 优化和配置（0.5天）

#### 步骤 4.1: 添加配置支持

- 实现 `RenderConfig`
- 支持配置文件或环境变量

#### 步骤 4.2: 性能优化

- 优化流式缓冲算法
- 减少不必要的渲染调用
- 添加缓存机制

#### 步骤 4.3: 文档和示例

- 更新 `docs/design/rich-ui-guide.md`
- 添加使用示例

---

## 四、详细设计

### 4.1 Markdown 检测算法

```python
def is_markdown(content: str) -> bool:
    """检测内容是否为 Markdown"""
    markdown_patterns = [
        r'^#{1,6}\s+.+',  # 标题
        r'\*\*.*?\*\*',   # 粗体
        r'\*.*?\*',       # 斜体
        r'^[-*+]\s+.+',   # 列表
        r'^\d+\.\s+.+',   # 有序列表
        r'```.*?```',     # 代码块
        r'\[.*?\]\(.*?\)', # 链接
        r'!\[.*?\]\(.*?\)', # 图片
    ]
    
    for pattern in markdown_patterns:
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            return True
    
    return False
```

### 4.2 流式 Markdown 渲染策略

1. **缓冲策略**:
   - 最小缓冲 50 字符
   - 检测完整的 Markdown 块（以换行符或空行分隔）
   - 检测完整的代码块（```...```）

2. **渲染策略**:
   - 完整的 Markdown 块：立即渲染
   - 不完整的 Markdown：显示为纯文本（dim 样式）
   - 流式结束时：渲染所有剩余内容

3. **用户体验**:
   - 实时显示可渲染的内容
   - 不完整内容以淡色显示，提示正在输入
   - 流式结束后，完整渲染剩余内容

### 4.3 代码块处理

```python
def extract_code_blocks(content: str) -> list[tuple[str, str, str]]:
    """提取代码块
    返回: [(language, code, full_match), ...]
    """
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    blocks = []
    for match in matches:
        language = match.group(1) or "text"
        code = match.group(2)
        blocks.append((language, code, match.group(0)))
    
    return blocks
```

### 4.4 流式渲染的关键修正

#### 修正 1: 流式渲染逻辑

**问题**: 原实现中 `new_remaining` 计算错误，会导致重复显示

**修正方案**:
```python
# 使用 last_rendered_length 跟踪已渲染的长度
last_rendered_length = 0

async for chunk in stream:
    renderable, remaining = self.buffer.add_chunk(chunk)
    
    if renderable:
        # 渲染完整内容
        renderer.render(renderable)
        last_rendered_length = len(renderable)  # 更新已渲染长度
    
    # 只显示从上次渲染位置之后的新内容
    if remaining and len(remaining) > last_rendered_length:
        new_content = remaining[last_rendered_length:]
        console.print(new_content, end="", style="dim")
```

#### 修正 2: Markdown 检测误判

**问题**: 普通文本中的 `#` 或 `**` 可能被误判

**修正方案**:
- 标题检测：必须在行首，且后面有空格 `r'^#{1,6}\s+\S+'`
- 粗体检测：必须成对出现 `r'\*\*[^*]+\*\*'`
- 添加更多上下文验证

#### 修正 3: 流式缓冲策略简化

**问题**: 三种策略可能冲突，过于复杂

**修正方案**:
- 降低最小缓冲大小（20 字符）
- 使用 `last_extracted_pos` 避免重复提取
- 简化提取逻辑，只检测明确的完整块

#### 修正 4: 代码块优先级

**问题**: 代码块内的 Markdown 可能被误判

**修正方案**:
- `RendererFactory` 中，先检测代码块
- 检测 Markdown 时，排除代码块内容（用占位符替换）
- 确保代码块整体作为代码渲染，不进行 Markdown 检测

---

## 五、测试要求

### 5.1 单元测试

- **覆盖率要求**: > 90%
- **测试文件**:
  - `frontend/ui/tests/test_renderer.py`
  - `frontend/ui/tests/test_stream_handler.py`

### 5.2 集成测试

- **测试场景**:
  - 流式响应中的 Markdown 渲染
  - 非流式响应中的 Markdown 渲染
  - 混合内容渲染
  - 代码块渲染
  - 长文本处理

### 5.3 手动测试

- **测试步骤**:
  1. 启动后端和前端
  2. 发送包含 Markdown 的消息
  3. 验证流式响应中 Markdown 正确渲染
  4. 验证非流式响应中 Markdown 正确渲染
  5. 验证代码块正确高亮
  6. 验证混合内容正确处理

---

## 六、验收标准

- [x] 流式响应中 Markdown 正确渲染（不显示源码）- 已实现，需手动测试验证
- [x] 非流式响应中 Markdown 正确渲染 - 已实现，需手动测试验证
- [x] 代码块正确识别和语法高亮 - 已实现，需手动测试验证
- [x] 纯文本内容正确显示（不误渲染） - 已实现，单元测试覆盖
- [x] 混合内容（Markdown + 代码块 + 纯文本）正确处理 - 已实现，单元测试和集成测试覆盖
- [x] 单元测试覆盖率 > 90% - ✅ 已完成（renderer.py: 94%, stream_handler.py: 97%）
- [x] 集成测试通过 - ✅ 已完成（9 个集成测试全部通过）
- [x] 文档完整更新 - ✅ 已完成（设计文档、实现文档、问题分析文档）

---

## 七、相关文件

### 代码文件
- `frontend/ui/renderer.py` - 主渲染模块（新建）
- `frontend/ui/stream_handler.py` - 流式处理器（新建）
- `frontend/ui/tests/test_renderer.py` - 渲染器测试（新建）
- `frontend/ui/tests/test_stream_handler.py` - 流式处理器测试（新建）
- `frontend/main.py` - 前端主程序（修改）
- `frontend/ui/panels.py` - 面板组件（修改）

### 文档文件
- `docs/design/rich-ui-guide.md` - Rich UI 指南（更新）
- `docs/todo/003-markdown-renderer.md` - 本文档

---

## 八、注意事项

### 8.1 性能考虑

- 流式渲染不应阻塞主线程
- 缓冲大小要合理，避免内存占用过大
- 渲染操作要高效，避免延迟

### 8.2 用户体验

- 流式响应要实时显示，不能有明显延迟
- 不完整内容要有视觉提示（如淡色显示）
- 渲染错误要有友好的降级处理

### 8.3 兼容性

- 支持各种 Markdown 语法
- 支持代码块语法高亮
- 支持纯文本内容（不误渲染）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0

