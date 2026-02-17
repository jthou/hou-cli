"""测试结果数据库存储"""
import sqlite3
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from shared.storage_utils import get_storage_manager


class TestResultsDB:
    """测试结果数据库管理器"""
    
    def __init__(self, db_name: str = "test_results.db"):
        """
        初始化测试结果数据库
        
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
            # 创建测试运行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    run_id TEXT PRIMARY KEY,
                    test_path TEXT,
                    verbose BOOLEAN,
                    coverage BOOLEAN,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration REAL,
                    success BOOLEAN,
                    total_tests INTEGER,
                    passed INTEGER,
                    failed INTEGER,
                    skipped INTEGER,
                    errors INTEGER,
                    success_rate REAL,
                    return_code INTEGER,
                    output TEXT,
                    error TEXT
                )
            """)
            
            # 创建测试结果详情表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    test_file TEXT,
                    status TEXT NOT NULL,
                    duration REAL,
                    error_message TEXT,
                    FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_runs_started_at 
                ON test_runs(started_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_results_run_id 
                ON test_results(run_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_results_status 
                ON test_results(status)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))
    
    def save_test_run(
        self,
        test_path: Optional[str] = None,
        verbose: bool = False,
        coverage: bool = False,
        result: Dict[str, Any] = None
    ) -> str:
        """
        保存测试运行结果
        
        Args:
            test_path: 测试路径
            verbose: 是否详细输出
            coverage: 是否生成覆盖率报告
            result: 测试结果字典
            
        Returns:
            测试运行 ID
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        completed_at = datetime.now().isoformat()
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 保存测试运行记录
            cursor.execute("""
                INSERT INTO test_runs (
                    run_id, test_path, verbose, coverage,
                    started_at, completed_at, duration,
                    success, total_tests, passed, failed,
                    skipped, errors, success_rate, return_code,
                    output, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                test_path,
                verbose,
                coverage,
                started_at,
                completed_at,
                result.get("duration", 0.0) if result else 0.0,
                result.get("success", False) if result else False,
                result.get("total_tests", 0) if result else 0,
                result.get("passed", 0) if result else 0,
                result.get("failed", 0) if result else 0,
                result.get("skipped", 0) if result else 0,
                result.get("errors", 0) if result else 0,
                (
                    (result.get("passed", 0) / result.get("total_tests", 1) * 100)
                    if result and result.get("total_tests", 0) > 0
                    else 0.0
                ),
                result.get("return_code", -1) if result else -1,
                result.get("output", "") if result else "",
                result.get("error") if result else None
            ))
            
            # 保存测试结果详情
            if result and result.get("test_results"):
                for test_result in result["test_results"]:
                    result_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO test_results (
                            result_id, run_id, test_name, test_file,
                            status, duration, error_message
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result_id,
                        run_id,
                        test_result.get("name", ""),
                        test_result.get("file", ""),
                        test_result.get("status", "unknown"),
                        test_result.get("duration", 0.0),
                        test_result.get("error_message")
                    ))
            
            conn.commit()
            return run_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_test_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """获取测试运行记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT run_id, test_path, verbose, coverage,
                       started_at, completed_at, duration,
                       success, total_tests, passed, failed,
                       skipped, errors, success_rate, return_code,
                       output, error
                FROM test_runs
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 获取测试结果详情
            cursor.execute("""
                SELECT test_name, test_file, status, duration, error_message
                FROM test_results
                WHERE run_id = ?
                ORDER BY test_name
            """, (run_id,))
            
            test_results = []
            for result_row in cursor.fetchall():
                test_results.append({
                    "name": result_row[0],
                    "file": result_row[1],
                    "status": result_row[2],
                    "duration": result_row[3],
                    "error_message": result_row[4]
                })
            
            return {
                "run_id": row[0],
                "test_path": row[1],
                "verbose": bool(row[2]),
                "coverage": bool(row[3]),
                "started_at": row[4],
                "completed_at": row[5],
                "duration": row[6],
                "success": bool(row[7]),
                "total_tests": row[8],
                "passed": row[9],
                "failed": row[10],
                "skipped": row[11],
                "errors": row[12],
                "success_rate": row[13],
                "return_code": row[14],
                "output": row[15],
                "error": row[16],
                "test_results": test_results
            }
        finally:
            conn.close()
    
    def list_test_runs(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "started_at",
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        列出测试运行记录
        
        Args:
            limit: 限制数量
            offset: 偏移量
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            测试运行记录列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            order_direction = "DESC" if order_desc else "ASC"
            query = f"""
                SELECT run_id, test_path, verbose, coverage,
                       started_at, completed_at, duration,
                       success, total_tests, passed, failed,
                       skipped, errors, success_rate, return_code
                FROM test_runs
                ORDER BY {order_by} {order_direction}
            """
            
            params = []
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            runs = []
            for row in rows:
                runs.append({
                    "run_id": row[0],
                    "test_path": row[1],
                    "verbose": bool(row[2]),
                    "coverage": bool(row[3]),
                    "started_at": row[4],
                    "completed_at": row[5],
                    "duration": row[6],
                    "success": bool(row[7]),
                    "total_tests": row[8],
                    "passed": row[9],
                    "failed": row[10],
                    "skipped": row[11],
                    "errors": row[12],
                    "success_rate": row[13],
                    "return_code": row[14]
                })
            
            return runs
        finally:
            conn.close()
    
    def get_latest_test_run(self) -> Optional[Dict[str, Any]]:
        """获取最新的测试运行记录"""
        runs = self.list_test_runs(limit=1)
        if runs:
            return self.get_test_run(runs[0]["run_id"])
        return None
    
    def get_test_statistics(self) -> Dict[str, Any]:
        """获取测试统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 总运行次数
            cursor.execute("SELECT COUNT(*) FROM test_runs")
            total_runs = cursor.fetchone()[0]
            
            # 成功次数
            cursor.execute("SELECT COUNT(*) FROM test_runs WHERE success = 1")
            successful_runs = cursor.fetchone()[0]
            
            # 平均成功率
            cursor.execute("SELECT AVG(success_rate) FROM test_runs WHERE total_tests > 0")
            avg_success_rate = cursor.fetchone()[0] or 0.0
            
            # 平均测试数
            cursor.execute("SELECT AVG(total_tests) FROM test_runs WHERE total_tests > 0")
            avg_total_tests = cursor.fetchone()[0] or 0.0
            
            # 平均持续时间
            cursor.execute("SELECT AVG(duration) FROM test_runs WHERE duration > 0")
            avg_duration = cursor.fetchone()[0] or 0.0
            
            # 最后一次运行时间
            cursor.execute("SELECT MAX(started_at) FROM test_runs")
            last_run_time = cursor.fetchone()[0]
            
            return {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": total_runs - successful_runs,
                "avg_success_rate": round(avg_success_rate, 2),
                "avg_total_tests": round(avg_total_tests, 2),
                "avg_duration": round(avg_duration, 2),
                "last_run_time": last_run_time
            }
        finally:
            conn.close()


# 全局测试结果数据库实例（单例模式）
_test_results_db: Optional[TestResultsDB] = None


def get_test_results_db(db_name: str = "test_results.db") -> TestResultsDB:
    """
    获取测试结果数据库实例
    
    Args:
        db_name: 数据库文件名
        
    Returns:
        测试结果数据库实例
    """
    global _test_results_db
    if _test_results_db is None:
        _test_results_db = TestResultsDB(db_name)
    return _test_results_db

