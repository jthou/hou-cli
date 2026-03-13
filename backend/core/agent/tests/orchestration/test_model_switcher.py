"""测试动态模型切换功能"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.core.agent.planning.model_switcher import ModelSwitcher, ModelSwitchRecord
from backend.core.agent.models import TaskComplexity
from backend.core.agent.tools.metadata import tool_metadata_registry


class TestModelSwitcher:
    """测试 ModelSwitcher 类"""
    
    @pytest.fixture
    def model_switcher(self):
        """创建 ModelSwitcher 实例"""
        with patch('backend.core.agent.planning.model_switcher.get_model_config_manager') as mock_config:
            mock_manager = Mock()
            mock_manager.get_chat_model.return_value = "chat-model"
            mock_manager.get_code_model.return_value = "code-model"
            mock_manager.get_reasoning_model.return_value = "reasoning-model"
            mock_config.return_value = mock_manager
            
            switcher = ModelSwitcher()
            switcher.config_manager = mock_manager
            return switcher
    
    def test_analyze_execution_result_success(self, model_switcher):
        """测试分析成功的执行结果"""
        tool_result = {
            "success": True,
            "data": {"result": "ok"}
        }
        
        result = model_switcher.analyze_execution_result(
            tool_name="google_search",
            tool_result=tool_result,
            current_model="chat-model"
        )
        
        # 成功的执行结果不应该触发切换
        assert result is None
    
    def test_analyze_execution_result_failure_with_complex_task(self, model_switcher):
        """测试分析失败的执行结果（复杂任务）"""
        tool_result = {
            "success": False,
            "error": "执行失败"
        }
        
        result = model_switcher.analyze_execution_result(
            tool_name="google_search",
            tool_result=tool_result,
            current_model="chat-model",
            task_complexity=TaskComplexity.COMPLEX
        )
        
        # 复杂任务失败时应该切换到推理模型
        assert result == "reasoning-model"
    
    def test_analyze_execution_result_failure_with_code_tool(self, model_switcher):
        """测试分析失败的执行结果（代码工具）"""
        # 注册一个需要代码能力的工具
        from backend.core.agent.models import ToolMetadata
        tool_metadata_registry.register(ToolMetadata(
            tool_name="exec_py",
            requires_code=True,
            recommended_model="code"
        ))
        
        tool_result = {
            "success": False,
            "error": "执行失败"
        }
        
        result = model_switcher.analyze_execution_result(
            tool_name="exec_py",
            tool_result=tool_result,
            current_model="chat-model"
        )
        
        # 代码工具失败时应该切换到代码模型
        assert result == "code-model"
    
    def test_should_switch_model(self, model_switcher):
        """测试是否应该切换模型"""
        # 正常情况：应该切换
        assert model_switcher.should_switch_model(
            current_model="chat-model",
            target_model="code-model",
        ) is True
        
        # 目标模型与当前模型相同：不应该切换
        assert model_switcher.should_switch_model(
            current_model="chat-model",
            target_model="chat-model",
        ) is False
        
        # 目标模型为 None：不应该切换
        assert model_switcher.should_switch_model(
            current_model="chat-model",
            target_model=None,
        ) is False
    
    def test_record_switch(self, model_switcher):
        """测试记录模型切换"""
        model_switcher.record_switch(
            from_model="chat-model",
            to_model="code-model",
            reason="测试切换",
            context={"tool": "exec_py"}
        )
        
        assert len(model_switcher.switch_history) == 1
        record = model_switcher.switch_history[0]
        assert record.from_model == "chat-model"
        assert record.to_model == "code-model"
        assert record.reason == "测试切换"
        assert record.context["tool"] == "exec_py"
    
    def test_get_switch_history(self, model_switcher):
        """测试获取切换历史"""
        # 记录多次切换
        for i in range(5):
            model_switcher.record_switch(
                from_model=f"model-{i}",
                to_model=f"model-{i+1}",
                reason=f"切换 {i}"
            )
        
        # 获取最近3条记录
        history = model_switcher.get_switch_history(limit=3)
        assert len(history) == 3
        
        # 检查最后一条记录
        assert history[-1]["to_model"] == "model-5"
    
    def test_get_recommended_model_by_tool(self, model_switcher):
        """测试根据工具获取推荐模型"""
        # 注册一个推荐代码模型的工具
        from backend.core.agent.models import ToolMetadata
        tool_metadata_registry.register(ToolMetadata(
            tool_name="exec_py",
            recommended_model="code"
        ))
        
        recommended = model_switcher.get_recommended_model("exec_py")
        assert recommended == "code-model"
    
    def test_get_recommended_model_by_complexity(self, model_switcher):
        """测试根据任务复杂度获取推荐模型"""
        recommended = model_switcher.get_recommended_model(
            tool_name="unknown_tool",
            task_complexity=TaskComplexity.COMPLEX
        )
        assert recommended == "reasoning-model"
    
    def test_get_recommended_model_default(self, model_switcher):
        """测试默认推荐模型"""
        recommended = model_switcher.get_recommended_model("unknown_tool")
        assert recommended == "chat-model"
    
    def test_switch_history_limit(self, model_switcher):
        """测试切换历史记录限制"""
        # 记录超过限制次数的切换
        for i in range(150):
            model_switcher.record_switch(
                from_model=f"model-{i}",
                to_model=f"model-{i+1}",
                reason=f"切换 {i}"
            )
        
        # 应该只保留最近100条记录
        assert len(model_switcher.switch_history) == 100
        assert model_switcher.switch_history[0].to_model == "model-51"  # 第51次切换

