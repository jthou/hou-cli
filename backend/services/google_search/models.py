"""Google 搜索数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GoogleSearchResult(BaseModel):
    """单个搜索结果"""
    
    title: str = Field(..., description="搜索结果标题")
    link: str = Field(..., description="搜索结果链接")
    snippet: str = Field(..., description="搜索结果摘要")
    display_link: Optional[str] = Field(None, description="显示的链接")


class GoogleSearchResponse(BaseModel):
    """Google 搜索响应"""
    
    results: List[GoogleSearchResult] = Field(default_factory=list, description="搜索结果列表")
    total_results: Optional[int] = Field(None, description="总结果数（如果可用）")
    search_time: Optional[float] = Field(None, description="搜索耗时（秒）")
    query: str = Field(..., description="搜索查询")

