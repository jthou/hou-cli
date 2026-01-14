"""PlanningManager 测试用例"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.agent.planning.manager import PlanningManager


class TestPlanningManager:
    """PlanningManager 测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """创建 PlanningManager 实例"""
        return PlanningManager(work_dir=temp_dir)
    
    def test_get_planning_files(self, manager):
        """测试获取规划文件路径"""
        files = manager.get_planning_files()
        assert files.task_plan.name == "task_plan.md"
        assert files.findings.name == "findings.md"
        assert files.progress.name == "progress.md"
    
    def test_get_planning_files_with_session(self, manager):
        """测试带会话ID的规划文件路径"""
        files = manager.get_planning_files(session_id="test_session_123")
        assert "test_session" in files.task_plan.name
        assert files.task_plan.name.endswith("task_plan.md")
    
    def test_create_planning_files(self, manager):
        """测试创建规划文件"""
        task = "测试任务：创建一个简单的Python脚本"
        files = manager.create_planning_files(task)
        
        # 检查文件是否创建
        assert files.task_plan.exists()
        assert files.findings.exists()
        assert files.progress.exists()
        
        # 检查文件内容
        task_plan_content = files.task_plan.read_text(encoding='utf-8')
        assert "测试任务" in task_plan_content or task in task_plan_content
    
    def test_read_task_plan(self, manager):
        """测试读取 task_plan.md"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        content = manager.read_task_plan()
        assert content is not None
        assert len(content) > 0
    
    def test_update_phase_status(self, manager):
        """测试更新阶段状态"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        # 更新阶段1状态为 complete
        result = manager.update_phase_status(1, "complete")
        assert result is True
        
        # 验证状态已更新
        content = manager.read_task_plan()
        assert "**Status:** complete" in content or "Status:** complete" in content
    
    def test_add_error(self, manager):
        """测试添加错误记录"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        result = manager.add_error("测试错误", 1, "测试解决方案")
        assert result is True
        
        content = manager.read_task_plan()
        assert "测试错误" in content
    
    def test_add_finding(self, manager):
        """测试添加发现"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        result = manager.add_finding("测试发现", category="Research Findings")
        assert result is True
        
        findings_content = manager.get_planning_files().findings.read_text(encoding='utf-8')
        assert "测试发现" in findings_content
    
    def test_add_progress(self, manager):
        """测试添加进度记录"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        result = manager.add_progress("执行了测试操作", files_modified=["test.py"])
        assert result is True
        
        progress_content = manager.get_planning_files().progress.read_text(encoding='utf-8')
        assert "执行了测试操作" in progress_content
    
    def test_check_completion(self, manager):
        """测试检查完成情况"""
        task = "测试任务"
        manager.create_planning_files(task)
        
        status = manager.check_completion()
        assert "complete" in status
        assert "total" in status
        assert status["total"] > 0

