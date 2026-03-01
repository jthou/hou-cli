"""GoogleSearchTool 测试（网页搜索：DuckDuckGo HTML，无需 API Key）"""

import pytest
from unittest.mock import patch, MagicMock

from backend.core.agent.tools.builtin.google_search_tool import GoogleSearchTool
from backend.services.google_search_service.browser_search import BrowserSearchError
from backend.services.google_search_service.models import GoogleSearchResponse, GoogleSearchResult


class TestGoogleSearchTool:
    """GoogleSearchTool 单元测试"""

    @pytest.fixture
    def tool(self):
        return GoogleSearchTool()

    def test_tool_initialization(self, tool):
        assert tool.name == "google_search"
        assert tool.description is not None
        assert len(tool.parameters) == 3
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "num_results" in param_names
        assert "language" in param_names

    def test_missing_query(self, tool):
        result = tool.execute()
        assert result.success is False
        assert "query" in result.error.lower() or "必需" in result.error

    @patch("backend.core.agent.tools.builtin.google_search_tool.browser_search")
    def test_search_success(self, mock_search, tool):
        mock_search.return_value = GoogleSearchResponse(
            results=[
                GoogleSearchResult(title="Python", link="https://python.org", snippet="...", display_link="python.org"),
            ],
            total_results=None,
            search_time=0.5,
            query="python",
        )
        result = tool.execute(query="python", num_results=3)
        assert result.success is True
        assert result.data["count"] == 1
        assert len(result.data["results"]) == 1
        assert result.data["results"][0]["title"] == "Python"
        assert result.data["results"][0]["link"] == "https://python.org"

    @patch("backend.core.agent.tools.builtin.google_search_tool.browser_search")
    def test_search_service_error(self, mock_search, tool):
        mock_search.side_effect = BrowserSearchError("请求失败")
        result = tool.execute(query="test")
        assert result.success is False
        assert "失败" in result.error or "请求" in result.error

    @patch("backend.core.agent.tools.builtin.google_search_tool.browser_search")
    def test_num_results_limits(self, mock_search, tool):
        mock_search.return_value = GoogleSearchResponse(
            results=[],
            total_results=None,
            search_time=0.1,
            query="test",
        )
        result1 = tool.execute(query="test", num_results=20)
        result2 = tool.execute(query="test", num_results=0)
        assert result1.success is True
        assert result2.success is True
        mock_search.assert_called()
        calls = mock_search.call_args_list
        assert calls[0][1]["num_results"] == 20
        assert calls[1][1]["num_results"] == 1


class TestGoogleSearchToolIntegration:
    """集成测试（需网络，可选）"""

    @pytest.fixture
    def tool(self):
        return GoogleSearchTool()

    @pytest.mark.integration
    def test_full_search_workflow(self, tool):
        result = tool.execute(query="Python programming", num_results=3)
        if result.success:
            assert "results" in result.data
            assert result.data["count"] <= 3
            for item in result.data["results"]:
                assert "title" in item
                assert "link" in item
                assert "snippet" in item
        else:
            pytest.skip(f"网络或 DuckDuckGo 不可用: {result.error}")
