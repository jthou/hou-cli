"""深度研究数据模型"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ResearchDepth(Enum):
    """研究深度"""
    SHALLOW = "shallow"  # 浅层：1-2轮搜索
    MEDIUM = "medium"    # 中等：3-5轮搜索
    DEEP = "deep"        # 深度：5+轮搜索


@dataclass
class ResearchFinding:
    """研究发现"""
    source: str  # 信息来源（工具名称）
    content: str  # 内容
    relevance_score: float = 0.0  # 相关性分数（0-1）
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchFinding':
        """从字典创建"""
        return cls(
            source=data["source"],
            content=data["content"],
            relevance_score=data.get("relevance_score", 0.0),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )


@dataclass
class ResearchAnalysis:
    """研究分析"""
    key_points: List[str] = field(default_factory=list)  # 关键点
    contradictions: List[str] = field(default_factory=list)  # 矛盾点
    gaps: List[str] = field(default_factory=list)  # 信息缺口
    confidence: float = 0.0  # 置信度（0-1）
    next_steps: List[str] = field(default_factory=list)  # 下一步研究建议
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key_points": self.key_points,
            "contradictions": self.contradictions,
            "gaps": self.gaps,
            "confidence": self.confidence,
            "next_steps": self.next_steps,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchAnalysis':
        """从字典创建"""
        return cls(
            key_points=data.get("key_points", []),
            contradictions=data.get("contradictions", []),
            gaps=data.get("gaps", []),
            confidence=data.get("confidence", 0.0),
            next_steps=data.get("next_steps", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class ResearchStep:
    """研究步骤"""
    name: str  # 步骤名称
    description: str  # 步骤描述
    tools: List[str] = field(default_factory=list)  # 使用的工具
    tool_params: Dict[str, Any] = field(default_factory=dict)  # 工具参数
    priority: int = 0  # 优先级（数字越大优先级越高）
    completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
            "tool_params": self.tool_params,
            "priority": self.priority,
            "completed": self.completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchStep':
        """从字典创建"""
        return cls(
            name=data["name"],
            description=data["description"],
            tools=data.get("tools", []),
            tool_params=data.get("tool_params", {}),
            priority=data.get("priority", 0),
            completed=data.get("completed", False)
        )


@dataclass
class ResearchPlan:
    """研究计划"""
    question: str  # 研究问题
    depth: ResearchDepth  # 研究深度
    steps: List[ResearchStep] = field(default_factory=list)  # 研究步骤
    research_angles: List[str] = field(default_factory=list)  # 研究角度
    information_needs: List[str] = field(default_factory=list)  # 需要收集的信息类型
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "question": self.question,
            "depth": self.depth.value,
            "steps": [step.to_dict() for step in self.steps],
            "research_angles": self.research_angles,
            "information_needs": self.information_needs,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchPlan':
        """从字典创建"""
        return cls(
            question=data["question"],
            depth=ResearchDepth(data.get("depth", "medium")),
            steps=[ResearchStep.from_dict(step_data) for step_data in data.get("steps", [])],
            research_angles=data.get("research_angles", []),
            information_needs=data.get("information_needs", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        )


@dataclass
class ResearchReport:
    """研究报告"""
    question: str  # 研究问题
    summary: str  # 摘要
    findings: List[ResearchFinding] = field(default_factory=list)  # 研究发现
    analysis: Optional[ResearchAnalysis] = None  # 分析结果
    conclusion: str = ""  # 结论
    sources: List[str] = field(default_factory=list)  # 信息来源
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "question": self.question,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "conclusion": self.conclusion,
            "sources": self.sources,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchReport':
        """从字典创建"""
        return cls(
            question=data["question"],
            summary=data.get("summary", ""),
            findings=[ResearchFinding.from_dict(f_data) for f_data in data.get("findings", [])],
            analysis=ResearchAnalysis.from_dict(data["analysis"]) if data.get("analysis") else None,
            conclusion=data.get("conclusion", ""),
            sources=data.get("sources", []),
            generated_at=datetime.fromisoformat(data.get("generated_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )

