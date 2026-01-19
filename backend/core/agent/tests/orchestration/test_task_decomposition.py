"""任务分解测试"""
import pytest
import json
from backend.core.agent.models import SubTask, ExecutionPlan, TaskComplexity


class TestTaskDecomposition:
    """任务分解测试"""
    
    def test_subtask_creation(self):
        """测试子任务创建"""
        subtask = SubTask(
            name="搜索信息",
            description="搜索相关信息",
            required_tools=["google_search"],
            dependencies=[],
            estimated_complexity=TaskComplexity.SIMPLE,
            recommended_model="chat"
        )
        
        assert subtask.name == "搜索信息"
        assert subtask.recommended_model == "chat"
        assert subtask.estimated_complexity == TaskComplexity.SIMPLE
    
    def test_subtask_serialization(self):
        """测试子任务序列化"""
        subtask = SubTask(
            name="测试任务",
            description="测试描述",
            required_tools=["tool1", "tool2"],
            dependencies=["task1"],
            estimated_complexity=TaskComplexity.MEDIUM,
            recommended_model="code"
        )
        
        # 转换为字典
        data = subtask.to_dict()
        assert data["name"] == "测试任务"
        assert data["estimated_complexity"] == "medium"
        assert data["recommended_model"] == "code"
        
        # 从字典创建
        restored = SubTask.from_dict(data)
        assert restored.name == subtask.name
        assert restored.estimated_complexity == subtask.estimated_complexity
    
    def test_execution_plan_creation(self):
        """测试执行计划创建"""
        subtasks = [
            SubTask(name="任务1", description="描述1", dependencies=[]),
            SubTask(name="任务2", description="描述2", dependencies=["任务1"]),
            SubTask(name="任务3", description="描述3", dependencies=[])
        ]
        
        plan = ExecutionPlan(
            subtasks=subtasks,
            parallel_groups=[["任务1", "任务3"]],  # 任务1和任务3可以并行
            sequential_tasks=["任务2"],  # 任务2需要等待任务1完成
            estimated_total_time=100
        )
        
        assert len(plan.subtasks) == 3
        assert len(plan.parallel_groups) == 1
        assert plan.estimated_total_time == 100
    
    def test_execution_plan_serialization(self):
        """测试执行计划序列化"""
        subtasks = [
            SubTask(name="任务1", description="描述1"),
            SubTask(name="任务2", description="描述2")
        ]
        
        plan = ExecutionPlan(
            subtasks=subtasks,
            parallel_groups=[["任务1", "任务2"]],
            sequential_tasks=[]
        )
        
        # 转换为字典
        data = plan.to_dict()
        assert len(data["subtasks"]) == 2
        assert len(data["parallel_groups"]) == 1
        
        # 从字典创建
        restored = ExecutionPlan.from_dict(data)
        assert len(restored.subtasks) == 2
        assert len(restored.parallel_groups) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

