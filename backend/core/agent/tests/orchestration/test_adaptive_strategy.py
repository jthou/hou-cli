"""测试自适应策略功能"""
import pytest
from unittest.mock import Mock, patch
from backend.core.agent.planning.adaptive_strategy import AdaptiveStrategy, ExecutionMetrics, StrategyAdjustment
from backend.core.agent.models import TaskComplexity


class TestAdaptiveStrategy:
    """测试 AdaptiveStrategy 类"""
    
    @pytest.fixture
    def adaptive_strategy(self):
        """创建 AdaptiveStrategy 实例"""
        return AdaptiveStrategy()
    
    def test_record_execution(self, adaptive_strategy):
        """测试记录执行指标"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=8,
            tool_failure_count=2,
            model_switch_count=1,
            execution_time=30.0,
            complexity=TaskComplexity.MEDIUM
        )
        
        adaptive_strategy.record_execution(metrics, "测试任务")
        
        assert len(adaptive_strategy.metrics_history) == 1
        assert adaptive_strategy.metrics_history[0].tool_success_rate == 0.8
    
    def test_analyze_and_adjust_high_failure_rate(self, adaptive_strategy):
        """测试高失败率时的策略调整"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=5,  # 50% 成功率，失败率 50% > 30% 阈值
            tool_failure_count=5,
            model_switch_count=0,
            execution_time=20.0,
            complexity=TaskComplexity.COMPLEX
        )
        
        adjustments = adaptive_strategy.analyze_and_adjust(metrics)
        
        assert len(adjustments) > 0
        assert any(adj.adjustment_type == "model_selection" for adj in adjustments)
    
    def test_analyze_and_adjust_frequent_switches(self, adaptive_strategy):
        """测试频繁模型切换时的策略调整"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=10,
            tool_failure_count=0,
            model_switch_count=5,  # 5 次切换 > 3 次阈值
            execution_time=20.0
        )
        
        adjustments = adaptive_strategy.analyze_and_adjust(metrics)
        
        assert len(adjustments) > 0
        assert any(adj.adjustment_type == "model_selection" for adj in adjustments)
        assert any("频繁" in adj.reason for adj in adjustments)
    
    def test_analyze_and_adjust_long_execution(self, adaptive_strategy):
        """测试长时间执行时的策略调整"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=10,
            tool_failure_count=0,
            model_switch_count=0,
            execution_time=120.0,  # 120 秒 > 60 秒阈值
            complexity=TaskComplexity.COMPLEX
        )
        
        adjustments = adaptive_strategy.analyze_and_adjust(metrics)
        
        assert len(adjustments) > 0
        assert any(adj.adjustment_type in ["task_decomposition", "execution_plan"] for adj in adjustments)
    
    def test_get_recommendations(self, adaptive_strategy):
        """测试获取推荐策略"""
        # 先记录一些历史数据
        for i in range(3):
            metrics = ExecutionMetrics(
                tool_call_count=10,
                tool_success_count=8,
                tool_failure_count=2,
                model_switch_count=1,
                execution_time=30.0,
                complexity=TaskComplexity.MEDIUM
            )
            adaptive_strategy.record_execution(metrics, "搜索相关信息")
        
        recommendations = adaptive_strategy.get_recommendations(
            "搜索相关信息",
            TaskComplexity.MEDIUM
        )
        
        assert "recommended_model" in recommendations
        assert "should_decompose" in recommendations
        assert "estimated_time" in recommendations
        assert "confidence" in recommendations
    
    def test_get_statistics(self, adaptive_strategy):
        """测试获取统计信息"""
        # 记录一些执行指标
        for i in range(5):
            metrics = ExecutionMetrics(
                tool_call_count=10,
                tool_success_count=8,
                tool_failure_count=2,
                model_switch_count=1,
                execution_time=30.0
            )
            adaptive_strategy.record_execution(metrics)
        
        stats = adaptive_strategy.get_statistics()
        
        assert stats["total_executions"] == 5
        assert stats["average_success_rate"] > 0
        assert stats["average_execution_time"] > 0
        assert stats["total_adjustments"] == 0  # 还没有调整
    
    def test_update_adjustment_effectiveness(self, adaptive_strategy):
        """测试更新策略调整效果"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=5,
            tool_failure_count=5,
            model_switch_count=0,
            execution_time=20.0,
            complexity=TaskComplexity.COMPLEX
        )
        
        adjustments = adaptive_strategy.analyze_and_adjust(metrics)
        
        if adjustments:
            adjustment = adjustments[0]
            adaptive_strategy.update_adjustment_effectiveness(adjustment, 0.8)
            
            assert adjustment.effectiveness == 0.8
    
    def test_metrics_properties(self):
        """测试 ExecutionMetrics 的属性"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=8,
            tool_failure_count=2
        )
        
        assert abs(metrics.tool_success_rate - 0.8) < 0.001
        assert abs(metrics.tool_failure_rate - 0.2) < 0.001
    
    def test_strategy_adjustment_serialization(self):
        """测试策略调整序列化"""
        metrics = ExecutionMetrics(
            tool_call_count=10,
            tool_success_count=8,
            tool_failure_count=2
        )
        
        adjustment = StrategyAdjustment(
            timestamp=None,
            adjustment_type="model_selection",
            reason="测试调整",
            old_value="old",
            new_value="new",
            metrics=metrics
        )
        
        # 设置时间戳
        from datetime import datetime
        adjustment.timestamp = datetime.now()
        
        data = adjustment.to_dict()
        
        assert data["adjustment_type"] == "model_selection"
        assert data["reason"] == "测试调整"
        assert "metrics" in data
        assert data["metrics"]["tool_success_rate"] == 0.8

