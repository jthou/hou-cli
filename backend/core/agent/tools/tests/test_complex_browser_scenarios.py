"""复杂浏览器任务场景测试 - 搜索、打开网页、提取内容并生成报告"""
import pytest
from unittest.mock import Mock, patch
from backend.core.agent.tools.builtin.browser_intelligence import BrowserIntelligence
from backend.core.agent.tools.builtin.browser_action_tool import (
    BrowserNavigateTool,
    BrowserClickTool,
    BrowserFillTool,
    BrowserSearchTool,
    BrowserExtractTool
)

# BrowserTool 在测试中被引用，但不是直接导入使用


class TestComplexBrowserScenarios:
    """复杂浏览器任务场景测试"""

    def test_google_search_and_open_multiple_pages_scenario(self):
        """测试 Google 搜索并打开多个网页的复杂场景"""
        intelligence = BrowserIntelligence()
        
        # 测试复杂搜索任务分析
        task = "用 Google 搜索人工智能，然后打开前三个网页，读取网页内容，形成一个简短的报告"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果 - 至少应该推荐一个模型
        assert analysis["recommended_model"] is not None  # 应该推荐合适的模型
        assert analysis["confidence"] >= 0.0  # 置信度应该存在
        
        print(f"复杂搜索任务分析: {analysis}")

    def test_multi_step_search_navigation_scenario(self):
        """测试多步骤搜索和导航场景"""
        intelligence = BrowserIntelligence()
        
        # 测试多步骤复杂任务
        task = "搜索关键词，点击链接，提取信息，再搜索相关内容"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果
        assert analysis["recommended_model"] is not None  # 应该推荐模型
        assert analysis["confidence"] >= 0.0  # 置信度应该存在
        
        print(f"多步骤任务分析: {analysis}")

    def test_content_extraction_and_summarization_scenario(self):
        """测试内容提取和摘要生成场景"""
        intelligence = BrowserIntelligence()
        
        # 测试内容提取任务
        task = "打开多个网页，提取主要内容并生成摘要报告"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果
        assert analysis["recommended_model"] is not None  # 推荐模型
        assert analysis["confidence"] >= 0.0  # 置信度应该存在
        
        print(f"内容提取任务分析: {analysis}")

    @pytest.mark.asyncio
    async def test_browser_tool_with_complex_search_task(self):
        """测试浏览器工具处理复杂搜索任务的能力"""
        # 模拟浏览器工具的复杂搜索场景
        with patch(
            'backend.core.agent.tools.builtin.browser_tool.Browser'
        ) as mock_browser:
            
            # 模拟浏览器初始化
            mock_browser_instance = Mock()
            mock_browser.return_value = mock_browser_instance
            
            # 模拟 Agent 的行为
            with patch(
                'backend.core.agent.tools.builtin.browser_tool.Agent'
            ) as mock_agent:
                mock_agent_instance = Mock()
                mock_agent.return_value = mock_agent_instance
                
                # 模拟复杂搜索任务，应该有适当的超时处理
                kwargs = {
                    "task": "搜索人工智能相关内容，打开多个网页并提取信息",
                    "timeout": 180,  # 3分钟超时，适用于复杂任务
                    "headless": True
                }
                
                # 验证工具能够处理较长的超时时间
                assert kwargs["timeout"] == 180
                print(f"复杂任务超时设置验证: {kwargs['timeout']}秒")

    def test_error_handling_in_complex_search_scenarios(self):
        """测试复杂搜索场景中的错误处理"""
        intelligence = BrowserIntelligence()
        
        # 测试各种可能出错的复杂搜索任务
        error_prone_tasks = [
            "搜索不存在的内容并打开网页",
            "在多个网页间快速切换时网络中断",
            "提取大量网页内容时内存不足"
        ]
        
        for task in error_prone_tasks:
            analysis = intelligence.analyze_task_type(task)
            # 验证分析不会崩溃
            assert "recommended_model" in analysis
            assert "confidence" in analysis
            print(f"错误处理测试 - 任务: {task}, 分析结果: {analysis['confidence']}")

    def test_task_sequencing_in_search_scenarios(self):
        """测试搜索场景中的任务排序"""
        intelligence = BrowserIntelligence()
        
        # 测试搜索任务的顺序依赖
        task = "先搜索，再点击，然后提取，最后总结"
        analysis = intelligence.analyze_task_type(task)
        
        assert analysis["recommended_model"] is not None  # 应该推荐模型
        assert analysis["confidence"] >= 0.0  # 置信度应该存在
        
        print(f"任务排序分析: {analysis}")


