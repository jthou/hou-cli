"""Tool 注册器测试"""
import pytest
from typing import Any
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.core.agent.tools.registry import ToolRegistry


class MockTool(Tool):
    """测试用的 Mock Tool"""
    
    def __init__(self, name: str = "mock_tool", return_value: Any = None):
        super().__init__(
            name=name,
            description="A mock tool for testing",
            parameters=[
                ToolParameter(name="param1", type="string", description="Test param", required=True)
            ]
        )
        self.return_value = return_value or {"result": "ok"}
        self.called_with = None
    
    def execute(self, **kwargs) -> ToolResult:
        self.called_with = kwargs
        return ToolResult(success=True, data=self.return_value)


class TestToolRegistry:
    """测试 ToolRegistry 类"""
    
    def test_registry_is_singleton(self):
        """测试注册器是单例"""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()
        assert registry1 is registry2
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        registry.clear()  # 清空注册表
        
        tool = MockTool(name="test_tool")
        registry.register(tool)
        
        assert registry.get_tool("test_tool") == tool
    
    def test_register_duplicate_tool_raises_error(self):
        """测试注册重复工具会抛出错误"""
        registry = ToolRegistry()
        registry.clear()
        
        tool1 = MockTool(name="duplicate_tool")
        tool2 = MockTool(name="duplicate_tool")
        
        registry.register(tool1)
        with pytest.raises(ValueError, match="Tool 'duplicate_tool' is already registered"):
            registry.register(tool2)
    
    def test_get_tool_exists(self):
        """测试获取已注册的工具"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool(name="existing_tool")
        registry.register(tool)
        
        retrieved = registry.get_tool("existing_tool")
        assert retrieved == tool
    
    def test_get_tool_not_exists(self):
        """测试获取不存在的工具返回 None"""
        registry = ToolRegistry()
        registry.clear()
        
        result = registry.get_tool("non_existent_tool")
        assert result is None
    
    def test_list_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        registry.clear()
        
        tool1 = MockTool(name="tool1")
        tool2 = MockTool(name="tool2")
        
        registry.register(tool1)
        registry.register(tool2)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools
    
    def test_get_tools_for_llm(self):
        """测试获取 LLM 格式的工具定义"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool(name="test_tool")
        registry.register(tool)
        
        llm_tools = registry.get_tools_for_llm()
        assert len(llm_tools) == 1
        assert llm_tools[0]["type"] == "function"
        assert llm_tools[0]["function"]["name"] == "test_tool"
        assert "parameters" in llm_tools[0]["function"]
    
    def test_execute_tool_success(self):
        """测试执行工具成功"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool(name="exec_tool", return_value={"data": "test"})
        registry.register(tool)
        
        result = registry.execute("exec_tool", param1="value1")
        assert result.success is True
        assert result.data == {"data": "test"}
        assert tool.called_with == {"param1": "value1"}
    
    def test_execute_tool_not_found(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()
        registry.clear()
        
        result = registry.execute("non_existent", param1="value1")
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_execute_tool_validation_fails(self):
        """测试执行工具时参数验证失败"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool(name="validation_tool")
        registry.register(tool)
        
        # 缺少必需参数
        result = registry.execute("validation_tool")
        assert result.success is False
        assert "parameter" in result.error.lower() or "required" in result.error.lower()
    
    def test_clear_registry(self):
        """测试清空注册表"""
        registry = ToolRegistry()
        registry.clear()
        
        tool = MockTool(name="temp_tool")
        registry.register(tool)
        assert registry.get_tool("temp_tool") is not None
        
        registry.clear()
        assert registry.get_tool("temp_tool") is None
        assert len(registry.list_tools()) == 0

