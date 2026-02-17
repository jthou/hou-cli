"""测试审计相关路由"""
import subprocess
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared.debug_utils import debug_log

router = APIRouter()


class TestRunRequest(BaseModel):
    """测试运行请求"""
    test_path: Optional[str] = None  # 测试路径，None 表示运行所有测试
    verbose: bool = False  # 是否显示详细输出
    coverage: bool = False  # 是否生成覆盖率报告


class TestResult(BaseModel):
    """测试结果模型"""
    success: bool
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    test_results: List[Dict[str, Any]]
    output: str
    error: Optional[str] = None


def run_pytest(
    test_path: Optional[str] = None,
    verbose: bool = True,  # 默认使用 verbose 以便解析
    coverage: bool = False
) -> Dict[str, Any]:
    """
    运行 pytest 测试并返回结果
    
    Args:
        test_path: 测试路径，None 表示运行所有测试
        verbose: 是否显示详细输出
        coverage: 是否生成覆盖率报告
        
    Returns:
        测试结果字典
    """
    try:
        # 获取项目根目录
        # __file__ 是 backend/api/test_routes.py
        # 所以 project_root = backend/api/../.. = 项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.resolve()
        test_dir = project_root / "backend" / "api" / "tests"
        
        # 验证路径
        if not test_dir.exists():
            debug_log(f"测试目录不存在: {test_dir}", level="error")
            # 尝试其他可能的路径
            test_dir = project_root / "backend" / "api" / "tests"
            if not test_dir.exists():
                raise FileNotFoundError(f"测试目录不存在: {test_dir}")
        
        debug_log(f"项目根目录: {project_root}")
        debug_log(f"测试目录: {test_dir}")
        
        # 获取 Python 可执行文件路径
        python_exe = os.getenv("VIRTUAL_ENV") + "/bin/python" if os.getenv("VIRTUAL_ENV") else "python"
        
        # 构建 pytest 命令
        cmd = [python_exe, "-m", "pytest"]
        
        # 如果指定了测试路径，使用它；否则使用默认测试目录
        if test_path:
            if os.path.isabs(test_path):
                test_target = test_path
            else:
                test_target = str(test_dir / test_path)
        else:
            test_target = str(test_dir)
        
        cmd.append(test_target)
        debug_log(f"测试目标: {test_target}")
        
        # 添加选项
        # 始终使用 -v 模式以便正确解析测试结果
        cmd.append("-v")
        
        # 添加其他选项
        cmd.extend([
            "--tb=short",  # 简短的错误回溯
        ])
        
        # 如果需要覆盖率
        if coverage:
            cmd.extend([
                "--cov=backend.api",
                "--cov-report=json",
                "--cov-report=term"
            ])
        
        # 运行测试
        debug_log(f"运行测试命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=600  # 10 分钟超时（测试可能需要较长时间）
        )
        
        # 解析输出
        output_lines = result.stdout.split('\n')
        error_lines = result.stderr.split('\n')
        all_lines = output_lines + error_lines
        
        # 解析测试结果
        total_tests = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        duration = 0.0
        
        test_results = []
        
        # 首先尝试从总结行解析（最可靠）
        # 格式: "============= 13 failed, 59 passed, 20 warnings, 2 errors in 3.91s ============="
        summary_line = None
        for line in all_lines:
            # 匹配总结行：包含等号、failed/passed、in 和时间
            # 格式: "============= 13 failed, 59 passed, 20 warnings, 2 errors in 3.52s ============="
            line_lower = line.lower().strip()
            # 更宽松的匹配条件：只要包含 failed/passed 和 in 和时间单位
            if (("failed" in line_lower or "passed" in line_lower) and 
                "in" in line_lower and 
                ("s" in line_lower or "second" in line_lower)):
                summary_line = line.strip()
                debug_log(f"找到总结行: {summary_line}")
                break
        
        if summary_line:
            debug_log(f"解析总结行: {summary_line}")
            # 使用正则表达式解析总结行
            # 匹配: "13 failed, 59 passed, 20 warnings, 2 errors in 3.91s"
            match = re.search(r'(\d+)\s+failed', summary_line, re.IGNORECASE)
            if match:
                failed = int(match.group(1))
                debug_log(f"解析到 failed: {failed}")
            
            match = re.search(r'(\d+)\s+passed', summary_line, re.IGNORECASE)
            if match:
                passed = int(match.group(1))
                debug_log(f"解析到 passed: {passed}")
            
            match = re.search(r'(\d+)\s+errors?', summary_line, re.IGNORECASE)
            if match:
                errors = int(match.group(1))
                debug_log(f"解析到 errors: {errors}")
            
            match = re.search(r'(\d+)\s+skipped', summary_line, re.IGNORECASE)
            if match:
                skipped = int(match.group(1))
                debug_log(f"解析到 skipped: {skipped}")
            
            # 解析时间
            match = re.search(r'in\s+([\d.]+)s', summary_line, re.IGNORECASE)
            if match:
                try:
                    duration = float(match.group(1))
                    debug_log(f"解析到 duration: {duration}")
                except ValueError:
                    pass
            
            total_tests = passed + failed + skipped + errors
            debug_log(f"总计: {total_tests} (passed={passed}, failed={failed}, skipped={skipped}, errors={errors})")
        else:
            debug_log("未找到总结行，尝试其他解析方法")
        
        # 解析每个测试用例的详细结果（用于 test_results 列表）
        for line in all_lines:
            line = line.strip()
            if not line or "===" in line:
                continue
            
            # 解析测试结果行，例如: 
            # "api/tests/test_chat_routes.py::TestChatRoutes::test_chat_endpoint_success PASSED"
            # "api/tests/test_chat_routes.py::TestChatRoutes::test_chat_endpoint_error FAILED"
            if "::" in line:
                if " PASSED" in line or line.endswith("PASSED"):
                    parts = line.split("::")
                    test_name = parts[-1].replace(" PASSED", "").replace("PASSED", "").strip()
                    test_file = parts[0] if len(parts) > 0 else "unknown"
                    test_results.append({
                        "name": test_name,
                        "status": "passed",
                        "file": test_file
                    })
                elif " FAILED" in line or line.endswith("FAILED"):
                    parts = line.split("::")
                    test_name = parts[-1].replace(" FAILED", "").replace("FAILED", "").strip()
                    test_file = parts[0] if len(parts) > 0 else "unknown"
                    test_results.append({
                        "name": test_name,
                        "status": "failed",
                        "file": test_file
                    })
                elif " SKIPPED" in line or line.endswith("SKIPPED"):
                    parts = line.split("::")
                    test_name = parts[-1].replace(" SKIPPED", "").replace("SKIPPED", "").strip()
                    test_file = parts[0] if len(parts) > 0 else "unknown"
                    test_results.append({
                        "name": test_name,
                        "status": "skipped",
                        "file": test_file
                    })
                elif " ERROR" in line or line.endswith("ERROR"):
                    parts = line.split("::")
                    test_name = parts[-1].replace(" ERROR", "").replace("ERROR", "").strip()
                    test_file = parts[0] if len(parts) > 0 else "unknown"
                    test_results.append({
                        "name": test_name,
                        "status": "error",
                        "file": test_file
                    })
        
        # 如果没有从总结行解析到结果，尝试从 "collected X items" 行获取总数
        if total_tests == 0:
            for line in all_lines:
                if "collected" in line.lower() and "item" in line.lower():
                    match = re.search(r'collected\s+(\d+)\s+item', line, re.IGNORECASE)
                    if match:
                        total_tests = int(match.group(1))
                        # 如果没有总结行，从返回码推断
                        if result.returncode == 0:
                            passed = total_tests
                        else:
                            # 无法确定具体分布，使用解析到的 test_results
                            if test_results:
                                for tr in test_results:
                                    if tr["status"] == "passed":
                                        passed += 1
                                    elif tr["status"] == "failed":
                                        failed += 1
                                    elif tr["status"] == "skipped":
                                        skipped += 1
                                    elif tr["status"] == "error":
                                        errors += 1
                                total_tests = len(test_results)
                            else:
                                failed = 1
                                total_tests = 1
                        break
            
            # 最后的后备方案
            if total_tests == 0:
                if result.returncode == 0:
                    passed = 1
                    total_tests = 1
                else:
                    failed = 1
                    total_tests = 1
        
        success = result.returncode == 0 and failed == 0 and errors == 0
        
        return {
            "success": success,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "duration": duration,
            "test_results": test_results,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
            "return_code": result.returncode
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 1,
            "duration": 0.0,
            "test_results": [],
            "output": "",
            "error": "测试运行超时（超过 10 分钟）",
            "return_code": -1
        }
    except Exception as e:
        debug_log(f"运行测试失败: {str(e)}", level="error")
        return {
            "success": False,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 1,
            "duration": 0.0,
            "test_results": [],
            "output": "",
            "error": str(e),
            "return_code": -1
        }


