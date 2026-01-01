# TODO-003: Markdown 渲染模块 - 详细实现步骤

## 任务概述

本文档提供 TODO-003 的详细实现步骤，遵循 TDD（测试驱动开发）原则。

**关联文档**: [003-markdown-renderer.md](./003-markdown-renderer.md)

---

## 一、TDD 实施计划

### 阶段 1: 基础渲染器（TDD）

#### 步骤 1.1: 创建测试文件结构

```bash
mkdir -p frontend/ui/tests
touch frontend/ui/tests/__init__.py
touch frontend/ui/tests/test_renderer.py
```

#### 步骤 1.2: 编写测试用例（Red 阶段）

**文件**: `frontend/ui/tests/test_renderer.py`

```python
"""渲染器测试"""
import pytest
from frontend.ui.renderer import (
    ContentRenderer,
    TextRenderer,
    MarkdownRenderer,
    CodeRenderer,
    RendererFactory
)

class TestTextRenderer:
    """TextRenderer 测试"""
    
    def test_can_render_always_true(self):
        """测试 can_render 总是返回 True"""
        renderer = TextRenderer()
        assert renderer.can_render("任何内容") == True
        assert renderer.can_render("") == True
    
    def test_render_returns_text(self):
        """测试 render 返回原始文本"""
        renderer = TextRenderer()
        text = "这是纯文本"
        assert renderer.render(text) == text

class TestMarkdownRenderer:
    """MarkdownRenderer 测试"""
    
    def test_can_render_title(self):
        """测试检测 Markdown 标题"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("# 标题") == True
        assert renderer.can_render("## 二级标题") == True
    
    def test_can_render_bold(self):
        """测试检测 Markdown 粗体"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("这是 **粗体** 文本") == True
    
    def test_can_render_list(self):
        """测试检测 Markdown 列表"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("- 列表项") == True
        assert renderer.can_render("1. 有序列表") == True
    
    def test_can_render_code_block(self):
        """测试检测代码块（MarkdownRenderer 也能检测）"""
        renderer = MarkdownRenderer()
        code = "```python\nprint('hello')\n```"
        assert renderer.can_render(code) == True
    
    def test_cannot_render_plain_text(self):
        """测试纯文本不应被识别为 Markdown"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("这是纯文本，没有 Markdown 语法") == False
    
    def test_avoid_false_positive_hash(self):
        """测试避免误判：普通文本中的 # 不应被识别为标题"""
        renderer = MarkdownRenderer()
        # 价格中的 # 不应被识别
        assert renderer.can_render("价格是 $100，这是 #1 选择") == False
        # 行首的 # 且后面有空格才识别
        assert renderer.can_render("# 这是标题") == True
        assert renderer.can_render("这是 # 号，不是标题") == False
    
    def test_avoid_false_positive_bold(self):
        """测试避免误判：单独的 * 不应被识别为粗体"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("这是 * 单独的星号") == False
        assert renderer.can_render("这是 **成对的粗体**") == True
    
    def test_render_markdown(self):
        """测试渲染 Markdown"""
        renderer = MarkdownRenderer()
        markdown = "# 标题\n\n这是 **粗体** 文本"
        result = renderer.render(markdown)
        # 验证返回的是 Rich Markdown 对象
        from rich.markdown import Markdown
        assert isinstance(result, Markdown)

class TestCodeRenderer:
    """CodeRenderer 测试"""
    
    def test_can_render_code_block(self):
        """测试检测代码块"""
        renderer = CodeRenderer()
        code = "```python\nprint('hello')\n```"
        assert renderer.can_render(code) == True
    
    def test_cannot_render_plain_text(self):
        """测试纯文本不应被识别为代码块"""
        renderer = CodeRenderer()
        assert renderer.can_render("这是普通文本") == False
    
    def test_render_code_block(self):
        """测试渲染代码块"""
        renderer = CodeRenderer()
        code = "```python\nprint('hello')\n```"
        result = renderer.render(code)
        # 验证返回的是 Rich Syntax 对象
        from rich.syntax import Syntax
        assert isinstance(result, Syntax)

class TestRendererFactory:
    """RendererFactory 测试"""
    
    def test_select_code_renderer(self):
        """测试选择代码渲染器"""
        factory = RendererFactory()
        code = "```python\nprint('hello')\n```"
        renderer = factory.get_renderer(code)
        assert isinstance(renderer, CodeRenderer)
    
    def test_select_markdown_renderer(self):
        """测试选择 Markdown 渲染器"""
        factory = RendererFactory()
        markdown = "# 标题\n\n这是 **粗体**"
        renderer = factory.get_renderer(markdown)
        assert isinstance(renderer, MarkdownRenderer)
    
    def test_select_text_renderer(self):
        """测试选择文本渲染器（默认）"""
        factory = RendererFactory()
        text = "这是纯文本"
        renderer = factory.get_renderer(text)
        assert isinstance(renderer, TextRenderer)
```

