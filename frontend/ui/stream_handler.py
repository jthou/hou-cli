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
        self.last_extracted_pos = 0
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

        策略（修复重复显示问题）：
        - 流式时，实时显示每个 chunk（作为纯文本，不渲染 Markdown）
        - 流式结束后，一次性渲染完整内容（格式化后的 Markdown）
        - 这样可以确保用户看到实时输出，且 Markdown 正确渲染
        
        注意：流式时显示纯文本预览，结束后渲染格式化内容。
        由于终端限制，无法完全清除已显示的内容，所以会显示两次
        （一次预览，一次渲染），但至少不会重复显示每个字符。
        """
        # 收集所有流式数据
        full_content = ""

        async for chunk in stream:
            # 只追加新内容，避免重复
            full_content += chunk
            # 流式时实时显示 chunk（作为纯文本预览）
            # 这样用户可以看到实时输出
            if show_incomplete:
                console.print(chunk, end="", style="dim")

        # 流式结束，渲染完整内容
        if full_content:
            # 换行（因为流式输出在同一行）
            console.print()  # 换行
            
            # 渲染完整内容（格式化后的 Markdown）
            renderer = self.factory.get_renderer(full_content)
            rendered = renderer.render(full_content)
            console.print(rendered)

