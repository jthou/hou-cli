# TODO-003: Markdown 渲染器设计问题分析

## 已修复的问题 ✅

1. ✅ 添加了 Markdown 误判测试用例（`test_avoid_false_positive_hash`, `test_avoid_false_positive_bold`）
2. ✅ 改进了 `RendererFactory` 的代码块优先级处理
3. ✅ 简化了流式缓冲策略，添加了 `last_extracted_pos`
4. ✅ 改进了流式渲染的重复显示问题

## 遗留问题 ⚠️

### 1. **集成代码未正确使用 StreamRenderer**（严重）

**位置**: `003-markdown-renderer-implementation.md` 第 557-580 行

**问题**:
```python
# 当前代码
async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
    factory = RendererFactory()
    stream_renderer = StreamRenderer(factory)
    
    # ❌ 错误：只是遍历了 stream，没有调用 render_stream
    async for chunk in client.stream_send(message, session_id=session_id):
        full_response += chunk
```

**修复方案**:
```python
async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
    """流式聊天（异步）"""
    console.print("[bold cyan]Agent: [/bold cyan]", end="")
    
    try:
        # 创建渲染器
        factory = RendererFactory()
        stream_renderer = StreamRenderer(factory)
        
        # ✅ 正确：直接使用 render_stream 方法
        async def stream_generator():
            async for chunk in client.stream_send(message, session_id=session_id):
                yield chunk
        
        await stream_renderer.render_stream(stream_generator(), console)
        console.print()  # 换行
        
        return True
    except Exception as e:
        console.print(f"\n[bold red]错误: {e}[/bold red]")
        return None
```

### 2. **StreamRenderer 中 last_rendered_length 逻辑错误**（严重）

**位置**: `003-markdown-renderer-implementation.md` 第 508-536 行

**问题**:
- `last_rendered_length` 被设置为 `len(renderable)`，但这是错误的
- `renderable` 是从 buffer 中提取的一部分，`remaining` 是 buffer 的剩余部分
- 两者不在同一个坐标系中，无法直接比较

**修复方案**:
```python
async def render_stream(
    self, 
    stream: AsyncIterator[str], 
    console: Console,
    show_incomplete: bool = True
):
    """渲染流式响应"""
    rendered_buffer_length = 0  # 已渲染的 buffer 长度
    
    async for chunk in stream:
        renderable, remaining = self.buffer.add_chunk(chunk)
        
        if renderable:
            # 渲染完整内容
            renderer = self.factory.get_renderer(renderable)
            rendered = renderer.render(renderable)
            console.print(rendered, end="")
            # 更新已渲染的长度（renderable 在 buffer 中的位置）
            rendered_buffer_length = len(self.buffer.buffer) - len(remaining)
        
        # 显示剩余的不完整内容
        if show_incomplete and remaining:
            # 计算未渲染的新内容
            unrendered_length = len(remaining) - (len(self.buffer.buffer) - rendered_buffer_length)
            if unrendered_length > 0:
                new_content = remaining[-unrendered_length:]
                console.print(new_content, end="", style="dim")
    
    # 流式结束，渲染剩余内容
    remaining = self.buffer.flush()
    if remaining:
        # 只渲染未渲染的部分
        unrendered = remaining[rendered_buffer_length:] if rendered_buffer_length < len(remaining) else remaining
        if unrendered:
            renderer = self.factory.get_renderer(unrendered)
            rendered = renderer.render(unrendered)
            console.print(rendered)
```

**更好的方案**（简化）:
```python
async def render_stream(
    self, 
    stream: AsyncIterator[str], 
    console: Console,
    show_incomplete: bool = True
):
    """渲染流式响应"""
    last_buffer_size = 0  # 上次渲染时的 buffer 大小
    
    async for chunk in stream:
        renderable, remaining = self.buffer.add_chunk(chunk)
        
        if renderable:
            # 渲染完整内容
            renderer = self.factory.get_renderer(renderable)
            rendered = renderer.render(renderable)
            console.print(rendered, end="")
            last_buffer_size = len(self.buffer.buffer) - len(remaining)
        
        # 显示剩余的不完整内容（新增部分）
        if show_incomplete and remaining:
            current_buffer_size = len(self.buffer.buffer)
            new_content_length = current_buffer_size - last_buffer_size - (len(renderable) if renderable else 0)
            if new_content_length > 0:
                new_content = remaining[-new_content_length:]
                console.print(new_content, end="", style="dim")
    
    # 流式结束，渲染剩余内容
    remaining = self.buffer.flush()
    if remaining:
        renderer = self.factory.get_renderer(remaining)
        rendered = renderer.render(remaining)
        console.print(rendered)
```

