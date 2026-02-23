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
        """测试创建任务成功（创建即入队，task_type 与 metadata 通过验证规范）"""
        mock_task_queue_db.create_task.return_value = "test-task-123"
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={
                    "task_type": "weather_query",
                    "task_name": "北京天气",
                    "priority": 2,
                    "max_retries": 3,
                    "metadata": {"location": "北京", "query_type": "current"},
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == "test-task-123"
        assert "已创建" in data["message"]
        mock_task_queue_db.create_task.assert_called_once()

    def test_create_task_invalid_task_type(self, client, mock_task_queue_db):
        """测试创建任务时无效的 task_type（验证规范：仅允许白名单类型）"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "invalid_type", "metadata": {}},
            )
        assert response.status_code == 400
        data = response.json()
        assert "无效的任务类型" in data["detail"]
        assert "invalid_type" in data["detail"]

    def test_create_task_weather_query_missing_location(self, client, mock_task_queue_db):
        """测试 weather_query 缺少必填 location 时返回 400"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "weather_query", "metadata": {}},
            )
        assert response.status_code == 400
        assert "缺少必填参数" in response.json()["detail"]
        assert "location" in response.json()["detail"]

    def test_create_task_weather_query_empty_location(self, client, mock_task_queue_db):
        """测试 weather_query location 为空字符串时返回 400"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "weather_query", "metadata": {"location": "   "}},
            )
        assert response.status_code == 400
        assert "必填参数不能为空" in response.json()["detail"]
        assert "location" in response.json()["detail"]

    def test_create_task_video_download_missing_url(self, client, mock_task_queue_db):
        """测试 video_download 缺少必填 url 时返回 400"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "video_download", "metadata": {}},
            )
        assert response.status_code == 400
        assert "缺少必填参数" in response.json()["detail"]
        assert "url" in response.json()["detail"]

    def test_create_task_weather_query_valid_metadata_passes(self, client, mock_task_queue_db):
        """测试 weather_query 带合法 location 与 query_type 时创建成功"""
        mock_task_queue_db.create_task.return_value = "tid-weather"
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={
                    "task_type": "weather_query",
                    "metadata": {"location": "上海", "query_type": "forecast"},
                },
            )
        assert response.status_code == 200
        assert response.json()["task_id"] == "tid-weather"
        mock_task_queue_db.create_task.assert_called_once()
        call_metadata = mock_task_queue_db.create_task.call_args[1]["metadata"]
        assert call_metadata.get("location") == "上海"
        assert call_metadata.get("query_type") == "forecast"

    def test_weather_query_create_via_api_and_verify_result(self, client, mock_task_queue_db):
        """用 API 创建天气预报查询任务，再通过 API 获取任务并验证结果结构（设计 doc §4）"""
        task_id = "weather-task-uuid-1"
        metadata = {"location": "北京", "query_type": "current"}
        # 创建：POST
        mock_task_queue_db.create_task.return_value = task_id
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            create_resp = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "weather_query", "metadata": metadata},
            )
        assert create_resp.status_code == 200
        data = create_resp.json()
        assert data["success"] is True
        assert data["task_id"] == task_id
        assert "已创建" in data.get("message", "")

        # 模拟任务已被 Worker 执行完成，result 符合 handler 约定（§3.1 / §4.3）
        completed_task = {
            "task_id": task_id,
            "task_type": "weather_query",
            "task_name": "北京天气查询 02-23 12:00",
            "status": "completed",
            "priority": 2,
            "worker_id": "worker-1",
            "created_at": "2024-01-01T00:00:00",
            "queued_at": "2024-01-01T00:00:00",
            "started_at": "2024-01-01T00:00:01",
            "completed_at": "2024-01-01T00:00:05",
            "duration": 4.0,
            "progress": 100,
            "message": None,
            "result": {
                "status": "success",
                "summary": "北京 晴 25°C",
                "location": "北京",
                "query_type": "current",
                "result": {
                    "location": "北京",
                    "query_type": "current",
                    "current_weather": {"temp": "25", "text": "晴", "humidity": "40"},
                },
            },
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "metadata": metadata,
        }
        mock_task_queue_db.get_task.return_value = completed_task

        # 获取：GET 详情
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            get_resp = client.get(f"/api/task-queue/tasks/{task_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["success"] is True
        task = get_data["task"]
        assert task["task_id"] == task_id
        assert task["task_type"] == "weather_query"
        assert task["status"] == "completed"
        assert task["metadata"] == metadata

        # 验证 result 结构（§4.3 weather_query 展示约定）
        result = task.get("result")
        assert result is not None
        assert result.get("status") == "success"
        assert "summary" in result and len(result["summary"]) > 0
        assert result.get("summary") == "北京 晴 25°C"
        inner = result.get("result")
        assert inner is not None
        assert "current_weather" in inner
        cur = inner["current_weather"]
        assert cur.get("temp") == "25"
        assert cur.get("text") == "晴"

    def test_weather_query_create_forecast_via_api_and_verify_result(self, client, mock_task_queue_db):
        """用 API 创建天气预报（forecast）任务，GET 详情并验证 result.forecast 结构"""
        task_id = "weather-forecast-uuid-1"
        metadata = {"location": "上海", "query_type": "forecast"}
        mock_task_queue_db.create_task.return_value = task_id
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            create_resp = client.post(
                "/api/task-queue/tasks",
                json={"task_type": "weather_query", "metadata": metadata},
            )
        assert create_resp.status_code == 200
        assert create_resp.json()["task_id"] == task_id

        completed_task = {
            "task_id": task_id,
            "task_type": "weather_query",
            "task_name": "上海天气预报 02-23 12:00",
            "status": "completed",
            "priority": 2,
            "worker_id": None,
            "created_at": "2024-01-01T00:00:00",
            "queued_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": "2024-01-01T00:00:10",
            "duration": 10.0,
            "progress": 100,
            "message": None,
            "result": {
                "status": "success",
                "summary": "上海 天气预报",
                "location": "上海",
                "query_type": "forecast",
                "result": {
                    "location": "上海",
                    "query_type": "forecast",
                    "forecast": {"daily": [{"fxDate": "2024-01-02", "tempMax": "10", "tempMin": "2", "textDay": "晴"}]},
                },
            },
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "metadata": metadata,
        }
        mock_task_queue_db.get_task.return_value = completed_task
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            get_resp = client.get(f"/api/task-queue/tasks/{task_id}")
        assert get_resp.status_code == 200
        task = get_resp.json()["task"]
        assert task["status"] == "completed"
        result = task["result"]
        assert result["status"] == "success"
        assert result["summary"] == "上海 天气预报"
        assert "forecast" in result.get("result", {})
        assert "daily" in result["result"]["forecast"]

    def test_frontend_flow_weather_query_create_and_list(self, client, mock_task_queue_db):
        """模拟前端：拉取 task-types，用 weather_query 的 metadata_schema 构建 payload 创建任务，再拉列表验证"""
        # 1. 前端会先 GET task-types（不 mock，用真实路由返回的类型列表）
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            types_resp = client.get("/api/task-queue/task-types")
        assert types_resp.status_code == 200
        types_data = types_resp.json()
        task_types = types_data.get("task_types") or []
        weather = next((t for t in task_types if t.get("type") == "weather_query"), None)
        assert weather is not None, "应有 weather_query 类型"
        schema = weather.get("metadata_schema") or {}
        assert "location" in schema and schema["location"].get("required") is True

        # 2. 前端提交的 payload（与 CreateTaskModal 一致）
        payload = {
            "task_type": "weather_query",
            "task_name": "",
            "priority": 2,
            "max_retries": 3,
            "metadata": {"location": "北京", "query_type": "current"},
        }
        mock_task_queue_db.create_task.return_value = "fe-weather-task-1"
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            create_resp = client.post("/api/task-queue/tasks", json=payload)
        assert create_resp.status_code == 200
        create_data = create_resp.json()
        assert create_data["success"] is True
        task_id = create_data["task_id"]
        assert task_id == "fe-weather-task-1"
        mock_task_queue_db.create_task.assert_called_once()
        call_kw = mock_task_queue_db.create_task.call_args[1]
        assert call_kw["task_type"] == "weather_query"
        assert call_kw["metadata"] == {"location": "北京", "query_type": "current"}

        # 3. 前端拉取列表，应包含新任务（mock 返回含该任务）
        mock_task_queue_db.list_tasks.return_value = [
            {
                "task_id": task_id,
                "task_type": "weather_query",
                "task_name": "北京天气查询 02-23 15:00",
                "status": "queued",
                "priority": 2,
                "metadata": payload["metadata"],
            }
        ]
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            list_resp = client.get("/api/task-queue/tasks")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["success"] is True
        tasks = list_data.get("tasks") or []
        assert len(tasks) >= 1
        found = next((t for t in tasks if t.get("task_id") == task_id), None)
        assert found is not None
        assert found["task_type"] == "weather_query"
        assert found.get("metadata", {}).get("location") == "北京"

    def test_create_task_invalid_priority(self, client, mock_task_queue_db):
        """测试创建任务时无效的优先级"""
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post(
                "/api/task-queue/tasks",
                json={
                    "task_type": "weather_query",
                    "task_name": "测试任务",
                    "metadata": {"location": "北京"},
                    "priority": 99,  # 无效的优先级
                },
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

    def test_restart_task_success(self, client, mock_task_queue_db):
        """重新开始：按原任务创建新任务，返回新 task_id"""
        old_task = {
            "task_id": "old-weather-1",
            "task_type": "weather_query",
            "task_name": "北京天气查询",
            "status": "failed",
            "priority": 2,
            "metadata": {"location": "北京", "query_type": "current"},
        }
        mock_task_queue_db.get_task.return_value = old_task
        mock_task_queue_db.create_task.return_value = "new-weather-2"
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post("/api/task-queue/tasks/old-weather-1/restart")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == "new-weather-2"
        assert "已基于原任务" in data.get("message", "")
        mock_task_queue_db.create_task.assert_called_once()
        call_kw = mock_task_queue_db.create_task.call_args[1]
        assert call_kw["task_type"] == "weather_query"
        assert call_kw["metadata"] == {"location": "北京", "query_type": "current"}

    def test_restart_task_not_found(self, client, mock_task_queue_db):
        """重新开始：任务不存在时 404"""
        mock_task_queue_db.get_task.return_value = None
        with patch('backend.api.task_queue_routes.get_task_queue_db', return_value=mock_task_queue_db):
            response = client.post("/api/task-queue/tasks/non-existent/restart")
        assert response.status_code == 404
        assert "不存在" in response.json().get("detail", "")

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

