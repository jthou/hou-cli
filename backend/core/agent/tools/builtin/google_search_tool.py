"""Google 搜索工具实现"""

import asyncio
import concurrent.futures
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.google_search import GoogleSearchService, GoogleSearchServiceError


class GoogleSearchTool(Tool):
    """Google 搜索工具
    
    允许 AI 助手使用 Google 搜索获取网络信息。
    """
    
    def __init__(self):
        """初始化 Google 搜索工具"""
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词或查询语句",
                required=True
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="返回结果数量（1-10，默认 5）",
                required=False,
                default=5
            ),
            ToolParameter(
                name="language",
                type="string",
                description="语言代码（可选，如 'zh-CN' 中文、'en' 英文）",
                required=False
            ),
        ]
        
        super().__init__(
            name="google_search",
            description=(
                "使用 Google 搜索获取网络信息。"
                "\n参数说明："
                "- query: 搜索关键词或查询语句（必需）"
                "- num_results: 返回结果数量（1-10，默认 5）"
                "- language: 语言代码（可选，如 'zh-CN' 中文、'en' 英文）"
                "\n使用场景："
                "- 获取最新的网络信息"
                "- 查找技术文档和教程"
                "- 搜索新闻和实时信息"
                "- 查找特定主题的参考资料"
                "\n注意："
                "- 每天有 100 次免费查询限制"
                "- 建议在需要最新信息或本地无法获取的信息时使用"
            ),
            parameters=parameters
        )
        
        # 延迟初始化搜索服务（避免启动时失败）
        self._search_service: Optional[GoogleSearchService] = None
    
    def _get_search_service(self) -> GoogleSearchService:
        """获取搜索服务实例（延迟初始化）"""
        if self._search_service is None:
            try:
                self._search_service = GoogleSearchService()
            except GoogleSearchServiceError as e:
                raise RuntimeError(
                    f"Google 搜索服务初始化失败: {str(e)}\n"
                    "请确保在 .env 文件中配置了 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID。"
                )
        return self._search_service
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行 Google 搜索
        
        Args:
            query: 搜索关键词或查询语句
            num_results: 返回结果数量（1-10，默认 5）
            language: 语言代码（可选）
            
        Returns:
            ToolResult: 搜索结果
        """
        try:
            # 获取参数
            query = kwargs.get("query")
            num_results = kwargs.get("num_results", 5)
            language = kwargs.get("language")
            
            if not query:
                return ToolResult(
                    success=False,
                    error="query 参数是必需的"
                )
            
            # 限制结果数量
            num_results = max(1, min(10, num_results))
            
            # 执行搜索（异步）
            service = self._get_search_service()
            
            # 检查是否已有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果已有运行的事件循环，使用线程池执行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(service.search(
                            query=query,
                            num_results=num_results,
                            language=language
                        ))
                    )
                    response = future.result(timeout=30)
            except RuntimeError:
                # 没有运行的事件循环，可以直接使用 asyncio.run
                response = asyncio.run(service.search(
                    query=query,
                    num_results=num_results,
                    language=language
                ))
            except concurrent.futures.TimeoutError:
                return ToolResult(
                    success=False,
                    error="Google 搜索超时，请稍后重试"
                )
            
            # 格式化结果
            results = []
            for result in response.results:
                results.append({
                    "title": result.title,
                    "link": result.link,
                    "snippet": result.snippet,
                    "display_link": result.display_link
                })
            
            # 构建摘要
            summary = (
                f"找到 {len(results)} 条结果"
                f"{f'（共 {response.total_results:,} 条）' if response.total_results else ''}"
                f"，耗时 {response.search_time:.2f} 秒"
            )
            
            return ToolResult(
                success=True,
                data={
                    "results": results,
                    "count": len(results),
                    "total_results": response.total_results,
                    "search_time": response.search_time,
                    "query": response.query,
                    "summary": summary
                }
            )
            
        except GoogleSearchServiceError as e:
            return ToolResult(
                success=False,
                error=f"Google 搜索失败: {str(e)}"
            )
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"搜索失败: {str(e)}"
            )