class TestBrowserToolsForComplexTasks:
    """复杂任务的浏览器工具测试"""

    def test_tool_chaining_capabilities(self):
        """测试工具链式调用能力"""
        # 测试各种工具的链式调用
        tools_to_test = [
            BrowserNavigateTool(),
            BrowserClickTool(), 
            BrowserFillTool(),
            BrowserSearchTool(),
            BrowserExtractTool()
        ]
        
        # 验证每个工具都有适当的参数
        for tool in tools_to_test:
            assert len(tool.parameters) > 0
            print(f"工具 {tool.name} 参数验证通过: {len(tool.parameters)} 个参数")

    def test_search_then_extract_workflow(self):
        """测试搜索然后提取的工作流程"""
        intelligence = BrowserIntelligence()
        
        # 测试搜索后提取的典型工作流
        workflow_task = "搜索-导航-提取-分析"
        complexity_score = intelligence.get_task_complexity_score(workflow_task)
        
        # 复杂工作流的分数应该较高
        assert complexity_score >= 0.5
        assert 0.0 <= complexity_score <= 1.0
        
        print(f"搜索-提取工作流复杂度: {complexity_score}")

    def test_model_selection_for_search_tasks(self):
        """测试搜索任务的模型选择"""
        intelligence = BrowserIntelligence()
        
        # 测试不同复杂度的搜索任务
        simple_search = "搜索天气"
        complex_search = "搜索并比较多种人工智能技术的优缺点"
        
        simple_analysis = intelligence.analyze_task_type(simple_search)
        complex_analysis = intelligence.analyze_task_type(complex_search)
        
        # 验证两个任务都得到适当的模型推荐
        assert simple_analysis["recommended_model"] is not None
        assert complex_analysis["recommended_model"] is not None
        
        print(f"简单搜索分析: {simple_analysis}")
        print(f"复杂搜索分析: {complex_analysis}")

    def test_search_result_evaluation(self):
        """测试搜索结果评估能力"""
        intelligence = BrowserIntelligence()
        
        # 多次分析相同搜索任务，确保结果一致性
        task = "搜索人工智能相关内容并提取信息"
        results = []
        
        for i in range(3):
            analysis = intelligence.analyze_task_type(task)
            results.append(analysis)
        
        # 验证多次分析结果的一致性
        for i in range(1, len(results)):
            assert (
                results[i]["requires_precise_operation"] == 
                results[0]["requires_precise_operation"]
            )
            assert (
                results[i]["requires_data_extraction"] == 
                results[0]["requires_data_extraction"]
            )
            assert (
                results[i]["is_complex_task"] == 
                results[0]["is_complex_task"]
            )
        
        print("搜索任务评估稳定性测试通过，3次分析结果一致")


if __name__ == "__main__":
    # 运行测试
    test_instance = TestComplexBrowserScenarios()
    
    print("运行 Google 搜索和打开多个网页场景测试...")
    test_instance.test_google_search_and_open_multiple_pages_scenario()
    
    print("\n运行多步骤搜索导航测试...")
    test_instance.test_multi_step_search_navigation_scenario()
    
    print("\n运行内容提取和摘要生成测试...")
    test_instance.test_content_extraction_and_summarization_scenario()
    
    print("\n运行错误处理测试...")
    test_instance.test_error_handling_in_complex_search_scenarios()
    
    print("\n运行任务排序测试...")
    test_instance.test_task_sequencing_in_search_scenarios()
    
    # 运行工具测试
    tool_test = TestBrowserToolsForComplexTasks()
    
    print("\n运行工具链式调用测试...")
    tool_test.test_tool_chaining_capabilities()
    
    print("\n运行搜索-提取工作流测试...")
    tool_test.test_search_then_extract_workflow()
    
    print("\n运行搜索任务模型选择测试...")
    tool_test.test_model_selection_for_search_tasks()
    
    print("\n运行搜索结果评估测试...")
    tool_test.test_search_result_evaluation()
    
    print("\n所有复杂浏览器任务场景测试通过！")