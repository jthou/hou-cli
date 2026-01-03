"""流式响应处理器"""
import re
from typing import AsyncIterator, Optional, Tuple
from rich.console import Console
from rich.live import Live
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

    def _clean_unicode(self, text: str) -> str:
        """
        清理无效的 Unicode 字符（代理对）
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        try:
            # 尝试编码为 UTF-8，如果失败则替换无效字符
            return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
        except Exception:
            # 如果仍然失败，使用 replace 策略
            return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    async def render_stream(
        self,
        stream: AsyncIterator[str],
        console: Console,
    ):
        """渲染流式响应（使用 Live 组件避免重复显示）

        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例

        策略：
        - 使用 Rich Live 组件实时更新渲染内容
        - Live 组件会自动保留最终内容，无需再次打印
        - 流式输出完成后，使用完整的 Markdown 渲染器进行最终渲染
        """
        full_content = ""
        
        # 使用 Live 组件实时更新（transient=True 表示流式输出完成后清除）
        # 这样可以在流式输出时显示进度，完成后用完整的 Markdown 渲染
        with Live(console=console, refresh_per_second=10, transient=True) as live:
            async for chunk in stream:
                # 清理无效的 Unicode 字符
                chunk = self._clean_unicode(chunk)
                full_content += chunk
                
                # 流式显示时，直接显示文本（避免表格不完整时的渲染问题）
                live.update(full_content)
        
        # 流式输出完成后，使用完整的 Markdown 渲染器进行最终渲染
        # 这样可以确保表格等复杂格式正确显示
        if full_content:
            try:
                renderer = self.factory.get_renderer(full_content)
                rendered = renderer.render(full_content)
                console.print(rendered)
            except Exception:
                # 如果最终渲染失败，直接显示文本
                console.print(full_content)

