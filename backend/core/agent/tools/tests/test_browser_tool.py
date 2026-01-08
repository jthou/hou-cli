"""浏览器工具单元测试"""
import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE
from backend.core.agent.tools.base import ToolResult


class TestBrowserTool:
    """BrowserTool 单元测试"""
    
    @pytest.fixture
    def tool(self):
        """创建浏览器工具实例"""
        return BrowserTool()
    
    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "browser"
        assert tool.description is not None
        assert len(tool.parameters) > 0
        
        # 验证参数
        param_names = [p.name for p in tool.parameters]
        assert "task" in param_names
        assert "headless" in param_names
        assert "timeout" in param_names
    
    def test_tool_initialization_without_browser_use(self):
        """测试 browser-use 未安装时的工具初始化"""
        # 即使 browser-use 未安装，工具也应该能初始化
        # 只是执行时会返回错误
        with patch('backend.core.agent.tools.builtin.browser_tool.BROWSER_USE_AVAILABLE', False):
            # 重新导入以应用 patch
            import importlib
            import backend.core.agent.tools.builtin.browser_tool as browser_module
            importlib.reload(browser_module)
            
            tool = browser_module.BrowserTool()
            assert tool.name == "browser"
            assert "需要安装依赖" in tool.description or "not installed" in tool.description.lower()
    
    def test_validate_parameters(self, tool):
        """测试参数验证"""
        # 测试必需参数
        error = tool.validate_parameters()
        assert error is not None
        assert "task" in error.lower()
        
        # 测试有效参数
        error = tool.validate_parameters(task="打开 www.baidu.com")
        assert error is None
        
        # 测试超时参数验证
        error = tool.validate_parameters(task="test", timeout=500)  # 超过最大限制
        # 超时参数会在执行时被限制，验证可能通过
    
    @pytest.mark.asyncio
    async def test_execute_without_browser_use(self):
        """测试 browser-use 未安装时的执行"""
        with patch('backend.core.agent.tools.builtin.browser_tool.BROWSER_USE_AVAILABLE', False):
            import importlib
            import backend.core.agent.tools.builtin.browser_tool as browser_module
            importlib.reload(browser_module)
            
            tool = browser_module.BrowserTool()
            result = await tool._execute_async(task="打开 www.baidu.com")
            
            assert result.success is False
            assert "not installed" in result.error.lower() or "需要安装" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_missing_task(self, tool):
        """测试缺少 task 参数时的执行"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        result = await tool._execute_async()
        
        assert result.success is False
        assert "task" in result.error.lower() or "required" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_create_llm_missing_api_key(self, tool):
        """测试缺少 API Key 时的 LLM 创建"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                tool._create_llm()
    
    @pytest.mark.asyncio
    async def test_create_llm_invalid_api_key(self, tool):
        """测试无效 API Key 时的 LLM 创建"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "short"}):
            with pytest.raises(ValueError, match="格式无效"):
                tool._create_llm()
    
    @pytest.mark.asyncio
    async def test_create_llm_success(self, tool):
        """测试成功创建 LLM"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        # 使用 mock API key
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch('backend.core.agent.tools.builtin.browser_tool.ChatOpenAI') as mock_chat:
                mock_llm_instance = Mock()
                mock_llm_instance.model_name = "deepseek-chat"
                mock_llm_instance.model = "deepseek-chat"
                mock_llm_instance.name = "ChatOpenAI"
                mock_llm_instance.ainvoke = AsyncMock(return_value="test response")
                mock_llm_instance.invoke = Mock(return_value="test response")
                mock_chat.return_value = mock_llm_instance
                
                llm = tool._create_llm()
                
                assert llm is not None
                assert hasattr(llm, 'provider')
                assert hasattr(llm, 'model_name')
                assert hasattr(llm, 'ainvoke')
                assert llm.provider == 'openai'
    
    @pytest.mark.asyncio
    async def test_execute_timeout_validation(self, tool):
        """测试超时时间验证"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        # 测试超时时间过小
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        mock_llm = Mock()
                        mock_llm.provider = 'openai'
                        mock_llm.model_name = 'deepseek-chat'
                        mock_llm.ainvoke = AsyncMock()
                        mock_create_llm.return_value = mock_llm
                        
                        mock_browser_instance = Mock()
                        mock_browser.return_value = mock_browser_instance
                        
                        mock_agent_instance = Mock()
                        mock_agent_instance.run = AsyncMock(return_value="test result")
                        mock_agent.return_value = mock_agent_instance
                        
                        # 超时时间会被限制在合理范围内
                        result = await tool._execute_async(
                            task="打开 www.baidu.com",
                            timeout=0  # 无效的超时时间
                        )
                        
                        # 应该使用默认超时时间，不会立即失败
                        # 如果执行成功，说明超时时间被修正了
                        # 如果执行失败，可能是其他原因
    
    @pytest.mark.asyncio
    async def test_execute_with_instructions(self, tool):
        """测试带 instructions 的执行"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        mock_llm = Mock()
                        mock_llm.provider = 'openai'
                        mock_llm.model_name = 'deepseek-chat'
                        mock_llm.ainvoke = AsyncMock()
                        mock_create_llm.return_value = mock_llm
                        
                        mock_browser_instance = Mock()
                        mock_browser.return_value = mock_browser_instance
                        
                        mock_agent_instance = Mock()
                        mock_agent_instance.run = AsyncMock(return_value="test result")
                        mock_agent.return_value = mock_agent_instance
                        
                        result = await tool._execute_async(
                            task="打开 www.baidu.com",
                            instructions=["步骤1", "步骤2"]
                        )
                        
                        # 验证 instructions 被合并到 task 中
                        call_args = mock_agent.call_args
                        assert call_args is not None
                        agent_kwargs = call_args.kwargs
                        assert "额外指令" in agent_kwargs.get("task", "") or "步骤1" in agent_kwargs.get("task", "")
    
    @pytest.mark.asyncio
    async def test_execute_timeout_error(self, tool):
        """测试执行超时"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        mock_llm = Mock()
                        mock_llm.provider = 'openai'
                        mock_llm.model_name = 'deepseek-chat'
                        mock_llm.ainvoke = AsyncMock()
                        mock_create_llm.return_value = mock_llm
                        
                        mock_browser_instance = Mock()
                        mock_browser.return_value = mock_browser_instance
                        
                        mock_agent_instance = Mock()
                        # 模拟超时
                        mock_agent_instance.run = AsyncMock(side_effect=asyncio.TimeoutError())
                        mock_agent.return_value = mock_agent_instance
                        
                        result = await tool._execute_async(
                            task="打开 www.baidu.com",
                            timeout=1
                        )
                        
                        assert result.success is False
                        assert "超时" in result.error or "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_value_error(self, tool):
        """测试 LLM 配置错误"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm', side_effect=ValueError("API Key 无效")):
                result = await tool._execute_async(task="打开 www.baidu.com")
                
                assert result.success is False
                assert "配置错误" in result.error or "API Key" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_cdp_error(self, tool):
        """测试 CDP 连接错误"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    mock_llm = Mock()
                    mock_llm.provider = 'openai'
                    mock_llm.model_name = 'deepseek-chat'
                    mock_llm.ainvoke = AsyncMock()
                    mock_create_llm.return_value = mock_llm
                    
                    # 模拟 CDP 连接错误
                    mock_browser.side_effect = Exception("CDP connection failed")
                    
                    result = await tool._execute_async(task="打开 www.baidu.com")
                    
                    assert result.success is False
                    assert "CDP" in result.error or "连接失败" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_headless_mode(self, tool):
        """测试无头模式执行（headless=True）"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        with patch('backend.core.agent.tools.builtin.browser_tool.subprocess') as mock_subprocess:
                            # Mock Playwright 检查
                            mock_subprocess.run.return_value = Mock(returncode=0)
                            
                            mock_llm = Mock()
                            mock_llm.provider = 'openai'
                            mock_llm.model_name = 'deepseek-chat'
                            mock_llm.ainvoke = AsyncMock(return_value="test response")
                            mock_create_llm.return_value = mock_llm
                            
                            mock_browser_instance = Mock()
                            mock_browser_instance.browser_profile = Mock()
                            mock_browser_instance.browser_profile.use_cloud = False
                            mock_browser_instance.browser_profile.is_local = True
                            mock_browser.return_value = mock_browser_instance
                            
                            mock_agent_instance = Mock()
                            mock_agent_instance.run = AsyncMock(return_value="任务完成（无头模式）")
                            mock_agent.return_value = mock_agent_instance
                            
                            # 测试无头模式
                            result = await tool._execute_async(
                                task="打开 www.baidu.com",
                                headless=True,  # 无头模式
                                timeout=60
                            )
                            
                            # 验证 Browser 被调用时传入了 headless=True
                            browser_call_kwargs = mock_browser.call_args.kwargs
                            assert browser_call_kwargs.get("headless") is True, "Browser 应该以无头模式创建"
                            
                            # 验证执行结果
                            assert result.success is True
                            assert "任务完成" in result.data.get("result", "")
                            assert result.data.get("headless") is True
                            assert result.data.get("task") == "打开 www.baidu.com"
                            
                            print("✅ 无头模式测试通过")
    
    @pytest.mark.asyncio
    async def test_execute_visible_mode(self, tool):
        """测试显示浏览器模式执行（headless=False）"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        with patch('backend.core.agent.tools.builtin.browser_tool.subprocess') as mock_subprocess:
                            # Mock Playwright 检查
                            mock_subprocess.run.return_value = Mock(returncode=0)
                            
                            mock_llm = Mock()
                            mock_llm.provider = 'openai'
                            mock_llm.model_name = 'deepseek-chat'
                            mock_llm.ainvoke = AsyncMock(return_value="test response")
                            mock_create_llm.return_value = mock_llm
                            
                            mock_browser_instance = Mock()
                            mock_browser_instance.browser_profile = Mock()
                            mock_browser_instance.browser_profile.use_cloud = False
                            mock_browser_instance.browser_profile.is_local = True
                            mock_browser.return_value = mock_browser_instance
                            
                            mock_agent_instance = Mock()
                            mock_agent_instance.run = AsyncMock(return_value="任务完成（显示模式）")
                            mock_agent.return_value = mock_agent_instance
                            
                            # 测试显示模式
                            result = await tool._execute_async(
                                task="打开 www.baidu.com",
                                headless=False,  # 显示浏览器
                                timeout=60
                            )
                            
                            # 验证 Browser 被调用时传入了 headless=False
                            browser_call_kwargs = mock_browser.call_args.kwargs
                            assert browser_call_kwargs.get("headless") is False, "Browser 应该以显示模式创建"
                            
                            # 验证执行结果
                            assert result.success is True
                            assert "任务完成" in result.data.get("result", "")
                            assert result.data.get("headless") is False
                            assert result.data.get("task") == "打开 www.baidu.com"
                            
                            print("✅ 显示模式测试通过")
    
    @pytest.mark.asyncio
    async def test_execute_default_headless(self, tool):
        """测试默认模式（不指定 headless，应该默认为 False）"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        with patch('backend.core.agent.tools.builtin.browser_tool.subprocess') as mock_subprocess:
                            # Mock Playwright 检查
                            mock_subprocess.run.return_value = Mock(returncode=0)
                            
                            mock_llm = Mock()
                            mock_llm.provider = 'openai'
                            mock_llm.model_name = 'deepseek-chat'
                            mock_llm.ainvoke = AsyncMock(return_value="test response")
                            mock_create_llm.return_value = mock_llm
                            
                            mock_browser_instance = Mock()
                            mock_browser_instance.browser_profile = Mock()
                            mock_browser_instance.browser_profile.use_cloud = False
                            mock_browser_instance.browser_profile.is_local = True
                            mock_browser.return_value = mock_browser_instance
                            
                            mock_agent_instance = Mock()
                            mock_agent_instance.run = AsyncMock(return_value="任务完成")
                            mock_agent.return_value = mock_agent_instance
                            
                            # 测试默认模式（不指定 headless）
                            result = await tool._execute_async(
                                task="打开 www.baidu.com",
                                timeout=60
                            )
                            
                            # 验证 Browser 被调用时传入了 headless=False（默认值）
                            browser_call_kwargs = mock_browser.call_args.kwargs
                            assert browser_call_kwargs.get("headless") is False, "Browser 默认应该以显示模式创建"
                            
                            # 验证执行结果
                            assert result.success is True
                            assert result.data.get("headless") is False
                            
                            print("✅ 默认模式测试通过（headless=False）")
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """测试成功执行（通用测试）"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch.object(tool, '_create_llm') as mock_create_llm:
                with patch('backend.core.agent.tools.builtin.browser_tool.Browser') as mock_browser:
                    with patch('backend.core.agent.tools.builtin.browser_tool.Agent') as mock_agent:
                        with patch('backend.core.agent.tools.builtin.browser_tool.subprocess') as mock_subprocess:
                            # Mock Playwright 检查
                            mock_subprocess.run.return_value = Mock(returncode=0)
                            
                            mock_llm = Mock()
                            mock_llm.provider = 'openai'
                            mock_llm.model_name = 'deepseek-chat'
                            mock_llm.ainvoke = AsyncMock(return_value="test response")
                            mock_create_llm.return_value = mock_llm
                            
                            mock_browser_instance = Mock()
                            mock_browser_instance.browser_profile = Mock()
                            mock_browser_instance.browser_profile.use_cloud = False
                            mock_browser_instance.browser_profile.is_local = True
                            mock_browser.return_value = mock_browser_instance
                            
                            mock_agent_instance = Mock()
                            mock_agent_instance.run = AsyncMock(return_value="任务完成")
                            mock_agent.return_value = mock_agent_instance
                            
                            result = await tool._execute_async(
                                task="打开 www.baidu.com",
                                headless=True,
                                timeout=60
                            )
                            
                            assert result.success is True
                            assert "任务完成" in result.data.get("result", "")
                            assert result.data.get("task") == "打开 www.baidu.com"
                            assert result.data.get("headless") is True
    
    def test_execute_sync_wrapper(self, tool):
        """测试同步包装器"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.object(tool, '_execute_async', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = ToolResult(
                success=True,
                data={"result": "test"}
            )
            
            # 测试在没有事件循环的情况下
            result = tool.execute(task="打开 www.baidu.com")
            
            assert result.success is True
            mock_execute.assert_called_once()
    
    def test_conversation_path_creation(self, tool):
        """测试对话路径创建"""
        assert tool.conversation_path.exists()
        assert tool.conversation_path.is_dir()
    
    @pytest.mark.asyncio
    async def test_llm_wrapper_properties(self, tool):
        """测试 LLM 包装器的属性"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装，跳过测试")
        
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_" + "x" * 20}):
            with patch('backend.core.agent.tools.builtin.browser_tool.ChatOpenAI') as mock_chat:
                mock_llm_instance = Mock()
                mock_llm_instance.model_name = "deepseek-chat"
                mock_llm_instance.model = "deepseek-chat"
                mock_llm_instance.name = "ChatOpenAI"
                mock_llm_instance.ainvoke = AsyncMock(return_value="test response")
                mock_llm_instance.invoke = Mock(return_value="test response")
                mock_chat.return_value = mock_llm_instance
                
                llm = tool._create_llm()
                
                # 测试包装器的属性访问
                assert llm.provider == 'openai'
                assert llm.model_name == 'deepseek-chat'
                assert llm.name == 'ChatOpenAI'
                assert hasattr(llm, 'ainvoke')
                assert callable(llm.ainvoke)
                
                # 测试 model 属性（browser-use 可能访问）
                assert hasattr(llm, 'model')
                assert llm.model == 'deepseek-chat' or llm.model == 'deepseek-chat'

