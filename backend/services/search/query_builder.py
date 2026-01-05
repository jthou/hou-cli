"""查询构建器

用于构建复杂的 mdfind 查询条件，支持多条件组合。
"""

import re
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class QueryOperator(Enum):
    """查询操作符"""
    AND = "&&"
    OR = "||"


class QueryBuilder:
    """mdfind 查询构建器
    
    用于构建复杂的 Spotlight 查询条件。
    支持文件名、文件类型、大小、修改时间等条件组合。
    """
    
    def __init__(self):
        """初始化查询构建器"""
        self.conditions: List[str] = []
        self.operator = QueryOperator.AND
    
    def name_contains(self, pattern: str) -> "QueryBuilder":
        """文件名包含模式
        
        Args:
            pattern: 文件名模式（支持通配符）
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        escaped_pattern = self._escape_pattern(pattern)
        condition = f"kMDItemFSName == '{escaped_pattern}'"
        self.conditions.append(condition)
        return self
    
    def name_matches(self, pattern: str) -> "QueryBuilder":
        """文件名完全匹配
        
        Args:
            pattern: 文件名模式
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        escaped_pattern = self._escape_pattern(pattern)
        condition = f"kMDItemFSName == '{escaped_pattern}'"
        self.conditions.append(condition)
        return self
    
    def file_type(self, extension: str) -> "QueryBuilder":
        """文件类型过滤
        
        Args:
            extension: 文件扩展名（如 '.py' 或 '*.py'）
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        # 移除通配符和点前缀
        ext = extension.lstrip('*').lstrip('.')
        if not ext.startswith('.'):
            ext = '.' + ext
        
        condition = f"kMDItemFSName == '*{ext}'"
        self.conditions.append(condition)
        return self
    
    def size_greater_than(self, size_bytes: int) -> "QueryBuilder":
        """文件大小大于指定值
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        condition = f"kMDItemFSSize > {size_bytes}"
        self.conditions.append(condition)
        return self
    
    def size_less_than(self, size_bytes: int) -> "QueryBuilder":
        """文件大小小于指定值
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        condition = f"kMDItemFSSize < {size_bytes}"
        self.conditions.append(condition)
        return self
    
    def size_between(self, min_bytes: int, max_bytes: int) -> "QueryBuilder":
        """文件大小在指定范围内
        
        Args:
            min_bytes: 最小文件大小（字节）
            max_bytes: 最大文件大小（字节）
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        condition = f"kMDItemFSSize >= {min_bytes} && kMDItemFSSize <= {max_bytes}"
        self.conditions.append(condition)
        return self
    
    def modified_after(self, date: datetime) -> "QueryBuilder":
        """修改时间在指定日期之后
        
        Args:
            date: 日期时间对象
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        # mdfind 使用时间戳
        timestamp = int(date.timestamp())
        condition = f"kMDItemFSContentChangeDate >= $time.iso({date.isoformat()})"
        self.conditions.append(condition)
        return self
    
    def modified_before(self, date: datetime) -> "QueryBuilder":
        """修改时间在指定日期之前
        
        Args:
            date: 日期时间对象
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        condition = f"kMDItemFSContentChangeDate <= $time.iso({date.isoformat()})"
        self.conditions.append(condition)
        return self
    
    def modified_between(self, start_date: datetime, end_date: datetime) -> "QueryBuilder":
        """修改时间在指定范围内
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        condition = (
            f"kMDItemFSContentChangeDate >= $time.iso({start_date.isoformat()}) && "
            f"kMDItemFSContentChangeDate <= $time.iso({end_date.isoformat()})"
        )
        self.conditions.append(condition)
        return self
    
    def modified_in_last_days(self, days: int) -> "QueryBuilder":
        """修改时间在最近 N 天
        
        Args:
            days: 天数
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        date = datetime.now() - timedelta(days=days)
        return self.modified_after(date)
    
    def content_contains(self, keyword: str) -> "QueryBuilder":
        """文件内容包含关键词
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        escaped_keyword = self._escape_string(keyword)
        condition = f"kMDItemTextContent == '{escaped_keyword}'"
        self.conditions.append(condition)
        return self
    
    def path_contains(self, path_pattern: str) -> "QueryBuilder":
        """路径包含模式
        
        Args:
            path_pattern: 路径模式
            
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        escaped_pattern = self._escape_pattern(path_pattern)
        condition = f"kMDItemPath == '*{escaped_pattern}*'"
        self.conditions.append(condition)
        return self
    
    def and_condition(self) -> "QueryBuilder":
        """设置条件连接符为 AND
        
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        self.operator = QueryOperator.AND
        return self
    
    def or_condition(self) -> "QueryBuilder":
        """设置条件连接符为 OR
        
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        self.operator = QueryOperator.OR
        return self
    
    def build(self) -> str:
        """构建查询字符串
        
        Returns:
            str: mdfind 查询字符串
            
        Raises:
            ValueError: 如果没有条件
        """
        if not self.conditions:
            raise ValueError("No conditions specified")
        
        if len(self.conditions) == 1:
            return self.conditions[0]
        
        operator = f" {self.operator.value} "
        return operator.join(self.conditions)
    
    def build_name_query(self, pattern: str) -> str:
        """构建简单的文件名查询
        
        Args:
            pattern: 文件名模式
            
        Returns:
            str: mdfind 查询字符串
        """
        escaped_pattern = self._escape_pattern(pattern)
        return f"kMDItemFSName == '{escaped_pattern}'"
    
    def build_content_query(self, keyword: str) -> str:
        """构建简单的文件内容查询
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            str: mdfind 查询字符串
        """
        escaped_keyword = self._escape_string(keyword)
        return f"kMDItemTextContent == '{escaped_keyword}'"
    
    def _escape_string(self, s: str) -> str:
        """转义字符串中的特殊字符
        
        Args:
            s: 要转义的字符串
            
        Returns:
            str: 转义后的字符串
        """
        # 转义单引号
        return s.replace("'", "\\'")
    
    def _escape_pattern(self, pattern: str) -> str:
        """转义模式字符串中的特殊字符
        
        Args:
            pattern: 要转义的模式字符串
            
        Returns:
            str: 转义后的模式字符串
        """
        # 转义单引号，但保留通配符 * 和 ?
        return pattern.replace("'", "\\'")
    
    def reset(self) -> "QueryBuilder":
        """重置构建器
        
        Returns:
            QueryBuilder: 返回自身以支持链式调用
        """
        self.conditions.clear()
        self.operator = QueryOperator.AND
        return self
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """验证查询是否有效
        
        Returns:
            tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        if not self.conditions:
            return False, "No conditions specified"
        
        # 检查是否有注入风险
        for condition in self.conditions:
            # 检查是否包含危险的命令注入字符
            if any(char in condition for char in [';', '&', '|', '`', '$', '(', ')']):
                # 但这些字符在 mdfind 查询中可能是合法的，所以只检查明显的注入模式
                if re.search(r'[;&|`]\s*(rm|del|delete|format)', condition, re.IGNORECASE):
                    return False, "Potentially dangerous query detected"
        
        return True, None
