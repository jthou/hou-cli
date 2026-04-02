"""MediaWiki 路由单元测试"""
import hashlib
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from backend.services.mediawiki_client_service.models import MediaWikiPage, MediaWikiSearchResult


class TestMediaWikiRoutes:
    """MediaWiki 路由测试类"""
    
    @pytest.fixture
    def mock_search_results(self):
        """创建模拟搜索结果"""
        return [
            MediaWikiSearchResult(
                title="测试页面1",
                snippet="这是测试内容1",
                url="http://example.com/测试页面1",
                score=0.95
            ),
            MediaWikiSearchResult(
                title="测试页面2",
                snippet="这是测试内容2",
                url="http://example.com/测试页面2",
                score=0.85
            )
        ]
    
    @pytest.fixture
    def mock_page(self):
        """创建模拟页面"""
        return MediaWikiPage(
            title="测试页面",
            content="这是页面内容",
            url="http://example.com/测试页面",
            categories=["测试", "示例"],
            links=["链接1", "链接2"],
            last_modified=datetime.now(),
            revision_id=12345
        )
    
    def test_search_mediawiki_success(self, client, mock_search_results):
        """测试 MediaWiki 搜索成功"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.search_pages = MagicMock(return_value=mock_search_results)
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/mediawiki/search?query=测试&limit=20")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["title"] == "测试页面1"
    
    def test_search_mediawiki_invalid_limit(self, client):
        """测试 MediaWiki 搜索无效的 limit"""
        # Mock get_mediawiki_client 以避免初始化错误
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/mediawiki/search?query=测试&limit=0")
            
            assert response.status_code == 400
            assert "limit must be between 1 and 100" in response.json()["detail"]
    
    def test_search_mediawiki_limit_too_large(self, client):
        """测试 MediaWiki 搜索 limit 过大"""
        # Mock get_mediawiki_client 以避免初始化错误
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/mediawiki/search?query=测试&limit=200")
            
            assert response.status_code == 400
    
    def test_get_mediawiki_page_success(self, client, mock_page):
        """测试获取 MediaWiki 页面成功"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_page = MagicMock(return_value=mock_page)
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/mediawiki/pages/测试页面")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["page"]["title"] == "测试页面"
            assert data["page"]["content"] == "这是页面内容"
            assert len(data["page"]["categories"]) == 2
    
    def test_parse_mediawiki_wikitext_success(self, client):
        """测试 MediaWiki wikitext 解析为 HTML 成功"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.parse_wikitext = MagicMock(
                return_value='<div class="mw-parser-output"><p>Hello</p></div>'
            )
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/mediawiki/parse",
                json={"wikitext": "Hello '''world'''"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "html" in data
            assert "mw-parser-output" in data["html"]
            mock_client.parse_wikitext.assert_called_once_with("Hello '''world'''", title=None)

    def test_parse_mediawiki_wikitext_with_title(self, client):
        """测试带 title 的 parse 请求"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.parse_wikitext = MagicMock(return_value="<p>OK</p>")
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/mediawiki/parse",
                json={"wikitext": "{{PAGENAME}}", "title": "Test"},
            )

            assert response.status_code == 200
            mock_client.parse_wikitext.assert_called_once_with("{{PAGENAME}}", title="Test")

    def test_get_mediawiki_page_not_found(self, client):
        """测试获取不存在的 MediaWiki 页面"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_page = MagicMock(return_value=None)
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/mediawiki/pages/不存在的页面")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_edit_mediawiki_page_success(self, client):
        """测试编辑 MediaWiki 页面成功"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.edit_page = MagicMock(return_value=True)
            mock_get_client.return_value = mock_client
            
            response = client.post(
                "/api/mediawiki/pages/测试页面",
                json={"content": "新内容", "summary": "测试编辑"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_client.edit_page.assert_called_once_with(
                "测试页面",
                "新内容",
                summary="测试编辑"
            )
    
    def test_edit_mediawiki_page_failed(self, client):
        """测试编辑 MediaWiki 页面失败"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.edit_page = MagicMock(return_value=False)
            mock_get_client.return_value = mock_client
            
            response = client.post(
                "/api/mediawiki/pages/测试页面",
                json={"content": "新内容", "summary": "测试编辑"}
            )
            
            assert response.status_code == 500
            assert "Edit failed" in response.json()["detail"]
    
    def test_edit_mediawiki_page_default_summary(self, client):
        """测试编辑 MediaWiki 页面使用默认摘要"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.edit_page = MagicMock(return_value=True)
            mock_get_client.return_value = mock_client
            
            response = client.post(
                "/api/mediawiki/pages/测试页面",
                json={"content": "新内容"}
            )
            
            assert response.status_code == 200
            mock_client.edit_page.assert_called_once_with(
                "测试页面",
                "新内容",
                summary="由 API 编辑"
            )
    
    def test_trigger_sync_all(self, client):
        """测试触发全量同步"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_sync_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.sync_all_pages = MagicMock(return_value={"synced": 10, "failed": 0})
            mock_get_service.return_value = mock_service
            
            response = client.post("/api/mediawiki/sync?force=false")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_service.sync_all_pages.assert_called_once_with(force=False)
    
    def test_trigger_sync_category(self, client):
        """测试触发分类同步"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_sync_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.sync_category = MagicMock(return_value={"synced": 5, "failed": 0})
            mock_get_service.return_value = mock_service
            
            response = client.post("/api/mediawiki/sync?force=true&category=测试分类")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_service.sync_category.assert_called_once_with("测试分类", force=True)
    
    def test_get_sync_status_success(self, client):
        """测试获取同步状态成功"""
        with patch('backend.api.mediawiki_routes.get_mediawiki_sync_service') as mock_get_service:
            mock_service = MagicMock()
            mock_status = {
                "is_syncing": False,
                "last_sync_time": "2024-01-01T12:00:00",
                "total_pages": 100,
                "synced_pages": 95
            }
            mock_service.get_sync_status = MagicMock(return_value=mock_status)
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/mediawiki/sync/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"]["total_pages"] == 100

    def test_upload_image_file_hashes_name_and_calls_upload(self, client):
        """粘贴上传：multipart 文件 → 内容哈希文件名 → upload_file。"""
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        with patch("backend.api.mediawiki_routes.get_mediawiki_client") as mock_get:
            mock_c = MagicMock()
            mock_c.upload_file = MagicMock(return_value=True)
            mock_get.return_value = mock_c
            response = client.post(
                "/api/mediawiki/upload-image-file",
                files=[("file", ("clip.png", png_header, "image/png"))],
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"].startswith("img_")
        assert data["filename"].endswith(".png")
        assert "[[File:" in data["wikitext"]
        mock_c.upload_file.assert_called_once()
        call_args = mock_c.upload_file.call_args[0]
        assert call_args[0] == data["filename"]

    def test_upload_image_special_filepath_no_http_get(self, client):
        """已是本站 Special:FilePath 时不再 httpx 拉取（避免 FilePath 502）。"""
        with patch("backend.api.mediawiki_routes.get_mediawiki_client") as mock_get:
            mock_c = MagicMock()
            mock_get.return_value = mock_c
            response = client.post(
                "/api/mediawiki/upload-image",
                json={
                    "image_url": "http://www.jthou.com/mediawiki/index.php/Special:FilePath/my_photo.png",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "my_photo.png"
        assert data["wikitext"] == "[[File:my_photo.png]]"
        mock_c.upload_file.assert_not_called()

    def test_wiki_filename_from_special_filepath_title_query(self):
        from backend.api.mediawiki_routes import _wiki_filename_from_special_filepath_url

        base = "http://www.jthou.com/mediawiki"
        u = "http://www.jthou.com/mediawiki/index.php?title=Special:FilePath%2Fa%20b.png"
        assert _wiki_filename_from_special_filepath_url(u, base) == "a b.png"

    def test_url_fetch_replace_matches_www_when_mediawiki_is_bare_host(self, monkeypatch):
        """MEDIAWIKI 配裸域时，www 图床 URL 也应触发 REPLACE_ORIGIN（避免 host 不一致不重写）。"""
        monkeypatch.setenv("MEDIAWIKI_URL", "http://jthou.com/mediawiki")
        monkeypatch.setenv("MEDIAWIKI_FETCH_REPLACE_ORIGIN", "http://127.0.0.1")
        monkeypatch.delenv("MEDIAWIKI_FETCH_REPLACE_FOR_HOSTS", raising=False)
        from backend.api.mediawiki_routes import _url_for_server_side_image_fetch

        out = _url_for_server_side_image_fetch("http://www.jthou.com/images/vim/a.png")
        assert out == "http://127.0.0.1/images/vim/a.png"

    def test_upload_image_from_url_uses_content_hash_filename(self, client):
        """URL 拉图上传：按字节哈希命名，不用 URL 里的 image.png。"""
        body = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        expected_name = f"img_{hashlib.sha256(body).hexdigest()[:16]}.png"

        class FakeResp:
            content = body
            headers = {"content-type": "image/png"}

            def raise_for_status(self):
                return None

        class FakeAsyncClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, headers=None):
                return FakeResp()

        with patch("backend.api.mediawiki_routes.httpx.AsyncClient", FakeAsyncClient):
            with patch("backend.api.mediawiki_routes.get_mediawiki_client") as mock_get:
                mock_c = MagicMock()
                mock_get.return_value = mock_c
                response = client.post(
                    "/api/mediawiki/upload-image",
                    json={"image_url": "https://cdn.example.com/path/image.png"},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == expected_name
        assert data["wikitext"] == f"[[File:{expected_name}]]"
        call_args = mock_c.upload_file.call_args[0]
        assert call_args[0] == expected_name

