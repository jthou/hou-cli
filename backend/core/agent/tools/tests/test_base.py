"""Tool 基类测试"""
import pytest
from typing import Dict, Any, List
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter


class TestTool:
    """测试 Tool 基类"""
    
    def test_tool_is_abstract(self):
        """测试 Tool 是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            Tool(name="test", description="test")
    
    def test_tool_subclass_must_implement_execute(self):
        """测试 Tool 子类必须实现 execute 方法"""
        class IncompleteTool(Tool):
            def __init__(self):
                super().__init__(name="test", description="test")
        
        with pytest.raises(TypeError):
            IncompleteTool()
    
    def test_tool_subclass_can_be_instantiated(self):
        """测试实现了 execute 方法的 Tool 子类可以实例化"""
        class CompleteTool(Tool):
            def __init__(self):
                super().__init__(name="test", description="test")
            
            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={"result": "ok"})
        
        tool = CompleteTool()
        assert tool.name == "test"
        assert tool.description == "test"
    
    def test_tool_execute_returns_tool_result(self):
        """测试 execute 方法返回 ToolResult"""
        class TestTool(Tool):
            def __init__(self):
                super().__init__(name="test", description="test")
            
            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={"value": 42})
        
        tool = TestTool()
        result = tool.execute()
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"value": 42}
        assert result.error is None
    
    def test_tool_result_success(self):
        """测试 ToolResult 成功情况"""
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_tool_result_error(self):
        """测试 ToolResult 错误情况"""
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
    
    def test_tool_parameter_validation(self):
        """测试 ToolParameter 参数验证"""
        param = ToolParameter(
            name="test_param",
            type="string",
            description="Test parameter",
            required=True
        )
        assert param.name == "test_param"
        assert param.type == "string"
        assert param.required is True

