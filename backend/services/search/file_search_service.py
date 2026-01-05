"""统一文件搜索服务"""

import platform
import time
import logging
import hashlib
import threading
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

from .models import FileSearchRequest, FileSearchResponse, FileSearchResult
from .platform.macos_search import MacOSSearchAdapter
from .platform.base import PlatformAdapter

logger = logging.getLogger(__name__)


class SearchCache:
    """搜索结果缓存
    
    使用内存缓存存储搜索结果，支持 TTL（Time To Live）。
    """
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        """初始化缓存
        
        Args:
            ttl_seconds: 缓存过期时间（秒），默认 5 分钟
            max_size: 最大缓存条目数，默认 100
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[FileSearchResponse, datetime]] = {}
        self._lock = threading.RLock()
    
    def _generate_key(self, request: FileSearchRequest) -> str:
        """生成缓存键
        
        Args:
            request: 搜索请求
            
        Returns:
            str: 缓存键
        """
        # 使用请求的关键字段生成哈希键
        key_data = f"{request.query}:{request.path}:{request.file_type}:{request.content_search}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, request: FileSearchRequest) -> Optional[FileSearchResponse]:
        """获取缓存结果
        
        Args:
            request: 搜索请求
            
        Returns:
            Optional[FileSearchResponse]: 缓存的结果，如果不存在或已过期则返回 None
        """
        with self._lock:
            key = self._generate_key(request)
            if key not in self._cache:
                return None
            
            response, cached_time = self._cache[key]
            
            # 检查是否过期
            if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
                del self._cache[key]
                return None
            
            # 返回缓存的响应（需要根据请求的 limit 和 offset 重新分页）
            return self._apply_pagination(response, request)
    
    def _apply_pagination(self, cached_response: FileSearchResponse, request: FileSearchRequest) -> FileSearchResponse:
        """对缓存结果应用新的分页参数
        
        Args:
            cached_response: 缓存的响应
            request: 新的搜索请求
            
        Returns:
            FileSearchResponse: 应用分页后的响应
        """
        # 如果分页参数相同，直接返回
        if (cached_response.limit == request.limit and 
            cached_response.offset == request.offset):
            return cached_response
        
        # 应用新的分页
        total = len(cached_response.results)
        paginated_results = cached_response.results[request.offset:request.offset + request.limit]
        has_more = (request.offset + request.limit) < total
        
        return FileSearchResponse(
            results=paginated_results,
            total=total,
            limit=request.limit,
            offset=request.offset,
            has_more=has_more,
            search_time_ms=cached_response.search_time_ms,
            search_type=cached_response.search_type,
            platform=cached_response.platform,
            query_summary=cached_response.query_summary
        )
    
    def set(self, request: FileSearchRequest, response: FileSearchResponse):
        """设置缓存结果
        
        Args:
            request: 搜索请求
            response: 搜索结果响应
        """
        with self._lock:
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self.max_size:
                # 删除最旧的条目
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][1]
                )
                del self._cache[oldest_key]
            
            key = self._generate_key(request)
            # 存储完整的结果列表（不分页），以便后续可以应用不同的分页
            self._cache[key] = (response, datetime.now())
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息
        
        Returns:
            Dict[str, int]: 缓存统计信息
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }


class FileSearchService:
    """统一文件搜索服务
    
    根据平台自动选择适配器，提供统一的搜索接口。
    """
    
    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 300):
        """初始化搜索服务
        
        Args:
            cache_enabled: 是否启用缓存
            cache_ttl: 缓存过期时间（秒），默认 5 分钟
        """
        # #region agent log
        import json
        log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H1",
                "location": "file_search_service.py:151",
                "message": "FileSearchService.__init__ entry",
                "data": {},
                "timestamp": int(__import__("time").time() * 1000)
            }) + "\n")
        # #endregion
        # #region agent log
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H2",
                "location": "file_search_service.py:158",
                "message": "Before _create_adapter",
                "data": {},
                "timestamp": int(__import__("time").time() * 1000)
            }) + "\n")
        # #endregion
        try:
            self.adapter = self._create_adapter()
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H2",
                    "location": "file_search_service.py:162",
                    "message": "After _create_adapter success",
                    "data": {"adapter_type": type(self.adapter).__name__},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
        except Exception as e:
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H2",
                    "location": "file_search_service.py:168",
                    "message": "_create_adapter failed",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            raise
        self.cache_enabled = cache_enabled
        self.cache = SearchCache(ttl_seconds=cache_ttl) if cache_enabled else None
        logger.info(
            f"FileSearchService initialized with {type(self.adapter).__name__}, "
            f"cache={'enabled' if cache_enabled else 'disabled'}"
        )
    
    def _create_adapter(self) -> PlatformAdapter:
        """根据平台创建适配器
        
        Returns:
            PlatformAdapter: 平台适配器实例
            
        Raises:
            NotImplementedError: 如果平台不支持
        """
        # #region agent log
        import json
        log_path = "/home/robo/justin/hou-cli/.cursor/debug.log"
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H2",
                "location": "file_search_service.py:166",
                "message": "_create_adapter entry",
                "data": {"system": platform.system()},
                "timestamp": int(__import__("time").time() * 1000)
            }) + "\n")
        # #endregion
        system = platform.system()
        if system == 'Darwin':  # macOS
            return MacOSSearchAdapter()
        elif system == 'Linux':
            # #region agent log
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H2",
                    "location": "file_search_service.py:178",
                    "message": "Before LinuxSearchAdapter import",
                    "data": {},
                    "timestamp": int(__import__("time").time() * 1000)
                }) + "\n")
            # #endregion
            try:
                from .platform.linux_search import LinuxSearchAdapter
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H2",
                        "location": "file_search_service.py:181",
                        "message": "Before LinuxSearchAdapter init",
                        "data": {},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
                adapter = LinuxSearchAdapter()
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H2",
                        "location": "file_search_service.py:186",
                        "message": "After LinuxSearchAdapter init success",
                        "data": {"adapter_type": type(adapter).__name__},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
                return adapter
            except ImportError as e:
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H2",
                        "location": "file_search_service.py:193",
                        "message": "LinuxSearchAdapter ImportError",
                        "data": {"error": str(e)},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
                raise NotImplementedError(
                    f"Linux platform adapter not available. "
                    "Please ensure linux_search.py exists."
                )
            except Exception as e:
                # #region agent log
                with open(log_path, "a") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H2",
                        "location": "file_search_service.py:201",
                        "message": "LinuxSearchAdapter init Exception",
                        "data": {"error": str(e), "error_type": type(e).__name__},
                        "timestamp": int(__import__("time").time() * 1000)
                    }) + "\n")
                # #endregion
                raise
        else:
            raise NotImplementedError(
                f"Platform {system} not supported yet. "
                "Currently only macOS and Linux are supported."
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
            # 检查缓存
            if self.cache_enabled and self.cache:
                cached_response = self.cache.get(request)
                if cached_response:
                    logger.debug(f"Cache hit for query: {request.query}")
                    return cached_response
            
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
            
            response = FileSearchResponse(
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
            
            # 缓存结果（存储完整结果，不分页）
            if self.cache_enabled and self.cache:
                # 创建完整结果的响应用于缓存
                full_response = FileSearchResponse(
                    results=results,  # 完整结果列表
                    total=total,
                    limit=request.limit,
                    offset=0,  # 缓存时使用 offset=0
                    has_more=False,  # 缓存完整结果
                    search_time_ms=search_time,
                    search_type=search_type,
                    platform=platform_name,
                    query_summary=query_summary
                )
                self.cache.set(request, full_response)
            
            return response
            
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
    
    def search_concurrent(
        self,
        requests: list[FileSearchRequest],
        max_workers: int = 5
    ) -> list[FileSearchResponse]:
        """并发执行多个搜索请求
        
        Args:
            requests: 搜索请求列表
            max_workers: 最大并发数
            
        Returns:
            list[FileSearchResponse]: 搜索结果响应列表
        """
        import concurrent.futures
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有搜索任务
            future_to_request = {
                executor.submit(self.search, request): request
                for request in requests
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_request):
                request = future_to_request[future]
                try:
                    response = future.result()
                    results.append(response)
                except Exception as e:
                    logger.error(f"Concurrent search failed for {request.query}: {e}")
                    # 创建错误响应
                    error_response = FileSearchResponse(
                        results=[],
                        total=0,
                        limit=request.limit,
                        offset=request.offset,
                        has_more=False,
                        search_time_ms=0,
                        search_type="name",
                        platform=platform.system().lower(),
                        query_summary=self._build_query_summary(request)
                    )
                    results.append(error_response)
        
        return results
