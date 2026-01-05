"""统一文件搜索服务"""

import platform
import time
import logging
from typing import Optional

from .models import FileSearchRequest, FileSearchResponse, FileSearchResult
from .platform.macos_search import MacOSSearchAdapter
from .platform.base import PlatformAdapter

logger = logging.getLogger(__name__)


class FileSearchService:
    """统一文件搜索服务
    
    根据平台自动选择适配器，提供统一的搜索接口。
    """
    
    def __init__(self):
        """初始化搜索服务"""
        self.adapter = self._create_adapter()
        logger.info(f"FileSearchService initialized with {type(self.adapter).__name__}")
    
    def _create_adapter(self) -> PlatformAdapter:
        """根据平台创建适配器
        
        Returns:
            PlatformAdapter: 平台适配器实例
            
        Raises:
            NotImplementedError: 如果平台不支持
        """
        system = platform.system()
        if system == 'Darwin':  # macOS
            return MacOSSearchAdapter()
        else:
            raise NotImplementedError(
                f"Platform {system} not supported yet. "
                "Currently only macOS is supported."
            )
    
    def search(self, request: FileSearchRequest) -> FileSearchResponse:
        """执行搜索
        
        Args:
            request: 搜索请求
            
        Returns:
            FileSearchResponse: 搜索结果响应
            
        Raises:
            RuntimeError: 当搜索失败时抛出
        """
        start_time = time.time()
        
        try:
            # 根据搜索类型调用不同的方法
            if request.content_search:
                results = self.adapter.search_by_content(
                    request.query,
                    request.path,
                    request.file_type,
                    request.limit
                )
                search_type = "content"
            else:
                results = self.adapter.search_by_name(
                    request.query,
                    request.path,
                    request.file_type,
                    request.limit
                )
                search_type = "name"
            
            # 应用排序
            if request.sort_by:
                results = self._sort_results(results, request.sort_by, request.sort_order)
            
            # 应用分页
            total = len(results)
            paginated_results = results[request.offset:request.offset + request.limit]
            has_more = (request.offset + request.limit) < total
            
            # 计算搜索耗时
            search_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 构建查询摘要
            query_summary = self._build_query_summary(request)
            
            # 获取平台信息
            platform_name = platform.system().lower()
            if platform_name == 'darwin':
                platform_name = 'macos'
            
            logger.info(
                f"Search completed: {len(paginated_results)}/{total} results "
                f"(has_more={has_more}), {search_time:.2f}ms, type={search_type}"
            )
            
            return FileSearchResponse(
                results=paginated_results,
                total=total,
                limit=request.limit,
                offset=request.offset,
                has_more=has_more,
                search_time_ms=search_time,
                search_type=search_type,
                platform=platform_name,
                query_summary=query_summary
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _sort_results(
        self,
        results: list[FileSearchResult],
        sort_by: str,
        sort_order: str
    ) -> list[FileSearchResult]:
        """对搜索结果进行排序
        
        Args:
            results: 搜索结果列表
            sort_by: 排序字段（name, size, modified_time）
            sort_order: 排序顺序（asc, desc）
            
        Returns:
            list[FileSearchResult]: 排序后的结果列表
        """
        reverse = sort_order.lower() == 'desc'
        
        if sort_by == 'name':
            return sorted(results, key=lambda x: x.name.lower(), reverse=reverse)
        elif sort_by == 'size':
            return sorted(results, key=lambda x: x.size, reverse=reverse)
        elif sort_by == 'modified_time':
            return sorted(results, key=lambda x: x.modified_time, reverse=reverse)
        else:
            logger.warning(f"Unknown sort_by field: {sort_by}, using default (name)")
            return sorted(results, key=lambda x: x.name.lower(), reverse=reverse)
    
    def _build_query_summary(self, request: FileSearchRequest) -> str:
        """构建查询摘要
        
        Args:
            request: 搜索请求
            
        Returns:
            str: 查询摘要字符串
        """
        parts = []
        parts.append(f"query='{request.query}'")
        
        if request.path:
            parts.append(f"path='{request.path}'")
        
        if request.file_type:
            parts.append(f"type='{request.file_type}'")
        
        if request.content_search:
            parts.append("content_search=true")
        
        if request.sort_by:
            parts.append(f"sort={request.sort_by}({request.sort_order})")
        
        parts.append(f"limit={request.limit}, offset={request.offset}")
        
        return ", ".join(parts)
