"""MediaWiki 客户端测试"""

import unittest
import os
from backend.services.mediawiki.client import MediaWikiClientService, MediaWikiClientError


class TestMediaWikiClient(unittest.TestCase):
    """MediaWiki 客户端测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 检查是否配置了 MediaWiki
        url = os.getenv("MEDIAWIKI_URL")
        if not url:
            self.skipTest("MEDIAWIKI_URL not configured")
        
        try:
            self.client = MediaWikiClientService()
            self.client.connect()
        except Exception as e:
            self.skipTest(f"MediaWiki connection failed: {e}")
    
    def test_connection(self):
        """测试连接"""
        self.assertTrue(self.client._connected)
        self.assertIsNotNone(self.client.site)
    
    def test_search_pages(self):
        """测试搜索页面"""
        results = self.client.search_pages("test", limit=5)
        self.assertIsInstance(results, list)
        # 至少应该返回一些结果（即使为空列表）
        if results:
            result = results[0]
            self.assertTrue(hasattr(result, 'title'))
            self.assertTrue(hasattr(result, 'snippet'))
    
    def test_get_page(self):
        """测试获取页面"""
        # 先搜索一个页面
        search_results = self.client.search_pages("test", limit=1)
        if search_results:
            title = search_results[0].title
            page = self.client.get_page(title)
            self.assertIsNotNone(page)
            self.assertEqual(page.title, title)
            self.assertTrue(hasattr(page, 'content'))
            self.assertTrue(hasattr(page, 'categories'))
    
    def test_get_page_not_found(self):
        """测试获取不存在的页面"""
        page = self.client.get_page("NonExistentPage12345")
        self.assertIsNone(page)
    
    def test_get_page_info(self):
        """测试获取页面信息"""
        search_results = self.client.search_pages("test", limit=1)
        if search_results:
            title = search_results[0].title
            info = self.client.get_page_info(title)
            self.assertIsNotNone(info)
            self.assertIn("title", info)
            self.assertIn("revision_id", info)


if __name__ == '__main__':
    unittest.main()

