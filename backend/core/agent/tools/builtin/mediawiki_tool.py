"""MediaWiki 工具实现"""

from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.mediawiki import MediaWikiClientService
from backend.services.mediawiki.models import MediaWikiPage, MediaWikiSearchResult


class MediaWikiTool(Tool):
    """MediaWiki 工具
    
    允许 AI 助手搜索、读取、编辑和创建 MediaWiki 页面。
    """
    
    def __init__(self):
        """初始化 MediaWiki 工具"""
        parameters = [
            ToolParameter(
                name="operation",
                type="string",
                description="操作类型：'search'（搜索）、'read'（读取）、'edit'（编辑）、'create'（创建）、'info'（获取信息）",
                required=True,
                enum=["search", "read", "edit", "create", "info"]
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词（operation='search' 时必需）",
                required=False
            ),
            ToolParameter(
                name="title",
                type="string",
                description="页面标题（operation='read'、'edit'、'create'、'info' 时必需）",
                required=False
            ),
            ToolParameter(
                name="content",
                type="string",
                description="页面内容（operation='edit'、'create' 时必需，wikitext 格式）",
                required=False
            ),
            ToolParameter(
                name="summary",
                type="string",
                description="编辑摘要（operation='edit'、'create' 时可选）",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="搜索结果数量限制（operation='search' 时可选，默认 10）",
                required=False,
                default=10
            ),
        ]
        
        super().__init__(
            name="mediawiki",
            description=(
                "访问和操作 MediaWiki 网站。可以搜索页面、读取页面内容、编辑现有页面、创建新页面。"
                "使用示例："
                "- 搜索：operation='search', query='关键词'"
                "- 读取：operation='read', title='页面标题'"
                "- 编辑：operation='edit', title='页面标题', content='新内容'"
                "- 创建：operation='create', title='页面标题', content='内容'"
            ),
            parameters=parameters
        )
        
        # 延迟初始化客户端（避免启动时失败）
        self._client: Optional[MediaWikiClientService] = None
    
    def _get_client(self) -> MediaWikiClientService:
        """获取 MediaWiki 客户端实例（延迟初始化）"""
        if self._client is None:
            try:
                self._client = MediaWikiClientService()
                self._client.connect()
            except Exception as e:
                raise RuntimeError(
                    f"MediaWiki 客户端初始化失败: {str(e)}\n"
                    "请确保已配置 MEDIAWIKI_URL、MEDIAWIKI_USERNAME、MEDIAWIKI_PASSWORD 等环境变量。"
                )
        return self._client
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行 MediaWiki 操作
        
        Args:
            operation: 操作类型
            query: 搜索关键词
            title: 页面标题
            content: 页面内容
            summary: 编辑摘要
            limit: 结果数量限制
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            operation = kwargs.get("operation")
            
            if not operation:
                return ToolResult(
                    success=False,
                    error="operation 参数是必需的"
                )
            
            client = self._get_client()
            
            if operation == "search":
                return self._handle_search(client, kwargs)
            elif operation == "read":
                return self._handle_read(client, kwargs)
            elif operation == "edit":
                return self._handle_edit(client, kwargs)
            elif operation == "create":
                return self._handle_create(client, kwargs)
            elif operation == "info":
                return self._handle_info(client, kwargs)
            else:
                return ToolResult(
                    success=False,
                    error=f"未知操作类型: {operation}"
                )
                
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"MediaWiki 操作失败: {str(e)}"
            )
    
    def _handle_search(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """处理搜索操作"""
        query = kwargs.get("query")
        if not query:
            return ToolResult(
                success=False,
                error="search 操作需要 query 参数"
            )
        
        limit = kwargs.get("limit", 10)
        results = client.search_pages(query, limit=limit)
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "score": result.score
            })
        
        return ToolResult(
            success=True,
            data={
                "operation": "search",
                "query": query,
                "count": len(results),
                "results": formatted_results,
                "summary": f"找到 {len(results)} 个相关页面"
            }
        )
    
    def _handle_read(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """处理读取操作"""
        title = kwargs.get("title")
        if not title:
            return ToolResult(
                success=False,
                error="read 操作需要 title 参数"
            )
        
        page = client.get_page(title)
        
        if not page:
            return ToolResult(
                success=False,
                error=f"页面 '{title}' 不存在"
            )
        
        return ToolResult(
            success=True,
            data={
                "operation": "read",
                "title": page.title,
                "content": page.content,
                "url": page.url,
                "categories": page.categories,
                "links_count": len(page.links),
                "last_modified": page.last_modified.isoformat(),
                "summary": f"成功读取页面 '{title}'，包含 {len(page.categories)} 个分类"
            }
        )
    
    def _handle_edit(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """处理编辑操作"""
        title = kwargs.get("title")
        content = kwargs.get("content")
        
        if not title:
            return ToolResult(
                success=False,
                error="edit 操作需要 title 参数"
            )
        
        if not content:
            return ToolResult(
                success=False,
                error="edit 操作需要 content 参数"
            )
        
        summary = kwargs.get("summary", "由 AI 助手编辑")
        success = client.edit_page(title, content, summary=summary)
        
        if success:
            return ToolResult(
                success=True,
                data={
                    "operation": "edit",
                    "title": title,
                    "summary": summary,
                    "message": f"成功编辑页面 '{title}'"
                }
            )
        else:
            return ToolResult(
                success=False,
                error=f"编辑页面 '{title}' 失败"
            )
    
    def _handle_create(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """处理创建操作"""
        title = kwargs.get("title")
        content = kwargs.get("content")
        
        if not title:
            return ToolResult(
                success=False,
                error="create 操作需要 title 参数"
            )
        
        if not content:
            return ToolResult(
                success=False,
                error="create 操作需要 content 参数"
            )
        
        summary = kwargs.get("summary", "由 AI 助手创建")
        success = client.create_page(title, content, summary=summary)
        
        if success:
            return ToolResult(
                success=True,
                data={
                    "operation": "create",
                    "title": title,
                    "summary": summary,
                    "message": f"成功创建页面 '{title}'"
                }
            )
        else:
            return ToolResult(
                success=False,
                error=f"创建页面 '{title}' 失败"
            )
    
    def _handle_info(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """处理获取信息操作"""
        title = kwargs.get("title")
        if not title:
            return ToolResult(
                success=False,
                error="info 操作需要 title 参数"
            )
        
        info = client.get_page_info(title)
        
        if not info:
            return ToolResult(
                success=False,
                error=f"页面 '{title}' 不存在"
            )
        
        return ToolResult(
            success=True,
            data={
                "operation": "info",
                "info": info,
                "summary": f"页面 '{title}' 的信息"
            }
        )

