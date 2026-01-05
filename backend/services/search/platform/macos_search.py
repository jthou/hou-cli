"""macOS 平台搜索适配器

使用系统内置的 mdfind 命令和 Spotlight 索引实现文件搜索。
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from ..models import FileSearchResult
from .base import PlatformAdapter

logger = logging.getLogger(__name__)


class MacOSSearchAdapter(PlatformAdapter):
    """macOS 平台搜索适配器
    
    使用 mdfind 命令利用 Spotlight 索引进行文件搜索。
    """
    
    def __init__(self):
        """初始化 macOS 搜索适配器
        
        Raises:
            RuntimeError: 如果 mdfind 命令不可用或 Spotlight 索引异常
        """
        self.available, self.error = self.check_availability()
        if not self.available:
            raise RuntimeError(
                f"macOS search not available: {self.error}\n"
                "Please ensure Spotlight is enabled:\n"
                "1. Go to System Preferences > Spotlight\n"
                "2. Make sure Spotlight is enabled\n"
                "3. Wait for indexing to complete"
            )
        logger.info("macOS search adapter initialized successfully")
    
    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """检查 mdfind 命令是否可用和 Spotlight 索引是否正常
        
        Returns:
            Tuple[bool, Optional[str]]: (是否可用, 错误信息)
        """
        try:
            # 检查 mdfind 命令是否存在
            result = subprocess.run(
                ['which', 'mdfind'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "mdfind command not found"
            
            # 执行测试查询验证 Spotlight 索引
            test_result = subprocess.run(
                ['mdfind', '-name', 'test'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # 即使没有结果，只要命令执行成功就认为可用
            if test_result.returncode != 0:
                return False, f"mdfind test query failed: {test_result.stderr}"
            
            return True, None
        except FileNotFoundError:
            return False, "mdfind command not found. Please enable Spotlight."
        except subprocess.TimeoutExpired:
            return False, "mdfind command timeout. Spotlight may be indexing."
        except Exception as e:
            return False, f"Error checking mdfind: {str(e)}"
    
    def search_by_name(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """按文件名搜索
        
        Args:
            pattern: 文件名模式（支持通配符，如 '*.py'）
            path: 搜索路径限制（可选）
            file_type: 文件类型过滤（可选，如 '*.py'）
            limit: 结果数量限制（可选）
            
        Returns:
            List[FileSearchResult]: 搜索结果列表
            
        Raises:
            RuntimeError: 当搜索失败时抛出
        """
        try:
            # 构建 mdfind 命令
            cmd = ['mdfind', '-name', pattern]
            
            # 添加路径限制
            if path:
                # 验证路径是否存在
                if not os.path.exists(path):
                    raise ValueError(f"Search path does not exist: {path}")
                # 转换为绝对路径
                abs_path = os.path.abspath(path)
                cmd.extend(['-onlyin', abs_path])
            
            logger.debug(f"Executing mdfind command: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"mdfind failed: {result.stderr}")
            
            # 解析输出
            paths = [
                p.strip() for p in result.stdout.strip().split('\n')
                if p.strip()
            ]
            
            # 应用文件类型过滤
            if file_type:
                # 移除通配符前缀（如 '*.py' -> '.py'）
                ext = file_type.lstrip('*')
                if not ext.startswith('.'):
                    ext = '.' + ext
                paths = [p for p in paths if p.endswith(ext)]
            
            # 应用结果限制
            if limit:
                paths = paths[:limit]
            
            # 转换为 FileSearchResult
            results = []
            for file_path in paths:
                try:
                    stat = os.stat(file_path)
                    results.append(FileSearchResult(
                        path=file_path,
                        name=os.path.basename(file_path),
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=Path(file_path).suffix or 'no extension'
                    ))
                except OSError as e:
                    # 文件可能已被删除，跳过
                    logger.warning(f"Failed to stat file {file_path}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} files matching pattern '{pattern}'")
            return results
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Search timeout. The search may be too large.")
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Search failed: {str(e)}")
    
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
        try:
            # 转义特殊字符（单引号）
            escaped_keyword = keyword.replace("'", "\\'")
            
            # 构建 mdfind 内容查询
            query = f"kMDItemTextContent == '{escaped_keyword}'"
            cmd = ['mdfind', query]
            
            # 添加路径限制
            if path:
                if not os.path.exists(path):
                    raise ValueError(f"Search path does not exist: {path}")
                abs_path = os.path.abspath(path)
                cmd.extend(['-onlyin', abs_path])
            
            logger.debug(f"Executing mdfind content search: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 内容搜索可能需要更长时间
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"mdfind content search failed: {result.stderr}")
            
            # 解析输出
            paths = [
                p.strip() for p in result.stdout.strip().split('\n')
                if p.strip()
            ]
            
            # 应用文件类型过滤
            if file_type:
                ext = file_type.lstrip('*')
                if not ext.startswith('.'):
                    ext = '.' + ext
                paths = [p for p in paths if p.endswith(ext)]
            
            # 应用结果限制
            if limit:
                paths = paths[:limit]
            
            # 转换为 FileSearchResult
            results = []
            for file_path in paths:
                try:
                    stat = os.stat(file_path)
                    results.append(FileSearchResult(
                        path=file_path,
                        name=os.path.basename(file_path),
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=Path(file_path).suffix or 'no extension'
                    ))
                except OSError as e:
                    logger.warning(f"Failed to stat file {file_path}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} files containing '{keyword}'")
            return results
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Content search timeout. The search may be too large.")
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            raise RuntimeError(f"Content search failed: {str(e)}")
