"""技能注册表"""
import logging
from typing import Dict, Optional, List
from pathlib import Path
import yaml

from backend.core.agent.skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """技能注册表，管理所有可用技能"""
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_configs: Dict[str, dict] = {}
    
    def register(self, skill: Skill):
        """注册技能"""
        if skill.name in self._skills:
            logger.warning(f"技能 {skill.name} 已存在，将被覆盖")
        
        self._skills[skill.name] = skill
        logger.info(f"技能已注册: {skill.name} (v{skill.version})")
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)
    
    def get_all(self) -> List[Skill]:
        """获取所有技能"""
        return list(self._skills.values())
    
    def load_from_yaml(self, yaml_path: Path):
        """从 YAML 文件加载技能配置"""
        if not yaml_path.exists():
            logger.warning(f"技能配置文件不存在: {yaml_path}")
            return
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._skill_configs[config['name']] = config
            logger.info(f"技能配置已加载: {config['name']} from {yaml_path}")
        except Exception as e:
            logger.error(f"加载技能配置失败 {yaml_path}: {e}", exc_info=True)
    
    def load_from_directory(self, directory: Path):
        """从目录加载所有技能配置
        
        支持的目录结构：
        1. 直接包含 YAML 文件：skill.yaml
        2. 技能子目录：skill_name/skill.yaml
        """
        if not directory.exists():
            logger.warning(f"技能配置目录不存在: {directory}")
            return
        
        # 方式 1: 直接包含 YAML 文件
        for yaml_file in directory.glob("*.yaml"):
            self.load_from_yaml(yaml_file)
        
        # 方式 2: 技能子目录（推荐）
        for skill_dir in directory.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                skill_yaml = skill_dir / "skill.yaml"
                if skill_yaml.exists():
                    self.load_from_yaml(skill_yaml)
    
    def get_config(self, name: str) -> Optional[dict]:
        """获取技能配置"""
        return self._skill_configs.get(name)
    
    def match(self, user_input: str) -> Optional[Skill]:
        """
        根据用户输入匹配技能
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            匹配的技能，如果没有匹配则返回 None
        """
        # 简单的关键词匹配（后续可以改进为更智能的匹配）
        user_input_lower = user_input.lower()
        
        for skill in self._skills.values():
            # 检查技能名称和描述中是否包含关键词
            if skill.name.lower() in user_input_lower:
                return skill
            
            # 检查描述中的关键词
            description_keywords = [
                "视频", "摘要", "字幕", "下载", "分析",
                "video", "summary", "subtitle", "download", "analyze"
            ]
            
            for keyword in description_keywords:
                if keyword in user_input_lower and keyword in skill.description.lower():
                    return skill
        
        return None

