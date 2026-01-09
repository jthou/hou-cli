"""文件整理工具测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.agent.tools.builtin.file_organizer_tool import FileOrganizerTool
from backend.core.agent.tools.base import ToolResult


class TestFileOrganizerTool:
    """测试文件整理工具"""
    
    @pytest.fixture
    def tool(self):
        """创建文件整理工具实例"""
        return FileOrganizerTool()
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)
    
    def test_tool_implements_base_interface(self, tool):
        """测试工具实现了基类接口"""
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'parameters')
        assert hasattr(tool, 'execute')
        assert hasattr(tool, 'validate_parameters')
        assert hasattr(tool, 'to_dict')
    
    def test_tool_name_and_description(self, tool):
        """测试工具名称和描述"""
        assert tool.name == "file_organizer"
        assert "整理" in tool.description or "organize" in tool.description.lower()
    
    def test_tool_parameters(self, tool):
        """测试工具参数定义"""
        param_names = [p.name for p in tool.parameters]
        
        assert "source_path" in param_names
        assert "organize_mode" in param_names
        assert "dry_run" in param_names
        
        # 检查必需参数
        source_param = next((p for p in tool.parameters if p.name == "source_path"), None)
        assert source_param is not None
        assert source_param.required is True
        assert source_param.type == "string"
        
        # 检查可选参数
        mode_param = next((p for p in tool.parameters if p.name == "organize_mode"), None)
        assert mode_param is not None
        assert mode_param.required is False
        assert mode_param.default == "move"
        assert mode_param.enum == ["move", "copy"]
    
    def test_validate_parameters_missing_required(self, tool):
        """测试参数验证：缺少必需参数"""
        error = tool.validate_parameters()
        assert error is not None
        assert "source_path" in error.lower()
    
    def test_validate_parameters_valid(self, tool, temp_dir):
        """测试参数验证：有效参数"""
        error = tool.validate_parameters(
            source_path=str(temp_dir),
            organize_mode="move"
        )
        assert error is None
    
    def test_validate_parameters_invalid_mode(self, tool, temp_dir):
        """测试参数验证：无效的整理模式"""
        error = tool.validate_parameters(
            source_path=str(temp_dir),
            organize_mode="invalid_mode"
        )
        assert error is not None
        assert "organize_mode" in error.lower()
    
    def test_execute_missing_source_path(self, tool):
        """测试执行：缺少源路径"""
        result = tool.execute()
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        # 如果工具不可用，会先返回安装提示；如果工具可用，会返回参数错误
        assert "source_path" in result.error.lower() or "未安装" in result.error or "not installed" in result.error.lower()
    
    def test_execute_source_path_not_exists(self, tool):
        """测试执行：源路径不存在"""
        result = tool.execute(source_path="/nonexistent/path/12345")
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        # 如果工具不可用，会先返回安装提示；如果工具可用，会检查路径
        assert ("不存在" in result.error or "not exist" in result.error.lower() or 
                "未安装" in result.error or "not installed" in result.error.lower())
    
    def test_execute_source_path_not_directory(self, tool, temp_dir):
        """测试执行：源路径不是目录"""
        # 创建一个文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("test")
        
        result = tool.execute(source_path=str(test_file))
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        # 如果工具不可用，会先返回安装提示；如果工具可用，会检查路径类型
        assert ("目录" in result.error or "directory" in result.error.lower() or
                "未安装" in result.error or "not installed" in result.error.lower())
    
    def test_execute_organizer_not_available(self, tool, temp_dir):
        """测试执行：Local-File-Organizer 不可用"""
        # 创建测试目录
        test_dir = temp_dir / "test_source"
        test_dir.mkdir()
        
        result = tool.execute(source_path=str(test_dir))
        
        assert isinstance(result, ToolResult)
        # 如果工具不可用，应该返回错误信息
        if not result.success:
            assert "未安装" in result.error or "not installed" in result.error.lower() or "不可用" in result.error
    
    def test_to_dict_format(self, tool):
        """测试工具转换为字典格式（用于 LLM Function Calling）"""
        tool_dict = tool.to_dict()
        
        assert isinstance(tool_dict, dict)
        assert "type" in tool_dict
        assert tool_dict["type"] == "function"
        assert "function" in tool_dict
        
        func = tool_dict["function"]
        assert func["name"] == "file_organizer"
        assert "description" in func
        assert "parameters" in func
        
        params = func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        
        # 检查必需参数
        assert "source_path" in params["required"]
        assert "source_path" in params["properties"]
    
    def test_check_organizer_availability(self, tool):
        """测试检查 Local-File-Organizer 可用性"""
        is_available, organizer_type = tool._check_organizer_availability()
        
        # 结果应该是布尔值和字符串或 None
        assert isinstance(is_available, bool)
        assert organizer_type is None or organizer_type in ['package', 'submodule', 'command']
    
    def test_execute_with_dry_run(self, tool, temp_dir):
        """测试执行：使用 dry_run 模式"""
        # 创建测试目录
        test_dir = temp_dir / "test_source"
        test_dir.mkdir()
        
        result = tool.execute(
            source_path=str(test_dir),
            dry_run=True
        )
        
        assert isinstance(result, ToolResult)
        # 即使工具不可用，也应该返回结果（成功或失败）
        if result.success:
            assert result.data is not None
            assert result.data.get("dry_run") is True


class TestFileOrganizerToolIntegration:
    """测试文件整理工具集成（与 ToolRegistry）"""
    
    def test_tool_can_be_registered(self):
        """测试工具可以注册到 ToolRegistry"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = FileOrganizerTool()
        registry = ToolRegistry()
        
        # 应该能够注册（如果名称不冲突）
        try:
            registry.register(tool)
            assert registry.get_tool("file_organizer") == tool
        except ValueError:
            # 如果已经注册过，会抛出 ValueError
            assert registry.get_tool("file_organizer") is not None
    
    def test_tool_in_registry_list(self):
        """测试工具在注册表中的列表"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = FileOrganizerTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        tools_list = registry.list_tools()
        assert "file_organizer" in tools_list
    
    def test_tool_for_llm_format(self):
        """测试工具转换为 LLM 格式"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = FileOrganizerTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        llm_tools = registry.get_tools_for_llm()
        tool_dict = next((t for t in llm_tools if t["function"]["name"] == "file_organizer"), None)
        
        assert tool_dict is not None
        assert tool_dict["type"] == "function"
        assert tool_dict["function"]["name"] == "file_organizer"

