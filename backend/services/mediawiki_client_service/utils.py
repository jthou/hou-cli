"""MediaWiki 工具函数"""

import os
from typing import List, Optional
from urllib.parse import quote


def format_page_url(page_title: str, base_url: Optional[str] = None) -> str:
    """格式化 MediaWiki 页面 URL
    
    MediaWiki 支持两种 URL 格式：
    1. 路径格式：/index.php/Page_Title（需要 URL 重写）
    2. 参数格式：/index.php?title=Page_Title（更通用，兼容性更好）
    
    这里使用参数格式，因为它更可靠，不依赖 URL 重写配置。
    
    Args:
        page_title: 页面标题
        base_url: MediaWiki 基础 URL，默认从环境变量读取
        
    Returns:
        str: 完整的页面 URL
    """
    if base_url is None:
        base_url = os.getenv("MEDIAWIKI_URL", "http://www.jthou.com/mediawiki")
    
    # 移除 URL 末尾的斜杠
    base_url = base_url.rstrip('/')
    
    # 使用 ?title= 参数格式，更通用和可靠
    # MediaWiki 标准：空格转换为下划线，然后进行 URL 编码
    # 这样生成的 URL 与 MediaWiki API 返回的 URL 格式一致
    encoded_title = page_title.replace(' ', '_')
    encoded_title = quote(encoded_title, safe='_')
    
    # 构建完整 URL（使用参数格式）
    url = f"{base_url}/index.php?title={encoded_title}"
    return url


def format_page_link(page_title: str, base_url: Optional[str] = None, link_text: Optional[str] = None) -> str:
    """格式化 MediaWiki 页面为 Markdown 链接
    
    Args:
        page_title: 页面标题
        base_url: MediaWiki 基础 URL，默认从环境变量读取
        link_text: 链接文本，默认使用页面标题
        
    Returns:
        str: Markdown 格式的链接
    """
    url = format_page_url(page_title, base_url)
    text = link_text or page_title
    return f"[{text}]({url})"


def format_page_list_with_links(page_titles: List[str], base_url: Optional[str] = None) -> str:
    """格式化页面列表，每个页面标题添加链接
    
    Args:
        page_titles: 页面标题列表
        base_url: MediaWiki 基础 URL，默认从环境变量读取
        
    Returns:
        str: 格式化后的列表，每个项目都是可点击的链接
    """
    formatted_items = []
    for title in page_titles:
        link = format_page_link(title, base_url)
        formatted_items.append(f"- {link}")
    
    return '\n'.join(formatted_items)


def format_page_list_with_bullets_and_links(page_titles: List[str], base_url: Optional[str] = None) -> str:
    """格式化页面列表，使用项目符号和链接
    
    Args:
        page_titles: 页面标题列表
        base_url: MediaWiki 基础 URL，默认从环境变量读取
        
    Returns:
        str: 格式化后的列表
    """
    return format_page_list_with_links(page_titles, base_url)

