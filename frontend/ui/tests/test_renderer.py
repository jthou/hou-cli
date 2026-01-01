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
        # 价格中的 # 不应被识别（不在行首）
        assert renderer.can_render("价格是 $100，这是 #1 选择") == False
        # 行首的 # 且后面有空格和非空白字符才识别
        assert renderer.can_render("# 这是标题") == True
        assert renderer.can_render("这是 # 号，不是标题") == False
        # 行首的 # 但后面没有非空白字符，不应识别
        assert renderer.can_render("# ") == False

    def test_avoid_false_positive_bold(self):
        """测试避免误判：单独的 * 不应被识别为粗体"""
        renderer = MarkdownRenderer()
        assert renderer.can_render("这是 * 单独的星号") == False
        assert renderer.can_render("这是 **成对的粗体**") == True
        # 三个星号不应被识别为粗体
        assert renderer.can_render("这是 *** 三个星号") == False

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

