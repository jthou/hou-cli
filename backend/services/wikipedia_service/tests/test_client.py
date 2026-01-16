"""Wikipedia 服务客户端测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import wikipedia
import wikipedia.exceptions

from backend.services.wikipedia_service.client import (
    WikipediaService,
    WikipediaServiceError
)
from backend.services.wikipedia_service.models import (
    WikipediaSearchResult,
    WikipediaPageResult,
    WikipediaSearchResponse
)


class TestWikipediaServiceInitialization:
    """测试 WikipediaService 初始化"""
    
    def test_init_default_language(self):
        """测试默认语言初始化"""
        with patch('wikipedia.set_lang') as mock_set_lang:
            service = WikipediaService()
            assert service.language == "zh"
            mock_set_lang.assert_called_once_with("zh")
    
    def test_init_custom_language(self):
        """测试自定义语言初始化"""
        with patch('wikipedia.set_lang') as mock_set_lang:
            service = WikipediaService(language="en")
            assert service.language == "en"
            mock_set_lang.assert_called_once_with("en")


class TestWikipediaServiceSearch:
    """测试 WikipediaService 搜索功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_search_success(self, service):
        """测试成功搜索"""
        # Mock Wikipedia 搜索结果
        mock_search_results = ["Python (programming language)", "Python (snake)", "Monty Python"]
        
        # Mock 页面对象
        mock_page = MagicMock()
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        mock_page.pageid = 12345
        
        with patch('wikipedia.search', return_value=mock_search_results):
            with patch('wikipedia.page', return_value=mock_page):
                result = service.search("Python", num_results=3)
                
                assert isinstance(result, WikipediaSearchResponse)
                assert len(result.results) == 3
                assert result.query == "Python"
                assert result.language == "zh"
                assert result.search_time is not None
                
                # 验证第一个结果
                assert result.results[0].title == "Python (programming language)"
                assert result.results[0].url == "https://zh.wikipedia.org/wiki/Python"
                assert result.results[0].page_id == 12345
    
    def test_search_with_language_override(self, service):
        """测试临时切换语言搜索"""
        with patch('wikipedia.set_lang') as mock_set_lang:
            with patch('wikipedia.search', return_value=[]):
                service.search("test", language="en")
                
                # 应该先切换到 en，然后恢复为 zh
                assert mock_set_lang.call_count >= 2
                mock_set_lang.assert_any_call("en")
                mock_set_lang.assert_any_call("zh")
    
    def test_search_handles_page_error(self, service):
        """测试处理页面不存在的情况"""
        mock_search_results = ["Valid Page", "Invalid Page"]
        
        mock_valid_page = MagicMock()
        mock_valid_page.url = "https://example.com/valid"
        mock_valid_page.pageid = 1
        
        with patch('wikipedia.search', return_value=mock_search_results):
            with patch('wikipedia.page') as mock_page:
                # 第一个页面成功，第二个页面不存在
                mock_page.side_effect = [
                    mock_valid_page,
                    wikipedia.exceptions.PageError("Invalid Page")
                ]
                
                result = service.search("test")
                
                # 应该只返回有效的页面
                assert len(result.results) == 1
                assert result.results[0].title == "Valid Page"
    
    def test_search_handles_disambiguation(self, service):
        """测试处理消歧义页面"""
        mock_search_results = ["Python"]
        
        # 创建消歧义错误
        disambiguation_error = wikipedia.exceptions.DisambiguationError(
            "Python",
            ["Python (programming language)", "Python (snake)"]
        )
        
        mock_page = MagicMock()
        mock_page.url = "https://example.com/python"
        mock_page.pageid = 1
        
        with patch('wikipedia.search', return_value=mock_search_results):
            with patch('wikipedia.page') as mock_page_func:
                # 第一次调用返回消歧义错误，第二次返回有效页面
                mock_page_func.side_effect = [disambiguation_error, mock_page]
                
                result = service.search("Python")
                
                # 应该使用第一个选项
                assert len(result.results) == 1
                assert result.results[0].title == "Python (programming language)"
    
    def test_search_json_error(self, service):
        """测试处理 JSON 解析错误"""
        with patch('wikipedia.search', side_effect=ValueError("Expecting value: line 1 column 1")):
            with pytest.raises(WikipediaServiceError) as exc_info:
                service.search("test")
            assert "JSON" in str(exc_info.value) or "API 返回无效响应" in str(exc_info.value)
    
    def test_search_general_error(self, service):
        """测试处理一般错误"""
        with patch('wikipedia.search', side_effect=Exception("Network error")):
            with pytest.raises(WikipediaServiceError) as exc_info:
                service.search("test")
            assert "搜索失败" in str(exc_info.value)


