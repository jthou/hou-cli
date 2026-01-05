"""查询构建器测试"""

import unittest
from datetime import datetime, timedelta
from backend.services.search.query_builder import QueryBuilder


class TestQueryBuilder(unittest.TestCase):
    """查询构建器测试"""
    
    def test_build_name_query(self):
        """测试构建文件名查询"""
        builder = QueryBuilder()
        query = builder.build_name_query("*.py")
        self.assertIn("kMDItemFSName", query)
        self.assertIn("*.py", query)
    
    def test_build_content_query(self):
        """测试构建内容查询"""
        builder = QueryBuilder()
        query = builder.build_content_query("test")
        self.assertIn("kMDItemTextContent", query)
        self.assertIn("test", query)
    
    def test_name_contains(self):
        """测试文件名包含条件"""
        builder = QueryBuilder()
        query = builder.name_contains("test").build()
        self.assertIn("kMDItemFSName", query)
        self.assertIn("test", query)
    
    def test_file_type(self):
        """测试文件类型过滤"""
        builder = QueryBuilder()
        query = builder.file_type(".py").build()
        self.assertIn(".py", query)
    
    def test_size_conditions(self):
        """测试文件大小条件"""
        builder = QueryBuilder()
        query = builder.size_greater_than(1024).build()
        self.assertIn("kMDItemFSSize", query)
        self.assertIn("1024", query)
        
        query = builder.reset().size_less_than(2048).build()
        self.assertIn("2048", query)
        
        query = builder.reset().size_between(1024, 2048).build()
        self.assertIn("1024", query)
        self.assertIn("2048", query)
    
    def test_modified_time_conditions(self):
        """测试修改时间条件"""
        builder = QueryBuilder()
        date = datetime.now() - timedelta(days=7)
        query = builder.modified_after(date).build()
        self.assertIn("kMDItemFSContentChangeDate", query)
        
        query = builder.reset().modified_in_last_days(7).build()
        self.assertIn("kMDItemFSContentChangeDate", query)
    
    def test_combined_conditions(self):
        """测试组合条件"""
        builder = QueryBuilder()
        query = builder.name_contains("test").file_type(".py").build()
        self.assertIn("test", query)
        self.assertIn(".py", query)
        # 应该包含 AND 连接符
        self.assertIn("&&", query)
    
    def test_and_or_conditions(self):
        """测试 AND/OR 条件"""
        builder = QueryBuilder()
        query = builder.name_contains("test").or_condition().file_type(".py").build()
        self.assertIn("||", query)
        
        query = builder.reset().name_contains("test").and_condition().file_type(".py").build()
        self.assertIn("&&", query)
    
    def test_escape_special_characters(self):
        """测试特殊字符转义"""
        builder = QueryBuilder()
        query = builder.name_contains("test'file").build()
        # 单引号应该被转义
        self.assertIn("\\'", query)
    
    def test_validate(self):
        """测试查询验证"""
        builder = QueryBuilder()
        # 空查询应该验证失败
        valid, error = builder.validate()
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        
        # 有条件的查询应该验证通过
        builder.name_contains("test")
        valid, error = builder.validate()
        self.assertTrue(valid)
    
    def test_reset(self):
        """测试重置构建器"""
        builder = QueryBuilder()
        builder.name_contains("test").file_type(".py")
        self.assertGreater(len(builder.conditions), 0)
        
        builder.reset()
        self.assertEqual(len(builder.conditions), 0)


if __name__ == '__main__':
    unittest.main()

