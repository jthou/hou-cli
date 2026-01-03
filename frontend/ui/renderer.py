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


