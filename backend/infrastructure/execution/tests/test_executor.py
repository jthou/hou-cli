"""执行器测试"""
import pytest
import asyncio
import platform
from backend.infrastructure.execution.executor import SubprocessExecutor
from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult


class TestSubprocessExecutor:
    """SubprocessExecutor 测试"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return SubprocessExecutor()
    
    @pytest.mark.asyncio
    async def test_execute_python_code(self, executor):
        """测试执行 Python 代码"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=10
        )
        result = await executor.execute(request)
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "hello" in result.output
        assert result.exit_code == 0
        assert result.language == "python"
    
    @pytest.mark.asyncio
    async def test_execute_python_code_with_error(self, executor):
        """测试执行有错误的 Python 代码"""
        request = ExecutionRequest(
            code="print('hello'",  # 语法错误
            language="python",
            timeout=10
        )
        result = await executor.execute(request)
        
        assert result.success is False
        assert result.exit_code != 0
        assert len(result.error) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(platform.system() == "Windows", reason="bash not available on Windows")
    async def test_execute_bash_code(self, executor):
        """测试执行 bash 代码（Linux/macOS）"""
        request = ExecutionRequest(
            code="echo 'hello'",
            language="bash",
            timeout=10
        )
        result = await executor.execute(request)
        
        assert result.success is True
        assert "hello" in result.output
        assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor):
        """测试执行超时"""
        request = ExecutionRequest(
            code="import time; time.sleep(5)",  # 睡眠5秒
            language="python",
            timeout=1  # 1秒超时
        )
        result = await executor.execute(request)
        
        # 应该因为超时而失败
        assert result.success is False
        assert "timeout" in result.error.lower() or result.exit_code != 0
    
    @pytest.mark.asyncio
    async def test_execute_invalid_language(self, executor):
        """测试执行不支持的语言"""
        request = ExecutionRequest(
            code="console.log('hello')",
            language="javascript",  # 不支持的语言
            timeout=10
        )
        result = await executor.execute(request)
        
        assert result.success is False
        assert "not supported" in result.error.lower() or "unsupported" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_resource_usage_tracking(self, executor):
        """测试资源使用情况跟踪"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=10
        )
        result = await executor.execute(request)
        
        assert result.resource_usage is not None
        assert result.resource_usage.execution_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_working_dir_isolation(self, executor):
        """测试工作目录隔离"""
        request = ExecutionRequest(
            code="import os; print(os.getcwd())",
            language="python",
            timeout=10
        )
        result = await executor.execute(request)
        
        assert result.success is True
        # 工作目录应该是临时目录，不是当前目录
        assert "hou-cli-sandbox" in result.output or "tmp" in result.output.lower()