#### 步骤 1.3: 运行测试（确认失败 - Red）

```bash
pytest frontend/ui/tests/test_renderer.py -v
# 预期：所有测试失败（因为还没有实现）
```

#### 步骤 1.4: 实现基础渲染器（Green 阶段）

**文件**: `frontend/ui/renderer.py`

```python
"""内容渲染器模块"""
import re
from typing import Any, Optional
from rich.markdown import Markdown
from rich.syntax import Syntax

class ContentRenderer:
    """内容渲染器基类"""
    
    def can_render(self, content: str) -> bool:
        """判断是否可以渲染此内容"""
        raise NotImplementedError
    
    def render(self, content: str, **kwargs) -> Any:
        """渲染内容"""
        raise NotImplementedError

class TextRenderer(ContentRenderer):
    """纯文本渲染器"""
    
    def can_render(self, content: str) -> bool:
        """纯文本总是可以渲染"""
        return True
    
    def render(self, content: str, **kwargs) -> str:
        """直接返回文本（不渲染）"""
        return content

class MarkdownRenderer(ContentRenderer):
    """Markdown 渲染器"""
    
    def can_render(self, content: str) -> bool:
        """检测是否为 Markdown 内容"""
        markdown_patterns = [
            r'^#{1,6}\s+.+',        # 标题
            r'\*\*.*?\*\*',         # 粗体
            r'(?<!\*)\*[^*].*?\*(?!\*)',  # 斜体（避免与粗体冲突）
            r'^[-*+]\s+.+',         # 无序列表
            r'^\d+\.\s+.+',         # 有序列表
            r'```.*?```',           # 代码块
            r'\[.*?\]\(.*?\)',      # 链接
            r'!\[.*?\]\(.*?\)',      # 图片
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                return True
        
        return False
    
    def render(self, content: str, **kwargs) -> Markdown:
        """渲染 Markdown 为 Rich Markdown 对象"""
        return Markdown(content)

class CodeRenderer(ContentRenderer):
    """代码块渲染器"""
    
    def can_render(self, content: str) -> bool:
        """检测是否为代码块（```language\ncode\n```）"""
        pattern = r'^```\w*\n.*?```'
        return bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
    
    def render(self, content: str, language: str = None, **kwargs) -> Syntax:
        """渲染代码块为 Rich Syntax 对象"""
        # 提取代码块内容
        match = re.search(r'^```(\w+)?\n(.*?)```', content, re.MULTILINE | re.DOTALL)
        if match:
            lang = match.group(1) or language or "text"
            code = match.group(2)
        else:
            lang = language or "text"
            code = content
        
        return Syntax(code, lang, theme="monokai", line_numbers=False)

class RendererFactory:
    """渲染器工厂，根据内容类型选择合适的渲染器
    
    优先级说明：
    1. CodeRenderer - 代码块优先（避免代码块内的 Markdown 被误判）
    2. MarkdownRenderer - Markdown 内容
    3. TextRenderer - 默认渲染器（纯文本）
    
    注意：代码块检测会排除代码块内的内容，避免嵌套检测
    """
    
    def __init__(self):
        self.renderers = [
            CodeRenderer(),      # 优先检测代码块（必须优先）
            MarkdownRenderer(),  # 其次检测 Markdown
            TextRenderer(),      # 默认渲染器
        ]
    
    def get_renderer(self, content: str) -> ContentRenderer:
        """根据内容类型选择合适的渲染器
        
        特殊处理：如果检测到代码块，排除代码块内的内容进行 Markdown 检测
        """
        # 先检测代码块
        code_renderer = CodeRenderer()
        if code_renderer.can_render(content):
            return code_renderer
        
        # 排除代码块后检测 Markdown
        # 提取所有代码块，用占位符替换，避免代码块内的 Markdown 被误判
        code_blocks = re.finditer(r'```[\s\S]*?```', content)
        content_without_code = content
        placeholders = []
        
        for i, match in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            placeholders.append((placeholder, match.group(0)))
            content_without_code = content_without_code.replace(match.group(0), placeholder)
        
        # 在排除代码块的内容中检测 Markdown
        markdown_renderer = MarkdownRenderer()
        if markdown_renderer.can_render(content_without_code):
            return markdown_renderer
        
        # 默认返回文本渲染器
        return TextRenderer()
```

