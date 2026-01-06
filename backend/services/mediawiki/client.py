"""MediaWiki 客户端服务"""

import os
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import mwclient
from mwclient.errors import APIError, LoginError

from .models import MediaWikiPage, MediaWikiSearchResult

logger = logging.getLogger(__name__)


class MediaWikiClientError(Exception):
    """MediaWiki 客户端错误"""
    pass


class MediaWikiClientService:
    """MediaWiki API 客户端服务
    
    封装 mwclient 库，提供 MediaWiki 操作的统一接口。
    支持基本认证和 Bot 认证。
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bot_name: Optional[str] = None,
        bot_password: Optional[str] = None
    ):
        """初始化 MediaWiki 客户端
        
        Args:
            url: MediaWiki 网站 URL（如 http://www.jthou.com/mediawiki）
            username: 用户名（基本认证）
            password: 密码（基本认证）
            bot_name: Bot 用户名（优先使用）
            bot_password: Bot 密码（优先使用）
        """
        self.url = url or os.getenv("MEDIAWIKI_URL", "http://www.jthou.com/mediawiki")
        self.username = username or os.getenv("MEDIAWIKI_USERNAME")
        self.password = password or os.getenv("MEDIAWIKI_PASSWORD")
        self.bot_name = bot_name or os.getenv("MEDIAWIKI_BOT_NAME")
        self.bot_password = bot_password or os.getenv("MEDIAWIKI_BOT_PASSWORD")
        
        self.site: Optional[mwclient.Site] = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接到 MediaWiki
        
        Returns:
            bool: 连接是否成功
            
        Raises:
            MediaWikiClientError: 连接失败时抛出
        """
        try:
            # 创建 Site 对象
            self.site = mwclient.Site(self.url)
            
            # 优先使用 Bot 认证
            if self.bot_name and self.bot_password:
                try:
                    self.site.login(self.bot_name, self.bot_password)
                    logger.info(f"Connected to MediaWiki as bot: {self.bot_name}")
                except LoginError as e:
                    logger.warning(f"Bot login failed: {e}, trying regular login")
                    if self.username and self.password:
                        self.site.login(self.username, self.password)
                        logger.info(f"Connected to MediaWiki as user: {self.username}")
                    else:
                        raise MediaWikiClientError(f"Authentication failed: {e}")
            elif self.username and self.password:
                self.site.login(self.username, self.password)
                logger.info(f"Connected to MediaWiki as user: {self.username}")
            else:
                # 无认证连接（只读）
                logger.info("Connected to MediaWiki without authentication (read-only)")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MediaWiki: {e}")
            raise MediaWikiClientError(f"Connection failed: {str(e)}")
    
    def _ensure_connected(self):
        """确保已连接"""
        if not self._connected or self.site is None:
            self.connect()
    
    def _retry_on_error(self, func, max_retries: int = 3, delay: float = 1.0):
        """错误重试装饰器
        
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
        """
        for attempt in range(max_retries):
            try:
                return func()
            except (APIError, ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(delay * (attempt + 1))  # 指数退避
                else:
                    raise MediaWikiClientError(f"Operation failed after {max_retries} attempts: {str(e)}")
    
    def search_pages(
        self,
        query: str,
        limit: int = 20,
        namespace: int = 0
    ) -> List[MediaWikiSearchResult]:
        """搜索页面
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            namespace: 命名空间（0 为主命名空间）
            
        Returns:
            List[MediaWikiSearchResult]: 搜索结果列表
        """
        self._ensure_connected()
        
        def _search():
            results = []
            search_results = self.site.search(
                query,
                namespace=namespace,
                limit=limit
            )
            
            for result in search_results:
                results.append(MediaWikiSearchResult(
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    url=f"{self.url}/index.php/{result.get('title', '').replace(' ', '_')}",
                    score=result.get("size", 0) / 1000.0,  # 简单的相关性分数
                    size=result.get("size"),
                    word_count=result.get("wordcount")
                ))
            
            return results
        
        return self._retry_on_error(_search)
    
    def get_page(self, title: str) -> Optional[MediaWikiPage]:
        """获取页面内容
        
        Args:
            title: 页面标题
            
        Returns:
            Optional[MediaWikiPage]: 页面对象，如果不存在返回 None
        """
        self._ensure_connected()
        
        def _get_page():
            try:
                page = self.site.Pages[title]
                
                if not page.exists:
                    return None
                
                # 获取页面内容
                content = page.text()
                
                # 获取页面信息
                page_info = page.info
                
                # 获取分类
                categories = [cat.name for cat in page.categories()]
                
                # 获取链接
                links = [link.name for link in page.links()]
                
                # 解析最后修改时间
                last_modified = datetime.fromisoformat(
                    page_info.get("touched", "").replace("Z", "+00:00")
                ) if page_info.get("touched") else datetime.now()
                
                return MediaWikiPage(
                    title=title,
                    content=content,
                    revision_id=page_info.get("lastrevid", 0),
                    last_modified=last_modified,
                    categories=categories,
                    links=links,
                    url=f"{self.url}/index.php/{title.replace(' ', '_')}"
                )
            except KeyError:
                return None
        
        return self._retry_on_error(_get_page)
    
    def edit_page(
        self,
        title: str,
        content: str,
        summary: str = "",
        minor: bool = False
    ) -> bool:
        """编辑页面
        
        Args:
            title: 页面标题
            content: 新内容（wikitext）
            summary: 编辑摘要
            minor: 是否为小编辑
            
        Returns:
            bool: 编辑是否成功
            
        Raises:
            MediaWikiClientError: 编辑失败时抛出
        """
        self._ensure_connected()
        
        def _edit():
            try:
                page = self.site.Pages[title]
                result = page.save(content, summary=summary, minor=minor)
                
                if result.get("result") == "Success":
                    logger.info(f"Successfully edited page: {title}")
                    return True
                else:
                    error = result.get("error", {}).get("info", "Unknown error")
                    raise MediaWikiClientError(f"Edit failed: {error}")
            except APIError as e:
                raise MediaWikiClientError(f"API error: {str(e)}")
        
        return self._retry_on_error(_edit)
    
    def create_page(
        self,
        title: str,
        content: str,
        summary: str = ""
    ) -> bool:
        """创建新页面
        
        Args:
            title: 页面标题
            content: 页面内容（wikitext）
            summary: 创建摘要
            
        Returns:
            bool: 创建是否成功
        """
        # 检查页面是否已存在
        existing_page = self.get_page(title)
        if existing_page:
            raise MediaWikiClientError(f"Page '{title}' already exists")
        
        return self.edit_page(title, content, summary)
    
    def upload_file(
        self,
        filename: str,
        file_path: str,
        description: str = "",
        ignore_warnings: bool = False
    ) -> bool:
        """上传文件
        
        Args:
            filename: 文件名（在 Wiki 中的名称）
            file_path: 本地文件路径
            description: 文件描述
            ignore_warnings: 是否忽略警告
            
        Returns:
            bool: 上传是否成功
        """
        self._ensure_connected()
        
        def _upload():
            try:
                with open(file_path, 'rb') as f:
                    result = self.site.upload(
                        file=f,
                        filename=filename,
                        description=description,
                        ignore=ignore_warnings
                    )
                
                if result.get("result") == "Success":
                    logger.info(f"Successfully uploaded file: {filename}")
                    return True
                else:
                    error = result.get("error", {}).get("info", "Unknown error")
                    raise MediaWikiClientError(f"Upload failed: {error}")
            except FileNotFoundError:
                raise MediaWikiClientError(f"File not found: {file_path}")
            except APIError as e:
                raise MediaWikiClientError(f"API error: {str(e)}")
        
        return self._retry_on_error(_upload)
    
    def get_categories(self, title: str) -> List[str]:
        """获取页面的分类
        
        Args:
            title: 页面标题
            
        Returns:
            List[str]: 分类列表
        """
        page = self.get_page(title)
        if page:
            return page.categories
        return []
    
    def get_all_pages(
        self,
        namespace: int = 0,
        limit: Optional[int] = None
    ) -> List[str]:
        """获取所有页面标题
        
        Args:
            namespace: 命名空间
            limit: 数量限制（None 表示不限制）
            
        Returns:
            List[str]: 页面标题列表
        """
        self._ensure_connected()
        
        def _get_all():
            pages = []
            count = 0
            for page in self.site.allpages(namespace=namespace):
                pages.append(page.name)
                count += 1
                if limit and count >= limit:
                    break
            return pages
        
        return self._retry_on_error(_get_all)
    
    def get_page_info(self, title: str) -> Optional[Dict[str, Any]]:
        """获取页面信息
        
        Args:
            title: 页面标题
            
        Returns:
            Optional[Dict]: 页面信息字典
        """
        page = self.get_page(title)
        if page:
            return {
                "title": page.title,
                "revision_id": page.revision_id,
                "last_modified": page.last_modified.isoformat(),
                "categories": page.categories,
                "links_count": len(page.links),
                "url": page.url
            }
        return None

