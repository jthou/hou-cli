"""流式响应处理器

简化策略：直接显示 Markdown 文本，确保换行正确
"""
from typing import AsyncIterator
from rich.console import Console
from rich.live import Live


class StreamRenderer:
    """流式渲染器，直接显示 Markdown 文本"""

    def __init__(self, renderer_factory=None):
        # renderer_factory 参数保留以兼容现有代码，但不再使用
        pass

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
        """渲染流式响应（直接显示 Markdown 原始文本）

        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例

        策略：直接输出 Markdown 原始格式，不使用 Rich 渲染，保留换行
        """
        full_content = ""
        
        # 使用 Live 组件实时更新，流式显示文本
        # 直接输出原始文本，不使用 Markdown 对象渲染
        with Live(console=console, refresh_per_second=10) as live:
            async for chunk in stream:
                # 清理无效的 Unicode 字符
                chunk = self._clean_unicode(chunk)
                full_content += chunk
                
                # 直接显示原始文本（保留所有换行和格式）
                live.update(full_content)
        
        # 流式完成后，Live 组件会保留最终内容
        # 不需要额外处理
