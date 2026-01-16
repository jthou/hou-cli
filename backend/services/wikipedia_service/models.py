"""Wikipedia 搜索数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field


class WikipediaSearchResult(BaseModel):
    """单个搜索结果"""
    
    title: str = Field(..., description="页面标题")
    page_id: Optional[int] = Field(None, description="页面 ID")
    snippet: Optional[str] = Field(None, description="搜索结果摘要")
    url: Optional[str] = Field(None, description="页面 URL")


class WikipediaPageResult(BaseModel):
    """Wikipedia 页面内容"""
    
    title: str = Field(..., description="页面标题")
    page_id: Optional[int] = Field(None, description="页面 ID")
    summary: str = Field(..., description="页面摘要")
    content: Optional[str] = Field(None, description="页面完整内容（可选）")
    url: Optional[str] = Field(None, description="页面 URL")
    language: str = Field(default="zh", description="语言代码")


class WikipediaSearchResponse(BaseModel):
    """Wikipedia 搜索响应"""
    
    results: List[WikipediaSearchResult] = Field(default_factory=list, description="搜索结果列表")
    total_results: Optional[int] = Field(None, description="总结果数（如果可用）")
    search_time: Optional[float] = Field(None, description="搜索耗时（秒）")
    query: str = Field(..., description="搜索查询")
    language: str = Field(default="zh", description="语言代码")


class WikipediaPageLinksResult(BaseModel):
    """页面链接结果"""
    
    title: str = Field(..., description="页面标题")
    url: Optional[str] = Field(None, description="页面 URL")
    links: List[str] = Field(default_factory=list, description="链接列表")
    links_count: int = Field(..., description="链接数量")
    language: str = Field(default="zh", description="语言代码")


class WikipediaPageCategoriesResult(BaseModel):
    """页面分类结果"""
    
    title: str = Field(..., description="页面标题")
    url: Optional[str] = Field(None, description="页面 URL")
    categories: List[str] = Field(default_factory=list, description="分类列表")
    categories_count: int = Field(..., description="分类数量")
    language: str = Field(default="zh", description="语言代码")


class WikipediaPageImagesResult(BaseModel):
    """页面图片结果"""
    
    title: str = Field(..., description="页面标题")
    url: Optional[str] = Field(None, description="页面 URL")
    images: List[str] = Field(default_factory=list, description="图片 URL 列表")
    images_count: int = Field(..., description="图片数量")
    language: str = Field(default="zh", description="语言代码")


class WikipediaPageReferencesResult(BaseModel):
    """页面引用结果"""
    
    title: str = Field(..., description="页面标题")
    url: Optional[str] = Field(None, description="页面 URL")
    references: List[str] = Field(default_factory=list, description="引用列表")
    references_count: int = Field(..., description="引用数量")
    language: str = Field(default="zh", description="语言代码")


class WikipediaFeaturedArticleResult(BaseModel):
    """今日特色文章结果"""
    
    title: str = Field(..., description="文章标题")
    url: Optional[str] = Field(None, description="文章 URL")
    summary: str = Field(..., description="文章摘要")
    language: str = Field(default="zh", description="语言代码")

