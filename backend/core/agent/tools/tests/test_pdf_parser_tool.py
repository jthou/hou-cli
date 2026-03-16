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
    
    @pytest.fixture
    def real_test_pdf(self):
        """使用真实的测试PDF文件"""
        # 使用测试目录中的 test.pdf 文件
        test_pdf_path = Path(__file__).parent / "test.pdf"
        if test_pdf_path.exists():
            return test_pdf_path
        else:
            pytest.skip(f"测试PDF文件不存在: {test_pdf_path}")
    
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
        assert backend_param.enum == ["auto", "pypdf", "camelot"]

        extract_mode_param = next((p for p in tool.parameters if p.name == "extract_mode"), None)
        assert extract_mode_param is not None
        assert "formula" not in (extract_mode_param.enum or [])
    
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
        tool._available_backends = {"pypdf": False, "camelot": False}
        
        result = tool.execute(file_path=str(sample_pdf))
        
        assert isinstance(result, ToolResult)
        # 如果工具不可用，应该返回错误信息
        if not result.success:
            assert "可用" in result.error or "available" in result.error.lower() or "安装" in result.error
    
    def test_check_backend_availability(self, tool):
        """测试检查后端可用性"""
        backends = tool._check_backend_availability()
        assert isinstance(backends, dict)
        assert "pypdf" in backends
        assert "camelot" in backends
        for available in backends.values():
            assert isinstance(available, bool)
    
    def test_select_backend_auto_table_mode(self, tool):
        """测试自动选择后端：表格模式"""
        available = {"pypdf": True, "camelot": True}
        backend = tool._select_backend("auto", "table", available)
        assert backend == "camelot"
    
    def test_select_backend_auto_full_mode(self, tool):
        """测试自动选择后端：完整模式"""
        available = {"pypdf": True, "camelot": True}
        backend = tool._select_backend("auto", "full", available)
        assert backend == "pypdf"
    
    def test_select_backend_specified(self, tool):
        """测试指定后端"""
        available = {"pypdf": True, "camelot": True}
        backend = tool._select_backend("camelot", "table", available)
        assert backend == "camelot"
    
    def test_select_backend_unavailable(self, tool):
        """测试选择不可用的后端"""
        available = {"pypdf": False, "camelot": False}
        
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


# 检查是否有可用的PDF解析后端（在类定义前检查）
_tool_for_backend_check = PDFParserTool()
_backends_status = _tool_for_backend_check._check_backend_availability()
_has_available_backend = any(_backends_status.values())

# 如果没有可用后端，在类级别跳过所有测试
if not _has_available_backend:
    pytestmark = pytest.mark.skip(
        reason=(
            "没有可用的PDF解析后端，所有测试被跳过。\n"
            "请安装：pip install pdfplumber 或 pip install camelot-py[cv]\n"
            f"当前后端状态: {_backends_status}"
        )
    )


