"""测试 Orchestrator 错误信息格式"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.skills.base import SkillResult


class TestOrchestratorErrorFormat:
    """测试 Orchestrator 错误信息格式"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_skill_failure_error_format(self, orchestrator):
        """测试技能执行失败时的错误信息格式"""
        # 模拟技能执行失败
        mock_skill = Mock()
        mock_skill.name = 'test_skill'
        mock_skill.execute = AsyncMock(return_value=SkillResult(
            success=False,
            error='Test error message',
            data=None
        ))
        
        orchestrator.skill_registry = Mock()
        orchestrator.skill_registry.match = Mock(return_value=mock_skill)
        
        # 执行流式处理
        chunks = []
        async for chunk in orchestrator.stream_process('test task'):
            chunks.append(chunk)
        
        # 验证错误信息格式
        error_chunks = [chunk for chunk in chunks if '技能执行失败' in chunk]
        assert len(error_chunks) > 0, "应该包含错误信息"
        
        # 验证错误信息以换行符结尾（不会和后面的内容连在一起）
        error_msg = error_chunks[0]
        assert error_msg.endswith('\n'), "错误信息应该以换行符结尾"
        
        # 验证错误信息格式正确
        assert '技能执行失败' in error_msg, "应该包含错误提示"
        assert 'Test error message' in error_msg, "应该包含具体错误信息"
    
    @pytest.mark.asyncio
    async def test_skill_exception_error_format(self, orchestrator):
        """测试技能执行异常时的错误信息格式"""
        # 模拟技能执行异常
        mock_skill = Mock()
        mock_skill.name = 'test_skill'
        mock_skill.execute = AsyncMock(side_effect=Exception('Test exception'))
        
        orchestrator.skill_registry = Mock()
        orchestrator.skill_registry.match = Mock(return_value=mock_skill)
        
        # 执行流式处理
        chunks = []
        async for chunk in orchestrator.stream_process('test task'):
            chunks.append(chunk)
        
        # 验证错误信息格式
        error_chunks = [chunk for chunk in chunks if '技能执行失败' in chunk or '[错误]' in chunk]
        assert len(error_chunks) > 0, "应该包含错误信息"
        
        # 验证错误信息格式
        error_msg = ''.join(error_chunks)
        assert '\n' in error_msg, "错误信息应该包含换行符"
        assert '技能执行失败' in error_msg or '[错误]' in error_msg, "应该包含错误提示"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

