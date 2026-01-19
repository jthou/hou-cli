"""模型选择逻辑测试"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from backend.core.agent.orchestrator import Orchestrator
from backend.services.llm.model_config import get_model_config_manager


class TestModelSelection:
    """模型选择测试"""
    
    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        return Orchestrator()
    
    @pytest.fixture
    def config_manager(self):
        """获取配置管理器"""
        return get_model_config_manager()
    
    @pytest.mark.asyncio
    async def test_simple_chat_task(self, orchestrator):
        """测试简单对话任务选择对话模型"""
        task = "今天天气怎么样？"
        
        selected_model = await orchestrator._select_model(task)
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_chat_model()
        
        assert selected_model == expected_model, f"简单对话任务应该选择对话模型，但选择了 {selected_model}"
    
    @pytest.mark.asyncio
    async def test_code_task(self, orchestrator):
        """测试代码任务选择编程模型"""
        task = "写一个 Python 函数计算斐波那契数列"
        
        selected_model = await orchestrator._select_model(task)
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_code_model()
        
        assert selected_model == expected_model, f"代码任务应该选择编程模型，但选择了 {selected_model}"
    
    @pytest.mark.asyncio
    async def test_reasoning_task(self, orchestrator):
        """测试推理任务选择推理模型"""
        task = "分析这个项目的代码结构并生成报告"
        
        selected_model = await orchestrator._select_model(task)
        config_manager = get_model_config_manager()
        expected_model = config_manager.get_reasoning_model()
        
        assert selected_model == expected_model, f"推理任务应该选择推理模型，但选择了 {selected_model}"
    
    @pytest.mark.asyncio
    async def test_keyword_matching(self, orchestrator):
        """测试关键词匹配"""
        # 代码关键词
        code_tasks = [
            "执行 ls /home",
            "运行 Python 脚本",
            "编写函数",
            "代码生成"
        ]
        
        config_manager = get_model_config_manager()
        expected_code_model = config_manager.get_code_model()
        
        for task in code_tasks:
            selected_model = await orchestrator._select_model(task)
            assert selected_model == expected_code_model, f"任务 '{task}' 应该选择编程模型"
    
    @pytest.mark.asyncio
    async def test_model_switch(self, orchestrator):
        """测试模型切换"""
        config_manager = get_model_config_manager()
        chat_model = config_manager.get_chat_model()
        code_model = config_manager.get_code_model()
        
        # 切换到对话模型
        orchestrator.llm_service.set_model(chat_model)
        assert orchestrator.llm_service.model == chat_model
        
        # 切换到编程模型
        orchestrator.llm_service.set_model(code_model)
        assert orchestrator.llm_service.model == code_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

