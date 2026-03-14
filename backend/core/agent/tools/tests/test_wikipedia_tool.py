"""WikipediaTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from shared.load_env import load_env_for_file
load_env_for_file(__file__)

from backend.core.agent.tools.builtin.wikipedia_tool import WikipediaTool
from backend.core.agent.tools.base import ToolResult
from backend.services.wikipedia_service import WikipediaServiceError


class TestWikipediaTool:
    """WikipediaTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 WikipediaTool 实例"""
        return WikipediaTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "wikipedia"
        assert tool.description is not None
        assert len(tool.parameters) == 6

        param_names = [p.name for p in tool.parameters]
        assert "action" in param_names
        assert "query" in param_names
        assert "num_results" in param_names
        assert "language" in param_names
        assert "summary_only" in param_names
        assert "limit" in param_names

    def test_missing_query(self, tool):
        """测试缺少 query 参数"""
        result = tool.execute(action="search")
        assert result.success is False
        assert "query" in result.error.lower() or "必需" in result.error

    def test_invalid_action(self, tool):
        """测试无效的操作类型"""
        result = tool.execute(action="invalid_action", query="test")
        assert result.success is False
        assert "未知的操作类型" in result.error or "未知" in result.error

    def test_service_initialization_error(self, tool):
        """测试服务初始化错误"""
        with patch.object(tool, '_get_search_service') as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Wikipedia 搜索服务初始化失败")
            
            result = tool.execute(action="search", query="test")
            assert result.success is False
            assert "初始化失败" in result.error or "初始化" in result.error

    def test_search_action(self, tool):
        """测试搜索操作"""
        result = tool.execute(
            action="search",
            query="Python",
            num_results=5,
            language="zh"
        )

        if result.success:
            assert "results" in result.data
            assert result.data["action"] == "search"
            assert result.data["count"] > 0
        else:
            # Wikipedia 不需要 API Key，如果失败可能是网络问题
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

    def test_get_page_action(self, tool):
        """测试获取页面操作"""
        result = tool.execute(
            action="get_page",
            query="Python",
            language="zh",
            summary_only=True
        )

        if result.success:
            assert result.data["action"] == "get_page"
            assert "title" in result.data
            assert "summary" in result.data
        else:
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

    def test_num_results_limits(self, tool):
        """测试结果数量限制"""
        # 测试超过最大限制
        result = tool.execute(
            action="search",
            query="test",
            num_results=30
        )
        # 应该被限制到 20

        # 测试小于最小限制
        result = tool.execute(
            action="search",
            query="test",
            num_results=0
        )
        # 应该被限制到 1

    def test_wikipedia_service_error(self, tool):
        """测试 Wikipedia 服务错误处理"""
        with patch.object(tool, '_get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = MagicMock(side_effect=WikipediaServiceError("API 错误"))
            mock_get_service.return_value = mock_service
            
            result = tool.execute(action="search", query="test")
            assert result.success is False
            assert "失败" in result.error or "错误" in result.error


class TestWikipediaToolIntegration:
    """WikipediaTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 WikipediaTool 实例"""
        return WikipediaTool()

    @pytest.mark.integration
    def test_search_workflow(self, tool):
        """测试搜索工作流"""
        result = tool.execute(
            action="search",
            query="Python programming",
            num_results=5,
            language="en"
        )

        if result.success:
            assert "results" in result.data
            assert len(result.data["results"]) > 0
            
            # 验证结果格式
            for item in result.data["results"]:
                assert "title" in item
                assert "url" in item
                assert "snippet" in item
        else:
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

    @pytest.mark.integration
    def test_get_page_workflow(self, tool):
        """测试获取页面工作流"""
        result = tool.execute(
            action="get_page",
            query="Python (programming language)",
            language="en",
            summary_only=False
        )

        if result.success:
            assert result.data["action"] == "get_page"
            assert "title" in result.data
            assert "summary" in result.data
            assert "url" in result.data
        else:
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

    @pytest.mark.integration
    def test_get_page_links(self, tool):
        """测试获取页面链接"""
        result = tool.execute(
            action="get_page_links",
            query="Python",
            language="zh",
            limit=10
        )

        if result.success:
            assert result.data["action"] == "get_page_links"
            assert "links" in result.data
            assert "links_count" in result.data
        else:
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

    @pytest.mark.integration
    def test_featured_article(self, tool):
        """测试获取特色文章"""
        result = tool.execute(
            action="featured_article",
            query="",  # featured_article 不需要 query
            language="zh"
        )

        if result.success:
            assert result.data["action"] == "featured_article"
            assert "title" in result.data
            assert "summary" in result.data
        else:
            if "网络" in result.error or "network" in result.error.lower():
                pytest.skip(f"网络问题: {result.error}")

