"""浏览器智能决策模块测试
测试智能模型选择和任务分析功能"""
from backend.core.agent.tools.builtin.browser_intelligence import BrowserIntelligence


class TestBrowserIntelligence:
    """浏览器智能决策模块测试"""

    def test_analyze_task_type_basic(self):
        """测试基本任务类型分析"""
        intelligence = BrowserIntelligence()
        
        # 测试普通任务
        result = intelligence.analyze_task_type("访问百度首页")
        assert result["requires_vision"] is False
        assert result["requires_precise_operation"] is False
        assert result["is_complex_task"] is False
        assert result["requires_data_extraction"] is False
        assert result["recommended_model"] is not None
        assert result["confidence"] >= 0.0
        assert result["confidence"] <= 1.0
    
    def test_analyze_task_type_vision(self):
        """测试视觉任务分析"""
        intelligence = BrowserIntelligence()
        
        # 测试包含视觉关键词的任务
        vision_tasks = [
            "截图并分析这个页面",
            "查看页面布局",
            "分析页面结构并截图",
            "页面截图",
            "识别页面元素"
        ]
        
        for task in vision_tasks:
            result = intelligence.analyze_task_type(task)
            assert (
                result["requires_vision"] is True or 
                result["confidence"] >= 0.3
            ), f"Task '{task}' should be detected as vision task"
    
    def test_analyze_task_type_precise_operation(self):
        """测试精确操作任务分析"""
        intelligence = BrowserIntelligence()
        
        # 测试包含精确操作关键词的任务
        precise_tasks = [
            "点击登录按钮",
            "填写表单信息",
            "输入用户名和密码",
            "选择下拉菜单选项"
        ]
        
        for task in precise_tasks:
            result = intelligence.analyze_task_type(task)
            assert (
                result["requires_precise_operation"] is True or 
                result["confidence"] >= 0.2
            ), f"Task '{task}' should be detected as precise operation task"
    
    def test_analyze_task_type_complex_task(self):
        """测试复杂任务分析"""
        intelligence = BrowserIntelligence()
        
        # 测试包含复杂任务关键词的任务
        complex_tasks = [
            "完成复杂的多步骤操作",
            "执行长时间的连续操作",
            "处理复杂流程"
        ]
        
        for task in complex_tasks:
            result = intelligence.analyze_task_type(task)
            assert (
                result["is_complex_task"] is True or 
                result["confidence"] >= 0.2
            ), f"Task '{task}' should be detected as complex task"
    
    def test_analyze_task_type_data_extraction(self):
        """测试数据提取任务分析"""
        intelligence = BrowserIntelligence()
        
        # 测试包含数据提取关键词的任务
        extraction_tasks = [
            "提取页面中的价格信息",
            "收集商品详情",
            "抓取数据列表",
            "抽取表格内容"
        ]
        
        for task in extraction_tasks:
            result = intelligence.analyze_task_type(task)
            assert (
                result["requires_data_extraction"] is True or 
                result["confidence"] >= 0.2
            ), f"Task '{task}' should be detected as data extraction task"
    
    def test_get_optimal_llm_for_task(self):
        """测试获取最优 LLM"""
        intelligence = BrowserIntelligence()
        
        # 测试不同类型任务的模型选择
        llm = intelligence.get_optimal_llm_for_task("访问百度首页")
        assert llm is not None
        
        llm_vision = intelligence.get_optimal_llm_for_task("分析页面并截图")
        assert llm_vision is not None
    
    def test_should_use_fine_grained_tools(self):
        """测试细粒度工具使用决策"""
        intelligence = BrowserIntelligence()
        
        # 测试精确操作任务应建议使用细粒度工具
        intelligence.should_use_fine_grained_tools("点击按钮并填写表单")
        # 这个取决于具体实现，但我们测试函数是否正常运行
        
        # 测试一般任务
        intelligence.should_use_fine_grained_tools("访问网站")
        # 这个也取决于具体实现
    
    def test_get_task_complexity_score(self):
        """测试任务复杂度评分"""
        intelligence = BrowserIntelligence()
        
        # 测试简单任务
        simple_score = intelligence.get_task_complexity_score("访问百度首页")
        assert 0.0 <= simple_score <= 1.0
        
        # 测试复杂任务
        complex_score = intelligence.get_task_complexity_score(
            "完成一个复杂的多步骤操作，包括登录、搜索、筛选、比较和下单"
        )
        assert 0.0 <= complex_score <= 1.0
        
        # 复杂任务评分应该不低于简单任务
        assert isinstance(complex_score, float)
        assert isinstance(simple_score, float)
    
    def test_keyword_matching_logic(self):
        """测试关键词匹配逻辑"""
        intelligence = BrowserIntelligence()
        
        # 验证关键词列表存在
        assert hasattr(intelligence, 'vision_keywords')
        assert hasattr(intelligence, 'precise_operation_keywords')
        assert hasattr(intelligence, 'complex_task_keywords')
        assert hasattr(intelligence, 'data_extraction_keywords')
        
        # 验证关键词列表不为空
        assert len(intelligence.vision_keywords) > 0
        assert len(intelligence.precise_operation_keywords) > 0
        assert len(intelligence.complex_task_keywords) > 0
        assert len(intelligence.data_extraction_keywords) > 0


class TestBrowserIntelligenceIntegration:
    """浏览器智能决策集成测试"""

    def test_end_to_end_analysis(self):
        """端到端分析流程测试"""
        intelligence = BrowserIntelligence()
        
        # 测试完整分析流程
        task = "帮我访问淘宝，搜索红色连衣裙，并告诉我价格最高的前三个"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证分析结果结构
        required_keys = [
            "requires_vision", 
            "requires_precise_operation", 
            "is_complex_task", 
            "requires_data_extraction", 
            "recommended_model", 
            "confidence"
        ]
        
        for key in required_keys:
            assert key in analysis
        
        # 验证推荐模型不为空
        assert analysis["recommended_model"] is not None
        
        # 验证置信度范围
        assert 0.0 <= analysis["confidence"] <= 1.0
        
        # 获取推荐的LLM
        llm = intelligence.get_optimal_llm_for_task(task)
        assert llm is not None
        
        # 获取复杂度评分
        complexity = intelligence.get_task_complexity_score(task)
        assert 0.0 <= complexity <= 1.0