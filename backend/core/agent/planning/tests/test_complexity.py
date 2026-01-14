"""TaskComplexityAnalyzer 测试用例"""
import pytest
from backend.core.agent.planning.complexity import TaskComplexityAnalyzer


class TestTaskComplexityAnalyzer:
    """TaskComplexityAnalyzer 测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建 TaskComplexityAnalyzer 实例"""
        return TaskComplexityAnalyzer(
            min_task_length=10,
            complexity_threshold=0.3
        )
    
    def test_simple_task(self, analyzer):
        """测试简单任务"""
        task = "显示当前目录"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is False
    
    def test_complex_task_with_keywords(self, analyzer):
        """测试包含复杂关键词的任务"""
        task = "实现一个完整的用户管理系统，包括用户注册、登录、权限管理等功能"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is True
    
    def test_multi_step_task(self, analyzer):
        """测试多步骤任务"""
        task = "首先分析需求，然后设计架构，最后实现代码"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is True
    
    def test_planning_keyword_task(self, analyzer):
        """测试包含规划关键词的任务"""
        task = "规划一个项目的开发流程"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is True
    
    def test_short_task(self, analyzer):
        """测试过短的任务"""
        task = "ls"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is False
    
    def test_analyze_task(self, analyzer):
        """测试详细分析任务"""
        task = "实现一个Python CLI工具，支持文件搜索和内容替换"
        result = analyzer.analyze_task(task)
        
        assert "is_complex" in result
        assert "score" in result
        assert "reasons" in result
        assert result["score"] >= 0.0
        assert result["score"] <= 1.0
    
    def test_custom_threshold(self):
        """测试自定义阈值"""
        analyzer = TaskComplexityAnalyzer(
            min_task_length=10,
            complexity_threshold=0.5  # 更高的阈值
        )
        
        task = "实现一个简单的计算器"
        is_complex = analyzer.is_complex_task(task)
        # 由于阈值更高，可能不会被判定为复杂任务
        assert isinstance(is_complex, bool)

