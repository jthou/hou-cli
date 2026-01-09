"""PDF解析工具测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.agent.tools.builtin.pdf_parser_tool import PDFParserTool
from backend.core.agent.tools.base import ToolResult


class TestPDFParserTool:
    """测试PDF解析工具"""
    
    @pytest.fixture
    def tool(self):
        """创建PDF解析工具实例"""
        return PDFParserTool()
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def sample_pdf(self, temp_dir):
        """创建示例PDF文件（实际测试中需要真实的PDF文件）"""
        # 注意：这里只是占位，实际测试需要真实的PDF文件
        pdf_path = temp_dir / "test.pdf"
        # 创建一个空文件作为占位（实际测试中应该使用真实PDF）
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return pdf_path
    
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
        assert tool.name == "pdf_parser"
        assert "PDF" in tool.description or "pdf" in tool.description.lower()
        assert "解析" in tool.description or "parse" in tool.description.lower()
    
    def test_tool_parameters(self, tool):
        """测试工具参数定义"""
        param_names = [p.name for p in tool.parameters]
        
        assert "file_path" in param_names
        assert "output_format" in param_names
        assert "extract_mode" in param_names
        assert "backend" in param_names
        
        # 检查必需参数
        file_path_param = next((p for p in tool.parameters if p.name == "file_path"), None)
        assert file_path_param is not None
        assert file_path_param.required is True
        assert file_path_param.type == "string"
        
        # 检查可选参数
        output_format_param = next((p for p in tool.parameters if p.name == "output_format"), None)
        assert output_format_param is not None
        assert output_format_param.required is False
        assert output_format_param.default == "markdown"
        assert output_format_param.enum == ["markdown", "json", "excel", "text"]
        
        backend_param = next((p for p in tool.parameters if p.name == "backend"), None)
        assert backend_param is not None
        assert backend_param.default == "auto"
        assert backend_param.enum == ["auto", "mineru", "logics", "camelot"]
    
    def test_validate_parameters_missing_required(self, tool):
        """测试参数验证：缺少必需参数"""
        error = tool.validate_parameters()
        assert error is not None
        assert "file_path" in error.lower()
    
    def test_validate_parameters_valid(self, tool, sample_pdf):
        """测试参数验证：有效参数"""
        error = tool.validate_parameters(
            file_path=str(sample_pdf),
            output_format="markdown"
        )
        assert error is None
    
    def test_validate_parameters_invalid_format(self, tool, sample_pdf):
        """测试参数验证：无效的输出格式"""
        error = tool.validate_parameters(
            file_path=str(sample_pdf),
            output_format="invalid_format"
        )
        assert error is not None
        assert "output_format" in error.lower()
    
    def test_validate_parameters_invalid_backend(self, tool, sample_pdf):
        """测试参数验证：无效的后端"""
        error = tool.validate_parameters(
            file_path=str(sample_pdf),
            backend="invalid_backend"
        )
        assert error is not None
        assert "backend" in error.lower()
    
    def test_execute_missing_file_path(self, tool):
        """测试执行：缺少文件路径"""
        result = tool.execute()
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "file_path" in result.error.lower()
    
    def test_execute_file_not_exists(self, tool):
        """测试执行：文件不存在"""
        result = tool.execute(file_path="/nonexistent/file.pdf")
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "不存在" in result.error or "not exist" in result.error.lower()
    
    def test_execute_file_not_pdf(self, tool, temp_dir):
        """测试执行：文件不是PDF格式"""
        # 创建一个非PDF文件
        text_file = temp_dir / "test.txt"
        text_file.write_text("This is not a PDF")
        
        result = tool.execute(file_path=str(text_file))
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "PDF" in result.error or "pdf" in result.error.lower()
    
    def test_execute_no_backend_available(self, tool, sample_pdf):
        """测试执行：没有可用的后端"""
        # 模拟没有可用后端的情况
        tool._available_backends = {"mineru": False, "logics": False, "camelot": False}
        
        result = tool.execute(file_path=str(sample_pdf))
        
        assert isinstance(result, ToolResult)
        # 如果工具不可用，应该返回错误信息
        if not result.success:
            assert "可用" in result.error or "available" in result.error.lower() or "安装" in result.error
    
    def test_check_backend_availability(self, tool):
        """测试检查后端可用性"""
        backends = tool._check_backend_availability()
        
        # 结果应该是字典
        assert isinstance(backends, dict)
        assert "mineru" in backends
        assert "logics" in backends
        assert "camelot" in backends
        # 值应该是布尔类型
        for available in backends.values():
            assert isinstance(available, bool)
    
    def test_select_backend_auto_table_mode(self, tool):
        """测试自动选择后端：表格模式"""
        available = {"mineru": True, "logics": True, "camelot": True}
        
        # 表格模式应该优先选择 Camelot
        backend = tool._select_backend("auto", "table", available)
        assert backend == "camelot"
    
    def test_select_backend_auto_full_mode(self, tool):
        """测试自动选择后端：完整模式"""
        available = {"mineru": True, "logics": True, "camelot": True}
        
        # 完整模式应该优先选择 MinerU
        backend = tool._select_backend("auto", "full", available)
        assert backend == "mineru"
    
    def test_select_backend_specified(self, tool):
        """测试指定后端"""
        available = {"mineru": True, "logics": True, "camelot": True}
        
        # 指定后端应该使用指定的
        backend = tool._select_backend("logics", "full", available)
        assert backend == "logics"
    
    def test_select_backend_unavailable(self, tool):
        """测试选择不可用的后端"""
        available = {"mineru": False, "logics": False, "camelot": False}
        
        with pytest.raises(RuntimeError, match="没有可用的"):
            tool._select_backend("auto", "full", available)
    
    def test_to_dict_format(self, tool):
        """测试工具转换为字典格式（用于 LLM Function Calling）"""
        tool_dict = tool.to_dict()
        
        assert isinstance(tool_dict, dict)
        assert "type" in tool_dict
        assert tool_dict["type"] == "function"
        assert "function" in tool_dict
        
        func = tool_dict["function"]
        assert func["name"] == "pdf_parser"
        assert "description" in func
        assert "parameters" in func
        
        params = func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        
        # 检查必需参数
        assert "file_path" in params["required"]
        assert "file_path" in params["properties"]


class TestPDFParserToolIntegration:
    """测试PDF解析工具集成（与 ToolRegistry）"""
    
    def test_tool_can_be_registered(self):
        """测试工具可以注册到 ToolRegistry"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = PDFParserTool()
        registry = ToolRegistry()
        
        # 应该能够注册（如果名称不冲突）
        try:
            registry.register(tool)
            assert registry.get_tool("pdf_parser") == tool
        except ValueError:
            # 如果已经注册过，会抛出 ValueError
            assert registry.get_tool("pdf_parser") is not None
    
    def test_tool_in_registry_list(self):
        """测试工具在注册表中的列表"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = PDFParserTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        tools_list = registry.list_tools()
        assert "pdf_parser" in tools_list
    
    def test_tool_for_llm_format(self):
        """测试工具转换为 LLM 格式"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = PDFParserTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        llm_tools = registry.get_tools_for_llm()
        tool_dict = next((t for t in llm_tools if t["function"]["name"] == "pdf_parser"), None)
        
        assert tool_dict is not None
        assert tool_dict["type"] == "function"
        assert tool_dict["function"]["name"] == "pdf_parser"