@router.post("/tests/run")
async def run_tests(request: TestRunRequest):
    """运行测试并保存结果到数据库"""
    try:
        # 运行测试
        result = run_pytest(
            test_path=request.test_path,
            verbose=request.verbose,
            coverage=request.coverage
        )
        
        # 保存测试结果到数据库
        try:
            from backend.infrastructure.storage.test_results_db import get_test_results_db
            test_db = get_test_results_db()
            run_id = test_db.save_test_run(
                test_path=request.test_path,
                verbose=request.verbose,
                coverage=request.coverage,
                result=result
            )
            result["run_id"] = run_id
        except Exception as db_error:
            debug_log(f"保存测试结果到数据库失败: {str(db_error)}", level="warning")
            # 即使数据库保存失败，也返回测试结果
        
        return result
    except Exception as e:
        debug_log(f"运行测试 API 失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"运行测试失败: {str(e)}"
        )


@router.get("/tests/list")
async def list_tests():
    """列出所有测试文件"""
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        test_dir = project_root / "backend" / "api" / "tests"
        
        if not test_dir.exists():
            return {
                "success": False,
                "error": f"测试目录不存在: {test_dir}",
                "tests": []
            }
        
        # 查找所有测试文件
        test_files = []
        for test_file in test_dir.glob("test_*.py"):
            test_files.append({
                "name": test_file.name,
                "path": str(test_file.relative_to(project_root)),
                "full_path": str(test_file)
            })
        
        return {
            "success": True,
            "tests": sorted(test_files, key=lambda x: x["name"])
        }
    except Exception as e:
        debug_log(f"列出测试文件失败: {str(e)}", level="error")
        return {
            "success": False,
            "error": str(e),
            "tests": []
        }


