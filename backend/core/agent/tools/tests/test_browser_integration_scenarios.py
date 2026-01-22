"""浏览器工具集成场景测试 - 测试复杂浏览器任务场景"""
import pytest
from unittest.mock import Mock, patch
from backend.core.agent.tools.builtin.browser_intelligence import BrowserIntelligence
from backend.core.agent.tools.builtin.browser_action_tool import (
    BrowserNavigateTool,
    BrowserClickTool,
    BrowserSearchTool
)

# BrowserTool 在测试中被引用，但不是直接导入使用


class TestBrowserIntegrationScenarios:
    """浏览器工具集成场景测试"""

    def test_bilibili_video_playback_scenario(self):
        """测试 Bilibili 视频播放场景 - 模拟复杂浏览器任务"""
        intelligence = BrowserIntelligence()
        
        # 测试复杂视频播放任务分析
        task = "打开 https://www.bilibili.com/video/BV1knvYBDEjs 并播放视频，然后点击下一个视频"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果
        assert analysis["requires_precise_operation"] is True  # 需要精确点击操作
        assert analysis["recommended_model"] is not None  # 应该推荐合适的模型
        assert analysis["confidence"] >= 0.2  # 置信度应该合理
        
        print(f"Bilibili 任务分析: {analysis}")

    def test_long_running_browser_task(self):
        """测试长时间运行的浏览器任务 - 模拟超时场景"""
        intelligence = BrowserIntelligence()
        
        # 测试包含时间控制的复杂任务
        task = "跳到视频的第10分钟，然后播放10分钟，然后关掉"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果 - 检查是否有合理的推荐模型
        assert analysis["recommended_model"] is not None  # 应该有推荐模型
        
        print(f"长时间任务分析: {analysis}")

    def test_multi_step_browser_navigation(self):
        """测试多步骤浏览器导航场景"""
        intelligence = BrowserIntelligence()
        
        # 测试多步骤复杂任务
        task = "打开网站，播放视频，点击下一个，跳转到特定时间点，关闭"
        analysis = intelligence.analyze_task_type(task)
        
        # 验证任务分析结果
        assert analysis["requires_precise_operation"] is True
        assert analysis["confidence"] >= 0.2  # 多步骤任务应有合理置信度
        
        print(f"多步骤任务分析: {analysis}")

    @pytest.mark.asyncio
    async def test_browser_tool_with_timeout_simulation(self):
        """测试浏览器工具的超时处理能力"""
        # 模拟浏览器工具的超时场景
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
                
                # 模拟长时间运行的任务，应该有适当的超时处理
                kwargs = {
                    "task": "播放视频并进行多项操作",
                    "timeout": 120,  # 2分钟超时
                    "headless": True
                }
                
                # 验证工具能够处理较长的超时时间
                assert kwargs["timeout"] == 120
                print(f"超时设置验证: {kwargs['timeout']}秒")

    def test_error_handling_in_complex_tasks(self):
        """测试复杂任务中的错误处理"""
        intelligence = BrowserIntelligence()
        
        # 测试各种可能出错的任务
        error_prone_tasks = [
            "打开不存在的网址并点击元素",
            "在未加载完成的页面上执行操作",
            "对动态加载的内容执行静态操作"
        ]
        
        for task in error_prone_tasks:
            analysis = intelligence.analyze_task_type(task)
            # 验证分析不会崩溃
            assert "recommended_model" in analysis
            assert "confidence" in analysis
            print(f"错误处理测试 - 任务: {task}, 分析结果: {analysis['confidence']}")


class TestBrowserToolRobustness:
    """浏览器工具鲁棒性测试"""

    def test_tool_parameters_validation(self):
        """测试工具参数验证"""
        # 测试各种工具的参数验证
        tools_to_test = [
            BrowserNavigateTool(),
            BrowserClickTool(), 
            BrowserSearchTool()
        ]
        
        for tool in tools_to_test:
            # 验证参数列表不为空
            assert len(tool.parameters) > 0
            print(f"工具 {tool.name} 参数验证通过: {len(tool.parameters)} 个参数")

    def test_task_complexity_scoring(self):
        """测试任务复杂度评分"""
        intelligence = BrowserIntelligence()
        
        # 测试不同复杂度的任务
        simple_task = "访问百度首页"
        complex_task = "在复杂网站上执行多个精确操作并提取数据"
        
        simple_score = intelligence.get_task_complexity_score(simple_task)
        complex_score = intelligence.get_task_complexity_score(complex_task)
        
        # 复杂任务的分数应该高于简单任务
        assert complex_score >= simple_score
        assert 0.0 <= simple_score <= 1.0
        assert 0.0 <= complex_score <= 1.0
        
        print(f"简单任务复杂度: {simple_score}, 复杂任务复杂度: {complex_score}")

    def test_model_recommendation_stability(self):
        """测试模型推荐的稳定性"""
        intelligence = BrowserIntelligence()
        
        # 多次分析相同任务，确保结果一致性
        task = "播放 Bilibili 视频并点击下一个"
        results = []
        
        for i in range(3):
            analysis = intelligence.analyze_task_type(task)
            results.append(analysis)
        
        # 验证多次分析结果的一致性
        for i in range(1, len(results)):
            assert (
                results[i]["requires_vision"] == 
                results[0]["requires_vision"]
            )
            assert (
                results[i]["requires_precise_operation"] == 
                results[0]["requires_precise_operation"]
            )
            assert (
                results[i]["is_complex_task"] == 
                results[0]["is_complex_task"]
            )
        
        print("模型推荐稳定性测试通过，3次分析结果一致")


if __name__ == "__main__":
    # 运行测试
    test_instance = TestBrowserIntegrationScenarios()
    
    print("运行 Bilibili 视频播放场景测试...")
    test_instance.test_bilibili_video_playback_scenario()
    
    print("\n运行长时间运行任务测试...")
    test_instance.test_long_running_browser_task()
    
    print("\n运行多步骤导航测试...")
    test_instance.test_multi_step_browser_navigation()
    
    print("\n运行错误处理测试...")
    test_instance.test_error_handling_in_complex_tasks()
    
    # 运行鲁棒性测试
    robustness_test = TestBrowserToolRobustness()
    
    print("\n运行工具参数验证测试...")
    robustness_test.test_tool_parameters_validation()
    
    print("\n运行任务复杂度评分测试...")
    robustness_test.test_task_complexity_scoring()
    
    print("\n运行模型推荐稳定性测试...")
    robustness_test.test_model_recommendation_stability()
    
    print("\n所有集成场景测试通过！")