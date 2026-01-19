"""执行计划生成器 - 根据子任务创建执行计划，识别依赖关系和并行执行机会"""
import logging
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict, deque
from backend.core.agent.models import SubTask, ExecutionPlan, TaskComplexity
from backend.services.llm.llm_service import LLMService
from backend.services.llm.model_config import get_model_config_manager

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """执行计划生成器
    
    根据子任务列表创建执行计划，分析依赖关系，识别可并行执行的任务。
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化执行计划生成器
        
        Args:
            llm_service: LLM 服务实例（可选，用于 LLM 辅助规划）
        """
        self.llm_service = llm_service
        self.config_manager = get_model_config_manager()
    
    def _build_dependency_graph(self, subtasks: List[SubTask]) -> Dict[str, Set[str]]:
        """
        构建依赖关系图
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            依赖图（任务名称 -> 依赖的任务名称集合）
        """
        graph = defaultdict(set)
        task_names = {task.name for task in subtasks}
        
        for task in subtasks:
            for dep in task.dependencies:
                if dep in task_names:
                    graph[task.name].add(dep)
                else:
                    logger.warning(f"子任务 '{task.name}' 依赖不存在的任务 '{dep}'")
        
        return dict(graph)
    
    def _detect_cycles(self, dependency_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        检测循环依赖
        
        Args:
            dependency_graph: 依赖图
            
        Returns:
            循环依赖列表
        """
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            rec_stack.remove(node)
            path.pop()
        
        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _identify_parallel_groups(
        self,
        subtasks: List[SubTask],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """
        识别可以并行执行的任务组
        
        Args:
            subtasks: 子任务列表
            dependency_graph: 依赖图
            
        Returns:
            并行执行组列表（每个组是一个任务名称列表）
        """
        # 构建反向依赖图（哪些任务依赖此任务）
        reverse_graph = defaultdict(set)
        for task_name, deps in dependency_graph.items():
            for dep in deps:
                reverse_graph[dep].add(task_name)
        
        # 找到所有没有依赖的任务（可以立即执行）
        task_names = {task.name for task in subtasks}
        ready_tasks = [task.name for task in subtasks if not dependency_graph.get(task.name)]
        
        if not ready_tasks:
            # 如果没有可以立即执行的任务，检查是否有循环依赖
            cycles = self._detect_cycles(dependency_graph)
            if cycles:
                logger.warning(f"检测到循环依赖: {cycles}")
                # 如果有循环依赖，返回所有任务作为一个组（强制并行，但会有问题）
                return [[task.name for task in subtasks]]
            else:
                # 没有循环依赖但没有可执行任务，说明所有任务都有依赖
                # 这种情况不应该发生，但为了安全返回空列表
                return []
        
        # 使用拓扑排序识别可以并行执行的任务
        parallel_groups = []
        completed = set()
        in_degree = {task.name: len(dependency_graph.get(task.name, set())) for task in subtasks}
        
        while len(completed) < len(subtasks):
            # 找到所有可以执行的任务（依赖已完成）
            current_group = []
            for task_name in task_names:
                if task_name not in completed and in_degree[task_name] == 0:
                    current_group.append(task_name)
            
            if not current_group:
                # 没有可以执行的任务，可能是有循环依赖
                remaining = task_names - completed
                if remaining:
                    logger.warning(f"无法继续执行，剩余任务: {remaining}")
                    # 将剩余任务作为一个组（可能会有问题，但至少可以尝试）
                    parallel_groups.append(list(remaining))
                break
            
            parallel_groups.append(current_group)
            completed.update(current_group)
            
            # 更新依赖计数
            for task_name in current_group:
                for dependent in reverse_graph.get(task_name, set()):
                    in_degree[dependent] -= 1
        
        return parallel_groups
    
    def _generate_execution_order(
        self,
        subtasks: List[SubTask],
        dependency_graph: Dict[str, Set[str]],
        parallel_groups: List[List[str]]
    ) -> List[str]:
        """
        生成执行顺序（拓扑排序）
        
        Args:
            subtasks: 子任务列表
            dependency_graph: 依赖图
            parallel_groups: 并行执行组
            
        Returns:
            执行顺序（任务名称列表）
        """
        execution_order = []
        for group in parallel_groups:
            execution_order.extend(group)
        
        return execution_order
    
    def _estimate_total_time(
        self,
        subtasks: List[SubTask],
        parallel_groups: List[List[str]]
    ) -> int:
        """
        估算总执行时间
        
        Args:
            subtasks: 子任务列表
            parallel_groups: 并行执行组
            
        Returns:
            预估总时间（秒）
        """
        total_time = 0
        task_times = {task.name: task.estimated_time or 30 for task in subtasks}
        
        for group in parallel_groups:
            # 并行组的执行时间是组内最长任务的执行时间
            group_time = max([task_times.get(task_name, 30) for task_name in group], default=30)
            total_time += group_time
        
        return total_time
    
    def plan_execution(
        self,
        subtasks: List[SubTask],
        task_description: str = "",
        use_llm: bool = False
    ) -> ExecutionPlan:
        """
        创建执行计划
        
        Args:
            subtasks: 子任务列表
            task_description: 原始任务描述
            use_llm: 是否使用 LLM 辅助规划
            
        Returns:
            执行计划
        """
        if not subtasks:
            logger.warning("子任务列表为空，创建空执行计划")
            return ExecutionPlan(
                task_description=task_description,
                subtasks=[],
                parallel_groups=[],
                sequential_tasks=[],
                estimated_total_time=0
            )
        
        logger.info(f"开始创建执行计划，共 {len(subtasks)} 个子任务")
        
        # 1. 构建依赖图
        dependency_graph = self._build_dependency_graph(subtasks)
        logger.debug(f"依赖图: {dependency_graph}")
        
        # 2. 检测循环依赖
        cycles = self._detect_cycles(dependency_graph)
        if cycles:
            logger.warning(f"检测到循环依赖: {cycles}")
            # 可以选择：抛出异常、忽略循环、或尝试修复
        
        # 3. 识别并行执行组
        parallel_groups = self._identify_parallel_groups(subtasks, dependency_graph)
        logger.info(f"识别到 {len(parallel_groups)} 个并行执行组")
        
        # 4. 生成执行顺序
        execution_order = self._generate_execution_order(subtasks, dependency_graph, parallel_groups)
        logger.debug(f"执行顺序: {execution_order}")
        
        # 5. 估算总时间
        estimated_total_time = self._estimate_total_time(subtasks, parallel_groups)
        logger.info(f"预估总执行时间: {estimated_total_time} 秒")
        
        # 6. 创建执行计划
        plan = ExecutionPlan(
            task_description=task_description,
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            sequential_tasks=execution_order,
            estimated_total_time=estimated_total_time,
            status="pending"
        )
        
        logger.info("执行计划创建完成")
        return plan
    
    async def plan_execution_with_llm(
        self,
        subtasks: List[SubTask],
        task_description: str = ""
    ) -> ExecutionPlan:
        """
        使用 LLM 辅助创建执行计划（可选）
        
        Args:
            subtasks: 子任务列表
            task_description: 原始任务描述
            
        Returns:
            执行计划
        """
        if not self.llm_service:
            logger.warning("LLM 服务未提供，使用规则基础规划")
            return self.plan_execution(subtasks, task_description, use_llm=False)
        
        # 先使用规则基础规划
        plan = self.plan_execution(subtasks, task_description, use_llm=False)
        
        # 可以使用 LLM 优化执行计划（未来扩展）
        # 例如：优化并行组、调整执行顺序、改进错误处理策略等
        
        return plan

