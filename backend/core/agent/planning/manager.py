"""规划文件管理器 - 实现 Manus 风格的持久化规划模式"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

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
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # 模板文件路径
        template_dir = Path(__file__).parent.parent.parent.parent / "externals" / "planning-with-files" / "templates"
        self.template_dir = template_dir
        
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
        """
        files = self.get_planning_files(session_id)
        
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
    
    def read_task_plan(self, session_id: Optional[str] = None) -> Optional[str]:
        """
        读取 task_plan.md
        
        Args:
            session_id: 会话 ID
        
        Returns:
            文件内容，如果文件不存在返回 None
        """
        files = self.get_planning_files(session_id)
        if files.task_plan.exists():
            return files.task_plan.read_text(encoding='utf-8')
        return None
    
    def update_phase_status(self, phase_num: int, status: str, session_id: Optional[str] = None) -> bool:
        """
        更新阶段状态
        
        Args:
            phase_num: 阶段编号（1-5）
            status: 状态（pending, in_progress, complete）
            session_id: 会话 ID
        
        Returns:
            是否更新成功
        """
        files = self.get_planning_files(session_id)
        if not files.task_plan.exists():
            return False
        
        content = files.task_plan.read_text(encoding='utf-8')
        
        # 查找对应的阶段
        pattern = rf"(### Phase {phase_num}:.*?\n.*?\*\*Status:\*\* )\w+"
        replacement = rf"\1{status}"
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            files.task_plan.write_text(new_content, encoding='utf-8')
            logger.info(f"更新阶段 {phase_num} 状态为 {status}")
            return True
        
        return False
    
    def add_error(self, error: str, attempt: int, resolution: str, session_id: Optional[str] = None) -> bool:
        """
        添加错误记录到 task_plan.md
        
        Args:
            error: 错误描述
            attempt: 尝试次数
            resolution: 解决方案
            session_id: 会话 ID
        
        Returns:
            是否添加成功
        """
        files = self.get_planning_files(session_id)
        if not files.task_plan.exists():
            return False
        
        content = files.task_plan.read_text(encoding='utf-8')
        
        # 在 Errors Encountered 表格中添加新行
        error_row = f"| {error} | {attempt} | {resolution} |\n"
        
        # 查找表格结束位置
        pattern = r"(\| Error \| Attempt \| Resolution \|\n\|-------\|---------\|------------\|\n)"
        
        if re.search(pattern, content):
            # 在表格后添加新行
            new_content = re.sub(
                pattern,
                rf"\1{error_row}",
                content
            )
        else:
            # 如果表格不存在，在 Errors Encountered 部分后添加
            pattern = r"(## Errors Encountered.*?\n)"
            new_content = re.sub(
                pattern,
                rf"\1{error_row}\n",
                content,
                flags=re.DOTALL
            )
        
        files.task_plan.write_text(new_content, encoding='utf-8')
        logger.info(f"添加错误记录: {error}")
        return True
    
    def add_finding(self, finding: str, category: str = "Research Findings", session_id: Optional[str] = None) -> bool:
        """
        添加发现到 findings.md
        
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
        
        content = files.findings.read_text(encoding='utf-8')
        
        # 在对应分类下添加新行
        pattern = rf"(## {category}.*?\n<!--.*?-->\n)(-)"
        replacement = rf"\1- {finding}\n\2"
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            files.findings.write_text(new_content, encoding='utf-8')
            logger.info(f"添加发现到 {category}: {finding[:50]}")
            return True
        
        return False
    
    def add_progress(self, action: str, files_modified: List[str] = None, session_id: Optional[str] = None) -> bool:
        """
        添加进度记录到 progress.md
        
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
        
        content = files.progress.read_text(encoding='utf-8')
        
        # 在 Actions taken 下添加新行
        pattern = r"(- Actions taken:.*?\n  -)(\n)"
        files_list = "\n".join([f"  - {f}" for f in (files_modified or [])])
        replacement = rf"\1\n  - {action}{f'\n{files_list}' if files_list else ''}\2"
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            files.progress.write_text(new_content, encoding='utf-8')
            logger.info(f"添加进度记录: {action}")
            return True
        
        return False
    
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

