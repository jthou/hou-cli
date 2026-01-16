"""Google 搜索服务客户端测试"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import httpx

from backend.services.google_search_service.client import (
    GoogleSearchService,
    GoogleSearchServiceError
)
from backend.services.google_search_service.models import (
    GoogleSearchResult,
    GoogleSearchResponse
)


class TestGoogleSearchServiceInitialization:
    """测试 GoogleSearchService 初始化"""
    
    def test_init_with_env_vars(self):
        """测试从环境变量初始化"""
        with patch.dict(os.environ, {
            'GOOGLE_SEARCH_API_KEY': 'test_api_key',
            'GOOGLE_SEARCH_ENGINE_ID': 'test_engine_id'
        }):
            service = GoogleSearchService()
            assert service.api_key == 'test_api_key'
            assert service.engine_id == 'test_engine_id'
            assert service.client is not None
    
    def test_init_with_parameters(self):
        """测试通过参数初始化"""
        service = GoogleSearchService(
            api_key='param_api_key',
            engine_id='param_engine_id'
        )
        assert service.api_key == 'param_api_key'
        assert service.engine_id == 'param_engine_id'
    
    def test_init_missing_api_key(self):
        """测试缺少 API Key 时抛出错误"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                GoogleSearchService()
            assert "GOOGLE_SEARCH_API_KEY" in str(exc_info.value)
    
    def test_init_missing_engine_id(self):
        """测试缺少 Engine ID 时抛出错误"""
        with patch.dict(os.environ, {'GOOGLE_SEARCH_API_KEY': 'test_key'}, clear=False):
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                GoogleSearchService()
            assert "GOOGLE_SEARCH_ENGINE_ID" in str(exc_info.value)


class TestGoogleSearchServiceSearch:
    """测试 GoogleSearchService 搜索功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return GoogleSearchService(
            api_key='test_api_key',
            engine_id='test_engine_id'
        )
    
    @pytest.mark.asyncio
    async def test_search_success(self, service):
        """测试成功搜索"""
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Title 1",
                    "link": "https://example.com/1",
                    "snippet": "Test snippet 1",
                    "displayLink": "example.com"
                },
                {
                    "title": "Test Title 2",
                    "link": "https://example.com/2",
                    "snippet": "Test snippet 2"
                }
            ],
            "searchInformation": {
                "totalResults": "1000"
            }
        }
        mock_response.raise_for_status = Mock()
        
        # Mock HTTP 客户端
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await service.search("test query", num_results=2)
            
            # 验证结果
            assert isinstance(result, GoogleSearchResponse)
            assert len(result.results) == 2
            assert result.total_results == 1000
            assert result.query == "test query"
            assert result.search_time is not None
            
            # 验证第一个结果
            assert result.results[0].title == "Test Title 1"
            assert result.results[0].link == "https://example.com/1"
            assert result.results[0].snippet == "Test snippet 1"
            assert result.results[0].display_link == "example.com"
            
            # 验证请求参数
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == service.API_BASE_URL
            assert call_args[1]['params']['q'] == "test query"
            assert call_args[1]['params']['num'] == 2
    
    @pytest.mark.asyncio
    async def test_search_with_language(self, service):
        """测试带语言参数的搜索"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            await service.search("test", language="zh-CN")
            
            call_args = mock_get.call_args
            assert call_args[1]['params'].get('lr') == 'lang_zh-CN'
    
    @pytest.mark.asyncio
    async def test_search_with_region(self, service):
        """测试带地区参数的搜索"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            await service.search("test", region="cn")
            
            call_args = mock_get.call_args
            assert call_args[1]['params'].get('gl') == 'cn'
    
    @pytest.mark.asyncio
    async def test_search_num_results_limit(self, service):
        """测试结果数量限制"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # 测试超过最大限制（应该限制到 10）
            await service.search("test", num_results=20)
            call_args = mock_get.call_args
            assert call_args[1]['params']['num'] == 10
            
            # 测试小于最小限制（应该限制到 1）
            await service.search("test", num_results=0)
            call_args = mock_get.call_args
            assert call_args[1]['params']['num'] == 1
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self, service):
        """测试空搜索结果"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [],
            "searchInformation": {}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await service.search("test")
            
            assert len(result.results) == 0
            # 注意：根据实现，当 searchInformation 存在但没有 totalResults 时，会使用默认值 "0" 并转换为 int(0)
            # 只有当 searchInformation 不存在时，total_results 才是 None
            assert result.total_results == 0
    
    @pytest.mark.asyncio
    async def test_search_http_error_400(self, service):
        """测试 HTTP 400 错误"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        
        error = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = error
            
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                await service.search("test")
            assert "400" in str(exc_info.value)
            assert "请求参数错误" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_http_error_403(self, service):
        """测试 HTTP 403 错误（API Key 无效）"""
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        error = httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = error
            
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                await service.search("test")
            assert "403" in str(exc_info.value)
            assert "API 密钥无效" in str(exc_info.value) or "配额" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_http_error_429(self, service):
        """测试 HTTP 429 错误（请求频率过高）"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        
        error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = error
            
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                await service.search("test")
            assert "429" in str(exc_info.value)
            assert "请求频率过高" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_network_error(self, service):
        """测试网络错误"""
        error = httpx.RequestError("Network error", request=MagicMock())
        
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = error
            
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                await service.search("test")
            assert "网络错误" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_general_exception(self, service):
        """测试一般异常"""
        with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            with pytest.raises(GoogleSearchServiceError) as exc_info:
                await service.search("test")
            assert "搜索失败" in str(exc_info.value)


class TestGoogleSearchServiceClose:
    """测试 GoogleSearchService 关闭功能"""
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭客户端"""
        service = GoogleSearchService(
            api_key='test_api_key',
            engine_id='test_engine_id'
        )
        
        with patch.object(service.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await service.close()
            mock_close.assert_called_once()

