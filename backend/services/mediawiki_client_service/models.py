"""MediaWiki 数据模型"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class MediaWikiPage(BaseModel):
    """MediaWiki 页面模型"""
    
    model_config = ConfigDict()
    
    title: str = Field(..., description="页面标题")
    content: str = Field(..., description="页面内容（wikitext）")
    revision_id: int = Field(..., description="修订版本 ID")
    last_modified: datetime = Field(..., description="最后修改时间")
    categories: List[str] = Field(default_factory=list, description="页面分类")
    links: List[str] = Field(default_factory=list, description="页面链接")
    url: Optional[str] = Field(None, description="页面 URL")
    
    @field_serializer('last_modified')
    def serialize_datetime(self, value: datetime, _info) -> str:
        """序列化 datetime 为 ISO 格式字符串"""
        return value.isoformat()


class MediaWikiSearchResult(BaseModel):
    """MediaWiki 搜索结果模型"""
    
    title: str = Field(..., description="页面标题")
    snippet: str = Field(..., description="搜索结果摘要")
    url: str = Field(..., description="页面 URL")
    score: float = Field(..., description="相关性分数")
    size: Optional[int] = Field(None, description="页面大小（字节）")
    word_count: Optional[int] = Field(None, description="字数")


class UnifiedSearchResult(BaseModel):
    """统一搜索结果模型"""
    
    source: str = Field(..., description="来源（mediawiki 或 knowledge_base）")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    score: float = Field(..., description="相关性分数")
    metadata: Dict = Field(default_factory=dict, description="元数据")
    url: Optional[str] = Field(None, description="URL（如果是 MediaWiki）")

