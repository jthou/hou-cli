"""文件搜索数据模型"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FileSearchRequest(BaseModel):
    """文件搜索请求模型"""
    
    query: str = Field(..., description="搜索关键词")
    path: Optional[str] = Field(None, description="搜索路径限制（可选）")
    file_type: Optional[str] = Field(None, description="文件类型过滤（可选，如 '*.py'）")
    content_search: bool = Field(False, description="是否进行文件内容搜索")
    limit: int = Field(100, ge=1, le=1000, description="结果数量限制")
    offset: int = Field(0, ge=0, description="分页偏移量")
    sort_by: Optional[str] = Field(None, description="排序字段（name, size, modified_time）")
    sort_order: str = Field("asc", description="排序顺序（asc, desc）")


class FileSearchResult(BaseModel):
    """文件搜索结果模型"""
    
    path: str = Field(..., description="文件完整路径")
    name: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    modified_time: datetime = Field(..., description="文件修改时间")
    file_type: str = Field(..., description="文件类型（扩展名）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileSearchResponse(BaseModel):
    """文件搜索响应模型"""
    
    results: List[FileSearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="总结果数")
    limit: int = Field(..., description="结果数量限制")
    offset: int = Field(..., description="分页偏移量")
    has_more: bool = Field(..., description="是否有更多结果")
    search_time_ms: Optional[float] = Field(None, description="搜索耗时（毫秒）")
    search_type: str = Field(..., description="搜索类型（name/content）")
    platform: str = Field(..., description="搜索平台（macos/linux/windows）")
    query_summary: Optional[str] = Field(None, description="查询摘要（用于调试）")