class TestWikipediaServiceGetPage:
    """测试 WikipediaService 获取页面功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_page_success_summary_only(self, service):
        """测试成功获取页面（仅摘要）"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.summary = "Python is a programming language"
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        mock_page.pageid = 12345
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page("Python", summary_only=True)
            
            assert isinstance(result, WikipediaPageResult)
            assert result.title == "Python"
            assert result.summary == "Python is a programming language"
            assert result.content is None  # summary_only=True
            assert result.url == "https://zh.wikipedia.org/wiki/Python"
            assert result.page_id == 12345
    
    def test_get_page_success_full_content(self, service):
        """测试成功获取页面（完整内容）"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.summary = "Summary"
        mock_page.content = "Full content here"
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        mock_page.pageid = 12345
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page("Python", summary_only=False)
            
            assert result.content == "Full content here"
    
    def test_get_page_disambiguation(self, service):
        """测试获取消歧义页面"""
        disambiguation_error = wikipedia.exceptions.DisambiguationError(
            "Python",
            ["Python (programming language)"]
        )
        
        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.summary = "Summary"
        mock_page.url = "https://example.com/python"
        mock_page.pageid = 1
        
        with patch('wikipedia.page') as mock_page_func:
            mock_page_func.side_effect = [disambiguation_error, mock_page]
            
            result = service.get_page("Python")
            
            assert result.title == "Python (programming language)"
    
    def test_get_page_not_found(self, service):
        """测试页面不存在"""
        with patch('wikipedia.page', side_effect=wikipedia.exceptions.PageError("Not found")):
            with pytest.raises(WikipediaServiceError) as exc_info:
                service.get_page("NonExistentPage")
            assert "页面不存在" in str(exc_info.value)
    
    def test_get_page_json_error(self, service):
        """测试 JSON 解析错误"""
        with patch('wikipedia.page', side_effect=ValueError("Expecting value: line 1")):
            with pytest.raises(WikipediaServiceError) as exc_info:
                service.get_page("test")
            assert "JSON" in str(exc_info.value) or "API 返回无效响应" in str(exc_info.value)


class TestWikipediaServiceGetPageLinks:
    """测试 WikipediaService 获取页面链接功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_page_links_success(self, service):
        """测试成功获取页面链接"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.links = ["Programming", "Language", "Computer Science"]
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page_links("Python")
            
            assert result.title == "Python"
            assert len(result.links) == 3
            assert result.links_count == 3
            assert "Programming" in result.links
    
    def test_get_page_links_with_limit(self, service):
        """测试带限制的获取页面链接"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.links = ["Link1", "Link2", "Link3", "Link4", "Link5"]
        mock_page.url = "https://example.com"
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page_links("Python", limit=3)
            
            assert len(result.links) == 3
            assert result.links_count == 3


class TestWikipediaServiceGetPageCategories:
    """测试 WikipediaService 获取页面分类功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_page_categories_success(self, service):
        """测试成功获取页面分类"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.categories = ["Programming languages", "Python programming language family"]
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page_categories("Python")
            
            assert result.title == "Python"
            assert len(result.categories) == 2
            assert result.categories_count == 2
            assert "Programming languages" in result.categories


class TestWikipediaServiceGetPageImages:
    """测试 WikipediaService 获取页面图片功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_page_images_success(self, service):
        """测试成功获取页面图片"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.png"
        ]
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page_images("Python")
            
            assert result.title == "Python"
            assert len(result.images) == 2
            assert result.images_count == 2


class TestWikipediaServiceGetPageReferences:
    """测试 WikipediaService 获取页面引用功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_page_references_success(self, service):
        """测试成功获取页面引用"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.references = ["Ref1", "Ref2", "Ref3"]
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        
        with patch('wikipedia.page', return_value=mock_page):
            result = service.get_page_references("Python")
            
            assert result.title == "Python"
            assert len(result.references) == 3
            assert result.references_count == 3


class TestWikipediaServiceGetRelatedPages:
    """测试 WikipediaService 获取相关页面功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('wikipedia.set_lang'):
            return WikipediaService(language="zh")
    
    def test_get_related_pages_success(self, service):
        """测试成功获取相关页面"""
        mock_page = MagicMock()
        mock_page.title = "Python"
        mock_page.links = ["Programming", "Language"]
        mock_page.url = "https://zh.wikipedia.org/wiki/Python"
        
        mock_link_page1 = MagicMock()
        mock_link_page1.url = "https://example.com/programming"
        mock_link_page1.pageid = 1
        
        mock_link_page2 = MagicMock()
        mock_link_page2.url = "https://example.com/language"
        mock_link_page2.pageid = 2
        
        with patch('wikipedia.page') as mock_page_func:
            # 第一次调用返回主页面，后续调用返回链接页面
            mock_page_func.side_effect = [mock_page, mock_link_page1, mock_link_page2]
            
            result = service.get_related_pages("Python", limit=2)
            
            assert isinstance(result, WikipediaSearchResponse)
            assert len(result.results) == 2
            assert result.query == "related to Python"

