"""Google Custom Search API 客户端"""

import os
import time
import logging
from typing import Optional, List
import httpx
from .models import GoogleSearchResult, GoogleSearchResponse

logger = logging.getLogger(__name__)


class GoogleSearchServiceError(Exception):
    """Google 搜索服务错误"""
    pass


class GoogleSearchService:
    """Google Custom Search API 服务"""
    
    API_BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, api_key: Optional[str] = None, engine_id: Optional[str] = None):
        """
        初始化 Google 搜索服务
        
        Args:
            api_key: Google Custom Search API 密钥（如果为 None，从环境变量读取）
            engine_id: Google Custom Search Engine ID（如果为 None，从环境变量读取）
        """
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.engine_id = engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not self.api_key:
            raise GoogleSearchServiceError(
                "GOOGLE_SEARCH_API_KEY 环境变量未设置。"
                "请在 .env 文件中配置 GOOGLE_SEARCH_API_KEY"
            )
        
        if not self.engine_id:
            raise GoogleSearchServiceError(
                "GOOGLE_SEARCH_ENGINE_ID 环境变量未设置。"
                "请在 .env 文件中配置 GOOGLE_SEARCH_ENGINE_ID"
            )
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        region: Optional[str] = None
    ) -> GoogleSearchResponse:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量（1-10，默认 10）
            language: 语言代码（可选，如 'zh-CN', 'en'）
            region: 地区代码（可选，如 'cn', 'us'）
            
        Returns:
            GoogleSearchResponse: 搜索结果
            
        Raises:
            GoogleSearchServiceError: 搜索失败时抛出
        """
        # 限制结果数量在 1-10 之间
        num_results = max(1, min(10, num_results))
        
        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": num_results
        }
        
        if language:
            params["lr"] = f"lang_{language}"
        
        if region:
            params["gl"] = region
        
        start_time = time.time()
        
        try:
            response = await self.client.get(self.API_BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析搜索结果
            results = []
            if "items" in data:
                for item in data["items"]:
                    results.append(GoogleSearchResult(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        display_link=item.get("displayLink")
                    ))
            
            search_time = time.time() - start_time
            
            # 获取总结果数（如果可用）
            total_results = None
            if "searchInformation" in data:
                total_results_str = data["searchInformation"].get("totalResults", "0")
                try:
                    total_results = int(total_results_str)
                except ValueError:
                    pass
            
            return GoogleSearchResponse(
                results=results,
                total_results=total_results,
                search_time=search_time,
                query=query
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Google Search API 错误: {e.response.status_code}"
            if e.response.status_code == 400:
                error_msg += " - 请求参数错误"
            elif e.response.status_code == 403:
                error_msg += " - API 密钥无效或配额已用完"
            elif e.response.status_code == 429:
                error_msg += " - 请求频率过高，请稍后重试"
            raise GoogleSearchServiceError(error_msg)
        except httpx.RequestError as e:
            raise GoogleSearchServiceError(f"网络错误: {str(e)}")
        except Exception as e:
            raise GoogleSearchServiceError(f"搜索失败: {str(e)}")
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    def __del__(self):
        """析构函数，确保客户端关闭"""
        # 注意：在异步环境中，最好显式调用 close()
        pass