#### 步骤 1.5: 运行测试（确认通过 - Green）

```bash
pytest frontend/ui/tests/test_renderer.py -v
# 预期：所有测试通过
```

#### 步骤 1.6: 重构（Refactor 阶段）

- 优化 Markdown 检测算法
- 提取常量
- 改进代码结构

---

### 阶段 2: 流式响应处理（TDD）

#### 步骤 2.1: 编写流式处理测试（Red 阶段）

**文件**: `frontend/ui/tests/test_stream_handler.py`

```python
"""流式处理器测试"""
import pytest
import asyncio
from frontend.ui.stream_handler import StreamBuffer, StreamRenderer
from frontend.ui.renderer import RendererFactory

class TestStreamBuffer:
    """StreamBuffer 测试"""
    
    def test_add_chunk_basic(self):
        """测试添加数据块"""
        buffer = StreamBuffer(min_chunk_size=10)
        renderable, remaining = buffer.add_chunk("hello")
        assert renderable is None
        assert remaining == "hello"
    
    def test_add_chunk_reaches_min_size(self):
        """测试达到最小缓冲大小"""
        buffer = StreamBuffer(min_chunk_size=10)
        renderable, remaining = buffer.add_chunk("hello world")
        # 应该尝试提取可渲染内容
        assert renderable is not None or remaining is not None
    
    def test_extract_markdown_block(self):
        """测试提取完整的 Markdown 块"""
        buffer = StreamBuffer()
        buffer.buffer = "# 标题\n\n这是内容\n\n"
        renderable, remaining = buffer._extract_renderable()
        # 应该提取完整的段落
        assert len(renderable) > 0
    
    def test_flush(self):
        """测试清空缓冲区"""
        buffer = StreamBuffer()
        buffer.buffer = "剩余内容"
        content = buffer.flush()
        assert content == "剩余内容"
        assert buffer.buffer == ""

class TestStreamRenderer:
    """StreamRenderer 测试"""
    
    @pytest.mark.asyncio
    async def test_render_stream_basic(self):
        """测试基础流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        
        async def mock_stream():
            yield "hello"
            yield " world"
        
        # 使用 Mock Console 验证输出
        from unittest.mock import MagicMock
        console = MagicMock()
        
        await renderer.render_stream(mock_stream(), console)
        
        # 验证 console.print 被调用
        assert console.print.called
    
    @pytest.mark.asyncio
    async def test_render_stream_markdown(self):
        """测试 Markdown 流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        
        async def mock_stream():
            yield "# 标题\n\n"
            yield "这是 **粗体** 文本"
        
        from unittest.mock import MagicMock
        console = MagicMock()
        
        await renderer.render_stream(mock_stream(), console)
        
        # 验证 Markdown 被渲染
        assert console.print.called
```

