"""MediaWiki 工具实现"""

import re
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.mediawiki_client_service import MediaWikiClientService
from backend.services.mediawiki_client_service.models import MediaWikiPage, MediaWikiSearchResult
from backend.services.mediawiki_client_service.utils import format_page_link, format_page_list_with_links


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
                "\n使用示例："
                "- 搜索：operation='search', query='关键词'"
                "- 读取：operation='read', title='页面标题'"
                "- 编辑：operation='edit', title='页面标题', content='新内容'"
                "- 创建：operation='create', title='页面标题', content='内容'"
                "\n重要提示："
                "当输出 MediaWiki 页面列表时，请使用 format_page_link() 或 format_page_list_with_links() 函数"
                "为每个页面标题添加可点击的链接。这些函数可以从 backend.services.mediawiki.utils 导入。"
                "链接格式为 Markdown：[页面标题](URL)，可以在支持 Markdown 的终端中点击打开浏览器。"
            ),
            parameters=parameters
        )
        
        # 延迟初始化客户端（避免启动时失败）
        self._client: Optional[MediaWikiClientService] = None
    
    def _ensure_category(self, content: str, category: str = "hou-cli") -> str:
        """
        确保内容中包含指定的分类
        
        Args:
            content: 页面内容
            category: 分类名称（不包含 Category: 前缀）
            
        Returns:
            包含分类的内容
        """
        category_tag = f"[[Category:{category}]]"
        
        # 检查是否已包含该分类
        # 支持多种格式：[[Category:hou-cli]]、[[Category: hou-cli]]、[[分类:hou-cli]] 等
        pattern = rf'\[\[Category:\s*{re.escape(category)}\s*\]\]'
        if re.search(pattern, content, re.IGNORECASE):
            # 分类已存在，直接返回
            return content
        
        # 查找所有现有的分类标签位置
        category_pattern = r'\[\[Category:[^\]]+\]\]'
        matches = list(re.finditer(category_pattern, content, re.IGNORECASE))
        
        if matches:
            # 如果已有分类，在最后一个分类后添加
            last_match = matches[-1]
            insert_pos = last_match.end()
            # 在最后一个分类后添加换行和新的分类
            new_content = content[:insert_pos] + f"\n{category_tag}" + content[insert_pos:]
        else:
            # 如果没有分类，在内容末尾添加
            # 确保末尾有换行
            if content and not content.endswith('\n'):
                new_content = content + f"\n\n{category_tag}"
            else:
                new_content = content + f"{category_tag}"
        
        return new_content
    
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
            # 为每个结果添加 Markdown 格式的链接
            link = format_page_link(result.title, link_text=result.title)
            formatted_results.append({
                "title": result.title,
                "title_link": link,  # 添加链接格式
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
                "summary": f"找到 {len(results)} 个相关页面（点击标题可在浏览器中打开）"
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
                "title_link": format_page_link(page.title, link_text=page.title),  # 添加链接格式（Markdown，可点击）
                "content": page.content,
                "url": page.url,
                "categories": page.categories,
                "links_count": len(page.links),
                "last_modified": page.last_modified.isoformat(),
                "summary": f"成功读取页面 '{title}'，包含 {len(page.categories)} 个分类（点击标题可在浏览器中打开）"
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
        
        # 自动添加 [[Category:hou-cli]] 分类
        content = self._ensure_category(content, "hou-cli")
        
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
        
        # 自动添加 [[Category:hou-cli]] 分类
        content = self._ensure_category(content, "hou-cli")
        
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

