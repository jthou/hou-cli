"""代码执行集成测试"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.tools.base import ToolResult


class TestCodeExecutionIntegration:
    """代码执行集成测试"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_tool_calling_mode(self, orchestrator):
        """测试工具调用模式：LLM 调用 execute_code 工具"""
        # 验证工具已注册
        tools = orchestrator.tool_registry.get_tools_for_llm()
        tool_names = [t['function']['name'] for t in tools]
        assert 'execute_code' in tool_names, "execute_code 工具未注册"
        
        # 模拟 LLM 调用工具
        mock_response = MagicMock()
        mock_response.tool_calls = [MagicMock()]
        mock_response.tool_calls[0].function.name = "execute_code"
        mock_response.tool_calls[0].function.arguments = json.dumps({
            "code": "print('hello from tool')",
            "language": "python",
            "timeout": 10
        })
        mock_response.tool_calls[0].id = "call_123"
        
        # Mock LLM 服务
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 第一轮：LLM 返回工具调用
            mock_chat.return_value = mock_response
            
            # 执行工具调用
            result = orchestrator.tool_registry.execute(
                'execute_code',
                code='print("hello from tool")',
                language='python',
                timeout=10
            )
            
            assert result.success is True
            assert 'hello from tool' in result.data.get('output', '')
            print("✅ 工具调用模式测试通过")
    
    @pytest.mark.asyncio
    async def test_auto_extract_mode(self, orchestrator):
        """测试自动提取模式：从 LLM 输出中自动检测并执行代码"""
        if not orchestrator.auto_code_executor:
            pytest.skip("自动代码执行器未初始化")
        
        # 模拟 LLM 输出（包含代码块）
        llm_output = """
        可以使用以下 Python 代码来计算 1 到 100 的和：
        
        ```python
        print(sum(range(1, 101)))
        ```
        """
        
        # 测试自动提取和执行
        result = await orchestrator.auto_code_executor.process_llm_output(
            llm_output,
            auto_execute=True,
            require_confirmation=False
        )
        
        assert result['code_executed'] is True
        assert len(result['execution_results']) == 1
        exec_result = result['execution_results'][0]['result']
        assert exec_result['success'] is True
        assert '5050' in exec_result['output']  # 1+2+...+100 = 5050
        print("✅ 自动提取模式测试通过")
    
    @pytest.mark.asyncio
    async def test_security_blocking(self, orchestrator):
        """测试安全限制：危险命令被阻止"""
        # 测试工具调用模式下的安全限制
        result = orchestrator.tool_registry.execute(
            'execute_code',
            code='rm -rf /',
            language='bash',
            timeout=10
        )
        
        assert result.success is False
        assert 'dangerous' in result.error.lower() or 'not allowed' in result.error.lower()
        print("✅ 安全限制测试通过（工具调用模式）")
        
        # 测试自动提取模式下的安全限制
        if orchestrator.auto_code_executor:
            llm_output = """
            ```bash
            rm -rf /
            ```
            """
            result = await orchestrator.auto_code_executor.process_llm_output(
                llm_output,
                auto_execute=True
            )
            
            if result['code_executed']:
                exec_result = result['execution_results'][0]['result']
                assert exec_result['success'] is False
                print("✅ 安全限制测试通过（自动提取模式）")
    
    @pytest.mark.asyncio
    async def test_multiple_code_blocks(self, orchestrator):
        """测试多个代码块自动执行"""
        if not orchestrator.auto_code_executor:
            pytest.skip("自动代码执行器未初始化")
        
        llm_output = """
        ```python
        print('first')
        ```
        
        ```python
        print('second')
        ```
        """
        
        result = await orchestrator.auto_code_executor.process_llm_output(
            llm_output,
            auto_execute=True
        )
        
        assert result['code_executed'] is True
        assert len(result['execution_results']) == 2
        assert result['execution_results'][0]['result']['success'] is True
        assert result['execution_results'][1]['result']['success'] is True
        print("✅ 多代码块执行测试通过")


