"""测试技能执行器的表达式求值功能"""
import pytest
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.tools.registry import ToolRegistry
from unittest.mock import Mock, MagicMock
from backend.services.llm.llm_service import LLMService


class TestExpressionEvaluation:
    """测试表达式求值"""
    
    @pytest.fixture
    def executor(self):
        """创建技能执行器实例"""
        tool_registry = ToolRegistry()
        llm_service = Mock(spec=LLMService)
        return SkillExecutor(tool_registry, llm_service)
    
    def test_evaluate_expression_boolean_comparison(self, executor):
        """测试布尔值比较表达式"""
        context = {
            'step_results': [
                {'download_success': True},
                {'need_retry': False}
            ]
        }
        
        # 测试 steps[0].download_success == true
        result = executor._evaluate_expression('${steps[0].download_success == true}', context)
        assert result is True, "布尔值比较应该返回 True"
        
        # 测试 steps[1].need_retry != true
        result = executor._evaluate_expression('${steps[1].need_retry != true}', context)
        assert result is True, "布尔值不等比较应该返回 True"
        
        # 测试 steps[0].download_success == false
        result = executor._evaluate_expression('${steps[0].download_success == false}', context)
        assert result is False, "布尔值比较应该返回 False"
    
    def test_evaluate_expression_string_boolean_conversion(self, executor):
        """测试字符串布尔值转换"""
        context = {
            'step_results': [
                {'download_success': 'true'},  # 字符串 "true"
                {'need_retry': 'false'}  # 字符串 "false"
            ]
        }
        
        # 测试字符串 "true" 转换为布尔值
        result = executor._evaluate_expression('${steps[0].download_success == true}', context)
        assert result is True, "字符串 'true' 应该转换为 True"
        
        # 测试字符串 "false" 转换为布尔值
        result = executor._evaluate_expression('${steps[1].need_retry == false}', context)
        assert result is True, "字符串 'false' 应该转换为 False"
    
    def test_evaluate_expression_step_results_type_check(self, executor):
        """测试 step_results 类型检查"""
        # 测试 step_results 是字符串的情况（应该不会出错）
        context = {
            'step_results': 'invalid_string'  # 错误类型
        }
        
        # 应该返回 None 或默认值，而不是抛出类型错误
        result = executor._evaluate_expression('${steps[0].download_success}', context)
        assert result is None or result == 'None', "应该安全处理类型错误"
    
    def test_evaluate_expression_step_results_list_check(self, executor):
        """测试 step_results 列表访问"""
        context = {
            'step_results': [
                {'download_success': True, 'progress': 50},
                {'need_retry': False, 'count': 3}
            ]
        }
        
        # 测试正常访问
        result = executor._evaluate_expression('${steps[0].download_success}', context)
        assert result is True, "应该能正确访问列表元素"
        
        # 测试索引超出范围
        result = executor._evaluate_expression('${steps[10].download_success}', context)
        assert result is None or result == 'None', "索引超出范围应该返回 None"
    
    def test_evaluate_expression_result_success_access(self, executor):
        """测试 result.success 访问"""
        context = {
            'result': {
                'success': True,
                'data': {'file': 'test.mp4'},
                'error': None
            }
        }
        
        # 测试访问 result.success
        result = executor._evaluate_expression('${result.success}', context)
        assert result is True, "应该能正确访问 result.success"
        
        # 测试 result.success == true
        result = executor._evaluate_expression('${result.success == true}', context)
        assert result is True, "result.success 比较应该返回 True"
    
    def test_evaluate_expression_config_field_access(self, executor):
        """测试 config.field 访问"""
        context = {
            'config': {
                'urls': ['url1', 'url2'],
                'max_length': 100,
                'enabled': True
            }
        }
        
        # 测试访问 config.enabled
        result = executor._evaluate_expression('${config.enabled}', context)
        assert result is True, "应该能正确访问 config.enabled"
        
        # 测试 config.enabled == true
        result = executor._evaluate_expression('${config.enabled == true}', context)
        assert result is True, "config.enabled 比较应该返回 True"
    
    def test_evaluate_expression_numeric_comparison(self, executor):
        """测试数字比较"""
        context = {
            'config': {
                'max_length': 100,
                'min_length': 10
            }
        }
        
        # 测试数字比较
        result = executor._evaluate_expression('${config.max_length > 50}', context)
        assert result is True, "数字比较应该返回 True"
        
        result = executor._evaluate_expression('${config.min_length < 20}', context)
        assert result is True, "数字比较应该返回 True"
    
    def test_evaluate_expression_complex_condition(self, executor):
        """测试复杂条件表达式"""
        context = {
            'step_results': [
                {'download_success': True, 'progress': 100},
                {'need_retry': False}
            ],
            'config': {
                'enabled': True
            }
        }
        
        # 测试复杂条件：steps[0].download_success == true and config.enabled == true
        result = executor._evaluate_expression(
            '${steps[0].download_success == true and config.enabled == true}',
            context
        )
        assert result is True, "复杂条件应该返回 True"
        
        # 测试 or 条件
        result = executor._evaluate_expression(
            '${steps[1].need_retry == true or config.enabled == true}',
            context
        )
        assert result is True, "OR 条件应该返回 True"
    
    def test_evaluate_expression_type_error_handling(self, executor):
        """测试类型错误处理"""
        context = {
            'step_results': [
                {'value': 'string_value'}  # 字符串值
            ],
            'config': {
                'number': 100  # 数字值
            }
        }
        
        # 测试字符串和数字比较（应该被安全处理）
        # 注意：Python 中字符串和数字比较会抛出 TypeError，但我们的代码应该捕获它
        try:
            result = executor._evaluate_expression('${steps[0].value < config.number}', context)
            # 如果成功，可能返回字符串（因为 eval 失败时返回原始表达式）
            # 或者返回布尔值（如果类型转换成功）
            assert isinstance(result, (bool, str)), f"应该返回布尔值或字符串，实际返回: {type(result)}"
        except (TypeError, ValueError) as e:
            # 如果抛出异常，应该被记录但不会崩溃
            assert '类型' in str(e) or 'type' in str(e).lower() or 'not supported' in str(e).lower(), f"应该是类型相关错误: {e}"
    
    def test_evaluate_expression_skip_if_condition(self, executor):
        """测试 skip_if 条件（模拟 skill.yaml 中的使用）"""
        context = {
            'step_results': [
                {'download_success': True}
            ]
        }
        
        # 模拟 skill.yaml 中的 skip_if: ${steps[0].download_success == true}
        result = executor._evaluate_expression('${steps[0].download_success == true}', context)
        assert result is True, "skip_if 条件应该正确评估"
    
    def test_evaluate_expression_need_retry_condition(self, executor):
        """测试 need_retry 条件（模拟 skill.yaml 中的使用）"""
        context = {
            'step_results': [
                {'download_success': False},
                {'need_retry': True}
            ]
        }
        
        # 模拟 skill.yaml 中的 skip_if: ${steps[1].need_retry != true}
        result = executor._evaluate_expression('${steps[1].need_retry != true}', context)
        assert result is False, "need_retry 条件应该正确评估"
        
        # 测试 need_retry == true
        result = executor._evaluate_expression('${steps[1].need_retry == true}', context)
        assert result is True, "need_retry == true 应该返回 True"


