"""WorkflowEngine 测试"""
import pytest
from unittest.mock import Mock
from backend.core.workflow.workflow_engine import WorkflowEngine


class TestWorkflowEngine:
    """WorkflowEngine 测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建 WorkflowEngine 实例"""
        return WorkflowEngine()
    
    @pytest.fixture
    def engine_with_orchestrator(self):
        """创建带 Orchestrator 的 WorkflowEngine 实例"""
        # [MOCK] 使用 Mock 数据模拟 Orchestrator
        print("[MOCK] 测试使用 Mock 数据: Orchestrator 对象")
        mock_orch = Mock()
        print(f"[MOCK] Mock Orchestrator 已创建: {type(mock_orch)}")
        return WorkflowEngine(orchestrator=mock_orch)
    
    def test_initialization(self, engine):
        """测试初始化"""
        assert engine.orchestrator is None
    
    def test_initialization_with_orchestrator(self, engine_with_orchestrator):
        """测试带 Orchestrator 的初始化"""
        assert engine_with_orchestrator.orchestrator is not None
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, engine):
        """测试执行工作流"""
        input_data = {"key": "value"}
        result = await engine.execute_workflow("test_workflow", input_data)
        
        assert isinstance(result, str)
        assert "test_workflow" in result
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_different_inputs(self, engine):
        """测试不同输入的执行"""
        test_cases = [
            ({"param1": "value1"}, "workflow1"),
            ({"param2": "value2", "param3": "value3"}, "workflow2"),
            ({}, "empty_workflow")
        ]
        
        for input_data, workflow_name in test_cases:
            result = await engine.execute_workflow(workflow_name, input_data)
            assert isinstance(result, str)
            assert workflow_name in result

