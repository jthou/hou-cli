"""测试执行计划生成器"""
import pytest
from backend.core.agent.planning.execution_planner import ExecutionPlanner
from backend.core.agent.models import SubTask, TaskComplexity


class TestExecutionPlanner:
    """测试 ExecutionPlanner 类"""
    
    @pytest.fixture
    def execution_planner(self):
        """创建 ExecutionPlanner 实例"""
        return ExecutionPlanner()
    
    def test_plan_execution_single_task(self, execution_planner):
        """测试单个任务的执行计划"""
        subtasks = [
            SubTask(name="任务1", description="描述1")
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        assert len(plan.subtasks) == 1
        assert len(plan.parallel_groups) == 1
        assert len(plan.parallel_groups[0]) == 1
        assert plan.parallel_groups[0][0] == "任务1"
    
    def test_plan_execution_with_dependencies(self, execution_planner):
        """测试带依赖关系的执行计划"""
        subtasks = [
            SubTask(name="任务1", description="描述1"),
            SubTask(name="任务2", description="描述2", dependencies=["任务1"]),
            SubTask(name="任务3", description="描述3", dependencies=["任务1"])
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        # 任务1应该先执行，任务2和任务3可以并行执行
        assert len(plan.parallel_groups) == 2
        assert "任务1" in plan.parallel_groups[0]
        assert "任务2" in plan.parallel_groups[1] or "任务3" in plan.parallel_groups[1]
    
    def test_plan_execution_parallel_tasks(self, execution_planner):
        """测试并行任务的执行计划"""
        subtasks = [
            SubTask(name="任务1", description="描述1"),
            SubTask(name="任务2", description="描述2"),
            SubTask(name="任务3", description="描述3")
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        # 所有任务应该可以并行执行
        assert len(plan.parallel_groups) == 1
        assert len(plan.parallel_groups[0]) == 3
    
    def test_plan_execution_sequential_tasks(self, execution_planner):
        """测试顺序任务的执行计划"""
        subtasks = [
            SubTask(name="任务1", description="描述1"),
            SubTask(name="任务2", description="描述2", dependencies=["任务1"]),
            SubTask(name="任务3", description="描述3", dependencies=["任务2"])
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        # 应该有三个顺序执行的组
        assert len(plan.parallel_groups) == 3
    
    def test_plan_execution_empty_subtasks(self, execution_planner):
        """测试空子任务列表的执行计划"""
        plan = execution_planner.plan_execution([], "测试任务")
        
        assert len(plan.subtasks) == 0
        assert len(plan.parallel_groups) == 0
        assert plan.estimated_total_time == 0
    
    def test_plan_execution_estimated_time(self, execution_planner):
        """测试预估执行时间"""
        subtasks = [
            SubTask(name="任务1", description="描述1", estimated_time=30),
            SubTask(name="任务2", description="描述2", estimated_time=60),
            SubTask(name="任务3", description="描述3", estimated_time=45)
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        # 如果所有任务并行，总时间应该是最大时间
        # 如果顺序执行，总时间应该是所有时间之和
        assert plan.estimated_total_time > 0
    
    def test_detect_cycles(self, execution_planner):
        """测试循环依赖检测"""
        subtasks = [
            SubTask(name="任务1", description="描述1", dependencies=["任务2"]),
            SubTask(name="任务2", description="描述2", dependencies=["任务1"])
        ]
        
        plan = execution_planner.plan_execution(subtasks, "测试任务")
        
        # 即使有循环依赖，也应该生成计划（但会警告）
        assert len(plan.subtasks) == 2

