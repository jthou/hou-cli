"""编排系统数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class SubTask:
    """子任务"""
    name: str
    description: str
    required_tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他子任务名称
    estimated_complexity: TaskComplexity = TaskComplexity.SIMPLE
    recommended_model: Optional[str] = None  # 推荐的模型类型（"chat", "code", "reasoning"）
    estimated_time: Optional[int] = None  # 预估执行时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "required_tools": self.required_tools,
            "dependencies": self.dependencies,
            "estimated_complexity": self.estimated_complexity.value,
            "recommended_model": self.recommended_model,
            "estimated_time": self.estimated_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubTask':
        """从字典创建"""
        return cls(
            name=data["name"],
            description=data["description"],
            required_tools=data.get("required_tools", []),
            dependencies=data.get("dependencies", []),
            estimated_complexity=TaskComplexity(data.get("estimated_complexity", "simple")),
            recommended_model=data.get("recommended_model"),
            estimated_time=data.get("estimated_time"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""  # 原始任务描述
    subtasks: List[SubTask] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)  # 可以并行执行的任务组（任务名称列表）
    sequential_tasks: List[str] = field(default_factory=list)  # 需要顺序执行的任务（任务名称列表）
    error_handling_strategy: Dict[str, Any] = field(default_factory=dict)
    estimated_total_time: Optional[int] = None  # 预估总执行时间（秒）
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, in_progress, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "task_description": self.task_description,
            "subtasks": [task.to_dict() for task in self.subtasks],
            "parallel_groups": self.parallel_groups,
            "sequential_tasks": self.sequential_tasks,
            "error_handling_strategy": self.error_handling_strategy,
            "estimated_total_time": self.estimated_total_time,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionPlan':
        """从字典创建"""
        return cls(
            plan_id=data.get("plan_id", str(uuid.uuid4())),
            task_description=data.get("task_description", ""),
            subtasks=[SubTask.from_dict(task_data) for task_data in data.get("subtasks", [])],
            parallel_groups=data.get("parallel_groups", []),
            sequential_tasks=data.get("sequential_tasks", []),
            error_handling_strategy=data.get("error_handling_strategy", {}),
            estimated_total_time=data.get("estimated_total_time"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExecutionState:
    """执行状态（用于恢复）"""
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_iteration: int = 0
    tool_call_history: List[Dict[str, Any]] = field(default_factory=list)
    last_tool_result: Optional[Dict[str, Any]] = None
    current_model: Optional[str] = None  # 当前使用的模型
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "current_iteration": self.current_iteration,
            "tool_call_history": self.tool_call_history,
            "last_tool_result": self.last_tool_result,
            "current_model": self.current_model,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionState':
        """从字典创建"""
        return cls(
            session_id=data["session_id"],
            messages=data.get("messages", []),
            current_iteration=data.get("current_iteration", 0),
            tool_call_history=data.get("tool_call_history", []),
            last_tool_result=data.get("last_tool_result"),
            current_model=data.get("current_model"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )
    
    def save(self, file_path: str):
        """保存状态到文件"""
        import json
        from pathlib import Path
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        self.updated_at = datetime.now()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> 'ExecutionState':
        """从文件加载状态"""
        import json
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"执行状态文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls.from_dict(data)


@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_name: str
    requires_reasoning: bool = False  # 是否需要推理
    requires_code: bool = False       # 是否需要代码能力
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    recommended_model: Optional[str] = None  # 推荐的模型类型（"chat", "code", "reasoning"）
    estimated_time: Optional[int] = None  # 预估执行时间（秒）
    can_parallel: bool = True  # 是否可以并行执行
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "requires_reasoning": self.requires_reasoning,
            "requires_code": self.requires_code,
            "complexity": self.complexity.value,
            "recommended_model": self.recommended_model,
            "estimated_time": self.estimated_time,
            "can_parallel": self.can_parallel,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolMetadata':
        """从字典创建"""
        return cls(
            tool_name=data["tool_name"],
            requires_reasoning=data.get("requires_reasoning", False),
            requires_code=data.get("requires_code", False),
            complexity=TaskComplexity(data.get("complexity", "simple")),
            recommended_model=data.get("recommended_model"),
            estimated_time=data.get("estimated_time"),
            can_parallel=data.get("can_parallel", True),
            metadata=data.get("metadata", {})
        )

