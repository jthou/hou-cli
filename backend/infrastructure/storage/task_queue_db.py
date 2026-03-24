"""任务队列数据库存储（时间统一 UTC）"""
import sqlite3
import json
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta, timezone
from pathlib import Path
from enum import Enum
from shared.storage_utils import get_storage_manager
from shared.debug_utils import debug_log
from shared.time_utils import utc_now, utc_now_iso


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
            if "created_by_schedule_id" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN created_by_schedule_id TEXT")
            # 任务链（子任务/父子链路）：主任务分解入队、链尾负责清理
            if "parent_task_id" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN parent_task_id TEXT")
            if "chain_id" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN chain_id TEXT")
            if "chain_index" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN chain_index INTEGER")
            if "chain_total" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN chain_total INTEGER")
            if "is_chain_tail" not in cols:
                cursor.execute("ALTER TABLE tasks ADD COLUMN is_chain_tail INTEGER DEFAULT 0")
            conn.commit()

            # 定时任务表补列
            cursor.execute("PRAGMA table_info(scheduled_tasks)")
            sched_cols = [row[1] for row in cursor.fetchall()]
            if "consecutive_errors" not in sched_cols:
                cursor.execute(
                    "ALTER TABLE scheduled_tasks ADD COLUMN consecutive_errors INTEGER DEFAULT 0"
                )
            if "last_error" not in sched_cols:
                cursor.execute("ALTER TABLE scheduled_tasks ADD COLUMN last_error TEXT")
            conn.commit()

            # FTS5：已完成任务全文索引（general_chat 上下文检索）
            self._migrate_tasks_fts(conn)
        except Exception as e:
            debug_log(f"初始化任务队列数据库失败: {e}", level="error")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_tasks_fts(self, conn: sqlite3.Connection) -> None:
        """
        创建 tasks_fts（FTS5）及同步触发器；必要时全量回填。

        时间：2026-03-14；理由：用户要求 SQLite FTS5 检索已完成任务；方法：unicode61 分词 +
        body=名称+类型+消息；INSERT/UPDATE/DELETE 触发器维护；启动时计数不一致则 rebuild。
        时间：2026-03-23；理由：macOS 等环境 SQLite 未编译 JSON1 时 json_extract 在触发器中报 near "(": syntax error；
        方法：不在 SQL 中解析 result JSON（summary 仍可由 list_tasks/关键词路径命中）。
        明确兜底：未编译 ENABLE_FTS5 时跳过（search_completed_tasks_fts 返回空，由上层回退关键词排序）。
        """
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT sqlite_compileoption_used('ENABLE_FTS5')")
            if cursor.fetchone()[0] != 1:
                debug_log("SQLite 未启用 FTS5，跳过 tasks_fts 迁移", level="warning")
                return

            # 时间：2026-03-13；理由：无 USING fts5 时 SQLite 报 near "(": syntax error；方法：标准 fts5 建表语法
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                    task_id UNINDEXED,
                    body,
                    tokenize = 'unicode61'
                )
                """
            )

            for name in ("trg_tasks_fts_ai", "trg_tasks_fts_au", "trg_tasks_fts_ad"):
                cursor.execute(f"DROP TRIGGER IF EXISTS {name}")

            # 仅拼接文本列：避免 json_extract（需 JSON1）；无 JSON1 的 libsqlite 会整段触发器解析失败
            _fts_body_sql = (
                "trim("
                "COALESCE(NEW.task_name, '') || ' ' || COALESCE(NEW.task_type, '') || ' ' || "
                "COALESCE(NEW.message, '')"
                ")"
            )
            cursor.execute(
                f"""
                CREATE TRIGGER trg_tasks_fts_ai AFTER INSERT ON tasks BEGIN
                  INSERT INTO tasks_fts(task_id, body) VALUES (
                    NEW.task_id,
                    {_fts_body_sql}
                  );
                END
                """
            )
            cursor.execute(
                f"""
                CREATE TRIGGER trg_tasks_fts_au AFTER UPDATE ON tasks BEGIN
                  DELETE FROM tasks_fts WHERE task_id = NEW.task_id;
                  INSERT INTO tasks_fts(task_id, body) VALUES (
                    NEW.task_id,
                    {_fts_body_sql}
                  );
                END
                """
            )
            cursor.execute(
                """
                CREATE TRIGGER trg_tasks_fts_ad AFTER DELETE ON tasks BEGIN
                  DELETE FROM tasks_fts WHERE task_id = OLD.task_id;
                END
                """
            )

            cursor.execute("SELECT COUNT(*) FROM tasks_fts")
            n_fts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks")
            n_tasks = cursor.fetchone()[0]
            if n_fts == 0 and n_tasks > 0:
                self._rebuild_tasks_fts(cursor)
            elif n_fts != n_tasks:
                self._rebuild_tasks_fts(cursor)

            cursor.execute("SELECT COUNT(*) FROM tasks_fts")
            n_fts_final = cursor.fetchone()[0]
            conn.commit()
            debug_log(f"tasks_fts 就绪: fts={n_fts_final}, tasks={n_tasks}")
        except Exception as e:
            debug_log(f"tasks_fts 迁移失败（将回退关键词检索）: {e}", level="warning")
            conn.rollback()

    def _rebuild_tasks_fts(self, cursor: sqlite3.Cursor) -> None:
        """全量重建 FTS 行（与触发器 body 表达式一致）。"""
        cursor.execute("DELETE FROM tasks_fts")
        cursor.execute(
            """
            INSERT INTO tasks_fts(task_id, body)
            SELECT task_id,
              trim(
                COALESCE(task_name, '') || ' ' || COALESCE(task_type, '') || ' ' ||
                COALESCE(message, '')
              )
            FROM tasks
            """
        )
    
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
        created_by_schedule_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        chain_index: Optional[int] = None,
        chain_total: Optional[int] = None,
        is_chain_tail: bool = False,
    ) -> str:
        """
        创建新任务

        Args:
            pipeline_id: 同一管道编排的组号（可选），前端用于分组展示。
            created_by_schedule_id: 由哪个定时任务创建（可选），用于溯源。
            parent_task_id: 若本任务由某任务分解而来，指向该父任务。
            chain_id: 同一条链上的任务共用同一 chain_id，用于按链分组与展示。
            chain_index: 本任务在链中的序号（0-based）。
            chain_total: 本链子任务总数。
            is_chain_tail: 是否为链尾；链尾任务执行完成后负责清理链上共享资源。
        """
        task_id = str(uuid.uuid4())
        now = utc_now_iso()
        dep_id = (depends_on_task_id or "").strip() or None
        bindings_json = json.dumps(input_bindings) if input_bindings else None
        pipe_id = (pipeline_id or "").strip() or None
        sched_id = (created_by_schedule_id or "").strip() or None
        parent_id = (parent_task_id or "").strip() or None
        cid = (chain_id or "").strip() or None
        tail = 1 if is_chain_tail else 0

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, task_type, task_name, status, priority,
                    max_retries, metadata, created_at, queued_at, updated_at,
                    depends_on_task_id, input_bindings, pipeline_id, created_by_schedule_id,
                    parent_task_id, chain_id, chain_index, chain_total, is_chain_tail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                sched_id,
                parent_id,
                cid,
                chain_index,
                chain_total,
                tail,
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
            now = utc_now_iso()
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
        now = utc_now_iso()
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
            
            now = utc_now_iso()
            started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00")) if started_at_str else utc_now()
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            duration = (utc_now() - started_at).total_seconds()
            
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
        now = utc_now_iso()
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
                       depends_on_task_id, input_bindings, pipeline_id, deleted_at,
                       created_by_schedule_id,
                       parent_task_id, chain_id, chain_index, chain_total, is_chain_tail
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
            if len(row) > 22:
                d["created_by_schedule_id"] = row[22]
            if len(row) > 23:
                d["parent_task_id"] = row[23]
            if len(row) > 24:
                d["chain_id"] = row[24]
            if len(row) > 25:
                d["chain_index"] = row[25]
            if len(row) > 26:
                d["chain_total"] = row[26]
            if len(row) > 27:
                d["is_chain_tail"] = bool(row[27])
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
                (json.dumps(result), utc_now_iso(), task_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新 result 失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_task_before_requeue(
        self,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        task_name: Optional[str] = None,
        priority: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """重新执行前可编辑的字段：metadata、task_name、priority、max_retries。仅允许对已完成、已失败、已取消的任务修改。"""
        allowed_statuses = (
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        )
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            updates = ["updated_at = ?"]
            params: List[Any] = [utc_now_iso()]
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))
            if task_name is not None:
                updates.append("task_name = ?")
                params.append(task_name)
            if priority is not None:
                updates.append("priority = ?")
                params.append(priority)
            if max_retries is not None:
                updates.append("max_retries = ?")
                params.append(max_retries)
            if len(params) == 1:
                return True
            params.append(task_id)
            cursor.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ? AND status IN (?, ?, ?)",
                params + list(allowed_statuses),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新任务失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def requeue_failed_task(self, task_id: str) -> bool:
        """将已失败的任务重置为待执行（清空 error），便于上游补全 result 后再次被拉取执行。"""
        now = utc_now_iso()
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
        now = utc_now_iso()
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
            now = utc_now_iso()
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
            now = utc_now_iso()
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
            now = utc_now_iso()
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
        created_by_schedule_id: Optional[str] = None,
        include_result: bool = False,
        task_types: Optional[List[str]] = None,
        pipeline_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        列出任务。
        include_deleted: None 或 'exclude' 仅未删除；'only' 仅已软删除。
        created_by_schedule_id: 仅返回该定时任务创建的任务（支持前缀匹配）。
        include_result: 为 True 时，已完成任务的 result 列解析为 JSON 并放入 task["result"]，供执行记录等场景统一展示。
        task_types: 仅返回指定任务类型（如 ["url_to_wiki", "pdf_to_wiki"]），为空则不过滤。
        pipeline_only: 为 True 时仅返回 pipeline_id 非空的任务（管道编排创建的任务）。
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT task_id, task_type, task_name, status, priority,
                       worker_id, created_at, started_at, completed_at,
                       duration, progress, message, error, retry_count, result,
                       metadata,
                       depends_on_task_id, input_bindings, pipeline_id, deleted_at,
                       created_by_schedule_id,
                       parent_task_id, chain_id, chain_index, chain_total, is_chain_tail
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
            if created_by_schedule_id:
                sid = created_by_schedule_id.strip()
                if len(sid) == 8:
                    conditions.append("created_by_schedule_id LIKE ?")
                    params.append(sid + "%")
                else:
                    conditions.append("created_by_schedule_id = ?")
                    params.append(sid)
            if task_types:
                placeholders = ",".join("?" * len(task_types))
                conditions.append(f"task_type IN ({placeholders})")
                params.extend(task_types)
            if pipeline_only:
                conditions.append("pipeline_id IS NOT NULL AND pipeline_id != ''")
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
                result_obj = None
                if row[3] == TaskStatus.COMPLETED.value and result_json:
                    try:
                        obj = json.loads(result_json)
                        if isinstance(obj, dict):
                            result_summary = obj.get("summary") or ""
                            if include_result:
                                result_obj = obj
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
                if result_obj is not None:
                    t["result"] = result_obj
                if len(row) > 15:
                    t["metadata"] = json.loads(row[15]) if row[15] else {}
                if len(row) > 17:
                    t["depends_on_task_id"] = row[16]
                    t["input_bindings"] = json.loads(row[17]) if row[17] else None
                if len(row) > 18:
                    t["pipeline_id"] = row[18]
                if len(row) > 19:
                    t["deleted_at"] = row[19]
                if len(row) > 20:
                    t["created_by_schedule_id"] = row[20]
                if len(row) > 21:
                    t["parent_task_id"] = row[21]
                if len(row) > 22:
                    t["chain_id"] = row[22]
                if len(row) > 23:
                    t["chain_index"] = row[23]
                if len(row) > 24:
                    t["chain_total"] = row[24]
                if len(row) > 25:
                    t["is_chain_tail"] = bool(row[25])
                tasks.append(t)
            
            return tasks
        except Exception as e:
            debug_log(f"列出任务失败: {e}", level="error")
            return []
        finally:
            conn.close()

    def search_completed_tasks_fts(
        self,
        query: str,
        *,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        对已 completed 且未软删除的任务做 FTS5 检索，按 bm25(f) 排序。

        时间：2026-03-14；理由：general_chat 按问题检索已完成任务；方法：fts5_match + MATCH + bm25；
        无 tasks_fts 或语法错误时返回 []，由调用方回退关键词排序。
        """
        from backend.infrastructure.storage.fts5_match import build_fts5_match_query

        mq = build_fts5_match_query(query)
        if not mq:
            return []
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT t.task_id
                    FROM tasks_fts
                    INNER JOIN tasks AS t ON t.task_id = tasks_fts.task_id
                    WHERE tasks_fts MATCH ?
                      AND t.status = ?
                      AND (t.deleted_at IS NULL)
                    ORDER BY bm25(tasks_fts)
                    LIMIT ?
                    """,
                    (mq, TaskStatus.COMPLETED.value, limit),
                )
                ids = [r[0] for r in cur.fetchall()]
            except sqlite3.OperationalError as e:
                if "no such table" in str(e).lower():
                    return []
                debug_log(f"tasks_fts 查询失败: {e}", level="warning")
                return []
        finally:
            conn.close()

        if not ids:
            return []
        out: List[Dict[str, Any]] = []
        for tid in ids:
            t = self.get_task(tid)
            if not t:
                continue
            rs = ""
            if t.get("status") == TaskStatus.COMPLETED.value and t.get("result"):
                rj = t.get("result")
                if isinstance(rj, dict):
                    rs = rj.get("summary") or ""
            out.append(
                {
                    "task_id": t["task_id"],
                    "task_type": t["task_type"],
                    "task_name": t["task_name"],
                    "status": t["status"],
                    "priority": t["priority"],
                    "worker_id": t.get("worker_id"),
                    "created_at": t.get("created_at"),
                    "started_at": t.get("started_at"),
                    "completed_at": t.get("completed_at"),
                    "duration": t.get("duration"),
                    "progress": t.get("progress"),
                    "message": t.get("message"),
                    "error": t.get("error"),
                    "retry_count": t.get("retry_count"),
                    "result_summary": rs or None,
                }
            )
        return out

    def list_completed_tasks_excluding_ids(
        self,
        exclude_ids: Optional[Set[str]],
        *,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        最近完成的 tasks，排除指定 task_id（用于 FTS 命中不足时按时间补位）。

        时间：2026-03-14；理由：与 FTS 结果合并去重；方法：拉一批 completed 再过滤（规模可控）。
        """
        if limit <= 0:
            return []
        ex = set(exclude_ids or [])
        if not ex:
            return self.list_tasks(status=TaskStatus.COMPLETED, limit=limit, offset=0)
        batch = self.list_tasks(status=TaskStatus.COMPLETED, limit=min(200, limit * 5), offset=0)
        out = [t for t in batch if t.get("task_id") not in ex]
        return out[:limit]

    def count_tasks(
        self,
        status: Optional[TaskStatus] = None,
        include_deleted: Optional[str] = None,
        created_by_schedule_id: Optional[str] = None,
        task_types: Optional[List[str]] = None,
        pipeline_only: bool = False,
    ) -> int:
        """统计符合条件的任务总数（与 list_tasks 使用相同过滤条件）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) FROM tasks"
            params = []
            conditions = []
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if include_deleted == "only":
                conditions.append("deleted_at IS NOT NULL")
            elif include_deleted is None or include_deleted == "exclude":
                conditions.append("deleted_at IS NULL")
            if created_by_schedule_id:
                sid = created_by_schedule_id.strip()
                if len(sid) == 8:
                    conditions.append("created_by_schedule_id LIKE ?")
                    params.append(sid + "%")
                else:
                    conditions.append("created_by_schedule_id = ?")
                    params.append(sid)
            if task_types:
                placeholders = ",".join("?" * len(task_types))
                conditions.append(f"task_type IN ({placeholders})")
                params.extend(task_types)
            if pipeline_only:
                conditions.append("pipeline_id IS NOT NULL AND pipeline_id != ''")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            debug_log(f"统计任务失败: {e}", level="error")
            return 0
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
        now = utc_now_iso()
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
        now = utc_now_iso()
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
            cutoff_time = utc_now_iso()
            cursor.execute("""
                SELECT task_id, worker_id
                FROM tasks
                WHERE status = ? AND started_at < datetime('now', '-' || ? || ' minutes')
            """, (TaskStatus.RUNNING.value, max_idle_minutes))
            
            stale_tasks = cursor.fetchall()
            
            if not stale_tasks:
                return 0
            
            # 将这些任务重新入队
            now = utc_now_iso()
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

    # ========== 定时任务 ==========

    def create_scheduled_task(
        self,
        task_type: str,
        task_name: str,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建定时任务，返回 schedule_id"""
        from backend.infrastructure.schedule import compute_next_run_time

        if schedule_type not in ("interval", "cron"):
            raise ValueError("schedule_type 必须是 'interval' 或 'cron'")
        if schedule_type == "interval":
            if "interval_seconds" not in schedule_config:
                raise ValueError("interval 类型需要 schedule_config.interval_seconds")
            sec = schedule_config.get("interval_seconds")
            if not isinstance(sec, (int, float)) or sec < 60:
                raise ValueError("interval_seconds 必须 >= 60")
        if schedule_type == "cron":
            if not (schedule_config.get("cron") or "").strip():
                raise ValueError("cron 类型需要 schedule_config.cron 非空")

        schedule_id = str(uuid.uuid4())
        now = utc_now_iso()
        next_run = compute_next_run_time(
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            last_run_time=None,
            created_at=now,
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO scheduled_tasks (
                    schedule_id, task_type, task_name, schedule_type, schedule_config,
                    next_run_time, is_active, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (
                schedule_id,
                task_type,
                task_name,
                schedule_type,
                json.dumps(schedule_config),
                next_run,
                json.dumps(metadata or {}),
                now,
                now,
            ))
            conn.commit()
            debug_log(f"创建定时任务: {schedule_id} ({task_name})")
            return schedule_id
        except Exception as e:
            debug_log(f"创建定时任务失败: {e}", level="error")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_due_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取到期的定时任务（is_active=1 且 next_run_time <= now）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT schedule_id, task_type, task_name, schedule_type, schedule_config,
                       next_run_time, last_run_time, is_active, metadata,
                       consecutive_errors, last_error, created_at, updated_at
                FROM scheduled_tasks
                WHERE is_active = 1 AND datetime(next_run_time) <= datetime('now')
                ORDER BY next_run_time ASC
            """)
            rows = cursor.fetchall()
            out = []
            for row in rows:
                cfg = json.loads(row[4]) if row[4] else {}
                meta = json.loads(row[8]) if row[8] else {}
                out.append({
                    "schedule_id": row[0],
                    "task_type": row[1],
                    "task_name": row[2],
                    "schedule_type": row[3],
                    "schedule_config": cfg,
                    "next_run_time": row[5],
                    "last_run_time": row[6],
                    "is_active": row[7],
                    "metadata": meta,
                    "consecutive_errors": row[9] if len(row) > 9 else 0,
                    "last_error": row[10] if len(row) > 10 else None,
                })
            return out
        except Exception as e:
            debug_log(f"获取到期定时任务失败: {e}", level="error")
            return []
        finally:
            conn.close()

    def update_scheduled_task_after_success(
        self,
        schedule_id: str,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        last_run_time: str,
    ) -> bool:
        """定时任务成功创建任务后更新状态"""
        from backend.infrastructure.schedule import compute_next_run_time

        next_run = compute_next_run_time(
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            last_run_time=last_run_time,
            created_at=last_run_time,
        )
        now = utc_now_iso()

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE scheduled_tasks
                SET next_run_time = ?, last_run_time = ?, consecutive_errors = 0,
                    last_error = NULL, updated_at = ?
                WHERE schedule_id = ?
            """, (next_run, last_run_time, now, schedule_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新定时任务成功状态失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_scheduled_task_on_failure(self, schedule_id: str, error: str) -> bool:
        """定时任务失败后应用错误退避"""
        from backend.infrastructure.schedule import error_backoff_seconds

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT consecutive_errors FROM scheduled_tasks WHERE schedule_id = ?",
                (schedule_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False
            consecutive = (row[0] or 0) + 1
            backoff_sec = error_backoff_seconds(consecutive)
            next_run = (utc_now() + timedelta(seconds=backoff_sec)).isoformat()
            now = utc_now_iso()

            cursor.execute("""
                UPDATE scheduled_tasks
                SET next_run_time = ?, consecutive_errors = ?, last_error = ?, updated_at = ?
                WHERE schedule_id = ?
            """, (next_run, consecutive, error[:500] if error else None, now, schedule_id))
            conn.commit()
            debug_log(f"定时任务 {schedule_id} 失败，退避 {backoff_sec}s，连续失败 {consecutive} 次")
            return True
        except Exception as e:
            debug_log(f"更新定时任务失败状态失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_scheduled_tasks(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """列出定时任务"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if active_only:
                cursor.execute("""
                    SELECT schedule_id, task_type, task_name, schedule_type, schedule_config,
                           next_run_time, last_run_time, is_active, metadata,
                           consecutive_errors, last_error, created_at, updated_at
                    FROM scheduled_tasks WHERE is_active = 1
                    ORDER BY next_run_time ASC
                """)
            else:
                cursor.execute("""
                    SELECT schedule_id, task_type, task_name, schedule_type, schedule_config,
                           next_run_time, last_run_time, is_active, metadata,
                           consecutive_errors, last_error, created_at, updated_at
                    FROM scheduled_tasks
                    ORDER BY next_run_time ASC
                """)
            rows = cursor.fetchall()
            out = []
            for row in rows:
                cfg = json.loads(row[4]) if row[4] else {}
                meta = json.loads(row[8]) if row[8] else {}
                out.append({
                    "schedule_id": row[0],
                    "task_type": row[1],
                    "task_name": row[2],
                    "schedule_type": row[3],
                    "schedule_config": cfg,
                    "next_run_time": row[5],
                    "last_run_time": row[6],
                    "is_active": bool(row[7]),
                    "metadata": meta,
                    "consecutive_errors": row[9] if len(row) > 9 else 0,
                    "last_error": row[10] if len(row) > 10 else None,
                    "created_at": row[11],
                    "updated_at": row[12],
                })
            return out
        except Exception as e:
            debug_log(f"列出定时任务失败: {e}", level="error")
            return []
        finally:
            conn.close()

    def update_scheduled_task(
        self,
        schedule_id: str,
        task_name: Optional[str] = None,
        schedule_type: Optional[str] = None,
        schedule_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新定时任务参数，修改 schedule_config 时会重新计算 next_run_time"""
        from backend.infrastructure.schedule import compute_next_run_time

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT schedule_type, schedule_config, last_run_time, created_at
                FROM scheduled_tasks WHERE schedule_id = ?
            """, (schedule_id,))
            row = cursor.fetchone()
            if not row:
                return False

            current_schedule_type, current_schedule_config, last_run_time, created_at = row
            current_cfg = json.loads(current_schedule_config) if current_schedule_config else {}

            st = schedule_type or current_schedule_type
            cfg = schedule_config if schedule_config is not None else current_cfg

            if st not in ("interval", "cron"):
                raise ValueError("schedule_type 必须是 'interval' 或 'cron'")
            if st == "interval":
                if "interval_seconds" not in cfg:
                    raise ValueError("interval 类型需要 schedule_config.interval_seconds")
                sec = cfg.get("interval_seconds")
                if not isinstance(sec, (int, float)) or sec < 60:
                    raise ValueError("interval_seconds 必须 >= 60")
            if st == "cron":
                if not (cfg.get("cron") or "").strip():
                    raise ValueError("cron 类型需要 schedule_config.cron 非空")

            now = utc_now_iso()
            updates = ["updated_at = ?"]
            params = [now]

            # 仅当调度配置变更时重新计算 next_run_time
            if schedule_type is not None or schedule_config is not None:
                next_run = compute_next_run_time(
                    schedule_type=st,
                    schedule_config=cfg,
                    last_run_time=last_run_time,
                    created_at=created_at,
                )
                updates.append("next_run_time = ?")
                params.append(next_run)

            if task_name is not None:
                updates.append("task_name = ?")
                params.append(task_name.strip() or "")
            if schedule_type is not None:
                updates.append("schedule_type = ?")
                params.append(schedule_type)
            if schedule_config is not None:
                updates.append("schedule_config = ?")
                params.append(json.dumps(schedule_config))
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))

            params.append(schedule_id)
            cursor.execute(
                f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE schedule_id = ?",
                params,
            )
            conn.commit()
            debug_log(f"更新定时任务: {schedule_id}")
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"更新定时任务失败: {e}", level="error")
            conn.rollback()
            raise
        finally:
            conn.close()

    def toggle_scheduled_task(self, schedule_id: str, is_active: bool) -> bool:
        """启用/禁用定时任务"""
        now = utc_now_iso()
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE scheduled_tasks SET is_active = ?, updated_at = ? WHERE schedule_id = ?
            """, (1 if is_active else 0, now, schedule_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"切换定时任务状态失败: {e}", level="error")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_scheduled_task(self, schedule_id: str) -> bool:
        """删除定时任务"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM scheduled_tasks WHERE schedule_id = ?", (schedule_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            debug_log(f"删除定时任务失败: {e}", level="error")
            conn.rollback()
            return False
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