class TestCodeExecutionE2E:
    """代码执行端到端测试（Mock LLM）"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建 Orchestrator 实例"""
        return Orchestrator()
    
    @pytest.mark.asyncio
    async def test_e2e_tool_calling(self, orchestrator):
        """端到端测试：LLM 工具调用执行代码"""
        # 创建模拟的 LLM 响应对象
        class MockToolCall:
            def __init__(self, name, arguments):
                self.function = MagicMock()
                self.function.name = name
                self.function.arguments = arguments
                self.id = "call_123"
        
        class MockResponse:
            def __init__(self):
                self.tool_calls = [
                    MockToolCall("execute_code", json.dumps({
                        "code": "print('hello from e2e test')",
                        "language": "python",
                        "timeout": 10
                    }))
                ]
        
        # Mock LLM 服务
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 第一轮：LLM 返回工具调用
            mock_chat.return_value = MockResponse()
            
            # 调用 _chat_with_tools
            system_prompt = "你是一个助手"
            user_prompt = "帮我执行代码 print('hello from e2e test')"
            tools = orchestrator.tool_registry.get_tools_for_llm()
            
            # 第二轮：LLM 基于工具执行结果生成回复
            mock_chat.return_value = "代码执行成功，输出：hello from e2e test"
            
            response = await orchestrator._chat_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools
            )
            
            # 验证响应包含执行结果
            assert response is not None
            assert len(response) > 0
            print("✅ 端到端工具调用测试通过")
    
    @pytest.mark.asyncio
    async def test_e2e_auto_extract(self, orchestrator):
        """端到端测试：LLM 生成代码，自动提取并执行"""
        if not orchestrator.auto_code_executor:
            pytest.skip("自动代码执行器未初始化")
        
        # 模拟 LLM 生成包含代码块的回复
        llm_output_with_code = """
        可以使用以下代码计算 1 到 100 的和：
        
        ```python
        result = sum(range(1, 101))
        print(result)
        ```
        """
        
        # Mock LLM 服务
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 第一轮：LLM 生成包含代码块的回复
            mock_chat.return_value = llm_output_with_code
            
            # 调用 _chat_with_tools（会自动检测并执行代码）
            system_prompt = "你是一个助手"
            user_prompt = "帮我计算 1 到 100 的和"
            tools = orchestrator.tool_registry.get_tools_for_llm()
            
            # 第二轮：LLM 基于执行结果生成最终回复
            mock_chat.return_value = "代码执行成功，结果是 5050"
            
            response = await orchestrator._chat_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools
            )
            
            # 验证响应
            assert response is not None
            assert len(response) > 0
            print("✅ 端到端自动提取测试通过")
    
    @pytest.mark.asyncio
    async def test_e2e_security_blocking(self, orchestrator):
        """端到端测试：安全限制阻止危险命令"""
        # 测试工具调用模式
        result = orchestrator.tool_registry.execute(
            'execute_code',
            code='import os; os.system("rm -rf /")',
            language='python',
            timeout=10
        )
        
        # 应该被安全限制阻止
        assert result.success is False
        assert 'dangerous' in result.error.lower() or 'not allowed' in result.error.lower() or 'restricted' in result.error.lower()
        print("✅ 端到端安全限制测试通过")
    
    @pytest.mark.asyncio
    async def test_e2e_mixed_mode(self, orchestrator):
        """端到端测试：混合模式（工具调用 + 自动提取）"""
        if not orchestrator.auto_code_executor:
            pytest.skip("自动代码执行器未初始化")
        
        # 模拟场景：LLM 先调用工具执行主要代码，然后在回复中包含示例代码
        class MockToolCall:
            def __init__(self, name, arguments):
                self.function = MagicMock()
                self.function.name = name
                self.function.arguments = arguments
                self.id = "call_123"
        
        class MockResponse:
            def __init__(self, has_tool_call=False):
                if has_tool_call:
                    self.tool_calls = [
                        MockToolCall("execute_code", json.dumps({
                            "code": "print('main code')",
                            "language": "python",
                            "timeout": 10
                        }))
                    ]
                else:
                    self.tool_calls = None
                    self.content = "主要代码已执行。示例代码：\n```python\nprint('example')\n```"
        
        # Mock LLM 服务
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 第一轮：LLM 调用工具
            mock_chat.return_value = MockResponse(has_tool_call=True)
            
            system_prompt = "你是一个助手"
            user_prompt = "执行代码并给出示例"
            tools = orchestrator.tool_registry.get_tools_for_llm()
            
            # 第二轮：LLM 生成包含示例代码的回复
            mock_chat.return_value = MockResponse(has_tool_call=False)
            
            response = await orchestrator._chat_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools
            )
            
            assert response is not None
            print("✅ 端到端混合模式测试通过")