@router.get("/tests/history")
async def get_test_history(limit: int = 20, offset: int = 0):
    """获取测试运行历史记录"""
    try:
        from backend.infrastructure.storage.test_results_db import get_test_results_db
        test_db = get_test_results_db()
        
        runs = test_db.list_test_runs(limit=limit, offset=offset)
        
        return {
            "success": True,
            "runs": runs,
            "total": len(runs)
        }
    except Exception as e:
        debug_log(f"获取测试历史失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取测试历史失败: {str(e)}"
        )


@router.get("/tests/history/{run_id}")
async def get_test_run_detail(run_id: str):
    """获取测试运行详情"""
    try:
        from backend.infrastructure.storage.test_results_db import get_test_results_db
        test_db = get_test_results_db()
        
        run = test_db.get_test_run(run_id)
        
        if not run:
            raise HTTPException(
                status_code=404,
                detail=f"测试运行记录不存在: {run_id}"
            )
        
        return {
            "success": True,
            "run": run
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"获取测试运行详情失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取测试运行详情失败: {str(e)}"
        )


@router.get("/tests/statistics")
async def get_test_statistics():
    """获取测试统计信息"""
    try:
        from backend.infrastructure.storage.test_results_db import get_test_results_db
        test_db = get_test_results_db()
        
        stats = test_db.get_test_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        debug_log(f"获取测试统计失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取测试统计失败: {str(e)}"
        )


@router.get("/tests/status")
async def get_test_status():
    """获取测试状态概览（从数据库获取最新结果）"""
    try:
        from backend.infrastructure.storage.test_results_db import get_test_results_db
        test_db = get_test_results_db()
        
        # 获取最新测试运行记录
        latest_run = test_db.get_latest_test_run()
        
        if latest_run:
            return {
                "success": True,
                "status": {
                    "last_run": latest_run.get("duration", 0),
                    "last_run_time": latest_run.get("started_at"),
                    "total_tests": latest_run.get("total_tests", 0),
                    "passed": latest_run.get("passed", 0),
                    "failed": latest_run.get("failed", 0),
                    "skipped": latest_run.get("skipped", 0),
                    "errors": latest_run.get("errors", 0),
                    "success_rate": latest_run.get("success_rate", 0)
                }
            }
        else:
            # 如果没有历史记录，返回默认值
            return {
                "success": True,
                "status": {
                    "last_run": 0,
                    "last_run_time": None,
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "success_rate": 0
                }
            }
    except Exception as e:
        debug_log(f"获取测试状态失败: {str(e)}", level="error")
        return {
            "success": False,
            "error": str(e),
            "status": None
        }

