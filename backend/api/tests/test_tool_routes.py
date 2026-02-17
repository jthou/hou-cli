"""工具路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestToolRoutes:
    """工具路由测试类"""
    
    @pytest.fixture
    def mock_tools(self):
        """创建模拟工具列表"""
        tool1 = MagicMock()
        tool1.name = "test_tool_1"
        tool1.description = "这是测试工具1的描述"
        
        tool2 = MagicMock()
        tool2.name = "test_tool_2"
        tool2.description = "这是测试工具2的描述"
        
        return [tool1, tool2]
    
    def test_list_tools_success(self, client, mock_tools):
        """测试获取工具列表成功"""
        with patch('backend.api.tool_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_tool_registry = MagicMock()
            mock_tool_registry._tools = {
                "tool1": mock_tools[0],
                "tool2": mock_tools[1]
            }
            mock_orch.tool_registry = mock_tool_registry
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/tools/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["tools"]) == 2
            assert data["tools"][0]["name"] == "test_tool_1"
            assert data["tools"][0]["description"] == "这是测试工具1的描述"
    
    def test_list_tools_empty(self, client):
        """测试工具列表为空"""
        with patch('backend.api.tool_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_tool_registry = MagicMock()
            mock_tool_registry._tools = {}
            mock_orch.tool_registry = mock_tool_registry
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/tools/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 0
            assert len(data["tools"]) == 0
    
    def test_list_tools_with_class_docstring(self, client):
        """测试工具使用类文档字符串作为描述"""
        tool = MagicMock()
        tool.name = "test_tool"
        tool.description = ""  # 空描述
        
        # 模拟类的文档字符串
        tool.__class__.__doc__ = "这是类的文档字符串"
        
        with patch('backend.api.tool_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_tool_registry = MagicMock()
            mock_tool_registry._tools = {"tool1": tool}
            mock_orch.tool_registry = mock_tool_registry
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/tools/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["tools"][0]["description"] == "这是类的文档字符串"
    
    def test_list_tools_default_description(self, client):
        """测试工具使用默认描述"""
        tool = MagicMock()
        tool.name = "test_tool"
        tool.description = ""  # 空描述
        tool.__class__.__doc__ = None  # 没有文档字符串
        
        with patch('backend.api.tool_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_tool_registry = MagicMock()
            mock_tool_registry._tools = {"tool1": tool}
            mock_orch.tool_registry = mock_tool_registry
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/tools/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["tools"][0]["description"] == "test_tool 工具"
    
    def test_list_tools_error(self, client):
        """测试获取工具列表错误处理"""
        with patch('backend.api.tool_routes.get_orchestrator') as mock_get_orch:
            mock_get_orch.side_effect = Exception("获取工具失败")
            
            response = client.get("/api/tools/list")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "获取工具失败" in data["error"]

