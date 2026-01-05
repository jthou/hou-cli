"""结果处理器测试"""
import pytest
from backend.infrastructure.execution.result_handler import ResultHandler
from backend.infrastructure.execution.models import ExecutionResult, ResourceUsage


class TestResultHandler:
    """ResultHandler 测试"""
    
    @pytest.fixture
    def handler(self):
        """创建结果处理器实例"""
        return ResultHandler()
    
    def test_truncate_large_output(self, handler):
        """测试截断大输出"""
        large_output = "x" * (11 * 1024 * 1024)  # 11MB
        truncated = handler.truncate_output(large_output)
        
        assert len(truncated.encode('utf-8')) <= 10 * 1024 * 1024  # 10MB
        assert "... (输出已截断" in truncated or "... (truncated" in truncated.lower()
    
    def test_no_truncate_small_output(self, handler):
        """测试不截断小输出"""
        small_output = "hello world"
        result = handler.truncate_output(small_output)
        
        assert result == small_output
    
    def test_format_error(self, handler):
        """测试错误格式化"""
        error = "SyntaxError: invalid syntax"
        formatted = handler.format_error(error)
        
        assert "SyntaxError" in formatted or "error" in formatted.lower()
    
    def test_format_resource_usage(self, handler):
        """测试资源使用格式化"""
        usage = ResourceUsage(
            memory_used_mb=100.5,
            cpu_used_percent=50.0,
            execution_time_seconds=1.5
        )
        formatted = handler.format_resource_usage(usage)
        
        assert "100" in formatted or "50" in formatted or "1.5" in formatted
    
    def test_process_result(self, handler):
        """测试处理执行结果"""
        result = ExecutionResult(
            success=True,
            output="hello" * 1000,  # 较大的输出
            exit_code=0,
            resource_usage=ResourceUsage(
                memory_used_mb=50.0,
                execution_time_seconds=0.5
            )
        )
        
        processed = handler.process_result(result)
        
        assert processed.success is True
        assert len(processed.output) <= len(result.output)  # 可能被截断
