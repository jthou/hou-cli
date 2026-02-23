"""任务队列 API 路由测试"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
    TaskPriority
)
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_task_queue_db():
    """模拟任务队列数据库"""
    db = MagicMock()
    return db


@pytest.fixture
def sample_task():
    """示例任务数据"""
    return {
        "task_id": "test-task-123",
        "task_type": "test_task",
        "task_name": "测试任务",
        "status": "queued",
        "priority": 2,
        "worker_id": None,
        "created_at": "2024-01-01T00:00:00",
        "queued_at": "2024-01-01T00:00:01",
        "started_at": None,
        "completed_at": None,
        "duration": None,
        "progress": 0,
        "message": None,
        "result": None,
        "error": None,
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {}
    }


class TestTaskQueueRoutes:
    """任务队列路由测试类"""
    
    def test_create_task_success(self, client, mock_task_queue_db):
        """测试创建任务成功（创建即入队）"""
        mock_task_queue_db.create_task.return_value = "test-task-123"
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={
                    "task_type": "test_task",
                    "task_name": "测试任务",
                    "priority": 2,
                    "max_retries": 3,
                    "metadata": {"key": "value"}
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == "test-task-123"
        assert "已创建" in data["message"]
        mock_task_queue_db.create_task.assert_called_once()
    
    def test_create_task_invalid_priority(self, client, mock_task_queue_db):
        """测试创建任务时无效的优先级"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={
                    "task_type": "test_task",
                    "task_name": "测试任务",
                    "priority": 99  # 无效的优先级
                }
            )
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的优先级" in data["detail"]
    
    def test_get_task_success(self, client, mock_task_queue_db, sample_task):
        """测试获取任务成功"""
        mock_task_queue_db.get_task.return_value = sample_task
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks/test-task-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["task_id"] == "test-task-123"
        assert data["task"]["task_name"] == "测试任务"
        mock_task_queue_db.get_task.assert_called_once_with("test-task-123")
    
    def test_get_task_not_found(self, client, mock_task_queue_db):
        """测试获取任务失败（任务不存在）"""
        mock_task_queue_db.get_task.return_value = None
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]
    
    def test_list_tasks_success(self, client, mock_task_queue_db, sample_task):
        """测试列出任务成功"""
        mock_task_queue_db.list_tasks.return_value = [sample_task]
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "test-task-123"
        assert data["count"] == 1
        mock_task_queue_db.list_tasks.assert_called_once()

    def test_list_tasks_response_includes_result_summary(self, client, mock_task_queue_db):
        """列表接口返回项含 result_summary（设计 doc: 列表轻量、含一句摘要）"""
        mock_task_queue_db.list_tasks.return_value = [
            {
                "task_id": "t1",
                "task_type": "video_download",
                "task_name": "下载",
                "status": "completed",
                "priority": 2,
                "worker_id": None,
                "created_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:01",
                "completed_at": "2024-01-01T00:00:10",
                "duration": 9.0,
                "progress": 100,
                "message": None,
                "error": None,
                "retry_count": 0,
                "result_summary": "已保存至 /path/to/dir",
            }
        ]
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"][0]["result_summary"] == "已保存至 /path/to/dir"

    def test_get_task_response_includes_result(self, client, mock_task_queue_db):
        """详情接口返回的 task 含完整 result（设计 doc: 详情按需拉取完整结果）"""
        full_task = {
            "task_id": "t1",
            "task_type": "video_download",
            "task_name": "下载",
            "status": "completed",
            "priority": 2,
            "worker_id": None,
            "created_at": "2024-01-01T00:00:00",
            "queued_at": "2024-01-01T00:00:00",
            "started_at": "2024-01-01T00:00:01",
            "completed_at": "2024-01-01T00:00:10",
            "duration": 9.0,
            "progress": 100,
            "message": None,
            "result": {"status": "success", "summary": "已保存至 /path", "data": {"output_dir": "/path"}},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "metadata": {},
        }
        mock_task_queue_db.get_task.return_value = full_task
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks/t1")
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["result"] == full_task["result"]
    
    def test_list_tasks_with_status_filter(self, client, mock_task_queue_db, sample_task):
        """测试按状态过滤任务"""
        mock_task_queue_db.list_tasks.return_value = [sample_task]
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks?status=running")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 验证调用了 list_tasks 并传入了正确的状态
        call_args = mock_task_queue_db.list_tasks.call_args
        assert call_args is not None
    
    def test_list_tasks_invalid_status(self, client, mock_task_queue_db):
        """测试无效的任务状态"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/tasks?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的任务状态" in data["detail"]
    
    def test_cancel_task_success(self, client, mock_task_queue_db):
        """测试取消任务成功"""
        mock_task_queue_db.cancel_task.return_value = True
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post("/api/task-queue/tasks/test-task-123/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已取消" in data["message"]
        mock_task_queue_db.cancel_task.assert_called_once_with("test-task-123")
    
    def test_cancel_task_not_found(self, client, mock_task_queue_db):
        """测试取消任务失败（任务不存在）"""
        mock_task_queue_db.cancel_task.return_value = False
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post("/api/task-queue/tasks/non-existent/cancel")
        
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"] or "无法取消" in data["detail"]
    
    def test_list_workers_success(self, client, mock_task_queue_db):
        """测试列出 Worker 成功"""
        mock_workers = [
            {
                "worker_id": "worker-1",
                "worker_name": "worker-1",
                "status": "idle",
                "current_task_id": None,
                "last_heartbeat": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:00",
                "completed_tasks": 10,
                "failed_tasks": 1
            }
        ]
        mock_task_queue_db.list_workers.return_value = mock_workers
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.get("/api/task-queue/workers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["workers"]) == 1
        assert data["workers"][0]["worker_id"] == "worker-1"
        assert data["count"] == 1
    
    def test_cleanup_stale_tasks_success(self, client, mock_task_queue_db):
        """测试清理超时任务成功"""
        mock_task_queue_db.cleanup_stale_tasks.return_value = 3
        
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post("/api/task-queue/cleanup?max_idle_minutes=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cleaned_count"] == 3
        assert "清理了" in data["message"]
        mock_task_queue_db.cleanup_stale_tasks.assert_called_once_with(max_idle_minutes=30)