class TestToolStepOutput:
    """测试工具步骤输出处理"""
    
    @pytest.fixture
    def executor(self):
        """创建技能执行器实例"""
        tool_registry = ToolRegistry()
        llm_service = Mock(spec=LLMService)
        return SkillExecutor(tool_registry, llm_service)
    
    @pytest.fixture
    def mock_tool_result(self):
        """创建模拟的工具结果"""
        from backend.core.agent.tools.base import ToolResult
        return ToolResult(
            success=True,
            data={'file': 'test.mp4', 'size': 1024},
            error=None
        )
    
    @pytest.mark.asyncio
    async def test_tool_step_output_result_success(self, executor, mock_tool_result):
        """测试工具步骤输出中的 result.success"""
        step = {
            'tool': 'test_tool',
            'outputs': {
                'download_success': '${result.success}'
            }
        }
        
        context = {}
        
        # 模拟工具执行
        executor.tool_registry = Mock()
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=mock_tool_result)
        # 确保 Mock 对象没有 _execute_async 属性，这样会使用 execute 方法
        delattr(mock_tool, '_execute_async') if hasattr(mock_tool, '_execute_async') else None
        executor.tool_registry.get_tool = Mock(return_value=mock_tool)
        
        # 执行工具步骤（异步）
        outputs = await executor._execute_tool_step(step, context)
        
        # 验证 result.success 被正确提取
        assert 'download_success' in outputs, "应该包含 download_success 输出"
        assert outputs['download_success'] is True, "download_success 应该是布尔值 True"
        assert isinstance(outputs['download_success'], bool), "download_success 应该是布尔类型"


class TestStepResultsTypeSafety:
    """测试 step_results 类型安全性"""
    
    @pytest.fixture
    def executor(self):
        """创建技能执行器实例"""
        tool_registry = ToolRegistry()
        llm_service = Mock(spec=LLMService)
        return SkillExecutor(tool_registry, llm_service)
    
    def test_step_results_string_type_error(self, executor):
        """测试 step_results 是字符串时的类型错误处理"""
        # 模拟 step_results 被错误地设置为字符串
        context = {
            'step_results': 'invalid_string'  # 错误类型
        }
        
        # 应该不会抛出类型错误
        try:
            result = executor._evaluate_expression('${steps[0].field}', context)
            # 应该返回 None 或安全值
            assert result is None or result == 'None' or result == '', "应该安全处理类型错误"
        except TypeError as e:
            pytest.fail(f"不应该抛出 TypeError: {e}")
    
    def test_step_results_none_type_error(self, executor):
        """测试 step_results 是 None 时的处理"""
        context = {
            'step_results': None
        }
        
        # 应该不会抛出类型错误
        try:
            result = executor._evaluate_expression('${steps[0].field}', context)
            assert result is None or result == 'None', "应该安全处理 None"
        except TypeError as e:
            pytest.fail(f"不应该抛出 TypeError: {e}")
    
    def test_step_results_dict_type_error(self, executor):
        """测试 step_results 是字典时的处理"""
        context = {
            'step_results': {'invalid': 'dict'}  # 错误类型，应该是列表
        }
        
        # 应该不会抛出类型错误
        try:
            result = executor._evaluate_expression('${steps[0].field}', context)
            assert result is None or result == 'None', "应该安全处理字典类型"
        except TypeError as e:
            pytest.fail(f"不应该抛出 TypeError: {e}")
    
    def test_step_results_index_out_of_range(self, executor):
        """测试索引超出范围"""
        context = {
            'step_results': [
                {'field': 'value'}
            ]
        }
        
        # 访问超出范围的索引
        result = executor._evaluate_expression('${steps[10].field}', context)
        assert result is None or result == 'None', "索引超出范围应该返回 None"
    
    def test_step_results_empty_list(self, executor):
        """测试空列表"""
        context = {
            'step_results': []
        }
        
        # 访问空列表
        result = executor._evaluate_expression('${steps[0].field}', context)
        assert result is None or result == 'None', "空列表应该返回 None"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

