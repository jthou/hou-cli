"""Wikipedia 路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestWikipediaRoutes:
    """Wikipedia 路由测试类"""

    def test_search_read_route_exists(self, client):
        """验证 /api/wikipedia/search-read 路由存在且可访问（返回 200 或 400，非 404）"""
        with patch('backend.api.wikipedia_routes.wp_search') as mock_search:
            mock_search.return_value = [{"title": "Python", "snippet": "...", "url": "https://zh.wikipedia.org/wiki/Python", "score": 1.0}]
            with patch('backend.api.wikipedia_routes.get_page_content') as mock_get:
                mock_get.return_value = {
                    "title": "Python",
                    "content": "'''Python''' 是一种编程语言。",
                    "url": "https://zh.wikipedia.org/wiki/Python",
                    "categories": ["编程语言"],
                }
                response = client.get("/api/wikipedia/search-read?terms=Python&per_term_limit=1&lang=zh")
                assert response.status_code != 404, "路由应存在，不应返回 404"
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["total_pages"] >= 1
                assert "results" in data

    def test_search_read_empty_terms_returns_400(self, client):
        """测试空 terms 返回 400"""
        response = client.get("/api/wikipedia/search-read?terms=&per_term_limit=5&lang=zh")
        assert response.status_code == 400

    def test_recent_read_route_exists(self, client):
        """验证 /api/wikipedia/recent-read 路由存在"""
        with patch('backend.api.wikipedia_routes.get_recently_changed_titles') as mock_rc:
            mock_rc.return_value = ["Python", "Java"]
            with patch('backend.api.wikipedia_routes.get_page_content') as mock_get:
                mock_get.return_value = {
                    "title": "Python",
                    "content": "'''Python''' 是一种编程语言。",
                    "url": "https://zh.wikipedia.org/wiki/Python",
                    "categories": [],
                }
                response = client.get("/api/wikipedia/recent-read?count=2&lang=zh")
                assert response.status_code != 404
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_random_read_route_exists(self, client):
        """验证 /api/wikipedia/random-read 路由存在"""
        with patch('backend.api.wikipedia_routes.get_random_titles') as mock_rand:
            mock_rand.return_value = ["Python", "Java"]
            with patch('backend.api.wikipedia_routes.get_page_content') as mock_get:
                mock_get.return_value = {
                    "title": "Python",
                    "content": "'''Python''' 是一种编程语言。",
                    "url": "https://zh.wikipedia.org/wiki/Python",
                    "categories": [],
                }
                response = client.get("/api/wikipedia/random-read?count=2&lang=zh")
                assert response.status_code != 404
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_get_page_route_exists(self, client):
        """验证 /api/wikipedia/pages/{title} 路由存在"""
        with patch('backend.api.wikipedia_routes.get_page_content') as mock_get:
            mock_get.return_value = {
                "title": "Python",
                "content": "'''Python''' 是一种编程语言。",
                "url": "https://zh.wikipedia.org/wiki/Python",
                "categories": ["编程语言"],
            }
            response = client.get("/api/wikipedia/pages/Python?lang=zh")
            assert response.status_code != 404
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["page"]["title"] == "Python"
            assert "content" in data["page"]

    def test_get_page_not_found_returns_404(self, client):
        """测试不存在的页面返回 404"""
        with patch('backend.api.wikipedia_routes.get_page_content') as mock_get:
            mock_get.return_value = None
            response = client.get("/api/wikipedia/pages/NonExistentPage12345?lang=zh")
            assert response.status_code == 404

    def test_parse_route_exists(self, client):
        """验证 /api/wikipedia/parse 路由存在"""
        with patch('backend.api.wikipedia_routes.parse_wikitext') as mock_parse:
            mock_parse.return_value = "<p>'''Python''' 是一种编程语言。</p>"
            response = client.post(
                "/api/wikipedia/parse",
                json={"wikitext": "'''Python''' 是一种编程语言。", "lang": "zh"},
            )
            assert response.status_code != 404
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "html" in data
            assert "base_url" in data

    def test_base_url_route_exists(self, client):
        """验证 /api/wikipedia/base-url 路由存在"""
        response = client.get("/api/wikipedia/base-url?lang=zh")
        assert response.status_code != 404
        assert response.status_code == 200
        data = response.json()
        assert "base_url" in data
        assert "zh.wikipedia.org" in data["base_url"]

    def test_diagnostic_route_exists(self, client):
        """验证 /api/wikipedia/diagnostic 可快速确认路由已加载（404 时需重启后端）"""
        response = client.get("/api/wikipedia/diagnostic")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
