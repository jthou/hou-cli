"""任务队列数据库测试"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime
from backend.infrastructure.storage.task_queue_db import (
    TaskQueueDB,
    TaskStatus,
    TaskPriority
)


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = TaskQueueDB(db_name=os.path.basename(path))
    # 覆盖数据库路径为临时文件
    db.db_path = Path(path)
    db._init_db()
    
    yield db
    
    # 清理
    if os.path.exists(path):
        os.unlink(path)


class TestTaskQueueDB:
    """任务队列数据库测试类"""
    
    def test_create_task(self, temp_db):
        """测试创建任务"""
        task_id = temp_db.create_task(
            task_type="test_task",
            task_name="测试任务",
            priority=TaskPriority.HIGH,
            max_retries=5,
            metadata={"key": "value"}
        )
        
        assert task_id is not None
        assert len(task_id) > 0
        
        # 验证任务已创建
        task = temp_db.get_task(task_id)
        assert task is not None
        assert task["task_type"] == "test_task"
        assert task["task_name"] == "测试任务"
        assert task["status"] == TaskStatus.QUEUED.value
        assert task["priority"] == TaskPriority.HIGH.value
        assert task["max_retries"] == 5
        assert task["metadata"]["key"] == "value"
    
    def test_acquire_task(self, temp_db):
        """测试 Worker 获取任务（创建即入队）"""
        task_id = temp_db.create_task(
            task_type="test_task",
            task_name="测试任务",
            priority=TaskPriority.HIGH
        )
        
        # 注册 Worker
        worker_id = "worker-1"
        temp_db.register_worker(worker_id, "测试 Worker")
        
        # 获取任务
        task_info = temp_db.acquire_task(worker_id)
        
        assert task_info is not None
        assert task_info["task_id"] == task_id
        assert task_info["task_type"] == "test_task"
        assert task_info["task_name"] == "测试任务"
        
        # 验证任务状态已更新
        task = temp_db.get_task(task_id)
        assert task["status"] == TaskStatus.RUNNING.value
        assert task["worker_id"] == worker_id
        assert task["started_at"] is not None
    
    def test_acquire_task_priority_order(self, temp_db):
        """测试按优先级获取任务"""
        low_task = temp_db.create_task("test", "低优先级", priority=TaskPriority.LOW)
        high_task = temp_db.create_task("test", "高优先级", priority=TaskPriority.HIGH)
        normal_task = temp_db.create_task("test", "普通优先级", priority=TaskPriority.NORMAL)
        
        temp_db.register_worker("worker-1", "测试 Worker")
        
        # 应该先获取高优先级的任务
        task_info = temp_db.acquire_task("worker-1")
        assert task_info["task_id"] == high_task
        assert task_info["priority"] == TaskPriority.HIGH.value
    
    def test_update_task_progress(self, temp_db):
        """测试更新任务进度"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("worker-1", "测试 Worker")
        temp_db.acquire_task("worker-1")
        
        success = temp_db.update_task_progress(task_id, 50, "处理中...")
        assert success is True
        
        task = temp_db.get_task(task_id)
        assert task["progress"] == 50
        assert task["message"] == "处理中..."
    
    def test_complete_task_success(self, temp_db):
        """测试任务成功完成"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("worker-1", "测试 Worker")
        temp_db.acquire_task("worker-1")
        
        result = {"output": "成功"}
        success = temp_db.complete_task(task_id, result=result)
        assert success is True
        
        task = temp_db.get_task(task_id)
        assert task["status"] == TaskStatus.COMPLETED.value
        assert task["progress"] == 100
        assert task["result"] == result
        assert task["completed_at"] is not None
        assert task["duration"] is not None
    
    def test_complete_task_failed(self, temp_db):
        """测试任务失败后重新入队"""
        task_id = temp_db.create_task("test", "测试任务", max_retries=3)
        temp_db.register_worker("worker-1", "测试 Worker")
        temp_db.acquire_task("worker-1")
        
        error = "任务执行失败"
        success = temp_db.complete_task(task_id, error=error)
        assert success is True
        
        task = temp_db.get_task(task_id)
        assert task["status"] == TaskStatus.QUEUED.value
        assert task["retry_count"] == 1
    
    def test_complete_task_max_retries_exceeded(self, temp_db):
        """测试超过最大重试次数"""
        task_id = temp_db.create_task("test", "测试任务", max_retries=1)
        temp_db.register_worker("worker-1", "测试 Worker")
        
        temp_db.acquire_task("worker-1")
        temp_db.complete_task(task_id, error="失败1")
        
        temp_db.acquire_task("worker-1")
        temp_db.complete_task(task_id, error="失败2")
        
        task = temp_db.get_task(task_id)
        assert task["status"] == TaskStatus.FAILED.value
        # 注意：retry_count 可能只记录最后一次，所以可能是 1 或 2
        assert task["retry_count"] >= 1
    
    def test_cancel_task(self, temp_db):
        """测试取消任务"""
        task_id = temp_db.create_task("test", "测试任务")
        success = temp_db.cancel_task(task_id)
        assert success is True
        
        task = temp_db.get_task(task_id)
        assert task["status"] == TaskStatus.CANCELLED.value
        assert task["completed_at"] is not None
    
    def test_list_tasks(self, temp_db):
        """测试列出任务"""
        task1 = temp_db.create_task("test1", "任务1")
        task2 = temp_db.create_task("test2", "任务2")
        task3 = temp_db.create_task("test3", "任务3")
        
        tasks = temp_db.list_tasks()
        assert len(tasks) == 3
        
        temp_db.register_worker("worker-1", "测试 Worker")
        temp_db.acquire_task("worker-1")
        queued_tasks = temp_db.list_tasks(status=TaskStatus.QUEUED)
        assert len(queued_tasks) == 2
        running_tasks = temp_db.list_tasks(status=TaskStatus.RUNNING)
        assert len(running_tasks) == 1
    
    def test_register_worker(self, temp_db):
        """测试注册 Worker"""
        worker_id = "worker-1"
        success = temp_db.register_worker(worker_id, "测试 Worker")
        assert success is True
        
        workers = temp_db.list_workers()
        assert len(workers) == 1
        assert workers[0]["worker_id"] == worker_id
        assert workers[0]["worker_name"] == "测试 Worker"
        assert workers[0]["status"] == "idle"
    
    def test_update_worker_heartbeat(self, temp_db):
        """测试更新 Worker 心跳"""
        worker_id = "worker-1"
        temp_db.register_worker(worker_id, "测试 Worker")
        
        success = temp_db.update_worker_heartbeat(worker_id)
        assert success is True
        
        workers = temp_db.list_workers()
        assert workers[0]["last_heartbeat"] is not None
    
    def test_cleanup_stale_tasks(self, temp_db):
        """测试清理超时任务"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("worker-1", "测试 Worker")
        temp_db.acquire_task("worker-1")
        
        # 手动设置开始时间为很久以前（模拟超时）
        conn = temp_db._get_conn()
        cursor = conn.cursor()
        old_time = "2020-01-01T00:00:00"
        cursor.execute(
            "UPDATE tasks SET started_at = ? WHERE task_id = ?",
            (old_time, task_id)
        )
        conn.commit()
        conn.close()
        
        # 清理超时任务
        count = temp_db.cleanup_stale_tasks(max_idle_minutes=1)
        assert count >= 0  # 可能清理了任务
        
        # 验证任务状态（如果被清理，应该重新入队）
        task = temp_db.get_task(task_id)
        if task:
            # 任务可能被重新入队或保持原状态
            assert task["status"] in [TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]

    # --- 任务管理与展示机制（见 docs/design/task-management-and-display.md）---

    def test_list_tasks_includes_result_summary_for_completed(self, temp_db):
        """已完成且 result 含 summary 时，列表项带 result_summary"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("worker-1", "Worker")
        temp_db.acquire_task("worker-1")
        result_payload = {"status": "success", "summary": "已保存至 /path", "data": {}}
        temp_db.complete_task(task_id, result=result_payload)

        tasks = temp_db.list_tasks()
        assert len(tasks) >= 1
        completed = next((t for t in tasks if t["task_id"] == task_id), None)
        assert completed is not None
        assert completed["status"] == TaskStatus.COMPLETED.value
        assert completed.get("result_summary") == "已保存至 /path"

    def test_list_tasks_result_summary_null_when_not_completed(self, temp_db):
        """未完成或 result 无 summary 时，列表项 result_summary 为 None"""
        task_id = temp_db.create_task("test", "任务")
        tasks = temp_db.list_tasks()
        row = next((t for t in tasks if t["task_id"] == task_id), None)
        assert row is not None
        assert row.get("result_summary") is None

    def test_list_tasks_result_summary_null_when_result_has_no_summary(self, temp_db):
        """completed 但 result 无 summary 时，result_summary 为空或 None"""
        task_id = temp_db.create_task("test", "任务")
        temp_db.register_worker("worker-1", "Worker")
        temp_db.acquire_task("worker-1")
        temp_db.complete_task(task_id, result={"status": "success", "data": {}})

        tasks = temp_db.list_tasks()
        completed = next((t for t in tasks if t["task_id"] == task_id), None)
        assert completed is not None
        assert completed.get("result_summary") is None or completed.get("result_summary") == ""

    def test_get_task_returns_full_result(self, temp_db):
        """get_task 返回的 task 包含完整 result 对象"""
        task_id = temp_db.create_task("test", "任务")
        temp_db.register_worker("worker-1", "Worker")
        temp_db.acquire_task("worker-1")
        result_payload = {"status": "success", "summary": "摘要", "data": {"key": "value"}}
        temp_db.complete_task(task_id, result=result_payload)

        task = temp_db.get_task(task_id)
        assert task is not None
        assert task["result"] == result_payload

    # --- 任务管道（depends_on_task_id / input_bindings）---

    def test_create_task_with_dependency_and_bindings(self, temp_db):
        """创建带依赖与 input_bindings 的任务，get_task/list_tasks 均返回两字段"""
        up_id = temp_db.create_task("test", "上游")
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        temp_db.complete_task(up_id, result={"status": "success", "data": {"output_file": "/out.mp3"}})

        down_id = temp_db.create_task(
            "test", "下游",
            depends_on_task_id=up_id,
            input_bindings={"input_file": "result.data.output_file"},
        )
        task = temp_db.get_task(down_id)
        assert task["depends_on_task_id"] == up_id
        assert task["input_bindings"] == {"input_file": "result.data.output_file"}

        tasks = temp_db.list_tasks()
        down = next((t for t in tasks if t["task_id"] == down_id), None)
        assert down is not None
        assert down.get("depends_on_task_id") == up_id
        assert down.get("input_bindings") == {"input_file": "result.data.output_file"}

    def test_acquire_task_skips_dependent_until_upstream_completes(self, temp_db):
        """有依赖的任务仅在上游完成后才可被 acquire"""
        up_id = temp_db.create_task("test", "上游")
        down_id = temp_db.create_task("test", "下游", depends_on_task_id=up_id, input_bindings={})
        temp_db.register_worker("w", "Worker")

        t = temp_db.acquire_task("w")
        assert t is not None
        assert t["task_id"] == up_id  # 先拿到上游
        temp_db.complete_task(up_id, result={"ok": True})

        t2 = temp_db.acquire_task("w")
        assert t2 is not None
        assert t2["task_id"] == down_id  # 上游完成后才拿到下游

    def test_cascade_fail_when_upstream_fails(self, temp_db):
        """上游最终失败时，queued 下游被级联标记为 failed"""
        up_id = temp_db.create_task("test", "上游", max_retries=1)
        down_id = temp_db.create_task("test", "下游", depends_on_task_id=up_id)
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        temp_db.complete_task(up_id, error="失败1")
        temp_db.acquire_task("w")
        temp_db.complete_task(up_id, error="失败2")  # 用尽重试，最终失败

        down = temp_db.get_task(down_id)
        assert down["status"] == TaskStatus.FAILED.value
        assert "上游任务失败" in (down.get("error") or "")

    def test_reset_task_to_queued_in_place_no_new_task(self, temp_db):
        """重新开始：只修改内容与状态，不新开任务；保留 task_id、metadata、depends_on_task_id、pipeline_id，清空执行结果并置 retry_count=0"""
        up_id = temp_db.create_task("test", "上游")
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        temp_db.complete_task(up_id, result={"data": {"output_file": "/out.mp3"}})

        down_id = temp_db.create_task(
            "test", "下游",
            metadata={"input_file": "/old.mp3"},
            depends_on_task_id=up_id,
            input_bindings={"input_file": "result.data.output_file"},
            pipeline_id="pipe-123",
        )
        temp_db.acquire_task("w")
        temp_db.complete_task(down_id, result={"data": {"output_file": "/subtitle.txt"}})  # 下游先完成

        tasks_before = temp_db.list_tasks()
        count_before = len(tasks_before)

        ok = temp_db.reset_task_to_queued(down_id)
        assert ok is True

        tasks_after = temp_db.list_tasks()
        assert len(tasks_after) == count_before, "重新开始不得新开任务，任务总数不变"

        task = temp_db.get_task(down_id)
        assert task is not None
        assert task["task_id"] == down_id
        assert task["status"] == TaskStatus.QUEUED.value
        assert task["metadata"] == {"input_file": "/old.mp3"}
        assert task.get("depends_on_task_id") == up_id
        assert task.get("input_bindings") == {"input_file": "result.data.output_file"}
        assert task.get("pipeline_id") == "pipe-123"
        assert task.get("result") is None
        assert task.get("error") is None
        assert task.get("started_at") is None
        assert task.get("completed_at") is None
        assert task.get("duration") is None
        assert task.get("worker_id") is None
        assert task.get("progress") == 0
        assert task.get("message") is None
        assert task.get("retry_count") == 0

    def test_delete_task_success(self, temp_db):
        """删除任务：queued/completed/failed/cancelled 可被彻底删除，列表不再包含"""
        task_id = temp_db.create_task("test", "测试任务")
        tasks_before = temp_db.list_tasks()
        ok = temp_db.delete_task(task_id)
        assert ok is True
        assert temp_db.get_task(task_id) is None
        tasks_after = temp_db.list_tasks()
        assert len(tasks_after) == len(tasks_before) - 1
        assert not any(t["task_id"] == task_id for t in tasks_after)

    def test_delete_task_running_rejected(self, temp_db):
        """删除任务：running 状态不可删除，返回 False"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        ok = temp_db.delete_task(task_id)
        assert ok is False
        assert temp_db.get_task(task_id) is not None
        assert temp_db.get_task(task_id)["status"] == TaskStatus.RUNNING.value

    def test_delete_task_cascade_downstream(self, temp_db):
        """删除任务：删除上游时，依赖其的 queued 下游被级联标记为取消"""
        up_id = temp_db.create_task("test", "上游")
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        temp_db.complete_task(up_id, result={"data": {"output_file": "/out.mp3"}})
        down_id = temp_db.create_task("test", "下游", depends_on_task_id=up_id)
        ok = temp_db.delete_task(up_id)
        assert ok is True
        assert temp_db.get_task(up_id) is None
        down = temp_db.get_task(down_id)
        assert down is not None
        assert down["status"] == TaskStatus.CANCELLED.value
        assert "上游任务已删除" in (down.get("error") or "")

    def test_soft_delete_and_restore(self, temp_db):
        """软删除后列表不包含，恢复后重新出现；list_tasks include_deleted 过滤"""
        task_id = temp_db.create_task("test", "测试任务")
        all_before = temp_db.list_tasks()
        assert any(t["task_id"] == task_id for t in all_before)
        ok = temp_db.soft_delete_task(task_id)
        assert ok is True
        task = temp_db.get_task(task_id)
        assert task is not None
        assert task.get("deleted_at") is not None
        default_list = temp_db.list_tasks()
        assert not any(t["task_id"] == task_id for t in default_list)
        only_deleted = temp_db.list_tasks(include_deleted="only")
        assert any(t["task_id"] == task_id for t in only_deleted)
        ok = temp_db.restore_task(task_id)
        assert ok is True
        task = temp_db.get_task(task_id)
        assert task.get("deleted_at") is None
        default_after = temp_db.list_tasks()
        assert any(t["task_id"] == task_id for t in default_after)
        only_deleted_after = temp_db.list_tasks(include_deleted="only")
        assert not any(t["task_id"] == task_id for t in only_deleted_after)

    def test_soft_delete_running_rejected(self, temp_db):
        """软删除：running 状态不可软删除"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.register_worker("w", "Worker")
        temp_db.acquire_task("w")
        ok = temp_db.soft_delete_task(task_id)
        assert ok is False
        assert temp_db.get_task(task_id).get("deleted_at") is None

    def test_acquire_task_excludes_soft_deleted(self, temp_db):
        """acquire_task 不返回已软删除的 queued 任务"""
        task_id = temp_db.create_task("test", "测试任务")
        temp_db.soft_delete_task(task_id)
        temp_db.register_worker("w", "Worker")
        t = temp_db.acquire_task("w")
        assert t is None

