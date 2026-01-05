"""数据模型测试"""
import pytest
from datetime import datetime
from backend.infrastructure.execution.models import (
    ExecutionRequest,
    ExecutionResult,
    ResourceUsage
)


class TestExecutionRequest:
    """ExecutionRequest 数据模型测试"""
    
    def test_execution_request_creation(self):
        """测试执行请求创建"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=30
        )
        assert request.code == "print('hello')"
        assert request.language == "python"
        assert request.timeout == 30
        assert request.memory_limit_mb is None
        assert request.cpu_limit is None
    
    def test_execution_request_with_limits(self):
        """测试带资源限制的执行请求"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=30,
            memory_limit_mb=512,
            cpu_limit=1.0
        )
        assert request.memory_limit_mb == 512
        assert request.cpu_limit == 1.0
    
    def test_execution_request_with_explanation(self):
        """测试带说明的执行请求"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=30,
            explanation="测试代码"
        )
        assert request.explanation == "测试代码"


class TestResourceUsage:
    """ResourceUsage 数据模型测试"""
    
    def test_resource_usage_creation(self):
        """测试资源使用情况创建"""
        usage = ResourceUsage(
            memory_used_mb=100.5,
            cpu_used_percent=50.0,
            execution_time_seconds=1.5
        )
        assert usage.memory_used_mb == 100.5
        assert usage.cpu_used_percent == 50.0
        assert usage.execution_time_seconds == 1.5
    
    def test_resource_usage_defaults(self):
        """测试资源使用情况默认值"""
        usage = ResourceUsage()
        assert usage.memory_used_mb == 0.0
        assert usage.cpu_used_percent == 0.0
        assert usage.execution_time_seconds == 0.0


class TestExecutionResult:
    """ExecutionResult 数据模型测试"""
    
    def test_execution_result_success(self):
        """测试成功执行结果"""
        result = ExecutionResult(
            success=True,
            output="hello",
            exit_code=0,
            language="python"
        )
        assert result.success is True
        assert result.output == "hello"
        assert result.exit_code == 0
        assert result.error == ""
        assert result.language == "python"
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)
    
    def test_execution_result_failure(self):
        """测试失败执行结果"""
        result = ExecutionResult(
            success=False,
            error="SyntaxError: invalid syntax",
            exit_code=1,
            language="python"
        )
        assert result.success is False
        assert result.error == "SyntaxError: invalid syntax"
        assert result.exit_code == 1
        assert result.output == ""
    
    def test_execution_result_with_resource_usage(self):
        """测试带资源使用情况的执行结果"""
        usage = ResourceUsage(
            memory_used_mb=50.0,
            cpu_used_percent=25.0,
            execution_time_seconds=0.5
        )
        result = ExecutionResult(
            success=True,
            output="hello",
            exit_code=0,
            resource_usage=usage
        )
        assert result.resource_usage == usage
        assert result.resource_usage.memory_used_mb == 50.0
    
    def test_execution_result_timestamp(self):
        """测试执行结果时间戳"""
        before = datetime.now()
        result = ExecutionResult(success=True)
        after = datetime.now()
        
        assert before <= result.timestamp <= after

