"""安全执行器测试"""
import pytest
import asyncio
from backend.infrastructure.execution.secure_executor import SecureExecutor
from backend.infrastructure.execution.models import ExecutionRequest


class TestSecureExecutor:
    """SecureExecutor 测试"""
    
    @pytest.fixture
    def executor(self):
        """创建安全执行器实例"""
        return SecureExecutor()
    
    @pytest.mark.asyncio
    async def test_block_dangerous_command(self, executor):
        """测试阻止危险命令"""
        request = ExecutionRequest(
            code="rm -rf /",
            language="bash",
            timeout=10
        )
        result = await executor.execute_code_safely(request)
        
        assert result.success is False
        assert "not allowed" in result.error.lower() or "blocked" in result.error.lower() or "dangerous" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_allow_safe_command(self, executor):
        """测试允许安全命令"""
        request = ExecutionRequest(
            code="print('hello')",
            language="python",
            timeout=10
        )
        result = await executor.execute_code_safely(request)
        
        assert result.success is True
        assert "hello" in result.output
    
    @pytest.mark.asyncio
    async def test_block_restricted_path(self, executor):
        """测试阻止访问受限路径"""
        request = ExecutionRequest(
            code="import os; print(os.listdir('/etc'))",
            language="python",
            timeout=10
        )
        result = await executor.execute_code_safely(request)
        
        # 应该被阻止或执行失败
        assert result.success is False or "restricted" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_block_invalid_language(self, executor):
        """测试阻止不支持的语言"""
        request = ExecutionRequest(
            code="console.log('hello')",
            language="javascript",
            timeout=10
        )
        result = await executor.execute_code_safely(request)
        
        assert result.success is False
        assert "not allowed" in result.error.lower() or "unsupported" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_code_length_limit(self, executor):
        """测试代码长度限制"""
        long_code = "print('hello')" * 10000  # 超长代码
        request = ExecutionRequest(
            code=long_code,
            language="python",
            timeout=10
        )
        result = await executor.execute_code_safely(request)
        
        assert result.success is False
        assert "too long" in result.error.lower() or "limit" in result.error.lower()






