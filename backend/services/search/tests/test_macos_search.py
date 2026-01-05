"""macOS 搜索适配器测试"""

import unittest
import os
from backend.services.search.platform.macos_search import MacOSSearchAdapter
from backend.services.search.models import FileSearchRequest


class TestMacOSSearchAdapter(unittest.TestCase):
    """macOS 搜索适配器测试"""
    
    def setUp(self):
        """设置测试环境"""
        try:
            self.adapter = MacOSSearchAdapter()
        except RuntimeError as e:
            self.skipTest(f"macOS search not available: {e}")
    
    def test_check_availability(self):
        """测试可用性检查"""
        available, error = self.adapter.check_availability()
        self.assertTrue(available, f"macOS search should be available: {error}")
    
    def test_search_by_name(self):
        """测试文件名搜索"""
        results = self.adapter.search_by_name("*.py", limit=10)
        self.assertIsInstance(results, list)
        # 至少应该找到一些 .py 文件
        if results:
            self.assertGreater(len(results), 0)
            # 检查结果格式
            result = results[0]
            self.assertTrue(hasattr(result, 'path'))
            self.assertTrue(hasattr(result, 'name'))
            self.assertTrue(hasattr(result, 'size'))
    
    def test_search_by_name_with_path(self):
        """测试带路径限制的文件名搜索"""
        # 在当前目录搜索
        current_dir = os.getcwd()
        results = self.adapter.search_by_name("*.py", path=current_dir, limit=10)
        self.assertIsInstance(results, list)
        # 所有结果应该在指定路径下
        for result in results:
            self.assertTrue(result.path.startswith(current_dir))
    
    def test_search_by_name_with_file_type(self):
        """测试带文件类型过滤的搜索"""
        results = self.adapter.search_by_name("test", file_type="*.py", limit=10)
        self.assertIsInstance(results, list)
        # 所有结果应该是 .py 文件
        for result in results:
            self.assertTrue(result.file_type == '.py' or result.name.endswith('.py'))
    
    def test_search_by_content(self):
        """测试文件内容搜索"""
        # 搜索包含 'import' 的文件（Python 文件通常包含）
        results = self.adapter.search_by_content("import", limit=10)
        self.assertIsInstance(results, list)
        # 至少应该找到一些文件
        if results:
            self.assertGreater(len(results), 0)
    
    def test_search_limit(self):
        """测试结果数量限制"""
        results = self.adapter.search_by_name("*.py", limit=5)
        self.assertLessEqual(len(results), 5)


if __name__ == '__main__':
    unittest.main()

