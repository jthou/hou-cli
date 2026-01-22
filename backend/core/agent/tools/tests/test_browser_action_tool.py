"""细粒度浏览器操作工具测试 - 测试各个专用浏览器操作工具"""
from backend.core.agent.tools.builtin.browser_action_tool import (
    BrowserActionTool,
    BrowserNavigateTool,
    BrowserClickTool,
    BrowserFillTool,
    BrowserSearchTool,
    BrowserExtractTool
)


class TestBrowserActionTool:
    """细粒度浏览器操作工具基类测试"""

    def test_base_class_initialization(self):
        """测试基类初始化"""
        tool = BrowserActionTool(
            name="test_tool",
            description="Test description"
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "Test description"
        assert tool.parameters is not None


class TestBrowserNavigateTool:
    """浏览器导航工具测试"""

    def test_navigate_tool_initialization(self):
        """测试导航工具初始化"""
        tool = BrowserNavigateTool()
        
        assert tool.name == "browser_navigate"
        assert tool.description is not None
        assert len(tool.parameters) >= 1
        
        # 验证参数
        param_names = [param.name for param in tool.parameters]
        assert "url" in param_names
        assert "new_tab" in param_names

    def test_navigate_tool_required_params(self):
        """测试导航工具必需参数"""
        tool = BrowserNavigateTool()
        
        url_param = next((p for p in tool.parameters if p.name == "url"), None)
        assert url_param is not None
        assert url_param.required is True

    def test_navigate_tool_optional_params(self):
        """测试导航工具可选参数"""
        tool = BrowserNavigateTool()
        
        new_tab_param = next(
            (p for p in tool.parameters if p.name == "new_tab"), None
        )
        assert new_tab_param is not None
        assert new_tab_param.required is False


class TestBrowserClickTool:
    """浏览器点击工具测试"""

    def test_click_tool_initialization(self):
        """测试点击工具初始化"""
        tool = BrowserClickTool()
        
        assert tool.name == "browser_click"
        assert tool.description is not None
        assert len(tool.parameters) >= 1
        
        # 验证参数
        param_names = [param.name for param in tool.parameters]
        assert "index" in param_names

    def test_click_tool_required_params(self):
        """测试点击工具必需参数"""
        tool = BrowserClickTool()
        
        index_param = next(
            (p for p in tool.parameters if p.name == "index"), None
        )
        assert index_param is not None
        assert index_param.required is True

    def test_click_tool_optional_params(self):
        """测试点击工具可选参数"""
        tool = BrowserClickTool()
        
        optional_params = ["text", "coordinate_x", "coordinate_y"]
        for param_name in optional_params:
            param = next(
                (p for p in tool.parameters if p.name == param_name), None
            )
            assert param is not None, f"Parameter {param_name} should exist"
            assert param.required is False


class TestBrowserFillTool:
    """浏览器填充工具测试"""

    def test_fill_tool_initialization(self):
        """测试填充工具初始化"""
        tool = BrowserFillTool()
        
        assert tool.name == "browser_fill"
        assert tool.description is not None
        assert len(tool.parameters) >= 2
        
        # 验证参数
        param_names = [param.name for param in tool.parameters]
        assert "index" in param_names
        assert "text" in param_names

    def test_fill_tool_required_params(self):
        """测试填充工具必需参数"""
        tool = BrowserFillTool()
        
        required_params = ["index", "text"]
        for param_name in required_params:
            param = next(
                (p for p in tool.parameters if p.name == param_name), None
            )
            assert param is not None, f"Parameter {param_name} should exist"
            assert param.required is True

    def test_fill_tool_optional_params(self):
        """测试填充工具可选参数"""
        tool = BrowserFillTool()
        
        clear_param = next(
            (p for p in tool.parameters if p.name == "clear"), None
        )
        assert clear_param is not None
        assert clear_param.required is False
        assert clear_param.type == "boolean"
        assert clear_param.default is True


class TestBrowserSearchTool:
    """浏览器搜索工具测试"""

    def test_search_tool_initialization(self):
        """测试搜索工具初始化"""
        tool = BrowserSearchTool()
        
        assert tool.name == "browser_search"
        assert tool.description is not None
        assert len(tool.parameters) >= 1
        
        # 验证参数
        param_names = [param.name for param in tool.parameters]
        assert "query" in param_names

    def test_search_tool_required_params(self):
        """测试搜索工具必需参数"""
        tool = BrowserSearchTool()
        
        query_param = next(
            (p for p in tool.parameters if p.name == "query"), None
        )
        assert query_param is not None
        assert query_param.required is True

    def test_search_tool_optional_params(self):
        """测试搜索工具可选参数"""
        tool = BrowserSearchTool()
        
        engine_param = next(
            (p for p in tool.parameters if p.name == "engine"), None
        )
        assert engine_param is not None
        assert engine_param.required is False
        assert engine_param.type == "string"


class TestBrowserExtractTool:
    """浏览器内容提取工具测试"""

    def test_extract_tool_initialization(self):
        """测试提取工具初始化"""
        tool = BrowserExtractTool()
        
        assert tool.name == "browser_extract"
        assert tool.description is not None
        assert len(tool.parameters) >= 1
        
        # 验证参数
        param_names = [param.name for param in tool.parameters]
        assert "query" in param_names

    def test_extract_tool_required_params(self):
        """测试提取工具必需参数"""
        tool = BrowserExtractTool()
        
        query_param = next(
            (p for p in tool.parameters if p.name == "query"), None
        )
        assert query_param is not None
        assert query_param.required is True

    def test_extract_tool_optional_params(self):
        """测试提取工具可选参数"""
        tool = BrowserExtractTool()
        
        extract_links_param = next(
            (p for p in tool.parameters if p.name == "extract_links"), None
        )
        assert extract_links_param is not None
        assert extract_links_param.required is False
        assert extract_links_param.type == "boolean"


class TestBrowserActionToolIntegration:
    """细粒度浏览器工具集成测试"""

    def test_all_tools_have_unique_names(self):
        """测试所有工具具有唯一名称"""
        tools = [
            BrowserNavigateTool(),
            BrowserClickTool(),
            BrowserFillTool(),
            BrowserSearchTool(),
            BrowserExtractTool()
        ]
        
        names = [tool.name for tool in tools]
        assert len(names) == len(set(names)), (
            f"Tool names must be unique: {names}"
        )
        
        expected_names = {
            "browser_navigate",
            "browser_click", 
            "browser_fill",
            "browser_search",
            "browser_extract"
        }
        assert set(names) == expected_names

    def test_all_tools_have_descriptions(self):
        """测试所有工具都有描述"""
        tools = [
            BrowserNavigateTool(),
            BrowserClickTool(),
            BrowserFillTool(),
            BrowserSearchTool(),
            BrowserExtractTool()
        ]
        
        for tool in tools:
            assert (
                tool.description is not None and 
                tool.description.strip() != ""
            )

    def test_tools_parameter_validation(self):
        """测试工具参数验证"""
        tools = [
            BrowserNavigateTool(),
            BrowserClickTool(),
            BrowserFillTool(),
            BrowserSearchTool(),
            BrowserExtractTool()
        ]
        
        for tool in tools:
            # 检查参数列表不为空
            assert len(tool.parameters) > 0
            
            # 检查每个参数都有名称
            for param in tool.parameters:
                assert hasattr(param, 'name')
                assert param.name is not None