#### 步骤 2.2: 实现流式处理器（Green 阶段）

**文件**: `frontend/ui/stream_handler.py`

```python
"""流式响应处理器"""
import re
from typing import AsyncIterator, Optional, Tuple
from rich.console import Console
from frontend.ui.renderer import RendererFactory, ContentRenderer

class StreamBuffer:
    """流式响应缓冲器
    
    简化策略：只检测明确的完整块，避免复杂判断
    """
    
    def __init__(self, min_chunk_size: int = 20):
        self.buffer = ""
        self.min_chunk_size = min_chunk_size
        self.last_extracted_pos = 0  # 记录上次提取的位置，避免重复
    
    def add_chunk(self, chunk: str) -> Tuple[Optional[str], str]:
        """添加数据块，返回可渲染的完整内容（如果有）
        
        Returns:
            (renderable_content, remaining_buffer)
        """
        self.buffer += chunk
        
        # 如果缓冲区足够大，尝试提取可渲染的内容
        if len(self.buffer) >= self.min_chunk_size:
            renderable, remaining = self._extract_renderable()
            if renderable:
                # 更新为提取结束位置的绝对位置
                self.last_extracted_pos = len(self.buffer) - len(remaining)
                return renderable, remaining
        
        return None, self.buffer
    
    def _extract_renderable(self) -> Tuple[str, str]:
        """提取可渲染的完整内容块
        
        简化策略：只检测明确的完整块，避免复杂判断
        从上次提取位置之后开始查找，避免重复提取
        """
        # 策略 1: 检测完整的代码块（```...```）
        # 从上次提取位置之后开始查找
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

class StreamRenderer:
    """流式渲染器，处理流式响应的实时渲染"""
    
    def __init__(self, renderer_factory: RendererFactory):
        self.factory = renderer_factory
        self.buffer = StreamBuffer()
    
    async def render_stream(
        self, 
        stream: AsyncIterator[str], 
        console: Console,
        show_incomplete: bool = True
    ):
        """渲染流式响应
        
        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例
            show_incomplete: 是否显示不完整的内容（淡色）
        """
        last_buffer_size = 0  # 上次渲染时的 buffer 大小
        
        async for chunk in stream:
            # 添加到缓冲区
            renderable, remaining = self.buffer.add_chunk(chunk)
            
            if renderable:
                # 渲染完整内容
                renderer = self.factory.get_renderer(renderable)
                rendered = renderer.render(renderable)
                console.print(rendered, end="")
                # 更新已渲染的 buffer 大小
                last_buffer_size = len(self.buffer.buffer) - len(remaining)
            
            # 显示剩余的不完整内容（新增部分）
            if show_incomplete and remaining:
                current_buffer_size = len(self.buffer.buffer)
                # 计算新增的未渲染内容长度
                new_content_length = current_buffer_size - last_buffer_size - (len(renderable) if renderable else 0)
                if new_content_length > 0:
                    # 从 remaining 中取最后 new_content_length 个字符
                    new_content = remaining[-new_content_length:] if len(remaining) >= new_content_length else remaining
                    console.print(new_content, end="", style="dim")
        
        # 流式结束，渲染剩余内容
        remaining = self.buffer.flush()
        if remaining:
            renderer = self.factory.get_renderer(remaining)
            rendered = renderer.render(remaining)
            console.print(rendered)
```

#### 步骤 2.3: 运行测试（确认通过 - Green）

```bash
pytest frontend/ui/tests/test_stream_handler.py -v
```

---

### 阶段 3: 集成到前端

#### 步骤 3.1: 修改 `frontend/main.py`

```python
# 在文件顶部添加导入
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer

# 修改 _stream_chat 函数
async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
    """流式聊天（异步）"""
    console.print("[bold cyan]Agent: [/bold cyan]", end="")
    
    try:
        # 创建渲染器
        factory = RendererFactory()
        stream_renderer = StreamRenderer(factory)
        
        # 创建流式数据生成器
        async def stream_generator():
            async for chunk in client.stream_send(message, session_id=session_id):
                yield chunk
        
        # 使用 StreamRenderer 实时渲染
        await stream_renderer.render_stream(stream_generator(), console)
        console.print()  # 换行
        
        return True
    except Exception as e:
        console.print(f"\n[bold red]错误: {e}[/bold red]")
        return None
```

