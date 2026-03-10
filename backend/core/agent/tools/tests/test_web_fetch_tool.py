"""Web Fetch 工具单元测试：URL 校验、抓取与正文提取。"""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.agent.tools.builtin.web_fetch_tool import (
    WebFetchTool,
    _validate_url,
    _extract_title_regex,
    _extract_fallback,
    _url_to_fallback_title,
)


class TestWebFetchValidation:
    """URL 校验"""

    def test_validate_url_empty(self):
        assert _validate_url("") == "URL 不能为空"
        assert _validate_url(None) == "URL 不能为空"

    def test_validate_url_https_ok(self):
        assert _validate_url("https://example.com/page") is None
        assert _validate_url("http://anthropic.com/engineering/foo") is None

    def test_validate_url_forbidden_scheme(self):
        assert "不允许的协议" in (_validate_url("file:///etc/passwd") or "")
        assert "不允许的协议" in (_validate_url("javascript:alert(1)") or "")

    def test_validate_url_no_scheme(self):
        assert _validate_url("example.com") is not None
        assert "完整" in (_validate_url("example.com") or "")

class TestWebFetchExtraction:
    """正文与标题提取（不依赖网络）"""

    def test_extract_title_regex(self):
        html = "<html><head><title>  Hello World  </title></head><body></body></html>"
        assert _extract_title_regex(html) == "Hello World"
        assert _extract_title_regex("<html><body>no title</body></html>") is None

    def test_extract_fallback(self):
        html = "<html><head><title>Test Page</title></head><body><p>Paragraph one.</p><p>Two.</p></body></html>"
        title, body = _extract_fallback(html)
        assert title == "Test Page"
        assert "Paragraph one" in body and "Two" in body

    def test_url_to_fallback_title(self):
        # path 最后一段 "-" 会转为空格
        assert _url_to_fallback_title(
            "https://anthropic.com/engineering/writing-tools-for-agents"
        ) == "writing tools for agents"
        assert _url_to_fallback_title("https://example.com") == "example.com"


class TestWebFetchToolExecute:
    """execute 集成（mock httpx）"""

    @pytest.fixture
    def tool(self):
        return WebFetchTool()

    def test_execute_invalid_url(self, tool):
        r = tool.execute(url="file:///etc/passwd")
        assert r.success is False
        assert r.error

    def test_execute_success_fallback_extraction(self, tool):
        html = (
            "<!DOCTYPE html><html><head><title>Test Article</title></head>"
            "<body><article><p>First paragraph.</p><p>Second.</p></article></body></html>"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        mock_get = MagicMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.get = mock_get
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch(
            "backend.core.agent.tools.builtin.web_fetch_tool.httpx.Client",
            return_value=mock_ctx,
        ):
            with patch(
                "backend.core.agent.tools.builtin.web_fetch_tool._extract_with_trafilatura",
                return_value=None,
            ):
                r = tool.execute(url="https://example.com/article")
        assert r.success is True
        assert r.data is not None
        assert r.data.get("title") == "Test Article"
        assert "First paragraph" in (r.data.get("content") or "")
        assert r.data.get("content_length", 0) > 0
        assert r.data.get("url") == "https://example.com/article"

    def test_execute_http_error(self, tool):
        import httpx as httpx_mod
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx_mod.HTTPStatusError("404", request=MagicMock(), response=mock_resp)
        )
        mock_ctx = MagicMock()
        mock_ctx.get = MagicMock(return_value=mock_resp)
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch(
            "backend.core.agent.tools.builtin.web_fetch_tool.httpx.Client",
            return_value=mock_ctx,
        ):
            r = tool.execute(url="https://example.com/missing")
        assert r.success is False
        assert "404" in (r.error or "") or "请求失败" in (r.error or "")
