"""规划文件管理器 - 实现 Manus 风格的持久化规划模式"""
import logging
import re
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class PlanningFiles:
    """规划文件路径"""
    task_plan: Path
    findings: Path
    progress: Path


class PlanningManager:
    """规划文件管理器
    
    实现 Manus 风格的 3 文件规划模式：
    - task_plan.md: 任务规划和进度跟踪
    - findings.md: 研究和发现
    - progress.md: 会话日志和测试结果
    """
    
    def __init__(self, work_dir: Optional[Path] = None):
        """
        初始化规划管理器
        
        Args:
            work_dir: 工作目录，规划文件将创建在此目录下
                     如果为 None，使用当前工作目录
        """
        self.work_dir = work_dir or Path.cwd()
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建规划文件目录失败: {str(e)}", exc_info=True)
            # 降级到当前目录
            self.work_dir = Path.cwd()
            logger.warning(f"使用当前目录作为规划文件目录: {self.work_dir}")
        
        # 模板文件路径
        template_dir = Path(__file__).parent.parent.parent.parent / "externals" / "planning-with-files" / "templates"
        self.template_dir = template_dir
        
        # 检查模板目录是否存在
        if not self.template_dir.exists():
            logger.warning(f"模板目录不存在: {self.template_dir}，将使用默认模板")
        
        # 性能优化：文件缓存机制
        self._file_cache: Dict[str, Tuple[str, float]] = {}  # {file_path: (content, timestamp)}
        self._cache_ttl = 5.0  # 缓存有效期（秒）
        self._cache_lock = Lock()
        
        # 性能优化：批量更新机制
        self._pending_updates: deque = deque()  # 待更新的操作队列
        self._batch_size = 5  # 批量大小
        self._batch_timeout = 2.0  # 批量超时（秒）
        self._last_batch_time = time.time()
        self._update_lock = Lock()
        
        # 性能优化：异步更新任务
        self._update_task: Optional[asyncio.Task] = None
        self._update_queue: Optional[asyncio.Queue] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"PlanningManager 初始化，工作目录: {self.work_dir}")
    
    def get_planning_files(self, session_id: Optional[str] = None) -> PlanningFiles:
        """
        获取规划文件路径
        
        Args:
            session_id: 会话 ID，如果提供，使用会话特定的文件名
        
        Returns:
            PlanningFiles: 规划文件路径
        """
        if session_id:
            # 使用会话 ID 作为文件名前缀
            prefix = f"{session_id[:8]}_"
        else:
            prefix = ""
        
        return PlanningFiles(
            task_plan=self.work_dir / f"{prefix}task_plan.md",
            findings=self.work_dir / f"{prefix}findings.md",
            progress=self.work_dir / f"{prefix}progress.md"
        )
    
    def create_planning_files(self, task: str, session_id: Optional[str] = None) -> PlanningFiles:
        """
        创建规划文件
        
        Args:
            task: 任务描述
            session_id: 会话 ID
        
        Returns:
            PlanningFiles: 创建的规划文件路径
        
        Raises:
            IOError: 如果文件创建失败
        """
        files = self.get_planning_files(session_id)
        
        try:
            # 创建 task_plan.md
            if not files.task_plan.exists():
                self._create_task_plan(files.task_plan, task)
                logger.info(f"创建 task_plan.md: {files.task_plan}")
            
            # 创建 findings.md
            if not files.findings.exists():
                self._create_findings(files.findings, task)
                logger.info(f"创建 findings.md: {files.findings}")
            
            # 创建 progress.md
            if not files.progress.exists():
                self._create_progress(files.progress)
                logger.info(f"创建 progress.md: {files.progress}")
        except Exception as e:
            logger.error(f"创建规划文件失败: {str(e)}", exc_info=True)
            raise IOError(f"创建规划文件失败: {str(e)}") from e
        
        return files
    
    def _create_task_plan(self, file_path: Path, task: str):
        """创建 task_plan.md"""
        # 读取模板
        template_path = self.template_dir / "task_plan.md"
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
        else:
            # 如果模板不存在，使用默认模板
            content = self._get_default_task_plan_template()
        
        # 替换占位符
        content = content.replace("[Brief Description]", task[:50])
        content = content.replace("[One sentence describing the end state]", task)
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
    
    def _create_findings(self, file_path: Path, task: str):
        """创建 findings.md"""
        # 读取模板
        template_path = self.template_dir / "findings.md"
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
        else:
            content = self._get_default_findings_template()
        
        # 在 Requirements 部分添加任务描述
        content = content.replace("<!-- Captured from user request -->", f"<!-- Captured from user request -->\n- {task}")
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
    
    def _create_progress(self, file_path: Path):
        """创建 progress.md"""
        # 读取模板
        template_path = self.template_dir / "progress.md"
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
        else:
            content = self._get_default_progress_template()
        
        # 替换日期
        today = datetime.now().strftime("%Y-%m-%d")
        content = content.replace("[DATE]", today)
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
    
    def _get_cached_content(self, file_path: Path) -> Optional[str]:
        """
        获取缓存的文件内容
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件内容，如果文件不存在或缓存失效返回 None
        """
        cache_key = str(file_path)
        current_time = time.time()
        
        with self._cache_lock:
            if cache_key in self._file_cache:
                content, timestamp = self._file_cache[cache_key]
                if current_time - timestamp < self._cache_ttl:
                    return content
                # 缓存失效，清除
                del self._file_cache[cache_key]
        
        # 缓存失效或不存在，重新读取
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                with self._cache_lock:
                    self._file_cache[cache_key] = (content, current_time)
                return content
            except Exception as e:
                logger.warning(f"读取文件失败: {file_path}, 错误: {str(e)}")
                return None
        return None
    
    def _invalidate_cache(self, file_path: Path):
        """使缓存失效"""
        cache_key = str(file_path)
        with self._cache_lock:
            if cache_key in self._file_cache:
                del self._file_cache[cache_key]
    
    def read_task_plan(self, session_id: Optional[str] = None) -> Optional[str]:
        """
        读取 task_plan.md（使用缓存）
        
        Args:
            session_id: 会话 ID
        
        Returns:
            文件内容，如果文件不存在返回 None
        """
        files = self.get_planning_files(session_id)
        return self._get_cached_content(files.task_plan)
    
    def _update_file_content(self, file_path: Path, update_func) -> bool:
        """
        更新文件内容（带缓存失效）
        
        Args:
            file_path: 文件路径
            update_func: 更新函数，接收内容，返回新内容
        
        Returns:
            是否更新成功
        """
        if not file_path.exists():
            return False
        
        try:
            # 使用缓存读取
            content = self._get_cached_content(file_path)
            if content is None:
                content = file_path.read_text(encoding='utf-8')
            
            new_content = update_func(content)
            
            if new_content != content:
                file_path.write_text(new_content, encoding='utf-8')
                # 使缓存失效
                self._invalidate_cache(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"更新文件失败: {file_path}, 错误: {str(e)}", exc_info=True)
            return False
    
    def update_phase_status(self, phase_num: int, status: str, session_id: Optional[str] = None) -> bool:
        """
        更新阶段状态（使用缓存）
        
        Args:
            phase_num: 阶段编号（1-5）
            status: 状态（pending, in_progress, complete）
            session_id: 会话 ID
        
        Returns:
            是否更新成功
        """
        files = self.get_planning_files(session_id)
        
        def update_func(content: str) -> str:
            pattern = rf"(### Phase {phase_num}:.*?\n.*?\*\*Status:\*\* )\w+"
            replacement = rf"\1{status}"
            return re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        result = self._update_file_content(files.task_plan, update_func)
        if result:
            logger.info(f"更新阶段 {phase_num} 状态为 {status}")
        return result
    
    def add_error(self, error: str, attempt: int, resolution: str, session_id: Optional[str] = None) -> bool:
        """
        添加错误记录到 task_plan.md（使用缓存）
        
        Args:
            error: 错误描述
            attempt: 尝试次数
            resolution: 解决方案
            session_id: 会话 ID
        
        Returns:
            是否添加成功
        """
        files = self.get_planning_files(session_id)
        
        def update_func(content: str) -> str:
            error_row = f"| {error} | {attempt} | {resolution} |\n"
            pattern = r"(\| Error \| Attempt \| Resolution \|\n\|-------\|---------\|------------\|\n)"
            
            if re.search(pattern, content):
                return re.sub(pattern, rf"\1{error_row}", content)
            else:
                pattern = r"(## Errors Encountered.*?\n)"
                return re.sub(pattern, rf"\1{error_row}\n", content, flags=re.DOTALL)
        
        result = self._update_file_content(files.task_plan, update_func)
        if result:
            logger.info(f"添加错误记录: {error}")
        return result
    
    def add_finding(self, finding: str, category: str = "Research Findings", session_id: Optional[str] = None) -> bool:
        """
        添加发现到 findings.md（使用缓存和批量更新）
        
        Args:
            finding: 发现内容
            category: 分类（Research Findings, Technical Decisions, Resources 等）
            session_id: 会话 ID
        
        Returns:
            是否添加成功
        """
        files = self.get_planning_files(session_id)
        if not files.findings.exists():
            return False
        
        # 添加到批量更新队列
        with self._update_lock:
            self._pending_updates.append(('finding', files.findings, finding, category))
            
            # 检查是否需要立即刷新
            should_flush = (
                len(self._pending_updates) >= self._batch_size or
                time.time() - self._last_batch_time > self._batch_timeout
            )
        
        if should_flush:
            self._flush_pending_updates()
        
        return True
    
    def _flush_pending_updates(self):
        """刷新待更新的操作"""
        if not self._pending_updates:
            return
        
        updates_to_process = []
        with self._update_lock:
            while self._pending_updates:
                updates_to_process.append(self._pending_updates.popleft())
            self._last_batch_time = time.time()
        
        # 按文件分组处理
        file_updates: Dict[Path, List] = {}
        for update in updates_to_process:
            update_type, file_path, *args = update
            if file_path not in file_updates:
                file_updates[file_path] = []
            file_updates[file_path].append((update_type, args))
        
        # 批量更新每个文件
        for file_path, updates in file_updates.items():
            try:
                content = self._get_cached_content(file_path)
                if content is None:
                    if file_path.exists():
                        content = file_path.read_text(encoding='utf-8')
                    else:
                        continue
                
                new_content = content
                for update_type, args in updates:
                    if update_type == 'finding':
                        finding, category = args
                        pattern = rf"(## {category}.*?\n<!--.*?-->\n)(-)"
                        replacement = rf"\1- {finding}\n\2"
                        new_content = re.sub(pattern, replacement, new_content, flags=re.DOTALL)
                    elif update_type == 'progress':
                        action, files_modified = args
                        pattern = r"(- Actions taken:.*?\n  -)(\n)"
                        files_list = "\n".join([f"  - {f}" for f in (files_modified or [])])
                        replacement = rf"\1\n  - {action}{f'\n{files_list}' if files_list else ''}\2"
                        new_content = re.sub(pattern, replacement, new_content, flags=re.DOTALL)
                
                if new_content != content:
                    file_path.write_text(new_content, encoding='utf-8')
                    self._invalidate_cache(file_path)
                    logger.debug(f"批量更新文件: {file_path.name}, 更新数量: {len(updates)}")
            except Exception as e:
                logger.error(f"批量更新文件失败: {file_path}, 错误: {str(e)}", exc_info=True)
    
    def add_progress(self, action: str, files_modified: List[str] = None, session_id: Optional[str] = None) -> bool:
        """
        添加进度记录到 progress.md（使用批量更新）
        
        Args:
            action: 执行的操作
            files_modified: 修改的文件列表
            session_id: 会话 ID
        
        Returns:
            是否添加成功
        """
        files = self.get_planning_files(session_id)
        if not files.progress.exists():
            return False
        
        # 添加到批量更新队列
        with self._update_lock:
            self._pending_updates.append(('progress', files.progress, action, files_modified))
            
            # 检查是否需要立即刷新
            should_flush = (
                len(self._pending_updates) >= self._batch_size or
                time.time() - self._last_batch_time > self._batch_timeout
            )
        
        if should_flush:
            self._flush_pending_updates()
        
        return True
    
    def flush_updates(self):
        """手动刷新待更新的操作（用于确保数据持久化）"""
        self._flush_pending_updates()
    
    def cleanup_old_files(self, max_age_days: int = 7, max_files: int = 100) -> Dict[str, int]:
        """
        清理旧文件
        
        Args:
            max_age_days: 最大保留天数
            max_files: 最大文件数量
        
        Returns:
            清理统计信息
        """
        stats = {
            "deleted_by_age": 0,
            "deleted_by_count": 0,
            "total_deleted": 0
        }
        
        try:
            # 获取所有规划文件
            all_files = list(self.work_dir.glob("*_*.md"))
            if not all_files:
                return stats
            
            # 按修改时间排序
            all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # 按时间清理
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            for file in all_files:
                if file.stat().st_mtime < cutoff_time:
                    try:
                        file.unlink()
                        stats["deleted_by_age"] += 1
                        # 清除缓存
                        self._invalidate_cache(file)
                    except Exception as e:
                        logger.warning(f"删除旧文件失败: {file}, 错误: {str(e)}")
            
            # 按数量清理（保留最新的 max_files 个）
            remaining_files = [f for f in all_files if f.exists()]
            if len(remaining_files) > max_files:
                files_to_delete = remaining_files[max_files:]
                for file in files_to_delete:
                    try:
                        file.unlink()
                        stats["deleted_by_count"] += 1
                        # 清除缓存
                        self._invalidate_cache(file)
                    except Exception as e:
                        logger.warning(f"删除多余文件失败: {file}, 错误: {str(e)}")
            
            stats["total_deleted"] = stats["deleted_by_age"] + stats["deleted_by_count"]
            
            if stats["total_deleted"] > 0:
                logger.info(f"清理规划文件: 按时间删除 {stats['deleted_by_age']} 个, "
                          f"按数量删除 {stats['deleted_by_count']} 个, "
                          f"总计 {stats['total_deleted']} 个")
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {str(e)}", exc_info=True)
        
        return stats
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            all_files = list(self.work_dir.glob("*_*.md"))
            total_size = sum(f.stat().st_size for f in all_files if f.exists())
            
            return {
                "files_count": len(all_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "cache_size": len(self._file_cache),
                "pending_updates": len(self._pending_updates)
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
            return {
                "files_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "cache_size": 0,
                "pending_updates": 0
            }
    
    def check_completion(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        检查任务完成情况
        
        Args:
            session_id: 会话 ID
        
        Returns:
            完成情况统计
        """
        files = self.get_planning_files(session_id)
        if not files.task_plan.exists():
            return {
                "complete": False,
                "total": 0,
                "complete_count": 0,
                "in_progress_count": 0,
                "pending_count": 0
            }
        
        content = files.task_plan.read_text(encoding='utf-8')
        
        # 统计阶段数量
        total = len(re.findall(r"### Phase \d+:", content))
        complete = len(re.findall(r"\*\*Status:\*\* complete", content))
        in_progress = len(re.findall(r"\*\*Status:\*\* in_progress", content))
        pending = len(re.findall(r"\*\*Status:\*\* pending", content))
        
        return {
            "complete": complete == total and total > 0,
            "total": total,
            "complete_count": complete,
            "in_progress_count": in_progress,
            "pending_count": pending
        }
    
    def _get_default_task_plan_template(self) -> str:
        """获取默认 task_plan.md 模板"""
        return """# Task Plan: [Brief Description]

## Goal
[One sentence describing the end state]

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [ ] Understand user intent
- [ ] Identify constraints and requirements
- [ ] Document findings in findings.md
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define technical approach
- [ ] Create project structure if needed
- [ ] Document decisions with rationale
- **Status:** pending

### Phase 3: Implementation
- [ ] Execute the plan step by step
- [ ] Write code to files before executing
- [ ] Test incrementally
- **Status:** pending

### Phase 4: Testing & Verification
- [ ] Verify all requirements met
- [ ] Document test results in progress.md
- [ ] Fix any issues found
- **Status:** pending

### Phase 5: Delivery
- [ ] Review all output files
- [ ] Ensure deliverables are complete
- [ ] Deliver to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
"""
    
    def _get_default_findings_template(self) -> str:
        """获取默认 findings.md 模板"""
        return """# Findings & Decisions

## Requirements
<!-- Captured from user request -->
-

## Research Findings
<!-- Key discoveries during exploration -->
-

## Technical Decisions
| Decision | Rationale |
|----------|-----------|

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
<!-- URLs, file paths, API references -->
-
"""
    
    def _get_default_progress_template(self) -> str:
        """获取默认 progress.md 模板"""
        return """# Progress Log

## Session: [DATE]

### Phase 1: Requirements & Discovery
- **Status:** in_progress
- **Started:** [DATE]
- Actions taken:
  -
- Files created/modified:
  -

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
|      |       |          |        |        |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
|           |       | 1       |            |
"""

