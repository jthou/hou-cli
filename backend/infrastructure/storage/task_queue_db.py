"""任务队列数据库存储"""
import sqlite3
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from shared.storage_utils import get_storage_manager
from shared.debug_utils import debug_log


class TaskStatus(str, Enum):
    """任务状态（单一等待态：创建即入队，由 Worker 轮询拉取）"""
    QUEUED = "queued"  # 待执行
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskQueueDB:
    """任务队列数据库管理器"""
    
    def __init__(self, db_name: str = "task_queue.db"):
        """
        初始化任务队列数据库
        
        Args:
            db_name: 数据库文件名
        """
        storage_manager = get_storage_manager()
        self.db_path = storage_manager.get_sqlite_path(db_name)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # 创建任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER NOT NULL DEFAULT 2,
                    worker_id TEXT,
                    created_at TEXT NOT NULL,
                    queued_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration REAL,
                    progress INTEGER DEFAULT 0,
                    message TEXT,
                    result TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    metadata TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority_created 
                ON tasks(priority DESC, created_at ASC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_worker_id 
                ON tasks(worker_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created_at 
                ON tasks(created_at DESC)
            """)
            
            # 创建 Worker 状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    worker_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'idle',
                    current_task_id TEXT,
                    last_heartbeat TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workers_status 
                ON workers(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workers_last_heartbeat 
                ON workers(last_heartbeat DESC)
            """)
            
            # 创建定时任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    schedule_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    next_run_time TEXT NOT NULL,
                    last_run_time TEXT,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run 
                ON scheduled_tasks(next_run_time)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_active 
                ON scheduled_tasks(is_active, next_run_time)
            """)
            
            conn.commit()
            debug_log("任务队列数据库初始化完成")

            # 任务管道：为 tasks 表增加依赖与输入绑定列（兼容已有库）
            cursor.execute("PRAGMA table_info(tasks)")
            cols = [row[1] for row in cursor.fetchall()]
            if "depends_on_task_id" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN depends_on_task_id TEXT")
            if "input_bindings" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN input_bindings TEXT")
            if "pipeline_id" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN pipeline_id TEXT")
            if "deleted_at" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN deleted_at TEXT")
            conn.commit()
        except Exception as e:
            debug_log(f"初始化任务队列数据库失败: {e}", level="error")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))

    def check_dependency_cycle(self, start_task_id: str) -> bool:
        """
        从 start_task_id 沿 depends_on_task_id 遍历，若再次遇到已访问的任务则存在循环。
        Returns True 表示存在循环。
        """
        visited = set()
        current = start_task_id
        while current:
            if current in visited:
                return True
            visited.add(current)
            task = self.get_task(current)
            if not task:
                break
            current = (task.get("depends_on_task_id") or "").strip() or None
        return False

    def create_task(
        self,
        task_type: str,
        task_name: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        depends_on_task_id: Optional[str] = None,
        input_bindings: Optional[Dict[str, str]] = None,
        pipeline_id: Optional[str] = None,
    ) -> str:
        """
        创建新任务

        Args:
            pipeline_id: 同一管道编排的组号（可选），前端用于分组展示。
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        dep_id = (depends_on_task_id or "").strip() or None
        bindings_json = json.dumps(input_bindings) if input_bindings else None
        pipe_id = (pipeline_id or "").strip() or None

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, task_type, task_name, status, priority,
                    max_retries, metadata, created_at, queued_at, updated_at,
                    depends_on_task_id, input_bindings, pipeline_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                task_type,
                task_name,
                TaskStatus.QUEUED.value,
                priority.value,
                max_retries,
                json.dumps(metadata or {}),
                now,
                now,
                now,
                dep_id,
                bindings_json,
                pipe_id,
            ))
            conn.commit()
            debug_log(f"创建任务: {task_id} ({task_name})")
            return task_id
        except Exception as e:
            debug_log(f"创建任务失败: {e}", level="error")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def acquire_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Worker 获取一个待处理的任务（按优先级和创建时间排序）
        
        Args:
            worker_id: Worker ID
            
        Returns:
            任务信息字典，如果没有可用任务则返回 None
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 使用事务锁定，确保只有一个 worker 能获取任务
            cursor.execute("BEGIN IMMEDIATE")
            
            # 查找一个可执行的任务：无依赖，或依赖任务已完成且 result 非空；排除已软删除
            cursor.execute("""
                SELECT t.task_id, t.task_type, t.task_name, t.priority, t.metadata,
                       t.depends_on_task_id, t.input_bindings
                FROM tasks t
                LEFT JOIN tasks dep ON t.depends_on_task_id = dep.task_id
                WHERE t.status = ?
                  AND (t.deleted_at IS NULL)
                  AND (t.depends_on_task_id IS NULL OR (dep.status = ? AND dep.result IS NOT NULL))
                ORDER BY t.priority DESC, t.created_at ASC
                LIMIT 1
            """, (TaskStatus.QUEUED.value, TaskStatus.COMPLETED.value))
            
            row = cursor.fetchone()
            
            if not row:
                conn.commit()
                return None
            
            task_id, task_type, task_name, priority, metadata_json = row[0], row[1], row[2], row[3], row[4]
            depends_on_task_id = row[5] if len(row) > 5 else None
            input_bindings_json = row[6] if len(row) > 6 else None
            
            # 更新任务状态为运行中
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE tasks
                SET status = ?, worker_id = ?, started_at = ?, updated_at = ?
                WHERE task_id = ?
            """, (
                TaskStatus.RUNNING.value,
                worker_id,
                now,
                now,
                task_id
            ))
            
            # 更新 worker 状态
            cursor.execute("""
                UPDATE workers
                SET status = 'busy', current_task_id = ?, last_heartbeat = ?
                WHERE worker_id = ?
            """, (task_id, now, worker_id))
            
            conn.commit()
            
            metadata = json.loads(metadata_json) if metadata_json else {}
            input_bindings = json.loads(input_bindings_json) if input_bindings_json else None
            
            debug_log(f"Worker {worker_id} 获取任务: {task_id} ({task_name})")
            
            out = {
                "task_id": task_id,
                "task_type": task_type,
                "task_name": task_name,
                "priority": priority,
                "metadata": metadata,
            }
            if depends_on_task_id:
                out["depends_on_task_id"] = depends_on_task_id
            if input_bindings:
                out["input_bindings"] = input_bindings
            return out
        except Exception as e:
            debug_log(f"获取任务失败: {e}", level="error")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None
    ) -> bool:
        """
        更新任务进度
        
        Args:
            task_id: 任务 ID
            progress: 进度（0-100）
            message: 进度消息
            
        Returns:
            是否成功
        """
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            updates = ["progress = ?", "updated_at = ?"]
            params = [max(0, min(100, progress)), now]
            
            if message:
                updates.append("message = ?")
                params.append(message)
            
            params.append(task_id)
            
            cursor.execute(f"""
                UPDATE tasks
                SET {', '.join(updates)}
                WHERE task_id = ?
            """, params)
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新任务进度失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def complete_task(
        self,
        task_id: str,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务 ID
            result: 任务结果
            error: 错误信息（如果有）
            
        Returns:
            是否成功
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取任务信息
            cursor.execute("""
                SELECT worker_id, started_at, retry_count, max_retries
                FROM tasks
                WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            worker_id, started_at_str, retry_count, max_retries = row
            
            now = datetime.now().isoformat()
            started_at = datetime.fromisoformat(started_at_str) if started_at_str else datetime.now()
            duration = (datetime.now() - started_at).total_seconds()
            
            if error:
                # 失败且还有重试次数：直接重新入队
                if retry_count < max_retries:
                    cursor.execute("""
                        UPDATE tasks
                        SET status = ?, error = ?, retry_count = ?, queued_at = ?, updated_at = ?
                        WHERE task_id = ?
                    """, (
                        TaskStatus.QUEUED.value,
                        error,
                        retry_count + 1,
                        now,
                        now,
                        task_id
                    ))
                    debug_log(f"任务 {task_id} 失败，将重试 ({retry_count + 1}/{max_retries})")
                else:
                    # 超过最大重试次数，标记为失败
                    cursor.execute("""
                        UPDATE tasks
                        SET status = ?, error = ?, completed_at = ?, duration = ?, updated_at = ?
                        WHERE task_id = ?
                    """, (
                        TaskStatus.FAILED.value,
                        error,
                        now,
                        duration,
                        now,
                        task_id
                    ))
                    
                    # 更新 worker 统计
                    if worker_id:
                        cursor.execute("""
                            UPDATE workers
                            SET status = 'idle', current_task_id = NULL, failed_tasks = failed_tasks + 1
                            WHERE worker_id = ?
                        """, (worker_id,))
                    
                    debug_log(f"任务 {task_id} 最终失败: {error}")
                    # 管道：级联标记依赖本任务的下游为失败
                    cursor.execute("""
                        UPDATE tasks SET status = ?, error = ?, updated_at = ?
                        WHERE depends_on_task_id = ? AND status = ?
                    """, (TaskStatus.FAILED.value, "上游任务失败，管道终止", now, task_id, TaskStatus.QUEUED.value))
            else:
                # 成功完成
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = ?, duration = ?, 
                        progress = 100, updated_at = ?
                    WHERE task_id = ?
                """, (
                    TaskStatus.COMPLETED.value,
                    json.dumps(result) if result is not None else None,
                    now,
                    duration,
                    now,
                    task_id
                ))
                
                # 更新 worker 统计
                if worker_id:
                    cursor.execute("""
                        UPDATE workers
                        SET status = 'idle', current_task_id = NULL, completed_tasks = completed_tasks + 1
                        WHERE worker_id = ?
                    """, (worker_id,))
                
                debug_log(f"任务 {task_id} 完成")
            
            conn.commit()
            return True
        except Exception as e:
            debug_log(f"完成任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功
        """
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取 worker_id
            cursor.execute("SELECT worker_id FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            worker_id = row[0] if row else None
            
            # 取消 QUEUED 或 RUNNING 状态的任务
            cursor.execute("""
                UPDATE tasks
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE task_id = ? AND status IN (?, ?)
            """, (
                TaskStatus.CANCELLED.value,
                now,
                now,
                task_id,
                TaskStatus.QUEUED.value,
                TaskStatus.RUNNING.value
            ))
            main_cancelled = cursor.rowcount
            # 管道：级联取消依赖本任务的下游（仅 queued）
            cursor.execute("""
                UPDATE tasks SET status = ?, error = ?, updated_at = ?
                WHERE depends_on_task_id = ? AND status = ?
            """, (TaskStatus.CANCELLED.value, "上游任务已取消，管道终止", now, task_id, TaskStatus.QUEUED.value))
            
            # 若已取消，更新 worker 状态
            if main_cancelled > 0:
                if worker_id:
                    cursor.execute("""
                        UPDATE workers
                        SET status = 'idle', current_task_id = NULL
                        WHERE worker_id = ?
                    """, (worker_id,))
            
            conn.commit()
            return main_cancelled > 0
        except Exception as e:
            debug_log(f"取消任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务信息字典
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT task_id, task_type, task_name, status, priority,
                       worker_id, created_at, queued_at, started_at, completed_at,
                       duration, progress, message, result, error,
                       retry_count, max_retries, metadata,
                       depends_on_task_id, input_bindings, pipeline_id, deleted_at
                FROM tasks
                WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            d = {
                "task_id": row[0],
                "task_type": row[1],
                "task_name": row[2],
                "status": row[3],
                "priority": row[4],
                "worker_id": row[5],
                "created_at": row[6],
                "queued_at": row[7],
                "started_at": row[8],
                "completed_at": row[9],
                "duration": row[10],
                "progress": row[11],
                "message": row[12],
                "result": json.loads(row[13]) if row[13] else None,
                "error": row[14],
                "retry_count": row[15],
                "max_retries": row[16],
                "metadata": json.loads(row[17]) if row[17] else {},
            }
            if len(row) > 18:
                d["depends_on_task_id"] = row[18]
                d["input_bindings"] = json.loads(row[19]) if row[19] else None
            if len(row) > 20:
                d["pipeline_id"] = row[20]
            if len(row) > 21:
                d["deleted_at"] = row[21]
            return d
        except Exception as e:
            debug_log(f"获取任务失败: {e}", level="error")
            return None
        finally:
            conn.close()
    
    def get_task_id_by_prefix(self, prefix: str) -> Optional[str]:
        """按 task_id 前缀查找（如 8 位短 id），返回第一个匹配的完整 task_id。"""
        if not prefix or len(prefix) < 4:
            return None
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT task_id FROM tasks WHERE task_id LIKE ? LIMIT 1",
                (prefix.strip() + "%",),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    
    def update_task_result(self, task_id: str, result: Dict[str, Any]) -> bool:
        """更新已存在任务的 result 字段（用于补全 output_file 等满足管道衔接）。"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE tasks SET result = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(result), datetime.now().isoformat(), task_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新 result 失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def requeue_failed_task(self, task_id: str) -> bool:
        """将已失败的任务重置为待执行（清空 error），便于上游补全 result 后再次被拉取执行。"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE tasks
                SET status = ?, error = NULL, updated_at = ?, completed_at = NULL, duration = NULL
                WHERE task_id = ? AND status = ?
            """, (TaskStatus.QUEUED.value, now, task_id, TaskStatus.FAILED.value))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"重新入队失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def reset_task_to_queued(self, task_id: str) -> bool:
        """将已完成或已失败的任务原地重置为待执行：只改状态与执行结果，不新开任务。清空 result、error、时间与进度等，retry_count 置 0，任务可再次被拉取执行。"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE tasks
                SET status = ?, result = NULL, error = NULL, completed_at = NULL, duration = NULL,
                    started_at = NULL, worker_id = NULL, progress = 0, message = NULL, retry_count = 0,
                    queued_at = ?, updated_at = ?
                WHERE task_id = ? AND status IN (?, ?)
            """, (TaskStatus.QUEUED.value, now, now, task_id, TaskStatus.COMPLETED.value, TaskStatus.FAILED.value))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"重置任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        """
        彻底删除任务（物理删除）。仅允许删除 queued、completed、failed、cancelled 状态，
        或已软删除（deleted_at 非空）的任务；running 且未软删除时需先取消再删除。
        删除前将依赖本任务的下游（depends_on_task_id = 本任务）级联标记为取消，再删除本任务。
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status, deleted_at FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return False
            status, deleted_at = row[0], row[1]
            if status == TaskStatus.RUNNING.value and not deleted_at:
                return False
            allowed = (
                TaskStatus.QUEUED.value,
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            )
            if status not in allowed and not deleted_at:
                return False
            now = datetime.now().isoformat()
            # 级联：将依赖本任务且为 queued 的下游标记为取消
            cursor.execute("""
                UPDATE tasks SET status = ?, error = ?, updated_at = ?
                WHERE depends_on_task_id = ? AND status = ?
            """, (TaskStatus.CANCELLED.value, "上游任务已删除，管道终止", now, task_id, TaskStatus.QUEUED.value))
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            if deleted:
                debug_log(f"任务已删除: {task_id}")
            return deleted
        except Exception as e:
            debug_log(f"删除任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def soft_delete_task(self, task_id: str) -> bool:
        """软删除任务：设置 deleted_at，仅允许对未软删除且非 running 的任务操作。"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE tasks SET deleted_at = ?, updated_at = ?
                WHERE task_id = ? AND deleted_at IS NULL AND status != ?
            """, (now, now, task_id, TaskStatus.RUNNING.value))
            ok = cursor.rowcount > 0
            conn.commit()
            if ok:
                debug_log(f"任务已软删除: {task_id}")
            return ok
        except Exception as e:
            debug_log(f"软删除任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def restore_task(self, task_id: str) -> bool:
        """恢复任务：清除 deleted_at，仅对已软删除的任务有效。"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE tasks SET deleted_at = NULL, updated_at = ?
                WHERE task_id = ? AND deleted_at IS NOT NULL
            """, (now, task_id))
            ok = cursor.rowcount > 0
            conn.commit()
            if ok:
                debug_log(f"任务已恢复: {task_id}")
            return ok
        except Exception as e:
            debug_log(f"恢复任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出任务。
        include_deleted: None 或 'exclude' 仅未删除；'only' 仅已软删除。
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT task_id, task_type, task_name, status, priority,
                       worker_id, created_at, started_at, completed_at,
                       duration, progress, message, error, retry_count, result,
                       depends_on_task_id, input_bindings, pipeline_id, deleted_at
                FROM tasks
            """
            params = []
            conditions = []
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if include_deleted == "only":
                conditions.append("deleted_at IS NOT NULL")
            elif include_deleted is None or include_deleted == "exclude":
                conditions.append("deleted_at IS NULL")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                result_json = row[14] if len(row) > 14 else None
                result_summary = ""
                if row[3] == TaskStatus.COMPLETED.value and result_json:
                    try:
                        obj = json.loads(result_json)
                        if isinstance(obj, dict):
                            result_summary = obj.get("summary") or ""
                    except Exception:
                        pass
                t = {
                    "task_id": row[0],
                    "task_type": row[1],
                    "task_name": row[2],
                    "status": row[3],
                    "priority": row[4],
                    "worker_id": row[5],
                    "created_at": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                    "duration": row[9],
                    "progress": row[10],
                    "message": row[11],
                    "error": row[12],
                    "retry_count": row[13],
                    "result_summary": result_summary or None,
                }
                if len(row) > 16:
                    t["depends_on_task_id"] = row[15]
                    t["input_bindings"] = json.loads(row[16]) if row[16] else None
                if len(row) > 17:
                    t["pipeline_id"] = row[17]
                if len(row) > 18:
                    t["deleted_at"] = row[18]
                tasks.append(t)
            
            return tasks
        except Exception as e:
            debug_log(f"列出任务失败: {e}", level="error")
            return []
        finally:
            conn.close()
    
    def register_worker(self, worker_id: str, worker_name: str) -> bool:
        """
        注册 Worker
        
        Args:
            worker_id: Worker ID
            worker_name: Worker 名称
            
        Returns:
            是否成功
        """
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO workers (
                    worker_id, worker_name, status, last_heartbeat, started_at
                ) VALUES (?, ?, 'idle', ?, ?)
            """, (worker_id, worker_name, now, now))
            
            conn.commit()
            debug_log(f"注册 Worker: {worker_id} ({worker_name})")
            return True
        except Exception as e:
            debug_log(f"注册 Worker 失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_worker_heartbeat(self, worker_id: str) -> bool:
        """
        更新 Worker 心跳
        
        Args:
            worker_id: Worker ID
            
        Returns:
            是否成功
        """
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE workers
                SET last_heartbeat = ?
                WHERE worker_id = ?
            """, (now, worker_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新 Worker 心跳失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def list_workers(self) -> List[Dict[str, Any]]:
        """
        列出所有 Worker
        
        Returns:
            Worker 列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT worker_id, worker_name, status, current_task_id,
                       last_heartbeat, started_at, completed_tasks, failed_tasks
                FROM workers
                ORDER BY last_heartbeat DESC
            """)
            
            rows = cursor.fetchall()
            workers = []
            
            for row in rows:
                workers.append({
                    "worker_id": row[0],
                    "worker_name": row[1],
                    "status": row[2],
                    "current_task_id": row[3],
                    "last_heartbeat": row[4],
                    "started_at": row[5],
                    "completed_tasks": row[6],
                    "failed_tasks": row[7]
                })
            
            return workers
        except Exception as e:
            debug_log(f"列出 Worker 失败: {e}", level="error")
            return []
        finally:
            conn.close()
    
    def cleanup_stale_tasks(self, max_idle_minutes: int = 30) -> int:
        """
        清理超时的运行中任务（可能是 worker 崩溃导致的）
        
        Args:
            max_idle_minutes: 最大空闲时间（分钟）
            
        Returns:
            清理的任务数量
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 查找超时的运行中任务
            cutoff_time = datetime.now().isoformat()
            cursor.execute("""
                SELECT task_id, worker_id
                FROM tasks
                WHERE status = ? AND started_at < datetime('now', '-' || ? || ' minutes')
            """, (TaskStatus.RUNNING.value, max_idle_minutes))
            
            stale_tasks = cursor.fetchall()
            
            if not stale_tasks:
                return 0
            
            # 将这些任务重新入队
            now = datetime.now().isoformat()
            task_ids = [task[0] for task in stale_tasks]
            worker_ids = set([task[1] for task in stale_tasks if task[1]])
            
            placeholders = ','.join(['?'] * len(task_ids))
            cursor.execute(f"""
                UPDATE tasks
                SET status = ?, worker_id = NULL, queued_at = ?, updated_at = ?
                WHERE task_id IN ({placeholders})
            """, [TaskStatus.QUEUED.value, now, now] + task_ids)
            
            # 更新 worker 状态
            for worker_id in worker_ids:
                cursor.execute("""
                    UPDATE workers
                    SET status = 'idle', current_task_id = NULL
                    WHERE worker_id = ?
                """, (worker_id,))
            
            conn.commit()
            
            count = len(stale_tasks)
            debug_log(f"清理了 {count} 个超时任务")
            return count
        except Exception as e:
            debug_log(f"清理超时任务失败: {e}", level="error")
            conn.rollback()
            return 0
        finally:
            conn.close()


# 全局实例
_task_queue_db: Optional[TaskQueueDB] = None


def get_task_queue_db() -> TaskQueueDB:
    """获取任务队列数据库实例"""
    global _task_queue_db
    if _task_queue_db is None:
        _task_queue_db = TaskQueueDB()
    return _task_queue_db

