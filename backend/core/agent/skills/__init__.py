"""技能系统模块"""
from backend.core.agent.skills.base import Skill, SkillResult
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.executor import SkillExecutor

__all__ = ['Skill', 'SkillResult', 'SkillRegistry', 'SkillExecutor']


