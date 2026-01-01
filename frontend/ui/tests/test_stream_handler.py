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

    @pytest.mark.asyncio
    async def test_render_stream_multiple_code_blocks(self):
        """测试多个代码块的流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)

        async def mock_stream():
            yield "```python\n"
            yield "print('hello')\n"
            yield "```\n\n"
            yield "```javascript\n"
            yield "console.log('world')\n"
            yield "```"

        from unittest.mock import MagicMock
        console = MagicMock()

        await renderer.render_stream(mock_stream(), console)
        assert console.print.called

    @pytest.mark.asyncio
    async def test_render_stream_mixed_content(self):
        """测试混合内容（Markdown + 代码块 + 纯文本）的流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)

        async def mock_stream():
            yield "# 标题\n\n"
            yield "这是 **粗体** 文本\n\n"
            yield "```python\nprint('code')\n```\n\n"
            yield "这是纯文本"

        from unittest.mock import MagicMock
        console = MagicMock()

        await renderer.render_stream(mock_stream(), console)
        assert console.print.called

    @pytest.mark.asyncio
    async def test_render_stream_empty(self):
        """测试空内容的流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)

        async def mock_stream():
            yield ""

        from unittest.mock import MagicMock
        console = MagicMock()

        await renderer.render_stream(mock_stream(), console)
        # 空内容不应出错
        assert True

    @pytest.mark.asyncio
    async def test_render_stream_very_long_content(self):
        """测试超长内容的流式渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)

        async def mock_stream():
            # 生成超长内容
            for i in range(1000):
                yield f"这是第 {i} 行内容。\n"

        from unittest.mock import MagicMock
        console = MagicMock()

        await renderer.render_stream(mock_stream(), console)
        assert console.print.called

