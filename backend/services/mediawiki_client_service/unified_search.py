"""统一搜索服务"""

import logging
from typing import List, Dict, Any, Optional
from .client import MediaWikiClientService
from .models import MediaWikiSearchResult, UnifiedSearchResult

logger = logging.getLogger(__name__)


class UnifiedSearchService:
    """统一搜索服务
    
    同时在 MediaWiki 和知识库中搜索，合并结果。
    """
    
    def __init__(
        self,
        mediawiki_client: Optional[MediaWikiClientService] = None
    ):
        """初始化统一搜索服务
        
        Args:
            mediawiki_client: MediaWiki 客户端（如果为 None，会创建新实例）
        """
        self.mediawiki_client = mediawiki_client or MediaWikiClientService()
        if not self.mediawiki_client._connected:
            try:
                self.mediawiki_client.connect()
            except Exception as e:
                logger.warning(f"MediaWiki client connection failed: {e}")
        
        # 知识库搜索服务（延迟初始化）
        self._kb_search_service = None
    
    def _get_kb_search_service(self):
        """获取知识库搜索服务（延迟初始化）"""
        if self._kb_search_service is None:
            try:
                # TODO: 导入知识库搜索服务
                # from backend.infrastructure.knowledge.search import VectorSearchService
                # from backend.infrastructure.knowledge.vector_store import VectorStore
                # vector_store = VectorStore()
                # self._kb_search_service = VectorSearchService(vector_store)
                pass
            except Exception as e:
                logger.warning(f"Knowledge base search service not available: {e}")
        return self._kb_search_service
    
    def search(
        self,
        query: str,
        limit: int = 20,
        sources: Optional[List[str]] = None
    ) -> List[UnifiedSearchResult]:
        """统一搜索
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            sources: 搜索来源列表（["mediawiki", "knowledge_base"]），None 表示搜索所有来源
            
        Returns:
            List[UnifiedSearchResult]: 合并后的搜索结果
        """
        if sources is None:
            sources = ["mediawiki", "knowledge_base"]
        
        all_results = []
        
        # 搜索 MediaWiki
        if "mediawiki" in sources:
            try:
                wiki_results = self.search_wiki_only(query, limit=limit)
                all_results.extend(wiki_results)
            except Exception as e:
                logger.error(f"MediaWiki search failed: {e}")
        
        # 搜索知识库
        if "knowledge_base" in sources:
            try:
                kb_results = self.search_kb_only(query, limit=limit)
                all_results.extend(kb_results)
            except Exception as e:
                logger.error(f"Knowledge base search failed: {e}")
        
        # 合并和排序结果
        merged_results = self.merge_results(all_results, limit=limit)
        
        return merged_results
    
    def search_wiki_only(
        self,
        query: str,
        limit: int = 20
    ) -> List[UnifiedSearchResult]:
        """仅搜索 MediaWiki
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            List[UnifiedSearchResult]: 搜索结果
        """
        try:
            results = self.mediawiki_client.search_pages(query, limit=limit)
            
            unified_results = []
            for result in results:
                unified_results.append(UnifiedSearchResult(
                    source="mediawiki",
                    title=result.title,
                    content=result.snippet,
                    score=result.score,
                    metadata={
                        "url": result.url,
                        "size": result.size,
                        "word_count": result.word_count
                    },
                    url=result.url
                ))
            
            return unified_results
        except Exception as e:
            logger.error(f"MediaWiki search error: {e}")
            return []
    
    def search_kb_only(
        self,
        query: str,
        limit: int = 20
    ) -> List[UnifiedSearchResult]:
        """仅搜索知识库
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            List[UnifiedSearchResult]: 搜索结果
        """
        kb_service = self._get_kb_search_service()
        if not kb_service:
            logger.warning("Knowledge base search service not available")
            return []
        
        try:
            # TODO: 调用知识库搜索服务
            # results = await kb_service.search(query, k=limit)
            # 
            # unified_results = []
            # for result in results:
            #     unified_results.append(UnifiedSearchResult(
            #         source="knowledge_base",
            #         title=result.get("metadata", {}).get("title", ""),
            #         content=result.get("content", ""),
            #         score=result.get("score", 0.0),
            #         metadata=result.get("metadata", {})
            #     ))
            # 
            # return unified_results
            return []
        except Exception as e:
            logger.error(f"Knowledge base search error: {e}")
            return []
    
    def merge_results(
        self,
        results: List[UnifiedSearchResult],
        limit: int = 20
    ) -> List[UnifiedSearchResult]:
        """合并搜索结果
        
        Args:
            results: 搜索结果列表
            limit: 结果数量限制
            
        Returns:
            List[UnifiedSearchResult]: 合并和排序后的结果
        """
        # 去重（基于标题）
        seen_titles = set()
        unique_results = []
        
        for result in results:
            title_key = f"{result.source}:{result.title}"
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_results.append(result)
        
        # 按分数排序
        sorted_results = sorted(
            unique_results,
            key=lambda x: x.score,
            reverse=True
        )
        
        return sorted_results[:limit]

