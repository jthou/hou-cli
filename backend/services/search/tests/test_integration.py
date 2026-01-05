"""集成测试"""

import unittest
import os
from backend.services.search import FileSearchService, FileSearchRequest


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        try:
            self.service = FileSearchService()
        except Exception as e:
            self.skipTest(f"FileSearchService not available: {e}")
    
    def test_basic_search_flow(self):
        """测试基本搜索流程"""
        request = FileSearchRequest(
            query="*.py",
            limit=10
        )
        
        response = self.service.search(request)
        
        # 检查响应格式
        self.assertIsNotNone(response)
        self.assertIsInstance(response.results, list)
        self.assertGreaterEqual(response.total, 0)
        self.assertEqual(response.limit, 10)
        self.assertIsNotNone(response.search_time_ms)
        self.assertIn(response.search_type, ["name", "content"])
        self.assertEqual(response.platform, "macos")
    
    def test_search_with_path(self):
        """测试带路径限制的搜索"""
        current_dir = os.getcwd()
        request = FileSearchRequest(
            query="*.py",
            path=current_dir,
            limit=10
        )
        
        response = self.service.search(request)
        
        # 所有结果应该在指定路径下
        for result in response.results:
            self.assertTrue(result.path.startswith(current_dir))
    
    def test_search_with_file_type(self):
        """测试带文件类型过滤的搜索"""
        request = FileSearchRequest(
            query="test",
            file_type="*.py",
            limit=10
        )
        
        response = self.service.search(request)
        
        # 所有结果应该是 .py 文件
        for result in response.results:
            self.assertTrue(result.file_type == '.py' or result.name.endswith('.py'))
    
    def test_search_with_sorting(self):
        """测试带排序的搜索"""
        request = FileSearchRequest(
            query="*.py",
            limit=10,
            sort_by="size",
            sort_order="desc"
        )
        
        response = self.service.search(request)
        
        # 检查结果是否按大小降序排列
        if len(response.results) > 1:
            sizes = [r.size for r in response.results]
            self.assertEqual(sizes, sorted(sizes, reverse=True))
    
    def test_search_with_pagination(self):
        """测试分页"""
        request1 = FileSearchRequest(
            query="*.py",
            limit=5,
            offset=0
        )
        
        request2 = FileSearchRequest(
            query="*.py",
            limit=5,
            offset=5
        )
        
        response1 = self.service.search(request1)
        response2 = self.service.search(request2)
        
        # 检查分页是否正确
        self.assertEqual(len(response1.results), min(5, response1.total))
        self.assertEqual(len(response2.results), min(5, max(0, response1.total - 5)))
        
        # 结果不应该重复
        if response1.results and response2.results:
            paths1 = {r.path for r in response1.results}
            paths2 = {r.path for r in response2.results}
            self.assertEqual(len(paths1 & paths2), 0, "分页结果不应该重复")
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        service_with_cache = FileSearchService(cache_enabled=True, cache_ttl=300)
        
        request = FileSearchRequest(
            query="*.py",
            limit=10
        )
        
        # 第一次搜索
        response1 = service_with_cache.search(request)
        time1 = response1.search_time_ms
        
        # 第二次搜索（应该使用缓存）
        response2 = service_with_cache.search(request)
        time2 = response2.search_time_ms
        
        # 结果应该一致
        self.assertEqual(response1.total, response2.total)
        # 缓存搜索应该更快（或至少不慢很多）
        self.assertLessEqual(time2, time1 * 1.1)  # 允许 10% 的误差
    
    def test_concurrent_search(self):
        """测试并发搜索"""
        requests = [
            FileSearchRequest(query="*.py", limit=10),
            FileSearchRequest(query="*.md", limit=10),
            FileSearchRequest(query="*.txt", limit=10),
        ]
        
        responses = self.service.search_concurrent(requests, max_workers=3)
        
        # 应该返回与请求数量相同的结果
        self.assertEqual(len(responses), len(requests))
        
        # 每个响应都应该是有效的
        for response in responses:
            self.assertIsNotNone(response)
            self.assertIsInstance(response.results, list)


if __name__ == '__main__':
    unittest.main()

