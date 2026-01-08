"""Markdown 渲染集成测试"""
import pytest
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer
from frontend.ui.panels import ChatPanel
from rich.console import Console


class TestMarkdownRenderingIntegration:
    """Markdown 渲染集成测试"""

    def test_markdown_in_chat_panel(self):
        """测试聊天面板中的 Markdown 渲染"""
        markdown = "# 标题\n\n这是 **粗体** 文本"
        panel = ChatPanel(markdown)
        assert panel is not None
        # 验证面板创建成功
        assert panel.title == "[bold green]Agent[/bold green]"

    def test_plain_text_in_chat_panel(self):
        """测试纯文本在聊天面板中的渲染"""
        text = "这是纯文本，没有 Markdown 语法"
        panel = ChatPanel(text)
        assert panel is not None
        assert panel.title == "[bold green]Agent[/bold green]"

    def test_code_block_in_chat_panel(self):
        """测试代码块在聊天面板中的渲染"""
        code = "```python\nprint('hello')\n```"
        panel = ChatPanel(code)
        assert panel is not None

    def test_mixed_content_in_chat_panel(self):
        """测试混合内容（Markdown + 代码块 + 纯文本）在聊天面板中的渲染"""
        mixed = "# 标题\n\n这是 **粗体** 文本\n\n```python\nprint('code')\n```\n\n这是纯文本"
        panel = ChatPanel(mixed)
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
        # 验证没有抛出异常

    @pytest.mark.asyncio
    async def test_stream_code_block_rendering(self):
        """测试流式代码块渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        console = Console()

        async def mock_stream():
            yield "```python\n"
            yield "print('hello')\n"
            yield "```"

        await renderer.render_stream(mock_stream(), console)
        # 验证没有抛出异常

    @pytest.mark.asyncio
    async def test_stream_mixed_content_rendering(self):
        """测试流式混合内容渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        console = Console()

        async def mock_stream():
            yield "# 标题\n\n"
            yield "这是 **粗体** 文本\n\n"
            yield "```python\n"
            yield "print('code')\n"
            yield "```\n\n"
            yield "这是纯文本"

        await renderer.render_stream(mock_stream(), console)
        # 验证没有抛出异常

    @pytest.mark.asyncio
    async def test_stream_empty_content(self):
        """测试流式空内容渲染"""
        factory = RendererFactory()
        renderer = StreamRenderer(factory)
        console = Console()

        async def mock_stream():
            yield ""

        await renderer.render_stream(mock_stream(), console)
        # 验证没有抛出异常

    def test_renderer_factory_with_chat_panel(self):
        """测试 RendererFactory 与 ChatPanel 的集成"""
        factory = RendererFactory()
        
        # 测试 Markdown 内容
        markdown = "# 标题\n\n这是 **粗体**"
        renderer = factory.get_renderer(markdown)
        assert renderer is not None
        
        # 测试代码块
        code = "```python\nprint('hello')\n```"
        renderer = factory.get_renderer(code)
        assert renderer is not None
        
        # 测试纯文本
        text = "这是纯文本"
        renderer = factory.get_renderer(text)
        assert renderer is not None









