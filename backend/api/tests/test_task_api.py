"""任务管理API测试"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.core.agent.task_manager import task_manager, TaskInfo, TaskStatus

# 在导入前设置环境变量
import os
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing')


class TestTaskAPI:
    """测试任务管理API"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from backend.main import app
        return app
    
    @pytest.fixture
    def clear_task_manager(self):
        """清理任务管理器"""
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
        yield
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
    
    @pytest.fixture
    def sample_task(self, clear_task_manager):
        """创建示例任务"""
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            progress=50,
            message="处理中...",
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        return task_id
    
    def test_get_task_success(self, app, sample_task):
        """测试获取任务成功"""
        client = TestClient(app)
        
        response = client.get(f"/api/tasks/{sample_task}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["task_id"] == sample_task
        assert data["task"]["task_name"] == "测试任务"
        assert data["task"]["status"] == "running"
        assert data["task"]["progress"] == 50
    
    def test_get_task_not_found(self, app, clear_task_manager):
        """测试获取不存在的任务"""
        client = TestClient(app)
        
        response = client.get("/api/tasks/non_existent_id")
        
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]
    
    def test_list_tasks(self, app, clear_task_manager):
        """测试列出任务"""
        # 创建多个任务
        task_ids = []
        for i in range(3):
            task_id = str(uuid.uuid4())
            task_info = TaskInfo(
                task_id=task_id,
                task_name=f"任务 {i}",
                status=TaskStatus.RUNNING,
                started_at=datetime.now()
            )
            task_manager._tasks[task_id] = task_info
            task_ids.append(task_id)
        
        client = TestClient(app)
        
        response = client.get("/api/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] >= 3
        assert len(data["tasks"]) >= 3
    
    def test_list_tasks_with_status_filter(self, app, clear_task_manager):
        """测试按状态筛选任务"""
        # 创建不同状态的任务
        running_task_id = str(uuid.uuid4())
        running_task = TaskInfo(
            task_id=running_task_id,
            task_name="运行中任务",
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        task_manager._tasks[running_task_id] = running_task
        
        completed_task_id = str(uuid.uuid4())
        completed_task = TaskInfo(
            task_id=completed_task_id,
            task_name="已完成任务",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        task_manager._tasks[completed_task_id] = completed_task
        
        client = TestClient(app)
        
        # 筛选运行中的任务
        response = client.get("/api/tasks?status=running")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 验证所有返回的任务都是运行中状态
        for task in data["tasks"]:
            assert task["status"] == "running"
    
    def test_list_tasks_with_limit(self, app, clear_task_manager):
        """测试限制返回任务数量"""
        # 创建多个任务
        for i in range(10):
            task_id = str(uuid.uuid4())
            task_info = TaskInfo(
                task_id=task_id,
                task_name=f"任务 {i}",
                status=TaskStatus.RUNNING,
                started_at=datetime.now()
            )
            task_manager._tasks[task_id] = task_info
        
        client = TestClient(app)
        
        # 限制返回5个任务
        response = client.get("/api/tasks?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tasks"]) <= 5
    
    def test_list_tasks_invalid_status(self, app, clear_task_manager):
        """测试无效的状态筛选"""
        client = TestClient(app)
        
        response = client.get("/api/tasks?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "无效" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, app, sample_task):
        """测试取消任务"""
        # Mock cancel_task 方法
        original_cancel = task_manager.cancel_task
        task_manager.cancel_task = AsyncMock(return_value=True)
        
        try:
            client = TestClient(app)
            
            response = client.post(f"/api/tasks/{sample_task}/cancel")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            task_manager.cancel_task = original_cancel
    
    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, app, clear_task_manager):
        """测试取消不存在的任务"""
        # Mock cancel_task 方法
        original_cancel = task_manager.cancel_task
        task_manager.cancel_task = AsyncMock(return_value=False)
        
        try:
            client = TestClient(app)
            
            response = client.post("/api/tasks/non_existent_id/cancel")
            
            assert response.status_code == 404
            data = response.json()
            assert "不存在" in data["detail"]
        finally:
            task_manager.cancel_task = original_cancel

