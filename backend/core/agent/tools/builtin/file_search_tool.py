"""文件搜索工具实现"""

from typing import Dict, Any, Optional, List
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.search import FileSearchService, FileSearchRequest


class FileSearchTool(Tool):
    """文件搜索工具
    
    允许AI助手搜索本地文件系统中的文件。
    """
    
    def __init__(self):
        """初始化文件搜索工具"""
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词或文件模式（如 '*.py', 'test', '*.xlsx'）",
                required=True
            ),
            ToolParameter(
                name="path",
                type="string",
                description="搜索路径限制（可选，如 '/Users/username/project'）",
                required=False
            ),
            ToolParameter(
                name="file_type",
                type="string",
                description=(
                    "文件类型过滤（可选），使用文件扩展名模式，如 '*.py'、'*.xlsx'、"
                    "'*.doc'、'*.docx'。根据用户需求自行决定要搜索的文件类型。"
                ),
                required=False
            ),
            ToolParameter(
                name="content_search",
                type="boolean",
                description="是否进行文件内容搜索（默认 false，仅搜索文件名）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="结果数量限制（默认 20，最大 100）",
                required=False,
                default=20
            ),
        ]
        
        super().__init__(
            name="file_search",
            description=(
                "搜索本地文件系统中的文件。支持文件名搜索和文件内容搜索。"
                "\n参数说明："
                "- query: 搜索模式，可以是文件名模式（支持通配符，如 '*.py'、'test*'）"
                "  或搜索关键词（用于内容搜索）"
                "- file_type: 文件类型过滤（可选），使用文件扩展名模式（如 '*.py'、"
                "'*.xlsx'、'*.doc'、'*.docx'）"
                "- content_search: 是否进行文件内容搜索（默认 false，仅搜索文件名）"
                "- path: 搜索路径限制（可选）"
                "- limit: 结果数量限制（默认 20，最大 100）"
                "\n使用示例："
                "- 搜索所有 Python 文件：query='*.py', file_type='*.py'"
                "- 搜索所有 Excel 文件：query='*.xlsx', file_type='*.xlsx'"
                "- 搜索包含特定内容的文件：query='关键词', content_search=true"
                "\n注意：根据用户需求，自行决定 query 和 file_type 参数的值。"
                "可以使用通配符、正则表达式模式或具体的文件扩展名。"
            ),
            parameters=parameters
        )
        
        # 延迟初始化搜索服务（避免启动时失败）
        self._search_service: Optional[FileSearchService] = None
    
    def _get_search_service(self) -> FileSearchService:
        """获取搜索服务实例（延迟初始化）"""
        if self._search_service is None:
            # #region agent log
            import json
            import os
            log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H1",
                    "location": "file_search_tool.py:64",
                    "message": "Before FileSearchService init",
                    "data": {},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            try:
                self._search_service = FileSearchService()
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H1",
                        "location": "file_search_tool.py:68",
                        "message": "After FileSearchService init success",
                        "data": {"service_type": type(self._search_service).__name__},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
            except Exception as e:
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H1",
                        "location": "file_search_tool.py:70",
                        "message": "FileSearchService init failed",
                        "data": {"error": str(e), "error_type": type(e).__name__},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
                raise RuntimeError(
                    f"文件搜索服务初始化失败: {str(e)}\n"
                    "请确保系统支持文件搜索（macOS 需要启用 Spotlight）。"
                )
        return self._search_service
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行文件搜索
        
        Args:
            query: 搜索关键词或文件模式
            path: 搜索路径限制（可选）
            file_type: 文件类型过滤（可选）
            content_search: 是否进行文件内容搜索
            limit: 结果数量限制
            
        Returns:
            ToolResult: 搜索结果
        """
        # #region agent log
        import json
        import os
        log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H4",
                "location": "file_search_tool.py:76",
                "message": "FileSearchTool.execute entry",
                "data": {"kwargs": kwargs},
                "timestamp": int(__import__("time").time() * 1000)
            }) + "\n")
        # #endregion
        try:
            # 获取参数
            query = kwargs.get("query")
            path = kwargs.get("path")
            file_type = kwargs.get("file_type")
            content_search = kwargs.get("content_search", False)
            limit = min(kwargs.get("limit", 20), 100)  # 限制最大值为 100
            
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H4",
                    "location": "file_search_tool.py:98",
                    "message": "Parameters extracted",
                    "data": {"query": query, "path": path, "file_type": file_type, "content_search": content_search, "limit": limit},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            
            if not query:
                return ToolResult(
                    success=False,
                    error="query 参数是必需的"
                )
            
            # 创建搜索请求
            request = FileSearchRequest(
                query=query,
                path=path,
                file_type=file_type,
                content_search=content_search,
                limit=limit,
                offset=0
            )
            
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H1",
                    "location": "file_search_tool.py:115",
                    "message": "Before _get_search_service",
                    "data": {"request_query": request.query, "request_file_type": request.file_type},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            
            # 执行搜索
            service = self._get_search_service()
            
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H1",
                    "location": "file_search_tool.py:120",
                    "message": "After _get_search_service",
                    "data": {"service_type": type(service).__name__},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H3",
                    "location": "file_search_tool.py:122",
                    "message": "Before service.search",
                    "data": {"request_query": request.query},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            
            response = service.search(request)
            
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H3",
                    "location": "file_search_tool.py:125",
                    "message": "After service.search",
                    "data": {"total": response.total, "results_count": len(response.results)},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            
            # 格式化结果
            results = []
            for result in response.results:
                results.append({
                    "path": result.path,
                    "name": result.name,
                    "size": result.size,
                    "size_human": self._format_size(result.size),
                    "modified_time": result.modified_time.isoformat(),
                    "file_type": result.file_type
                })
            
            # 即使没有结果，也返回成功，但提供明确的提示信息
            if response.total == 0:
                summary = (
                    f"未找到匹配的文件。"
                    f"搜索模式: {query}"
                    f"{f', 文件类型: {file_type}' if file_type else ''}"
                    f"{f', 搜索路径: {path}' if path else ''}"
                )
            else:
                summary = (
                    f"找到 {response.total} 个文件"
                    f"（显示前 {len(results)} 个，"
                    f"耗时 {response.search_time_ms:.2f}ms）"
                )
            
            return ToolResult(
                success=True,
                data={
                    "results": results,
                    "total": response.total,
                    "count": len(results),
                    "has_more": response.has_more,
                    "search_time_ms": response.search_time_ms,
                    "search_type": response.search_type,
                    "platform": response.platform,
                    "summary": summary
                }
            )
            
        except RuntimeError as e:
            # #region agent log
            import json
            import os
            log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H5",
                    "location": "file_search_tool.py:148",
                    "message": "RuntimeError caught",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            # #region agent log
            import json
            import os
            log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H5",
                    "location": "file_search_tool.py:153",
                    "message": "Exception caught",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            return ToolResult(
                success=False,
                error=f"文件搜索失败: {str(e)}"
            )
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

