"""MediaWiki 工具测试"""

import unittest
import os
from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool


class TestMediaWikiTool(unittest.TestCase):
    """MediaWiki 工具测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 检查是否配置了 MediaWiki
        url = os.getenv("MEDIAWIKI_URL")
        if not url:
            self.skipTest("MEDIAWIKI_URL not configured")
        
        try:
            self.tool = MediaWikiTool()
        except Exception as e:
            self.skipTest(f"MediaWiki tool initialization failed: {e}")
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        self.assertEqual(self.tool.name, "mediawiki")
        self.assertGreater(len(self.tool.parameters), 0)
    
    def test_search_operation(self):
        """测试搜索操作"""
        result = self.tool.execute(
            operation="search",
            query="test",
            limit=5
        )
        
        self.assertIsInstance(result, type(self.tool.execute.__annotations__['return']))
        if result.success:
            self.assertIn("results", result.data)
            self.assertIn("count", result.data)
    
    def test_read_operation(self):
        """测试读取操作"""
        # 先搜索一个页面
        search_result = self.tool.execute(
            operation="search",
            query="test",
            limit=1
        )
        
        if search_result.success and search_result.data.get("count", 0) > 0:
            title = search_result.data["results"][0]["title"]
            
            read_result = self.tool.execute(
                operation="read",
                title=title
            )
            
            if read_result.success:
                self.assertIn("content", read_result.data)
                self.assertIn("title", read_result.data)
    
    def test_info_operation(self):
        """测试获取信息操作"""
        # 先搜索一个页面
        search_result = self.tool.execute(
            operation="search",
            query="test",
            limit=1
        )
        
        if search_result.success and search_result.data.get("count", 0) > 0:
            title = search_result.data["results"][0]["title"]
            
            info_result = self.tool.execute(
                operation="info",
                title=title
            )
            
            if info_result.success:
                self.assertIn("info", info_result.data)


if __name__ == '__main__':
    unittest.main()

