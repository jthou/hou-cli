"""集成测试场景"""
import pytest
import asyncio
from typing import Dict, List
from backend.core.agent.orchestrator import Orchestrator
from backend.services.llm.model_config import get_model_config_manager


# 测试场景定义
TEST_SCENARIOS = [
    {
        "name": "简单对话任务",
        "task": "今天天气怎么样？",
        "expected_model": "chat",
        "expected_iterations": 1,
        "should_decompose": False
    },
    {
        "name": "代码生成任务",
        "task": "写一个 Python 函数计算斐波那契数列",
        "expected_model": "code",
        "expected_iterations": 2,
        "should_decompose": False
    },
    {
        "name": "简单工具调用",
        "task": "执行 ls /home",
        "expected_model": "code",
        "expected_iterations": 1,
        "should_decompose": False
    },
    {
        "name": "搜索任务",
        "task": "搜索 Python 教程",
        "expected_model": "chat",
        "expected_iterations": 1,
        "should_decompose": False
    },
    {
        "name": "复杂推理任务",
        "task": "分析这个项目的代码结构并生成报告",
        "expected_model": "reasoning",
        "expected_iterations": 5,
        "should_decompose": True
    },
    {
        "name": "多步骤任务",
        "task": "搜索相关信息，然后生成一篇文章",
        "expected_model": "reasoning",
        "expected_iterations": 3,
        "should_decompose": True
    }
]


class TestIntegrationScenarios:
    """集成测试场景"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        return Orchestrator()
    
    @pytest.fixture
    def config_manager(self):
        """获取配置管理器"""
        return get_model_config_manager()
    
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
    @pytest.mark.asyncio
    async def test_scenario_model_selection(self, orchestrator, config_manager, scenario):
        """测试场景的模型选择"""
        task = scenario["task"]
        expected_model_type = scenario["expected_model"]
        
        # 选择模型
        selected_model = await orchestrator._select_model(task)
        
        # 获取期望的模型
        if expected_model_type == "chat":
            expected_model = config_manager.get_chat_model()
        elif expected_model_type == "code":
            expected_model = config_manager.get_code_model()
        elif expected_model_type == "reasoning":
            expected_model = config_manager.get_reasoning_model()
        else:
            pytest.fail(f"未知的模型类型: {expected_model_type}")
        
        assert selected_model == expected_model, \
            f"场景 '{scenario['name']}' 应该选择 {expected_model_type} 模型，但选择了 {selected_model}"
    
    @pytest.mark.asyncio
    async def test_simple_chat_scenario(self, orchestrator):
        """测试简单对话场景"""
        scenario = TEST_SCENARIOS[0]  # 简单对话任务
        
        # 选择模型
        selected_model = await orchestrator._select_model(scenario["task"])
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_chat_model()
        
        assert selected_model == expected_model
        
        # 设置模型
        orchestrator.llm_service.set_model(selected_model)
        assert orchestrator.llm_service.model == selected_model
    
    @pytest.mark.asyncio
    async def test_code_scenario(self, orchestrator):
        """测试代码生成场景"""
        scenario = TEST_SCENARIOS[1]  # 代码生成任务
        
        # 选择模型
        selected_model = await orchestrator._select_model(scenario["task"])
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_code_model()
        
        assert selected_model == expected_model
        
        # 设置模型
        orchestrator.llm_service.set_model(selected_model)
        assert orchestrator.llm_service.model == selected_model
    
    @pytest.mark.asyncio
    async def test_reasoning_scenario(self, orchestrator):
        """测试推理场景"""
        scenario = TEST_SCENARIOS[4]  # 复杂推理任务
        
        # 选择模型
        selected_model = await orchestrator._select_model(scenario["task"])
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_reasoning_model()
        
        assert selected_model == expected_model
        
        # 设置模型
        orchestrator.llm_service.set_model(selected_model)
        assert orchestrator.llm_service.model == selected_model


def get_test_scenarios() -> List[Dict]:
    """获取测试场景列表"""
    return TEST_SCENARIOS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