### 3. **StreamBuffer 的 last_extracted_pos 更新错误**（中等）

**位置**: `003-markdown-renderer-implementation.md` 第 415-430 行

**问题**:
```python
# 当前代码
if renderable:
    self.last_extracted_pos = len(renderable)  # ❌ 错误：应该是绝对位置
```

**修复方案**:
```python
def add_chunk(self, chunk: str) -> Tuple[Optional[str], str]:
    """添加数据块，返回可渲染的完整内容（如果有）"""
    self.buffer += chunk
    
    if len(self.buffer) >= self.min_chunk_size:
        renderable, remaining = self._extract_renderable()
        if renderable:
            # ✅ 正确：更新为提取结束位置的绝对位置
            self.last_extracted_pos = len(self.buffer) - len(remaining)
            return renderable, remaining
    
    return None, self.buffer
```

### 4. **Markdown 检测实现与测试不匹配**（中等）

**位置**: `003-markdown-renderer-implementation.md` 第 199-216 行

**问题**:
- 测试用例要求 `"价格是 $100，这是 #1 选择"` 返回 `False`
- 但当前正则 `r'^#{1,6}\s+.+'` 在 MULTILINE 模式下可能匹配行中的 `#1`
- 测试要求 `"这是 # 号，不是标题"` 返回 `False`，但当前实现可能误判

**修复方案**:
```python
def can_render(self, content: str) -> bool:
    """检测是否为 Markdown 内容"""
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
```

### 5. **流式渲染的 remaining 处理逻辑混乱**（中等）

**问题**:
- `remaining` 是 buffer 的剩余部分
- `last_rendered_length` 是已渲染的长度
- 两者不在同一个坐标系中，比较逻辑错误

**建议**:
简化逻辑，使用更清晰的状态跟踪：
```python
class StreamRenderer:
    def __init__(self, renderer_factory: RendererFactory):
        self.factory = renderer_factory
        self.buffer = StreamBuffer()
        self.rendered_length = 0  # 已渲染的 buffer 总长度
    
    async def render_stream(self, stream, console, show_incomplete=True):
        async for chunk in stream:
            renderable, remaining = self.buffer.add_chunk(chunk)
            
            if renderable:
                # 渲染完整内容
                renderer = self.factory.get_renderer(renderable)
                rendered = renderer.render(renderable)
                console.print(rendered, end="")
                # 更新已渲染长度
                self.rendered_length = len(self.buffer.buffer) - len(remaining)
            
            # 显示新增的不完整内容
            if show_incomplete and remaining:
                current_total = len(self.buffer.buffer)
                new_unrendered = current_total - self.rendered_length
                if new_unrendered > 0:
                    # 从 remaining 中取最后 new_unrendered 个字符
                    new_content = remaining[-new_unrendered:] if len(remaining) >= new_unrendered else remaining
                    console.print(new_content, end="", style="dim")
        
        # 流式结束
        remaining = self.buffer.flush()
        if remaining:
            unrendered = remaining[self.rendered_length:] if self.rendered_length < len(remaining) else remaining
            if unrendered:
                renderer = self.factory.get_renderer(unrendered)
                rendered = renderer.render(unrendered)
                console.print(rendered)
```

### 6. **缺少错误处理**（轻微）

**问题**:
- 渲染失败时没有降级策略
- Markdown 解析异常时没有回退

**建议**:
```python
def render(self, content: str, **kwargs) -> Markdown:
    """渲染 Markdown 为 Rich Markdown 对象"""
    try:
        return Markdown(content)
    except Exception:
        # 降级到纯文本
        return content
```

### 7. **测试用例不完整**（轻微）

**缺失的测试**:
- 边界情况：空内容、超长内容
- 错误情况：无效 Markdown、解析异常
- 流式场景：多个代码块、混合内容

## 建议的修复优先级

1. **P0（必须修复）**:
   - 问题 1: 集成代码未正确使用 StreamRenderer
   - 问题 2: StreamRenderer 逻辑错误

2. **P1（应该修复）**:
   - 问题 3: StreamBuffer 的 last_extracted_pos 更新
   - 问题 4: Markdown 检测实现

3. **P2（建议修复）**:
   - 问题 5: 流式渲染逻辑简化
   - 问题 6: 错误处理
   - 问题 7: 测试用例补充

