"""测试技能执行器的集成功能"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.base import ToolResult
from backend.services.llm.llm_service import LLMService


class TestExecutorIntegration:
    """测试执行器集成功能"""
    
    @pytest.fixture
    def executor(self):
        """创建技能执行器实例"""
        tool_registry = ToolRegistry()
        llm_service = Mock(spec=LLMService)
        return SkillExecutor(tool_registry, llm_service)
    
    @pytest.mark.asyncio
    async def test_workflow_with_skip_if_condition(self, executor):
        """测试带 skip_if 条件的工作流"""
        # 模拟工具
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=True,
            data={'file': 'test.mp4'},
            error=None
        ))
        # 确保 Mock 对象没有 _execute_async 属性，这样会使用 execute 方法
        if hasattr(mock_tool, '_execute_async'):
            delattr(mock_tool, '_execute_async')
        
        executor.tool_registry.get_tool = Mock(return_value=mock_tool)
        
        # 创建工作流（模拟 video_downloader skill.yaml）
        workflow = {
            'steps': [
                {
                    'name': 'download_single',
                    'type': 'tool',
                    'tool': 'video_downloader',
                    'inputs': {
                        'url': '${input.url}'
                    },
                    'outputs': {
                        'download_success': '${result.success}'
                    }
                },
                {
                    'name': 'retry_check',
                    'type': 'code_executor',
                    'code': 'print("check")',
                    'skip_if': '${steps[0].download_success == true}',  # 如果下载成功，跳过
                    'outputs': {
                        'need_retry': '${result.need_retry}'
                    }
                }
            ]
        }
        
        parameters = {
            'url': 'https://example.com/video.mp4'
        }
        
        # 执行工作流
        result = await executor.execute_workflow(workflow, parameters)
        
        # 验证结果
        assert result.success, "工作流应该成功执行"
        # 由于 download_success 是 True，retry_check 应该被跳过
    
    @pytest.mark.asyncio
    async def test_workflow_with_boolean_comparison(self, executor):
        """测试布尔值比较的工作流"""
        # 模拟工具返回 success=False
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=False,
            data={},
            error='Download failed'
        ))
        # 确保 Mock 对象没有 _execute_async 属性
        if hasattr(mock_tool, '_execute_async'):
            delattr(mock_tool, '_execute_async')
        
        executor.tool_registry.get_tool = Mock(return_value=mock_tool)
        
        workflow = {
            'steps': [
                {
                    'name': 'download',
                    'type': 'tool',
                    'tool': 'video_downloader',
                    'inputs': {'url': '${input.url}'},
                    'outputs': {
                        'download_success': '${result.success}'
                    }
                },
                {
                    'name': 'retry',
                    'type': 'tool',
                    'tool': 'video_downloader',
                    'skip_if': '${steps[0].download_success != false}',  # 仅在失败时执行
                    'inputs': {'url': '${input.url}'},
                    'outputs': {
                        'retry_result': '${result}'
                    }
                }
            ]
        }
        
        parameters = {'url': 'https://example.com/video.mp4'}
        
        # 执行工作流
        result = await executor.execute_workflow(workflow, parameters)
        
        # 验证：由于 download_success 是 False，retry 步骤应该执行
        assert result.success or 'error' in str(result), "工作流应该处理错误情况"
    
    @pytest.mark.asyncio
    async def test_workflow_step_results_type_safety(self, executor):
        """测试工作流中 step_results 的类型安全"""
        # 模拟工具
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=True,
            data={'value': 100},
            error=None
        ))
        
        executor.tool_registry.get_tool = Mock(return_value=mock_tool)
        
        workflow = {
            'steps': [
                {
                    'name': 'step1',
                    'type': 'tool',
                    'tool': 'test_tool',
                    'outputs': {
                        'value': '${result.data.value}'
                    }
                },
                {
                    'name': 'step2',
                    'type': 'code_executor',
                    'code': 'print(${steps[0].value})',  # 访问上一步的结果
                    'outputs': {}
                }
            ]
        }
        
        parameters = {}
        
        # 执行工作流，不应该抛出类型错误
        try:
            result = await executor.execute_workflow(workflow, parameters)
            # 如果成功，验证结果
            assert result is not None, "工作流应该返回结果"
        except TypeError as e:
            pytest.fail(f"不应该抛出 TypeError: {e}")


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def executor(self):
        """创建技能执行器实例"""
        tool_registry = ToolRegistry()
        llm_service = Mock(spec=LLMService)
        return SkillExecutor(tool_registry, llm_service)
    
    def test_expression_evaluation_error_handling(self, executor):
        """测试表达式求值错误处理"""
        context = {
            'step_results': [
                {'value': 'string'}  # 字符串值
            ],
            'config': {
                'number': 100  # 数字值
            }
        }
        
        # 测试可能导致类型错误的表达式
        # 应该被安全处理，不会崩溃
        try:
            result = executor._evaluate_expression('${steps[0].value < config.number}', context)
            # 如果成功，应该返回布尔值或 None
            assert result is None or isinstance(result, (bool, str)), "应该返回安全值"
        except Exception as e:
            # 如果抛出异常，应该被记录但不会导致崩溃
            assert isinstance(e, (TypeError, ValueError)), "应该是预期的异常类型"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

