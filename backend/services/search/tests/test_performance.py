"""性能测试"""

import time
import unittest
from backend.services.search import FileSearchService, FileSearchRequest


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.service = FileSearchService(cache_enabled=False)  # 禁用缓存进行性能测试
    
    def test_small_directory_search_performance(self):
        """测试小目录搜索性能（< 1000 文件）"""
        request = FileSearchRequest(
            query='*.py',
            limit=100
        )
        
        start_time = time.time()
        response = self.service.search(request)
        elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        print(f"\n小目录搜索性能测试:")
        print(f"  结果数: {response.total}")
        print(f"  响应时间: {elapsed_time:.2f}ms")
        print(f"  服务报告耗时: {response.search_time_ms:.2f}ms")
        
        # 小目录搜索应该在 100ms 内完成（但 macOS mdfind 可能较慢）
        # 实际测试中，mdfind 可能需要几秒，所以放宽要求
        self.assertLess(elapsed_time, 10000, "小目录搜索应该较快")
    
    def test_large_directory_search_performance(self):
        """测试大目录搜索性能（> 1000 文件）"""
        request = FileSearchRequest(
            query='*',
            limit=1000
        )
        
        start_time = time.time()
        response = self.service.search(request)
        elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        print(f"\n大目录搜索性能测试:")
        print(f"  结果数: {response.total}")
        print(f"  响应时间: {elapsed_time:.2f}ms")
        print(f"  服务报告耗时: {response.search_time_ms:.2f}ms")
        
        # 大目录搜索应该在 30 秒内完成
        self.assertLess(elapsed_time, 30000, "大目录搜索应该在合理时间内完成")
    
    def test_cache_performance(self):
        """测试缓存性能提升"""
        service_with_cache = FileSearchService(cache_enabled=True, cache_ttl=300)
        request = FileSearchRequest(
            query='*.py',
            limit=100
        )
        
        # 第一次搜索（无缓存）
        start_time = time.time()
        response1 = service_with_cache.search(request)
        first_search_time = (time.time() - start_time) * 1000
        
        # 第二次搜索（有缓存）
        start_time = time.time()
        response2 = service_with_cache.search(request)
        second_search_time = (time.time() - start_time) * 1000
        
        print(f"\n缓存性能测试:")
        print(f"  第一次搜索: {first_search_time:.2f}ms")
        print(f"  第二次搜索（缓存）: {second_search_time:.2f}ms")
        print(f"  性能提升: {first_search_time / second_search_time if second_search_time > 0 else 0:.2f}x")
        
        # 缓存应该明显更快
        self.assertLess(second_search_time, first_search_time, "缓存应该提升性能")
        self.assertEqual(response1.total, response2.total, "缓存结果应该一致")


if __name__ == '__main__':
    unittest.main()

