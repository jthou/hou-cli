"""平台适配器基类"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from ..models import FileSearchResult


class PlatformAdapter(ABC):
    """平台适配器抽象基类
    
    所有平台特定的搜索实现都应该继承此类，并实现所有抽象方法。
    """
    
    @abstractmethod
    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """检查平台搜索功能是否可用
        
        Returns:
            Tuple[bool, Optional[str]]: (是否可用, 错误信息)
        """
        pass
    
    @abstractmethod
    def search_by_name(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """按文件名搜索
        
        Args:
            pattern: 文件名模式（支持通配符和正则表达式）
            path: 搜索路径限制（可选）
            file_type: 文件类型过滤（可选，如 '*.py'）
            limit: 结果数量限制（可选）
            
        Returns:
            List[FileSearchResult]: 搜索结果列表
            
        Raises:
            RuntimeError: 当搜索失败时抛出
        """
        pass
    
    @abstractmethod
    def search_by_content(
        self,
        keyword: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """按文件内容搜索
        
        Args:
            keyword: 搜索关键词
            path: 搜索路径限制（可选）
            file_type: 文件类型过滤（可选）
            limit: 结果数量限制（可选）
            
        Returns:
            List[FileSearchResult]: 搜索结果列表
            
        Raises:
            RuntimeError: 当搜索失败时抛出
        """
        pass


