"""WorkflowIdentifier 测试"""
import pytest
from backend.core.workflow.workflow_identifier import WorkflowIdentifier


class TestWorkflowIdentifier:
    """WorkflowIdentifier 测试类"""
    
    @pytest.fixture
    def identifier(self):
        """创建 WorkflowIdentifier 实例"""
        return WorkflowIdentifier()
    
    def test_initialization(self, identifier):
        """测试初始化"""
        assert identifier.workflow_registry is not None
        assert isinstance(identifier.workflow_registry, dict)
        assert "pdf_analysis" in identifier.workflow_registry
    
    @pytest.mark.asyncio
    async def test_identify(self, identifier):
        """测试任务识别"""
        result = await identifier.identify("测试任务")
        
        assert isinstance(result, dict)
        assert "mode" in result
        assert "workflow_name" in result
        assert "confidence" in result
        assert result["mode"] == "dynamic"
    
    @pytest.mark.asyncio
    async def test_identify_with_different_tasks(self, identifier):
        """测试不同任务的识别"""
        tasks = [
            "分析PDF文档",
            "代码审查",
            "普通对话"
        ]
        
        for task in tasks:
            result = await identifier.identify(task)
            assert result["mode"] in ["dynamic", "sop"]
            assert 0 <= result["confidence"] <= 1

