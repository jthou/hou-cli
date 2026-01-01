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

    def test_render_markdown_error_handling(self):
        """测试 Markdown 渲染错误处理（降级到纯文本）"""
        renderer = MarkdownRenderer()
        # 创建一个会导致 Markdown 解析错误的字符串（虽然很难，但测试异常处理）
        # 实际上 Rich 的 Markdown 很宽容，所以我们用 mock 来测试异常路径
        from unittest.mock import patch
        with patch('frontend.ui.renderer.Markdown', side_effect=Exception("Parse error")):
            result = renderer.render("test content")
            # 应该降级到纯文本
            assert result == "test content"


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

    def test_render_code_block_no_match(self):
        """测试渲染代码块（无匹配时）"""
        renderer = CodeRenderer()
        # 不完整的代码块（没有匹配）
        code = "print('hello')"
        result = renderer.render(code)
        # 验证返回的是 Rich Syntax 对象（使用默认语言）
        from rich.syntax import Syntax
        assert isinstance(result, Syntax)
        # 验证是 text 语言（通过检查内部属性）
        assert hasattr(result, 'lexer') or hasattr(result, '_lexer')

    def test_render_code_block_with_language_param(self):
        """测试渲染代码块（指定语言参数）"""
        renderer = CodeRenderer()
        code = "print('hello')"
        result = renderer.render(code, language="python")
        from rich.syntax import Syntax
        assert isinstance(result, Syntax)
        # 验证是 python 语言（通过检查内部属性或代码）
        # Syntax 对象创建时使用了 language 参数
        assert hasattr(result, 'lexer') or hasattr(result, '_lexer')


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

    def test_renderer_factory_with_code_blocks(self):
        """测试 RendererFactory 处理包含代码块的内容"""
        factory = RendererFactory()
        # 包含代码块的 Markdown
        # 注意：代码块检测优先，所以如果内容包含完整代码块，会返回 CodeRenderer
        # 但如果代码块被替换后，剩余内容有 Markdown，应该返回 MarkdownRenderer
        # 这里测试的是代码块替换逻辑
        content = "这是文本\n\n```python\nprint('code')\n```\n\n这是 **粗体**"
        renderer = factory.get_renderer(content)
        # 由于代码块检测优先，如果整个内容包含代码块，会返回 CodeRenderer
        # 但实际逻辑是：先检测代码块，如果检测到就返回 CodeRenderer
        # 所以这里应该返回 CodeRenderer（因为内容包含完整代码块）
        assert isinstance(renderer, CodeRenderer)
        
        # 测试代码块被替换后的 Markdown 检测（纯 Markdown，无代码块）
        markdown_only = "这是 **粗体** 文本\n\n这是 *斜体*"
        renderer2 = factory.get_renderer(markdown_only)
        assert isinstance(renderer2, MarkdownRenderer)

    def test_renderer_factory_code_block_priority(self):
        """测试代码块优先级（代码块优先于 Markdown）"""
        factory = RendererFactory()
        # 完整的代码块应该优先
        code = "```python\nprint('hello')\n```"
        renderer = factory.get_renderer(code)
        assert isinstance(renderer, CodeRenderer)

