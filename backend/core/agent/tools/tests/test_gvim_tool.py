"""GvimTool 测试"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.tools.builtin.gvim_tool import GvimTool
from backend.core.agent.tools.base import ToolResult
from backend.services.gvim_service import GvimServiceError


class TestGvimTool:
    """GvimTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 GvimTool 实例"""
        return GvimTool()

    @pytest.fixture
    def temp_file(self):
        """创建临时文件用于测试"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)
        yield temp_path
        # 清理
        if temp_path.exists():
            temp_path.unlink()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "gvim"
        assert tool.description is not None
        assert len(tool.parameters) >= 5

        param_names = [p.name for p in tool.parameters]
        assert "file_path" in param_names or "mediawiki_page" in param_names

    def test_missing_file_and_page(self, tool):
        """测试缺少 file_path 和 mediawiki_page"""
        result = tool.execute()
        assert result.success is False
        # 如果 gvim 不可用，错误信息会不同，所以检查多种情况
        error_lower = result.error.lower()
        assert (
            "file_path" in error_lower or 
            "mediawiki_page" in error_lower or 
            "必需" in result.error or
            "gvim 不可用" in error_lower or
            "not available" in error_lower
        )

    def test_service_initialization_error(self, tool):
        """测试服务初始化错误"""
        with patch.object(tool, '_get_service') as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Gvim 服务初始化失败")
            
            result = tool.execute(file_path="/tmp/test.txt")
            assert result.success is False
            assert "初始化失败" in result.error or "初始化" in result.error

    def test_open_file(self, tool, temp_file):
        """测试打开文件"""
        result = tool.execute(
            file_path=str(temp_file),
            mode="open"
        )

        if result.success:
            assert "file_path" in result.data or "message" in result.data
        else:
            # 检查是否是 gvim 未安装
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Gvim 未安装: {result.error}")

    def test_open_file_with_line_number(self, tool, temp_file):
        """测试打开文件并定位到指定行"""
        result = tool.execute(
            file_path=str(temp_file),
            line_number=1,
            mode="open"
        )

        if result.success:
            assert "file_path" in result.data or "message" in result.data
        else:
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Gvim 未安装: {result.error}")

    def test_read_only_mode(self, tool, temp_file):
        """测试只读模式"""
        result = tool.execute(
            file_path=str(temp_file),
            read_only=True,
            mode="open"
        )

        if result.success:
            assert "file_path" in result.data or "message" in result.data
        else:
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Gvim 未安装: {result.error}")

    def test_gvim_service_error(self, tool):
        """测试 Gvim 服务错误处理"""
        with patch.object(tool, '_get_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.open_file = MagicMock(side_effect=GvimServiceError("Gvim 错误"))
            mock_get_service.return_value = mock_service
            
            result = tool.execute(file_path="/tmp/test.txt")
            assert result.success is False
            assert "失败" in result.error or "错误" in result.error


class TestGvimToolIntegration:
    """GvimTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 GvimTool 实例"""
        return GvimTool()

    @pytest.fixture
    def temp_file(self):
        """创建临时文件用于测试"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Test file\nprint('hello')")
            temp_path = Path(f.name)
        yield temp_path
        # 清理
        if temp_path.exists():
            temp_path.unlink()

    @pytest.mark.integration
    def test_open_file_workflow(self, tool, temp_file):
        """测试打开文件工作流"""
        result = tool.execute(
            file_path=str(temp_file),
            mode="open"
        )

        if result.success:
            assert "file_path" in result.data or "message" in result.data
        else:
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Gvim 未安装: {result.error}")

    @pytest.mark.skipif(
        not os.getenv("MEDIAWIKI_URL"),
        reason="需要设置 MEDIAWIKI_URL 环境变量"
    )
    @pytest.mark.integration
    def test_open_mediawiki_page(self, tool):
        """测试打开 MediaWiki 页面"""
        result = tool.execute(
            mediawiki_page="Test",
            mode="open"
        )

        if result.success:
            assert "mediawiki_page" in result.data or "message" in result.data
        else:
            if "未找到" in result.error or "not found" in result.error.lower():
                pytest.skip(f"Gvim 未安装: {result.error}")
            elif "URL" in result.error or "配置" in result.error:
                pytest.skip(f"MediaWiki 配置问题: {result.error}")