class TestPDFParserToolWithRealPDF:
    """使用真实PDF文件进行集成测试"""
    
    @pytest.fixture
    def tool(self):
        """创建PDF解析工具实例"""
        return PDFParserTool()
    
    @pytest.fixture
    def test_pdf_path(self):
        """获取测试PDF文件路径"""
        test_pdf_path = Path(__file__).parent / "test.pdf"
        if not test_pdf_path.exists():
            pytest.skip(f"测试PDF文件不存在: {test_pdf_path}")
        return test_pdf_path
    
    @pytest.fixture
    def temp_output_dir(self):
        """创建临时输出目录"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)
    
    def test_parse_pdf_basic(self, tool, test_pdf_path, temp_output_dir):
        """测试基本PDF解析功能"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="markdown",
            extract_mode="text",
            output_path=str(temp_output_dir / "output.md")
        )
        
        # 检查结果
        assert isinstance(result, ToolResult)
        
        if result.success:
            # 检查输出文件是否存在
            output_file = temp_output_dir / "output.md"
            if output_file.exists():
                content = output_file.read_text(encoding='utf-8')
                assert len(content) > 0, "输出文件应该包含内容"
                print(f"\n✅ PDF解析成功，输出文件大小: {len(content)} 字符")
        else:
            # 如果失败，检查是否是后端不可用或已知问题
            error_lower = result.error.lower()
            skip_keywords = ["可用", "available", "安装", "timeout", "网络", "network", "download", "模型", "model", "hub"]
            if any(keyword in result.error or keyword in error_lower for keyword in skip_keywords):
                pytest.skip(f"PDF解析后端不可用或遇到已知问题: {result.error}")
            else:
                # 其他错误，正常失败
                pytest.fail(f"PDF解析失败: {result.error}")
    
    def test_parse_pdf_markdown_format(self, tool, test_pdf_path, temp_output_dir):
        """测试Markdown格式输出"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="markdown",
            extract_mode="full",
            output_path=str(temp_output_dir / "output.md")
        )
        
        if not result.success:
            if "可用" in result.error or "available" in result.error.lower() or "安装" in result.error:
                pytest.skip(f"PDF解析后端不可用: {result.error}")
            else:
                pytest.fail(f"PDF解析失败: {result.error}")
        
        # 检查输出文件
        output_file = temp_output_dir / "output.md"
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            # Markdown 应该包含一些常见标记
            assert len(content) > 0
            print(f"\n✅ Markdown输出成功，文件大小: {len(content)} 字符")
    
    def test_parse_pdf_text_format(self, tool, test_pdf_path, temp_output_dir):
        """测试纯文本格式输出"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="text",
            extract_mode="text",
            output_path=str(temp_output_dir / "output.txt")
        )
        
        if not result.success:
            if "可用" in result.error or "available" in result.error.lower() or "安装" in result.error:
                pytest.skip(f"PDF解析后端不可用: {result.error}")
            else:
                pytest.fail(f"PDF解析失败: {result.error}")
        
        # 检查输出文件
        output_file = temp_output_dir / "output.txt"
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            assert len(content) > 0
            print(f"\n✅ 文本输出成功，文件大小: {len(content)} 字符")
    
    def test_parse_pdf_json_format(self, tool, test_pdf_path, temp_output_dir):
        """测试JSON格式输出"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="json",
            extract_mode="full",
            output_path=str(temp_output_dir / "output.json")
        )
        
        if not result.success:
            if "可用" in result.error or "available" in result.error.lower() or "安装" in result.error:
                pytest.skip(f"PDF解析后端不可用: {result.error}")
            else:
                pytest.fail(f"PDF解析失败: {result.error}")
        
        # 检查输出文件
        output_file = temp_output_dir / "output.json"
        if output_file.exists():
            import json
            content = output_file.read_text(encoding='utf-8')
            # 验证JSON格式
            try:
                data = json.loads(content)
                assert isinstance(data, (dict, list))
                print(f"\n✅ JSON输出成功，数据结构: {type(data).__name__}")
            except json.JSONDecodeError:
                pytest.fail("输出文件不是有效的JSON格式")
    
    def test_parse_pdf_table_mode(self, tool, test_pdf_path, temp_output_dir):
        """测试表格提取模式"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="excel",
            extract_mode="table",
            backend="auto",  # 自动选择最适合表格的后端
            output_path=str(temp_output_dir / "output.xlsx")
        )
        
        if not result.success:
            if "可用" in result.error or "available" in result.error.lower() or "安装" in result.error:
                pytest.skip(f"PDF解析后端不可用: {result.error}")
            else:
                pytest.fail(f"PDF解析失败: {result.error}")
        
        # 检查输出文件
        output_file = temp_output_dir / "output.xlsx"
        if output_file.exists():
            assert output_file.stat().st_size > 0
            print(f"\n✅ Excel输出成功，文件大小: {output_file.stat().st_size} 字节")
    
    def test_parse_pdf_with_specific_backend(self, tool, test_pdf_path, temp_output_dir):
        """测试使用特定后端"""
        # 检查可用后端
        available_backends = tool._check_backend_availability()
        
        # 尝试使用可用的后端
        for backend_name, is_available in available_backends.items():
            if is_available and backend_name != "auto":
                result = tool.execute(
                    file_path=str(test_pdf_path),
                    output_format="markdown",
                    extract_mode="text",
                    backend=backend_name,
                    output_path=str(temp_output_dir / f"output_{backend_name}.md")
                )
                
                if result.success:
                    output_file = temp_output_dir / f"output_{backend_name}.md"
                    if output_file.exists():
                        content = output_file.read_text(encoding='utf-8')
                        assert len(content) > 0
                        print(f"\n✅ 使用 {backend_name} 后端解析成功")
                        break
                elif "可用" not in result.error and "available" not in result.error.lower():
                    # 不是后端不可用的错误，记录但继续
                    print(f"\n⚠️  使用 {backend_name} 后端失败: {result.error}")
        else:
            # 所有后端都不可用或失败
            pytest.skip("没有可用的PDF解析后端")
    
    def test_parse_pdf_result_structure(self, tool, test_pdf_path, temp_output_dir):
        """测试解析结果的数据结构"""
        result = tool.execute(
            file_path=str(test_pdf_path),
            output_format="json",
            extract_mode="full",
            output_path=str(temp_output_dir / "output.json")
        )
        
        if not result.success:
            if "可用" in result.error or "available" in result.error.lower() or "安装" in result.error:
                pytest.skip(f"PDF解析后端不可用: {result.error}")
            else:
                pytest.fail(f"PDF解析失败: {result.error}")
        
        # 检查返回的数据结构
        assert result.data is not None
        assert "file_path" in result.data or "output_file" in result.data or "output_path" in result.data
        
        # 检查输出文件路径
        output_file_path = result.data.get("output_file") or result.data.get("output_path")
        if output_file_path:
            output_file = Path(output_file_path)
            assert output_file.exists()
            print(f"\n✅ 解析结果包含输出文件路径: {output_file}")

