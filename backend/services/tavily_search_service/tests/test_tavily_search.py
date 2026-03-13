"""Tavily 搜索服务单元测试（mock API 调用）"""

import os
import pytest
from unittest.mock import patch, MagicMock

from backend.services.tavily_search_service.tavily_search import (
    search as tavily_search,
    TavilySearchError,
)
from backend.services.google_search_service.models import GoogleSearchResponse, GoogleSearchResult


class TestTavilySearch:
    """Tavily 搜索单元测试"""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """确保测试时有 TAVILY_API_KEY"""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-tvly-key"}):
            yield

    def test_missing_api_key(self):
        """测试未设置 TAVILY_API_KEY 时抛出错误"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(TavilySearchError) as exc_info:
                tavily_search("test query")
            assert "TAVILY_API_KEY" in str(exc_info.value)

    @patch("tavily.TavilyClient")
    @patch("backend.services.tavily_search_service.tavily_search.append_tavily_audit")
    def test_search_success(self, mock_audit, mock_client_cls):
        """测试成功搜索（Tavily 返回 dict）"""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Python", "url": "https://python.org", "content": "Python website"},
                {"title": "Docs", "url": "https://docs.python.org", "content": "Documentation"},
            ],
            "query": "python",
            "response_time": 0.5,
        }
        mock_client_cls.return_value = mock_client

        result = tavily_search("python", num_results=5)

        assert isinstance(result, GoogleSearchResponse)
        assert result.query == "python"
        assert len(result.results) == 2
        assert result.results[0].title == "Python"
        assert result.results[0].link == "https://python.org"
        assert result.results[0].snippet == "Python website"
        assert result.results[1].title == "Docs"
        assert result.results[1].link == "https://docs.python.org"
        mock_client.search.assert_called_once()
        call_kw = mock_client.search.call_args[1]
        assert call_kw["query"] == "python"
        assert call_kw["max_results"] == 5
        assert call_kw["search_depth"] == "basic"
        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["query"] == "python"
        assert mock_audit.call_args[1]["credits_used"] == 1

    @patch("tavily.TavilyClient")
    @patch("backend.services.tavily_search_service.tavily_search.append_tavily_audit")
    def test_search_advanced_depth(self, mock_audit, mock_client_cls):
        """测试 advanced 搜索深度（2 credits）"""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": [], "query": "test", "response_time": 0.1}
        mock_client_cls.return_value = mock_client

        tavily_search("test", search_depth="advanced")

        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["credits_used"] == 2
        assert mock_audit.call_args[1]["search_depth"] == "advanced"

    @patch("tavily.TavilyClient")
    @patch("backend.services.tavily_search_service.tavily_search.append_tavily_audit")
    def test_search_num_results_limit(self, mock_audit, mock_client_cls):
        """测试 num_results 限制在 1-20"""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": [], "query": "test", "response_time": 0.1}
        mock_client_cls.return_value = mock_client

        tavily_search("test", num_results=50)
        assert mock_client.search.call_args[1]["max_results"] == 20

        tavily_search("test", num_results=0)
        assert mock_client.search.call_args[1]["max_results"] == 1

    @patch("tavily.TavilyClient")
    def test_search_api_error(self, mock_client_cls):
        """测试 API 调用失败"""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API rate limit exceeded")
        mock_client_cls.return_value = mock_client

        with pytest.raises(TavilySearchError) as exc_info:
            tavily_search("test")
        assert "Tavily" in str(exc_info.value) or "API" in str(exc_info.value)

    @patch("tavily.TavilyClient")
    @patch("backend.services.tavily_search_service.tavily_search.append_tavily_audit")
    def test_search_object_results(self, mock_audit, mock_client_cls):
        """测试 Tavily 返回 dict 格式的 results（兼容对象格式）"""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Obj Title", "url": "https://example.com", "content": "Content here"},
            ],
            "query": "test",
            "response_time": 0.1,
        }
        mock_client_cls.return_value = mock_client

        result = tavily_search("test")

        assert len(result.results) == 1
        assert result.results[0].title == "Obj Title"
        assert result.results[0].link == "https://example.com"
        assert result.results[0].snippet == "Content here"


class TestTavilyUsageAudit:
    """Tavily 审计模块测试"""

    @patch("backend.services.tavily_search_service.tavily_usage_audit._get_conn")
    def test_append_audit_disabled(self, mock_conn):
        """测试 TAVILY_AUDIT_DISABLED=1 时不写入"""
        with patch.dict(os.environ, {"TAVILY_AUDIT_DISABLED": "1"}):
            from backend.services.tavily_search_service.tavily_usage_audit import (
                append_tavily_audit,
                _is_audit_disabled,
            )

            assert _is_audit_disabled() is True
            append_tavily_audit(query="test")
            mock_conn.assert_not_called()

    @patch("backend.services.tavily_search_service.tavily_usage_audit._get_conn")
    def test_append_audit_writes(self, mock_conn):
        """测试正常写入审计"""
        mock_conn.return_value = MagicMock()
        with patch.dict(os.environ, {"TAVILY_AUDIT_DISABLED": ""}, clear=False):
            from backend.services.tavily_search_service.tavily_usage_audit import (
                append_tavily_audit,
            )

            append_tavily_audit(
                query="test query",
                credits_used=2,
                search_depth="advanced",
                num_results=5,
                response_time=0.5,
            )
            mock_conn.assert_called()
            conn = mock_conn.return_value
            conn.execute.assert_called()
            call_args = conn.execute.call_args[0]
            assert "?" in call_args[0]
            assert "test query" in call_args[1]
            assert 2 in call_args[1]
            assert 5 in call_args[1]