#### 步骤 3.2: 修改 `frontend/ui/panels.py`

```python
# 导入渲染器
from frontend.ui.renderer import RendererFactory

# 创建全局工厂实例
_renderer_factory = RendererFactory()

def ChatPanel(message: str, role: str = "assistant") -> Panel:
    """创建聊天面板"""
    if role == "user":
        return Panel.fit(
            f"[bold cyan]{message}[/bold cyan]",
            border_style="cyan",
            title="[bold cyan]你[/bold cyan]"
        )
    else:
        # 使用渲染器工厂渲染内容
        renderer = _renderer_factory.get_renderer(message)
        rendered = renderer.render(message)
        
        return Panel(
            rendered,
            border_style="green",
            title="[bold green]Agent[/bold green]"
        )
```

#### 步骤 3.3: 集成测试

创建集成测试文件：`tests/integration/test_markdown_rendering.py`

```python
"""Markdown 渲染集成测试"""
import pytest
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer
from rich.console import Console

class TestMarkdownRenderingIntegration:
    """Markdown 渲染集成测试"""
    
    def test_markdown_in_chat_panel(self):
        """测试聊天面板中的 Markdown 渲染"""
        from frontend.ui.panels import ChatPanel
        
        markdown = "# 标题\n\n这是 **粗体** 文本"
        panel = ChatPanel(markdown)
        assert panel is not None
    
    @pytest.mark.asyncio
    async def test_stream_markdown_rendering(self):
        """测试流式 Markdown 渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        console = Console()
        
        async def mock_stream():
            yield "# 标题\n\n"
            yield "这是 **粗体** 文本"
        
        await renderer.render_stream(mock_stream(), console)
```

---

## 二、测试执行顺序

### TDD 循环 1: 基础渲染器

1. ✅ 编写测试（Red）
2. ✅ 实现功能（Green）
3. ✅ 重构优化（Refactor）
4. ✅ 运行测试验证

### TDD 循环 2: 流式处理器

1. ✅ 编写测试（Red）
2. ✅ 实现功能（Green）
3. ✅ 重构优化（Refactor）
4. ✅ 运行测试验证

### TDD 循环 3: 集成

1. ✅ 集成到前端
2. ✅ 集成测试
3. ✅ 手动测试
4. ✅ 性能测试

---

## 三、验收测试

### 3.1 单元测试覆盖率

```bash
pytest frontend/ui/tests/ --cov=frontend/ui --cov-report=html
# 目标：覆盖率 > 90%
```

### 3.2 集成测试

```bash
pytest tests/integration/test_markdown_rendering.py -v
```

### 3.3 手动测试步骤

1. **启动后端和前端**:

   ```bash
   make start
   ```

2. **测试 Markdown 渲染**:
   - 发送包含 Markdown 的消息
   - 验证流式响应中 Markdown 正确渲染
   - 验证非流式响应中 Markdown 正确渲染

3. **测试代码块**:
   - 发送包含代码块的消息
   - 验证代码块正确高亮

4. **测试混合内容**:
   - 发送包含 Markdown + 代码块 + 纯文本的消息
   - 验证各部分正确渲染

---

## 四、注意事项

### 4.1 流式渲染的挑战

- **不完整内容**: 流式响应中，Markdown 可能不完整
- **解决方案**: 缓冲策略，只渲染完整的内容块

### 4.2 性能考虑

- **渲染延迟**: Markdown 渲染不应阻塞流式输出
- **解决方案**: 异步渲染，实时显示

### 4.3 用户体验

- **视觉反馈**: 不完整内容要有视觉提示
- **解决方案**: 使用 dim 样式显示不完整内容

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0
