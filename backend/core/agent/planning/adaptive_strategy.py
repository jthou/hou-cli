"""自适应策略管理器 - 根据执行情况自动调整策略"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from backend.core.agent.planning.model_switcher import ModelSwitcher
from backend.core.agent.models import TaskComplexity

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """执行指标"""
    tool_call_count: int = 0
    tool_success_count: int = 0
    tool_failure_count: int = 0
    model_switch_count: int = 0
    execution_time: float = 0.0  # 秒
    average_tool_time: float = 0.0  # 秒
    complexity: Optional[TaskComplexity] = None
    
    @property
    def tool_success_rate(self) -> float:
        """工具调用成功率"""
        if self.tool_call_count == 0:
            return 1.0
        return self.tool_success_count / self.tool_call_count
    
    @property
    def tool_failure_rate(self) -> float:
        """工具调用失败率"""
        return 1.0 - self.tool_success_rate


@dataclass
class StrategyAdjustment:
    """策略调整"""
    timestamp: datetime
    adjustment_type: str  # "model_selection", "task_decomposition", "execution_plan"
    reason: str
    old_value: Any
    new_value: Any
    metrics: ExecutionMetrics
    effectiveness: Optional[float] = None  # 调整后的效果（0-1）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "adjustment_type": self.adjustment_type,
            "reason": self.reason,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "metrics": {
                "tool_success_rate": self.metrics.tool_success_rate,
                "tool_failure_rate": self.metrics.tool_failure_rate,
                "model_switch_count": self.metrics.model_switch_count,
                "execution_time": self.metrics.execution_time
            },
            "effectiveness": self.effectiveness
        }


class AdaptiveStrategy:
    """自适应策略管理器
    
    根据执行情况自动调整策略，包括：
    1. 监控执行状态（工具调用成功率、模型切换次数、执行时间等）
    2. 自动调整策略（模型选择、任务分解、执行计划等）
    3. 学习机制（记录成功和失败的案例，优化策略）
    """
    
    def __init__(self, model_switcher: Optional[ModelSwitcher] = None):
        """
        初始化自适应策略管理器
        
        Args:
            model_switcher: 模型切换器（可选）
        """
        self.model_switcher = model_switcher
        self.metrics_history: deque = deque(maxlen=100)  # 保留最近100次执行的指标
        self.adjustments_history: List[StrategyAdjustment] = []
        self.learning_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 策略阈值
        self.tool_failure_threshold = 0.3  # 工具失败率超过30%时调整策略
        self.model_switch_threshold = 3  # 模型切换次数超过3次时优化选择逻辑
        self.execution_time_threshold = 60.0  # 执行时间超过60秒时优化策略
    
    def record_execution(
        self,
        metrics: ExecutionMetrics,
        task_description: Optional[str] = None
    ):
        """
        记录执行指标
        
        Args:
            metrics: 执行指标
            task_description: 任务描述（可选，用于学习）
        """
        self.metrics_history.append(metrics)
        
        # 记录学习数据
        if task_description:
            self.learning_data[task_description].append({
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "tool_success_rate": metrics.tool_success_rate,
                    "tool_failure_rate": metrics.tool_failure_rate,
                    "model_switch_count": metrics.model_switch_count,
                    "execution_time": metrics.execution_time,
                    "complexity": metrics.complexity.value if metrics.complexity else None
                }
            })
    
    def analyze_and_adjust(
        self,
        current_metrics: ExecutionMetrics
    ) -> List[StrategyAdjustment]:
        """
        分析当前执行情况并调整策略
        
        Args:
            current_metrics: 当前执行指标
            
        Returns:
            策略调整列表
        """
        adjustments = []
        
        # 1. 分析工具调用失败率
        if current_metrics.tool_failure_rate > self.tool_failure_threshold:
            adjustment = self._adjust_for_tool_failures(current_metrics)
            if adjustment:
                adjustments.append(adjustment)
        
        # 2. 分析模型切换次数
        if current_metrics.model_switch_count > self.model_switch_threshold:
            adjustment = self._adjust_for_frequent_switches(current_metrics)
            if adjustment:
                adjustments.append(adjustment)
        
        # 3. 分析执行时间
        if current_metrics.execution_time > self.execution_time_threshold:
            adjustment = self._adjust_for_long_execution(current_metrics)
            if adjustment:
                adjustments.append(adjustment)
        
        # 记录调整
        for adjustment in adjustments:
            self.adjustments_history.append(adjustment)
            logger.info(f"策略调整: {adjustment.adjustment_type} - {adjustment.reason}")
        
        return adjustments
    
    def _adjust_for_tool_failures(
        self,
        metrics: ExecutionMetrics
    ) -> Optional[StrategyAdjustment]:
        """针对工具调用失败调整策略"""
        if metrics.complexity == TaskComplexity.COMPLEX:
            # 复杂任务失败率高，建议使用推理模型
            return StrategyAdjustment(
                timestamp=datetime.now(),
                adjustment_type="model_selection",
                reason=f"工具失败率高 ({metrics.tool_failure_rate:.2%})，复杂任务建议使用推理模型",
                old_value="当前模型选择策略",
                new_value="优先使用推理模型",
                metrics=metrics
            )
        else:
            # 简单任务失败率高，可能需要更好的模型选择
            return StrategyAdjustment(
                timestamp=datetime.now(),
                adjustment_type="model_selection",
                reason=f"工具失败率高 ({metrics.tool_failure_rate:.2%})，优化模型选择逻辑",
                old_value="当前模型选择策略",
                new_value="优化模型选择",
                metrics=metrics
            )
    
    def _adjust_for_frequent_switches(
        self,
        metrics: ExecutionMetrics
    ) -> Optional[StrategyAdjustment]:
        """针对频繁模型切换调整策略"""
        return StrategyAdjustment(
            timestamp=datetime.now(),
            adjustment_type="model_selection",
            reason=f"模型切换频繁 ({metrics.model_switch_count} 次)，优化初始模型选择",
            old_value="当前模型选择策略",
            new_value="改进初始模型选择，减少切换",
            metrics=metrics
        )
    
    def _adjust_for_long_execution(
        self,
        metrics: ExecutionMetrics
    ) -> Optional[StrategyAdjustment]:
        """针对长时间执行调整策略"""
        if metrics.complexity == TaskComplexity.COMPLEX:
            # 复杂任务执行时间长，可能需要任务分解
            return StrategyAdjustment(
                timestamp=datetime.now(),
                adjustment_type="task_decomposition",
                reason=f"执行时间过长 ({metrics.execution_time:.1f} 秒)，复杂任务建议分解",
                old_value="不分解或简单分解",
                new_value="更细致的任务分解",
                metrics=metrics
            )
        else:
            # 简单任务执行时间长，可能需要优化执行计划
            return StrategyAdjustment(
                timestamp=datetime.now(),
                adjustment_type="execution_plan",
                reason=f"执行时间过长 ({metrics.execution_time:.1f} 秒)，优化执行计划",
                old_value="当前执行计划",
                new_value="优化执行顺序和并行策略",
                metrics=metrics
            )
    
    def get_recommendations(
        self,
        task_description: str,
        task_complexity: Optional[TaskComplexity] = None
    ) -> Dict[str, Any]:
        """
        根据历史数据获取推荐策略
        
        Args:
            task_description: 任务描述
            task_complexity: 任务复杂度
            
        Returns:
            推荐策略字典
        """
        recommendations = {
            "recommended_model": None,
            "should_decompose": False,
            "estimated_time": None,
            "confidence": 0.0
        }
        
        # 查找相似任务的历史数据
        similar_tasks = self._find_similar_tasks(task_description)
        
        if similar_tasks:
            # 分析历史数据
            success_rates = []
            execution_times = []
            model_switches = []
            
            for task_data in similar_tasks:
                for record in task_data["records"]:
                    metrics = record["metrics"]
                    success_rates.append(metrics.get("tool_success_rate", 0.0))
                    execution_times.append(metrics.get("execution_time", 0.0))
                    model_switches.append(metrics.get("model_switch_count", 0))
            
            if success_rates:
                avg_success_rate = sum(success_rates) / len(success_rates)
                avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None
                avg_switches = sum(model_switches) / len(model_switches) if model_switches else 0
                
                recommendations["estimated_time"] = avg_execution_time
                recommendations["confidence"] = min(len(similar_tasks) / 10.0, 1.0)  # 最多10个样本
                
                # 根据历史数据推荐
                if avg_success_rate < 0.7:
                    # 成功率低，建议使用推理模型
                    recommendations["recommended_model"] = "reasoning"
                elif task_complexity == TaskComplexity.COMPLEX:
                    recommendations["recommended_model"] = "reasoning"
                    recommendations["should_decompose"] = True
                elif avg_execution_time and avg_execution_time > 30.0:
                    recommendations["should_decompose"] = True
        
        return recommendations
    
    def _find_similar_tasks(self, task_description: str) -> List[Dict[str, Any]]:
        """查找相似任务的历史数据"""
        similar_tasks = []
        
        # 简单的关键词匹配（可以改进为更智能的相似度计算）
        task_keywords = set(task_description.lower().split())
        
        for task_desc, records in self.learning_data.items():
            desc_keywords = set(task_desc.lower().split())
            # 计算关键词重叠度
            overlap = len(task_keywords & desc_keywords) / max(len(task_keywords), len(desc_keywords), 1)
            
            if overlap > 0.3:  # 30% 重叠度
                similar_tasks.append({
                    "task_description": task_desc,
                    "records": records,
                    "similarity": overlap
                })
        
        # 按相似度排序
        similar_tasks.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similar_tasks[:5]  # 返回最相似的5个任务
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.metrics_history:
            return {
                "total_executions": 0,
                "average_success_rate": 0.0,
                "average_execution_time": 0.0,
                "total_adjustments": len(self.adjustments_history)
            }
        
        success_rates = [m.tool_success_rate for m in self.metrics_history]
        execution_times = [m.execution_time for m in self.metrics_history]
        
        return {
            "total_executions": len(self.metrics_history),
            "average_success_rate": sum(success_rates) / len(success_rates),
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0.0,
            "total_adjustments": len(self.adjustments_history),
            "recent_adjustments": [
                adj.to_dict() for adj in self.adjustments_history[-10:]
            ]
        }
    
    def update_adjustment_effectiveness(
        self,
        adjustment: StrategyAdjustment,
        effectiveness: float
    ):
        """
        更新策略调整的效果
        
        Args:
            adjustment: 策略调整
            effectiveness: 效果（0-1，1表示完全有效）
        """
        adjustment.effectiveness = effectiveness
        logger.info(f"策略调整效果更新: {adjustment.adjustment_type} - {effectiveness:.2%}")

