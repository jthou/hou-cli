"""网页搜索工具实现（Tavily API 或 DuckDuckGo，有 TAVILY_API_KEY 时优先 Tavily）"""

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.google_search_service.unified_search import web_search


class GoogleSearchTool(Tool):
    """网页搜索工具（通过 DuckDuckGo 获取结果，与原有 google_search 工具同名、同参数）"""

    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词或查询语句",
                required=True,
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="返回结果数量（可设置，建议 1–100，默认 10）",
                required=False,
                default=10,
            ),
            ToolParameter(
                name="language",
                type="string",
                description="语言代码（可选，如 'zh-CN' 中文、'en' 英文）",
                required=False,
            ),
        ]
        super().__init__(
            name="google_search",
            description=(
                "使用网页搜索获取网络信息（有 TAVILY_API_KEY 时用 Tavily，否则用 DuckDuckGo）。"
                "\n参数说明："
                "- query: 搜索关键词或查询语句（必需）"
                "- num_results: 返回结果数量（可设置，建议 1–100，默认 10）"
                "- language: 语言代码（可选，如 'zh-CN'、'en'）"
                "\n使用场景："
                "- 获取最新网络信息、技术文档、新闻与参考资料"
            ),
            parameters=parameters,
        )

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        num_results = kwargs.get("num_results", 10)
        language = kwargs.get("language")

        if not query:
            return ToolResult(success=False, error="query 参数是必需的")
        num_results = max(1, min(100, num_results))

        try:
            response = web_search(
                query=query,
                num_results=num_results,
                language=language,
            )
        except Exception as e:
            return ToolResult(success=False, error=f"搜索失败: {str(e)}")

        results = [
            {
                "title": r.title,
                "link": r.link,
                "snippet": r.snippet,
                "display_link": r.display_link,
            }
            for r in response.results
        ]
        summary = (
            f"找到 {len(results)} 条结果，耗时 {response.search_time:.2f} 秒"
            if response.search_time is not None
            else f"找到 {len(results)} 条结果"
        )
        return ToolResult(
            success=True,
            data={
                "results": results,
                "count": len(results),
                "total_results": response.total_results,
                "search_time": response.search_time,
                "query": response.query,
                "summary": summary,
            },
        )
