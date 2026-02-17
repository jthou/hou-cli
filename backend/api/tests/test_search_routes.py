"""搜索路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.services.file_search_service.models import FileSearchResponse, FileSearchResult
from backend.services.mediawiki_client_service.models import UnifiedSearchResult


class TestSearchRoutes:
    """搜索路由测试类"""
    
    @pytest.fixture
    def mock_search_response(self):
        """创建模拟搜索响应"""
        return FileSearchResponse(
            results=[
                FileSearchResult(
                    path="/test/file1.py",
                    name="file1.py",
                    size=1024,
                    modified_time=1234567890.0,
                    file_type=".py"
                ),
                FileSearchResult(
                    path="/test/file2.py",
                    name="file2.py",
                    size=2048,
                    modified_time=1234567891.0,
                    file_type=".py"
                )
            ],
            total=2,
            limit=100,
            offset=0,
            has_more=False,
            search_type="name",
            platform="test"
        )
    
    def test_search_files_success(self, client, mock_search_response):
        """测试文件搜索成功"""
        with patch('backend.api.search_routes.get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = MagicMock(return_value=mock_search_response)
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/files?query=test")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["name"] == "file1.py"
    
    def test_search_files_with_filters(self, client, mock_search_response):
        """测试带过滤条件的文件搜索"""
        with patch('backend.api.search_routes.get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = MagicMock(return_value=mock_search_response)
            mock_get_service.return_value = mock_service
            
            response = client.get(
                "/api/search/files?query=test&path=/test&file_type=*.py&content_search=true&limit=50"
            )
            
            assert response.status_code == 200
            # 验证搜索服务被正确调用
            mock_service.search.assert_called_once()
            call_args = mock_service.search.call_args[0][0]
            assert call_args.query == "test"
            assert call_args.path == "/test"
            assert call_args.file_type == "*.py"
            assert call_args.content_search is True
            assert call_args.limit == 50
    
    def test_search_files_invalid_limit(self, client):
        """测试无效的 limit 参数"""
        response = client.get("/api/search/files?query=test&limit=0")
        
        assert response.status_code == 400
        assert "limit must be between 1 and 1000" in response.json()["detail"]
    
    def test_search_files_invalid_limit_too_large(self, client):
        """测试 limit 参数过大"""
        response = client.get("/api/search/files?query=test&limit=2000")
        
        assert response.status_code == 400
    
    def test_search_files_invalid_offset(self, client):
        """测试无效的 offset 参数"""
        response = client.get("/api/search/files?query=test&offset=-1")
        
        assert response.status_code == 400
        assert "offset must be >= 0" in response.json()["detail"]
    
    def test_search_files_error(self, client):
        """测试文件搜索错误处理"""
        with patch('backend.api.search_routes.get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = MagicMock(side_effect=Exception("搜索失败"))
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/files?query=test")
            
            assert response.status_code == 500
            assert "搜索失败" in response.json()["detail"]
    
    def test_check_search_availability_success(self, client):
        """测试检查搜索可用性成功"""
        with patch('backend.api.search_routes.get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.check_availability = MagicMock(return_value=(True, None))
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/availability")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["available"] is True
            assert data["error"] is None
    
    def test_check_search_availability_unavailable(self, client):
        """测试搜索不可用"""
        with patch('backend.api.search_routes.get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.check_availability = MagicMock(return_value=(False, "搜索工具未安装"))
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/availability")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["available"] is False
            assert "搜索工具未安装" in data["error"]
    
    def test_unified_search_success(self, client):
        """测试统一搜索成功"""
        with patch('backend.api.search_routes.get_unified_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_results = [
                UnifiedSearchResult(
                    source="mediawiki",
                    title="测试页面",
                    content="这是测试内容",
                    score=0.95,
                    url="http://example.com/测试页面",
                    metadata={}
                ),
                UnifiedSearchResult(
                    source="knowledge_base",
                    title="知识库条目",
                    content="知识库内容",
                    score=0.85,
                    url=None,
                    metadata={}
                )
            ]
            mock_service.search = MagicMock(return_value=mock_results)
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/unified?query=测试&limit=20")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["source"] == "mediawiki"
    
    def test_unified_search_with_sources(self, client):
        """测试带来源过滤的统一搜索"""
        with patch('backend.api.search_routes.get_unified_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = MagicMock(return_value=[])
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/search/unified?query=测试&limit=20&sources=mediawiki,knowledge_base")
            
            assert response.status_code == 200
            mock_service.search.assert_called_once()
            call_args = mock_service.search.call_args
            assert call_args[0][0] == "测试"
            assert call_args[1]["limit"] == 20
            assert "mediawiki" in call_args[1]["sources"]
            assert "knowledge_base" in call_args[1]["sources"]
    
    def test_unified_search_invalid_limit(self, client):
        """测试统一搜索无效的 limit"""
        response = client.get("/api/search/unified?query=测试&limit=0")
        
        assert response.status_code == 400
    
    def test_unified_search_limit_too_large(self, client):
        """测试统一搜索 limit 过大"""
        response = client.get("/api/search/unified?query=测试&limit=200")
        
        assert response.status_code == 400

