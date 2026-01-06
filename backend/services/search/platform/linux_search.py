"""Linux 平台文件搜索适配器

优先使用 locate/plocate 命令进行快速索引搜索，
如果不可用则降级到文件系统遍历。
支持使用 ripgrep 或 grep 进行文件内容搜索。
"""
import os
import subprocess
import shutil
import logging
import fnmatch
import re
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from ..models import FileSearchResult
from .base import PlatformAdapter

logger = logging.getLogger(__name__)


class LinuxSearchAdapter(PlatformAdapter):
    """Linux 平台文件搜索适配器
    
    优先使用 locate/plocate 命令进行快速索引搜索，
    如果不可用则降级到文件系统遍历。
    
    特性:
    - 支持 locate 和 plocate 命令
    - 自动检测并使用最快的可用命令
    - 支持路径限制和文件类型过滤
    - 大目录搜索时自动使用异步遍历优化性能
    - 支持使用 ripgrep 或 grep 进行文件内容搜索
    """
    
    def __init__(self):
        """初始化 Linux 搜索适配器
        
        Raises:
            RuntimeError: 如果 locate/plocate 和文件系统遍历都不可用
        """
        self.locate_cmd: Optional[str] = None
        self.db_path: Optional[str] = None
        self.use_fallback: bool = False
        try:
            self._check_availability()
        except Exception as e:
            raise
        logger.info(
            f"Linux search adapter initialized: "
            f"locate_cmd={self.locate_cmd}, use_fallback={self.use_fallback}"
        )
    
    def _check_availability(self):
        """检查可用性并初始化"""
        available, error = self.check_availability()
        if not available:
            logger.warning(f"locate/plocate 不可用，将使用文件系统遍历: {error}")
            self.use_fallback = True
    
    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """检查 locate/plocate 命令和数据库是否可用
        
        Returns:
            Tuple[bool, Optional[str]]: (是否可用, 错误信息或None)
        """
        # 优先检查 plocate（更快）
        if shutil.which("plocate"):
            self.locate_cmd = "plocate"
            db_path = "/var/lib/plocate/plocate.db"
            if os.path.exists(db_path):
                self.db_path = db_path
                # 执行测试查询验证数据库是否可用
                try:
                    test_result = subprocess.run(
                        [self.locate_cmd, '-b', 'test'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # 即使没有结果，只要命令执行成功就认为可用
                    if test_result.returncode != 0 and "database" in test_result.stderr.lower():
                        return False, f"Database error: {test_result.stderr}"
                except subprocess.TimeoutExpired:
                    logger.warning("Test query timeout, but command is available")
                    return True, None
                except Exception as e:
                    return False, f"Test query failed: {str(e)}"
                return True, None
            else:
                return False, (
                    f"plocate 命令可用，但数据库不存在: {db_path}\n"
                    f"请运行: sudo updatedb"
                )
        
        # 检查 locate (mlocate)
        if shutil.which("locate"):
            self.locate_cmd = "locate"
            db_path = "/var/lib/mlocate/mlocate.db"
            if os.path.exists(db_path):
                self.db_path = db_path
                # 执行测试查询验证数据库是否可用
                try:
                    test_result = subprocess.run(
                        [self.locate_cmd, '-b', 'test'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if test_result.returncode != 0 and "database" in test_result.stderr.lower():
                        return False, f"Database error: {test_result.stderr}"
                except subprocess.TimeoutExpired:
                    logger.warning("Test query timeout, but command is available")
                    return True, None
                except Exception as e:
                    return False, f"Test query failed: {str(e)}"
                return True, None
            else:
                return False, (
                    f"locate 命令可用，但数据库不存在: {db_path}\n"
                    f"请运行: sudo updatedb"
                )
        
        # 命令不存在
        return False, (
            "locate 或 plocate 命令不可用\n"
            "请安装 mlocate 或 plocate 包：\n"
            "  Ubuntu/Debian: sudo apt-get install mlocate\n"
            "  Fedora/RHEL: sudo dnf install mlocate\n"
            "  Arch Linux: sudo pacman -S mlocate\n"
            "安装后运行: sudo updatedb"
        )
    
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
            ValueError: 当搜索路径不存在时抛出
        """
        # 验证路径
        if path:
            if not os.path.exists(path):
                raise ValueError(f"Search path does not exist: {path}")
            path = os.path.abspath(path)
        
        logger.debug(f"Search by name: pattern={pattern}, path={path}, file_type={file_type}, limit={limit}")
        
        if self.use_fallback or not self.locate_cmd:
            # 使用文件系统遍历降级方案
            return self._search_by_filesystem(pattern, path, file_type, limit)
        
        # 使用 locate/plocate 命令
        try:
            result = self._search_by_locate(pattern, path, file_type, limit)
            return result
        except Exception as e:
            logger.warning(f"locate 搜索失败，降级到文件系统遍历: {e}")
            return self._search_by_filesystem(pattern, path, file_type, limit)
    
    def _normalize_file_type(self, file_type: Optional[str]) -> Optional[str]:
        """规范化文件类型过滤
        
        Args:
            file_type: 文件类型（如 '*.py' 或 '.py'）
            
        Returns:
            规范化后的扩展名（如 '.py'）或 None
        """
        if not file_type:
            return None
        
        # 移除通配符前缀
        ext = file_type.lstrip('*')
        
        # 确保以点开头
        if not ext.startswith('.'):
            ext = '.' + ext
        
        return ext
    
    def _search_by_locate(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """使用 locate/plocate 命令搜索"""
        # 构建命令
        # 使用 -b 参数进行精确文件名匹配（只匹配文件名，不匹配路径）
        cmd = [self.locate_cmd, "-b", pattern]
        
        logger.debug(f"Executing {self.locate_cmd} command: {' '.join(cmd)}")
        
        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30.0,  # 与 macOS 一致
                check=False  # 不抛出异常，locate 找不到结果时返回非0
            )
            
            if result.returncode != 0:
                # locate 找不到结果时返回空列表
                if result.stderr and "database" in result.stderr.lower():
                    # 数据库相关错误，降级到文件系统遍历
                    logger.warning(f"locate 数据库错误: {result.stderr}")
                    raise RuntimeError(f"locate database error: {result.stderr}")
                return []
            
            # 解析输出
            paths = [
                p.strip() for p in result.stdout.strip().split('\n')
                if p.strip()
            ]
            
            if not paths:
                return []
            
            # 应用路径限制
            if path:
                root_path = Path(path).resolve()
                paths = [
                    p for p in paths
                    if Path(p).resolve().is_relative_to(root_path)
                ]
            
            # 应用文件类型过滤（在结果中过滤，更精确）
            if file_type:
                ext = self._normalize_file_type(file_type)
                paths = [p for p in paths if p.endswith(ext)]
            
            # 应用结果限制
            if limit:
                paths = paths[:limit]
            
            # 转换为 FileSearchResult
            results = []
            for path_str in paths:
                try:
                    file_path = Path(path_str)
                    if not file_path.exists():
                        continue
                    
                    stat = file_path.stat()
                    # 获取文件扩展名，统一使用 'no extension'
                    file_ext = file_path.suffix if file_path.suffix else 'no extension'
                    
                    results.append(FileSearchResult(
                        path=str(file_path.resolve()),
                        name=file_path.name,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=file_ext
                    ))
                except (OSError, PermissionError) as e:
                    # 忽略无法访问的文件
                    logger.debug(f"无法访问文件 {path_str}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} files matching pattern '{pattern}'")
            return results
            
        except subprocess.TimeoutExpired:
            logger.warning(f"locate command timeout after 30s, falling back to filesystem search")
            raise RuntimeError("Search timeout. The search may be too large.")
        except RuntimeError:
            # 重新抛出 RuntimeError（数据库错误）
            raise
        except Exception as e:
            logger.error(f"locate command failed: {e}", exc_info=True)
            logger.warning(f"Falling back to filesystem search: {str(e)}")
            raise RuntimeError(f"Search failed: {str(e)}")
    
    def _search_by_filesystem(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """使用文件系统遍历搜索（降级方案）"""
        # 验证路径
        if path:
            if not os.path.exists(path):
                raise ValueError(f"Search path does not exist: {path}")
            path = os.path.abspath(path)
        
        # 对于大目录，使用异步遍历
        use_async = limit is None or limit > 100
        
        if use_async:
            try:
                return asyncio.run(self._async_search_filesystem(pattern, path, file_type, limit))
            except Exception as e:
                logger.warning(f"异步搜索失败，降级到同步: {e}")
                return self._sync_search_filesystem(pattern, path, file_type, limit)
        else:
            return self._sync_search_filesystem(pattern, path, file_type, limit)
    
    def _sync_search_filesystem(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """同步文件系统遍历搜索"""
        results = []
        
        # 确定搜索根目录
        root_path = Path(path) if path else Path.cwd()
        if not root_path.exists():
            logger.warning(f"搜索根目录不存在: {root_path}")
            return []
        
        # 规范化文件类型
        file_ext = self._normalize_file_type(file_type)
        
        # 搜索文件
        try:
            # 使用 rglob 递归搜索
            for file_path in root_path.rglob("*"):
                if file_path.is_file() and fnmatch.fnmatch(file_path.name, pattern):
                    # 应用文件类型过滤
                    if file_ext and not file_path.name.endswith(file_ext):
                        continue
                    
                    try:
                        stat = file_path.stat()
                        # 统一使用 'no extension'
                        file_ext_result = file_path.suffix if file_path.suffix else 'no extension'
                        
                        results.append(FileSearchResult(
                            path=str(file_path.resolve()),
                            name=file_path.name,
                            size=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                            file_type=file_ext_result
                        ))
                        
                        # 应用结果限制
                        if limit and len(results) >= limit:
                            break
                    except (OSError, PermissionError):
                        continue
            
            logger.info(f"Found {len(results)} files matching pattern '{pattern}' (filesystem search)")
            return results
            
        except Exception as e:
            logger.error(f"文件系统遍历失败: {e}", exc_info=True)
            return []
    
    async def _async_search_filesystem(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None,
        max_depth: int = 10,
        max_concurrent: int = 10
    ) -> List[FileSearchResult]:
        """异步文件系统遍历搜索（大目录优化）"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 确定搜索根目录
        root_path = Path(path) if path else Path.cwd()
        if not root_path.exists():
            logger.warning(f"搜索根目录不存在: {root_path}")
            return []
        
        # 规范化文件类型
        file_ext = self._normalize_file_type(file_type)
        
        async def process_file(file_path: Path) -> Optional[FileSearchResult]:
            """处理单个文件"""
            try:
                # 检查匹配
                if not fnmatch.fnmatch(file_path.name, pattern):
                    return None
                
                # 应用文件类型过滤
                if file_ext and not file_path.name.endswith(file_ext):
                    return None
                
                # 获取文件信息
                stat = file_path.stat()
                # 统一使用 'no extension'
                file_ext_result = file_path.suffix if file_path.suffix else 'no extension'
                
                return FileSearchResult(
                    path=str(file_path.resolve()),
                    name=file_path.name,
                    size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                    file_type=file_ext_result
                )
            except (OSError, PermissionError):
                return None
        
        async def search_directory(dir_path: Path, depth: int = 0):
            """递归搜索目录"""
            if depth > max_depth:
                return
            
            async with semaphore:
                try:
                    # 获取目录内容
                    try:
                        entries = list(dir_path.iterdir())
                    except (OSError, PermissionError):
                        return
                    
                    # 处理文件和子目录
                    tasks = []
                    for entry in entries:
                        if entry.is_file():
                            tasks.append(process_file(entry))
                        elif entry.is_dir():
                            tasks.append(search_directory(entry, depth + 1))
                    
                    # 等待所有任务完成
                    file_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 收集文件结果
                    for result in file_results:
                        if isinstance(result, FileSearchResult):
                            results.append(result)
                            # 应用结果限制
                            if limit and len(results) >= limit:
                                return
                        elif isinstance(result, Exception):
                            logger.debug(f"处理文件时出错: {result}")
                
                except Exception as e:
                    logger.debug(f"搜索目录时出错 {dir_path}: {e}")
        
        # 开始异步搜索
        await search_directory(root_path)
        
        logger.info(f"Found {len(results)} files matching pattern '{pattern}' (async filesystem search)")
        return results
    
    def search_by_content(
        self,
        keyword: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """按文件内容搜索
        
        使用 ripgrep (rg) 或 grep 进行内容搜索。
        
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
        # 验证路径
        if path:
            if not os.path.exists(path):
                raise ValueError(f"Search path does not exist: {path}")
            path = os.path.abspath(path)
        
        # 优先使用 ripgrep (更快)
        if shutil.which("rg"):
            return self._search_by_ripgrep(keyword, path, file_type, limit)
        elif shutil.which("grep"):
            return self._search_by_grep(keyword, path, file_type, limit)
        else:
            raise RuntimeError(
                "Content search requires ripgrep (rg) or grep.\n"
                "Install ripgrep: sudo apt-get install ripgrep\n"
                "Or use grep: sudo apt-get install grep"
            )
    
    def _search_by_ripgrep(
        self,
        keyword: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """使用 ripgrep 进行内容搜索"""
        try:
            # 构建 ripgrep 命令
            # --files-with-matches: 只输出包含匹配的文件名
            # -s: 抑制错误消息
            cmd = ['rg', '--files-with-matches', '-s']
            
            # 添加文件类型过滤
            if file_type:
                ext = self._normalize_file_type(file_type)
                if ext:
                    # ripgrep 使用 -g 参数进行文件类型过滤
                    cmd.extend(['-g', f'*{ext}'])
            
            # 添加搜索路径和模式
            # ripgrep 格式: rg [OPTIONS] PATTERN [PATH...]
            search_path = path if path else '.'
            cmd.extend([keyword, search_path])
            
            logger.debug(f"Executing ripgrep command: {' '.join(cmd)}")
            
            # 执行命令（减少超时时间，对于大目录应该提示用户）
            timeout = 30  # 减少到 30 秒
            if path and path in ['/home', '/home/robo', '/']:
                # 对于大路径，使用更短的超时时间
                timeout = 20
                logger.warning(f"搜索路径较大 ({path})，使用较短的超时时间 ({timeout}s)")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                # ripgrep 找不到结果时返回非0，但不一定是错误
                if result.stderr:
                    logger.warning(f"ripgrep stderr: {result.stderr}")
                # 如果没有输出，返回空列表
                if not result.stdout.strip():
                    return []
            
            # 解析输出
            paths = [
                p.strip() for p in result.stdout.strip().split('\n')
                if p.strip()
            ]
            
            # 应用结果限制
            if limit:
                paths = paths[:limit]
            
            # 转换为 FileSearchResult
            results = []
            for path_str in paths:
                try:
                    file_path = Path(path_str)
                    if not file_path.exists():
                        continue
                    
                    stat = file_path.stat()
                    file_ext = file_path.suffix if file_path.suffix else 'no extension'
                    
                    results.append(FileSearchResult(
                        path=str(file_path.resolve()),
                        name=file_path.name,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=file_ext
                    ))
                except (OSError, PermissionError) as e:
                    logger.debug(f"无法访问文件 {path_str}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} files containing '{keyword}'")
            return results
            
        except subprocess.TimeoutExpired:
            error_msg = (
                f"内容搜索超时（{timeout}秒）。搜索路径可能过大。\n"
                f"建议：\n"
                f"1. 缩小搜索范围（指定更具体的路径）\n"
                f"2. 使用文件名搜索而不是内容搜索\n"
                f"3. 考虑使用更具体的搜索关键词"
            )
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"ripgrep search failed: {e}")
            raise RuntimeError(f"Content search failed: {str(e)}")
    
    def _search_by_grep(
        self,
        keyword: str,
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileSearchResult]:
        """使用 grep 进行内容搜索"""
        try:
            # 构建 grep 命令
            # -r: 递归搜索
            # -l: 只输出包含匹配的文件名
            # --max-count=1: 每个文件最多匹配一次（提高性能）
            cmd = ['grep', '-r', '-l', '--max-count=1']
            
            # 添加文件类型过滤
            if file_type:
                ext = self._normalize_file_type(file_type)
                if ext:
                    # grep 使用 --include 参数进行文件类型过滤
                    cmd.extend(['--include', f'*{ext}'])
            
            # 限制搜索深度（避免搜索过深）
            # 注意：grep 不支持深度限制，但我们可以使用 find 配合 grep
            # 为了简化，这里先使用基本的 grep，如果超时则提示用户缩小搜索范围
            
            # 添加搜索模式和路径
            # grep 格式: grep [OPTIONS] PATTERN [PATH...]
            search_path = path if path else '.'
            cmd.extend([keyword, search_path])
            
            logger.debug(f"Executing grep command: {' '.join(cmd)}")
            
            # 执行命令（减少超时时间，对于大目录应该提示用户）
            # 如果路径很大（如 /home/robo），应该提示用户缩小搜索范围
            timeout = 30  # 减少到 30 秒
            if path and path in ['/home', '/home/robo', '/']:
                # 对于大路径，使用更短的超时时间
                timeout = 20
                logger.warning(f"搜索路径较大 ({path})，使用较短的超时时间 ({timeout}s)")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                # grep 找不到结果时返回非0，但不一定是错误
                if result.stderr:
                    logger.warning(f"grep stderr: {result.stderr}")
                # 如果没有输出，返回空列表
                if not result.stdout.strip():
                    return []
            
            # 解析输出
            paths = [
                p.strip() for p in result.stdout.strip().split('\n')
                if p.strip()
            ]
            
            # 应用结果限制
            if limit:
                paths = paths[:limit]
            
            # 转换为 FileSearchResult
            results = []
            for path_str in paths:
                try:
                    file_path = Path(path_str)
                    if not file_path.exists():
                        continue
                    
                    stat = file_path.stat()
                    file_ext = file_path.suffix if file_path.suffix else 'no extension'
                    
                    results.append(FileSearchResult(
                        path=str(file_path.resolve()),
                        name=file_path.name,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=file_ext
                    ))
                except (OSError, PermissionError) as e:
                    logger.debug(f"无法访问文件 {path_str}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} files containing '{keyword}'")
            return results
            
        except subprocess.TimeoutExpired:
            error_msg = (
                f"内容搜索超时（{timeout}秒）。搜索路径可能过大。\n"
                f"建议：\n"
                f"1. 缩小搜索范围（指定更具体的路径）\n"
                f"2. 使用文件名搜索而不是内容搜索\n"
                f"3. 安装 ripgrep (rg) 以获得更快的搜索速度"
            )
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"grep search failed: {e}")
            raise RuntimeError(f"Content search failed: {str(e)}")
