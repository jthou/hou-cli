"""BaseAgent 测试"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.agent.base_agent import BaseAgent


class ConcreteAgent(BaseAgent):
    """具体 Agent 实现（用于测试）"""
    
    async def execute(self, task):
        return f"执行任务: {task.get('task', '')}"


class TestBaseAgent:
    """BaseAgent 测试类"""
    
    @pytest.fixture
    def agent(self):
        """创建 Agent 实例"""
        return ConcreteAgent(
            name="测试Agent",
            description="用于测试的Agent",
            capabilities=["测试能力1", "测试能力2"]
        )
    
    def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent.name == "测试Agent"
        assert agent.description == "用于测试的Agent"
        assert len(agent.capabilities) == 2
        assert agent.llm_service is not None
    
    @pytest.mark.asyncio
    async def test_think_without_context(self, agent):
        """测试思考过程（无上下文）"""
        # [MOCK] 使用 Mock 数据模拟 llm_service.chat 方法
        print("[MOCK] 测试使用 Mock 数据: llm_service.chat 返回 '思考结果'")
        with patch.object(agent.llm_service, 'chat') as mock_chat:
            mock_chat.return_value = "思考结果"
            print(f"[MOCK] Mock llm_service.chat 已设置，返回值: '思考结果'")
            
            result = await agent.think("测试提示")
            
            assert result == "思考结果"
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]
            print(f"[MOCK] Mock chat 被调用，system_prompt包含'测试Agent': {'测试Agent' in call_kwargs['system_prompt']}, user_prompt: {call_kwargs['user_prompt']}")
            assert "测试Agent" in call_kwargs["system_prompt"]
            assert call_kwargs["user_prompt"] == "测试提示"
    
    @pytest.mark.asyncio
    async def test_think_with_context(self, agent):
        """测试思考过程（有上下文）"""
        # [MOCK] 使用 Mock 数据模拟 llm_service.chat 方法（带上下文）
        context = {"key": "value", "info": "测试信息"}
        print(f"[MOCK] 测试使用 Mock 数据: llm_service.chat 返回 '思考结果'，上下文: {context}")
        with patch.object(agent.llm_service, 'chat') as mock_chat:
            mock_chat.return_value = "思考结果"
            print(f"[MOCK] Mock llm_service.chat 已设置，返回值: '思考结果'")
            
            result = await agent.think("测试提示", context=context)
            
            assert result == "思考结果"
            call_kwargs = mock_chat.call_args[1]
            print(f"[MOCK] Mock chat 被调用，system_prompt包含'上下文信息': {'上下文信息' in call_kwargs['system_prompt']}")
            assert "上下文信息" in call_kwargs["system_prompt"]
    
    @pytest.mark.asyncio
    async def test_execute(self, agent):
        """测试执行任务"""
        task = {"task": "测试任务", "params": {"key": "value"}}
        
        result = await agent.execute(task)
        
        assert result == "执行任务: 测试任务"
    
    def test_capabilities_formatting(self, agent):
        """测试能力格式化"""
        assert "测试能力1" in agent.capabilities
        assert "测试能力2" in agent.capabilities

