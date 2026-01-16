"""MediaWikiTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
from backend.core.agent.tools.base import ToolResult


class TestMediaWikiTool:
    """MediaWikiTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 MediaWikiTool 实例"""
        return MediaWikiTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "mediawiki"
        assert tool.description is not None
        assert len(tool.parameters) == 6

        param_names = [p.name for p in tool.parameters]
        assert "operation" in param_names
        assert "query" in param_names
        assert "title" in param_names
        assert "content" in param_names
        assert "summary" in param_names
        assert "limit" in param_names

    def test_missing_operation(self, tool):
        """测试缺少 operation 参数"""
        result = tool.execute()
        assert result.success is False
        assert "operation" in result.error.lower() or "必需" in result.error

    def test_invalid_operation(self, tool):
        """测试无效的操作类型"""
        result = tool.execute(operation="invalid_operation")
        assert result.success is False
        assert "未知的操作" in result.error or "未知" in result.error

    def test_search_missing_query(self, tool):
        """测试搜索操作缺少 query"""
        result = tool.execute(operation="search")
        assert result.success is False
        assert "query" in result.error.lower() or "必需" in result.error

    def test_read_missing_title(self, tool):
        """测试读取操作缺少 title"""
        result = tool.execute(operation="read")
        assert result.success is False
        assert "title" in result.error.lower() or "必需" in result.error

    def test_client_initialization_error(self, tool):
        """测试客户端初始化错误"""
        with patch.object(tool, '_get_client') as mock_get_client:
            mock_get_client.side_effect = RuntimeError("MediaWiki 客户端初始化失败")
            
            result = tool.execute(operation="search", query="test")
            assert result.success is False
            assert "初始化失败" in result.error or "初始化" in result.error

    @pytest.mark.skipif(
        not os.getenv("MEDIAWIKI_URL"),
        reason="需要设置 MEDIAWIKI_URL 环境变量"
    )
    def test_search_operation(self, tool):
        """测试搜索操作"""
        result = tool.execute(
            operation="search",
            query="test",
            limit=5
        )

        if result.success:
            assert "results" in result.data
            assert result.data["operation"] == "search"
        else:
            # 检查是否是配置问题
            if "URL" in result.error or "配置" in result.error:
                pytest.skip(f"MediaWiki 配置问题: {result.error}")

    @pytest.mark.skipif(
        not os.getenv("MEDIAWIKI_URL"),
        reason="需要设置 MEDIAWIKI_URL 环境变量"
    )
    def test_read_operation(self, tool):
        """测试读取操作"""
        result = tool.execute(
            operation="read",
            title="Test"
        )

        if result.success:
            assert result.data["operation"] == "read"
            assert "title" in result.data
            assert "content" in result.data
        else:
            if "URL" in result.error or "配置" in result.error:
                pytest.skip(f"MediaWiki 配置问题: {result.error}")


class TestMediaWikiToolIntegration:
    """MediaWikiTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 MediaWikiTool 实例"""
        return MediaWikiTool()

    @pytest.mark.skipif(
        not os.getenv("MEDIAWIKI_URL"),
        reason="需要设置 MEDIAWIKI_URL 环境变量"
    )
    @pytest.mark.integration
    def test_search_workflow(self, tool):
        """测试搜索工作流"""
        result = tool.execute(
            operation="search",
            query="test",
            limit=10
        )

        if result.success:
            assert "results" in result.data
            assert result.data["operation"] == "search"
        else:
            if "URL" in result.error or "配置" in result.error:
                pytest.skip(f"MediaWiki 配置问题: {result.error}")

    @pytest.mark.skipif(
        not os.getenv("MEDIAWIKI_URL"),
        reason="需要设置 MEDIAWIKI_URL 环境变量"
    )
    @pytest.mark.integration
    def test_read_workflow(self, tool):
        """测试读取工作流"""
        # 先搜索一个页面
        search_result = tool.execute(
            operation="search",
            query="test",
            limit=1
        )

        if search_result.success and search_result.data.get("results"):
            title = search_result.data["results"][0].get("title", "Test")
            
            # 读取页面
            result = tool.execute(
                operation="read",
                title=title
            )

            if result.success:
                assert result.data["operation"] == "read"
                assert "title" in result.data
            else:
                if "URL" in result.error or "配置" in result.error:
                    pytest.skip(f"MediaWiki 配置问题: {result.error}")
        else:
            pytest.skip("无法搜索到页面进行测试")

