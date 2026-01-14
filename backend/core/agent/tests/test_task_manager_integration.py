"""任务管理器集成测试"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from backend.core.agent.task_manager import (
    TaskManager, TaskInfo, TaskStatus, task_manager
)


class TestTaskManagerIntegration:
    """测试任务管理器的集成功能"""
    
    @pytest.fixture
    def clear_task_manager(self):
        """清理任务管理器"""
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
        yield
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
    
    def test_task_creation(self, clear_task_manager):
        """测试任务创建"""
        import uuid
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        
        # 验证任务已创建
        assert task_id in task_manager._tasks
        assert task_manager._tasks[task_id].task_name == "测试任务"
        assert task_manager._tasks[task_id].status == TaskStatus.RUNNING
    
    def test_task_progress_update(self, clear_task_manager):
        """测试任务进度更新"""
        import uuid
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            progress=0,
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        
        # 更新进度
        task_manager.update_task_progress(task_id, 50, "处理中...")
        
        # 验证进度已更新
        assert task_manager._tasks[task_id].progress == 50
        assert task_manager._tasks[task_id].message == "处理中..."
    
    def test_task_status_update(self, clear_task_manager):
        """测试任务状态更新"""
        import uuid
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        
        # 更新状态
        task_manager.update_task(task_id, status=TaskStatus.COMPLETED, progress=100)
        
        # 验证状态已更新
        assert task_manager._tasks[task_id].status == TaskStatus.COMPLETED
        assert task_manager._tasks[task_id].progress == 100
    
    def test_task_to_dict(self, clear_task_manager):
        """测试任务信息转换为字典"""
        import uuid
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            progress=50,
            message="处理中",
            started_at=datetime.now()
        )
        
        task_dict = task_info.to_dict()
        
        # 验证字典格式
        assert task_dict["task_id"] == task_id
        assert task_dict["task_name"] == "测试任务"
        assert task_dict["status"] == "running"
        assert task_dict["progress"] == 50
        assert task_dict["message"] == "处理中"
        assert "created_at" in task_dict
        assert "started_at" in task_dict
    
    @pytest.mark.asyncio
    async def test_task_manager_singleton(self):
        """测试任务管理器单例模式"""
        manager1 = TaskManager()
        manager2 = TaskManager()
        
        # 验证是同一个实例
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_get_task(self, clear_task_manager):
        """测试获取任务"""
        import uuid
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        
        # 获取任务
        retrieved_task = task_manager.get_task(task_id)
        
        # 验证任务信息
        assert retrieved_task is not None
        assert retrieved_task.task_id == task_id
        assert retrieved_task.task_name == "测试任务"
        
        # 测试获取不存在的任务
        non_existent = task_manager.get_task("non_existent_id")
        assert non_existent is None

