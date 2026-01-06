"""Wikipedia 工具实现"""

import webbrowser
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.wikipedia import WikipediaService, WikipediaServiceError


class WikipediaTool(Tool):
    """Wikipedia 工具
    
    支持多种操作：搜索、获取页面内容、在浏览器中打开页面等。
    """
    
    def __init__(self):
        """初始化 Wikipedia 工具"""
        parameters = [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型："
                    "'search'（搜索）、'get_page'（获取页面内容）、'open_page'（在浏览器中打开页面）、"
                    "'get_page_links'（获取页面链接）、'get_page_categories'（获取页面分类）、"
                    "'get_page_images'（获取页面图片）、'get_page_references'（获取页面引用）、"
                    "'related_pages'（获取相关页面）、'featured_article'（获取今日特色文章）"
                ),
                required=True,
                enum=["search", "get_page", "open_page", "get_page_links", "get_page_categories", 
                      "get_page_images", "get_page_references", "related_pages", "featured_article"]
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词或页面标题（必需）",
                required=True
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="搜索结果数量（1-20，默认 5，仅用于 search 操作）",
                required=False,
                default=5
            ),
            ToolParameter(
                name="language",
                type="string",
                description="语言代码（可选，如 'zh' 中文、'en' 英文，默认 'zh'）",
                required=False,
                default="zh"
            ),
            ToolParameter(
                name="summary_only",
                type="boolean",
                description="是否只返回摘要（默认 true，仅用于 get_page 操作）",
                required=False,
                default=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="限制返回数量（可选，用于 get_page_links、get_page_images、get_page_references、related_pages）",
                required=False
            ),
        ]
        
        super().__init__(
            name="wikipedia",
            description=(
                "Wikipedia 工具，支持多种操作模式。"
                "\n操作类型："
                "- search: 搜索 Wikipedia 页面"
                "- get_page: 获取指定页面的内容（摘要或完整内容）"
                "- open_page: 在浏览器中打开指定页面"
                "- get_page_links: 获取页面的所有链接"
                "- get_page_categories: 获取页面的分类"
                "- get_page_images: 获取页面的图片列表"
                "- get_page_references: 获取页面的引用/参考文献"
                "- related_pages: 获取相关页面（通过页面链接）"
                "- featured_article: 获取今日特色文章"
                "\n参数说明："
                "- action: 操作类型（必需）"
                "- query: 搜索关键词或页面标题（必需，featured_article 不需要）"
                "- num_results: 搜索结果数量（1-20，默认 5，仅用于 search）"
                "- language: 语言代码（可选，默认 'zh'）"
                "- summary_only: 是否只返回摘要（默认 true，仅用于 get_page）"
                "- limit: 限制返回数量（可选，用于 get_page_links、get_page_images 等）"
                "\n使用场景："
                "- 搜索百科知识（search）"
                "- 获取页面详细内容（get_page）"
                "- 在浏览器中查看完整页面（open_page）"
                "- 浏览页面链接和分类（get_page_links、get_page_categories）"
                "- 查看页面图片和引用（get_page_images、get_page_references）"
                "- 发现相关内容（related_pages）"
                "- 阅读特色文章（featured_article）"
                "\n重要提示："
                "- 工具返回的结果中包含 'title' 和 'url' 两个字段"
                "- 生成 Markdown 链接时，必须使用 'title' 字段作为链接文本，'url' 字段作为链接地址"
                "- 格式：[title](url)，例如：[飞行时间质谱](https://zh.wikipedia.org/wiki/...)"
                "- 绝对不要从 URL 中提取标题，URL 中的标题是 URL 编码的（包含 %E6 等字符）"
                "- 绝对不要使用 URL 中的编码部分作为页面标题来调用 Wikipedia API"
                "- 如果需要获取页面内容，使用工具返回的 'title' 字段，而不是 URL"
                "\n注意："
                "- 无需 API key，完全免费"
                "- 支持多语言"
                "- 建议用于获取权威的知识库信息"
            ),
            parameters=parameters
        )
        
        # 延迟初始化搜索服务（避免启动时失败）
        self._search_service: Optional[WikipediaService] = None
    
    def _get_search_service(self, language: str = "zh") -> WikipediaService:
        """获取搜索服务实例（延迟初始化）"""
        if self._search_service is None or self._search_service.language != language:
            try:
                self._search_service = WikipediaService(language=language)
            except Exception as e:
                raise RuntimeError(
                    f"Wikipedia 搜索服务初始化失败: {str(e)}"
                )
        return self._search_service
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行 Wikipedia 操作
        
        Args:
            action: 操作类型（'search'、'get_page' 或 'open_page'）
            query: 搜索关键词或页面标题
            num_results: 搜索结果数量（仅用于 search）
            language: 语言代码（可选，默认 'zh'）
            summary_only: 是否只返回摘要（仅用于 get_page）
            
        Returns:
            ToolResult: 操作结果
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 获取参数
            action = kwargs.get("action", "search")
            query = kwargs.get("query")
            num_results = kwargs.get("num_results", 5)
            language = kwargs.get("language", "zh")
            summary_only = kwargs.get("summary_only", True)
            
            if not query:
                return ToolResult(
                    success=False,
                    error="query 参数是必需的"
                )
            
            service = self._get_search_service(language=language)
            
            # 根据操作类型执行不同的操作
            limit = kwargs.get("limit")
            
            if action == "search":
                return self._handle_search(service, query, num_results, language)
            elif action == "get_page":
                return self._handle_get_page(service, query, language, summary_only)
            elif action == "open_page":
                return self._handle_open_page(service, query, language)
            elif action == "get_page_links":
                return self._handle_get_page_links(service, query, language, limit)
            elif action == "get_page_categories":
                return self._handle_get_page_categories(service, query, language)
            elif action == "get_page_images":
                return self._handle_get_page_images(service, query, language, limit)
            elif action == "get_page_references":
                return self._handle_get_page_references(service, query, language, limit)
            elif action == "related_pages":
                return self._handle_related_pages(service, query, language, limit or 10)
            elif action == "featured_article":
                return self._handle_featured_article(service, language)
            else:
                return ToolResult(
                    success=False,
                    error=f"未知的操作类型: {action}。支持的操作：'search'、'get_page'、'open_page'、'get_page_links'、'get_page_categories'、'get_page_images'、'get_page_references'、'related_pages'、'featured_article'"
                )
            
        except WikipediaServiceError as e:
            return ToolResult(
                success=False,
                error=f"Wikipedia 操作失败: {str(e)}"
            )
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Wikipedia 操作异常: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"操作失败: {str(e)}"
            )
    
    def _handle_search(
        self,
        service: WikipediaService,
        query: str,
        num_results: int,
        language: str
    ) -> ToolResult:
        """处理搜索操作"""
        # 限制结果数量
        num_results = max(1, min(20, num_results))
        
        # 执行搜索
        response = service.search(
            query=query,
            num_results=num_results,
            language=language
        )
        
        # 格式化结果
        results = []
        for result in response.results:
            results.append({
                "title": result.title,
                "page_id": result.page_id,
                "url": result.url,
                "snippet": result.snippet
            })
        
        # 构建摘要
        summary = (
            f"找到 {len(results)} 条结果"
            f"{f'（共 {response.total_results} 条）' if response.total_results else ''}"
            f"，耗时 {response.search_time:.2f} 秒"
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "search",
                "results": results,
                "count": len(results),
                "total_results": response.total_results,
                "search_time": response.search_time,
                "query": response.query,
                "language": response.language,
                "summary": summary
            }
        )
    
    def _handle_get_page(
        self,
        service: WikipediaService,
        title: str,
        language: str,
        summary_only: bool
    ) -> ToolResult:
        """处理获取页面内容操作"""
        page = service.get_page(
            title=title,
            language=language,
            summary_only=summary_only
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "get_page",
                "title": page.title,
                "page_id": page.page_id,
                "summary": page.summary,
                "content": page.content if not summary_only else None,
                "url": page.url,
                "language": page.language,
                "summary_length": len(page.summary),
                "has_full_content": page.content is not None
            }
        )
    
    def _handle_open_page(
        self,
        service: WikipediaService,
        title: str,
        language: str
    ) -> ToolResult:
        """处理在浏览器中打开页面操作"""
        try:
            # 获取页面 URL
            page = service.get_page(
                title=title,
                language=language,
                summary_only=True  # 只需要 URL，不需要内容
            )
            
            if not page.url:
                return ToolResult(
                    success=False,
                    error=f"无法获取页面 URL: {title}"
                )
            
            # 在浏览器中打开
            webbrowser.open(page.url)
            
            return ToolResult(
                success=True,
                data={
                    "action": "open_page",
                    "title": page.title,
                    "url": page.url,
                    "language": page.language,
                    "message": f"已在浏览器中打开: {page.title}"
                }
            )
            
        except WikipediaServiceError as e:
            return ToolResult(
                success=False,
                error=f"无法打开页面: {str(e)}"
            )
    
    def _handle_get_page_links(
        self,
        service: WikipediaService,
        title: str,
        language: str,
        limit: Optional[int]
    ) -> ToolResult:
        """处理获取页面链接操作"""
        result = service.get_page_links(
            title=title,
            language=language,
            limit=limit
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "get_page_links",
                "title": result.title,
                "url": result.url,
                "links": result.links,
                "links_count": result.links_count,
                "language": result.language,
                "message": f"找到 {result.links_count} 个链接"
            }
        )
    
    def _handle_get_page_categories(
        self,
        service: WikipediaService,
        title: str,
        language: str
    ) -> ToolResult:
        """处理获取页面分类操作"""
        result = service.get_page_categories(
            title=title,
            language=language
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "get_page_categories",
                "title": result.title,
                "url": result.url,
                "categories": result.categories,
                "categories_count": result.categories_count,
                "language": result.language,
                "message": f"找到 {result.categories_count} 个分类"
            }
        )
    
    def _handle_get_page_images(
        self,
        service: WikipediaService,
        title: str,
        language: str,
        limit: Optional[int]
    ) -> ToolResult:
        """处理获取页面图片操作"""
        result = service.get_page_images(
            title=title,
            language=language,
            limit=limit
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "get_page_images",
                "title": result.title,
                "url": result.url,
                "images": result.images,
                "images_count": result.images_count,
                "language": result.language,
                "message": f"找到 {result.images_count} 张图片"
            }
        )
    
    def _handle_get_page_references(
        self,
        service: WikipediaService,
        title: str,
        language: str,
        limit: Optional[int]
    ) -> ToolResult:
        """处理获取页面引用操作"""
        result = service.get_page_references(
            title=title,
            language=language,
            limit=limit
        )
        
        return ToolResult(
            success=True,
            data={
                "action": "get_page_references",
                "title": result.title,
                "url": result.url,
                "references": result.references,
                "references_count": result.references_count,
                "language": result.language,
                "message": f"找到 {result.references_count} 个引用"
            }
        )
    
    def _handle_related_pages(
        self,
        service: WikipediaService,
        title: str,
        language: str,
        limit: int
    ) -> ToolResult:
        """处理获取相关页面操作"""
        response = service.get_related_pages(
            title=title,
            language=language,
            limit=limit
        )
        
        results = []
        for result in response.results:
            results.append({
                "title": result.title,
                "page_id": result.page_id,
                "url": result.url
            })
        
        return ToolResult(
            success=True,
            data={
                "action": "related_pages",
                "title": title,
                "results": results,
                "count": len(results),
                "language": response.language,
                "message": f"找到 {len(results)} 个相关页面"
            }
        )
    
    def _handle_featured_article(
        self,
        service: WikipediaService,
        language: str
    ) -> ToolResult:
        """处理获取特色文章操作"""
        result = service.get_featured_article(language=language)
        
        return ToolResult(
            success=True,
            data={
                "action": "featured_article",
                "title": result.title,
                "url": result.url,
                "summary": result.summary,
                "language": result.language,
                "message": f"今日特色文章: {result.title}"
            }
        )

