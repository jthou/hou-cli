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
        user_input_lower = user_input.lower()
        
        # 收集所有匹配的技能及其匹配分数
        matched_skills = []
        
        for skill in self._skills.values():
            score = 0
            
            # 1. 精确名称匹配（最高优先级）
            if skill.name.lower() in user_input_lower:
                score += 1000
                matched_skills.append((score, skill))
                continue
            
            # 2. 检查用户输入中的关键词
            download_keywords = ["下载", "download", "下", "获取视频"]
            summary_keywords = ["摘要", "总结", "summary", "分析", "analyze", "阅读", "read"]
            video_keywords = ["视频", "video", "bilibili", "b站", "哔哩"]
            
            has_download = any(kw in user_input_lower for kw in download_keywords)
            has_summary = any(kw in user_input_lower for kw in summary_keywords)
            has_video = any(kw in user_input_lower for kw in video_keywords)
            
            # 3. 检查技能描述中的关键词
            skill_desc_lower = skill.description.lower()
            skill_has_download = any(kw in skill_desc_lower for kw in download_keywords)
            skill_has_summary = any(kw in skill_desc_lower for kw in summary_keywords)
            skill_has_video = any(kw in skill_desc_lower for kw in video_keywords)
            
            # 4. 计算匹配分数
            # 如果用户只要求下载，优先匹配专门的下载技能
            if has_download and not has_summary:
                if skill_has_download and not skill_has_summary:
                    # 专门的下载技能（如 video_downloader）
                    score += 500
                elif skill_has_download and skill_has_summary:
                    # 复合技能（如 video_summary），分数较低
                    score += 100
            
            # 如果用户要求摘要/分析，匹配摘要技能
            if has_summary:
                if skill_has_summary:
                    score += 300
            
            # 视频相关关键词匹配
            if has_video and skill_has_video:
                score += 50
            
            # 5. 优先级加分（P0 > P1 > P2）
            priority = getattr(skill, 'priority', 'P1')
            if priority == 'P0':
                score += 100
            elif priority == 'P1':
                score += 50
            
            # 6. 如果分数大于 0，添加到匹配列表
            if score > 0:
                matched_skills.append((score, skill))
        
        # 如果没有匹配的技能，返回 None
        if not matched_skills:
            return None
        
        # 按分数降序排序，返回最高分的技能
        matched_skills.sort(key=lambda x: x[0], reverse=True)
        best_match = matched_skills[0][1]
        
        logger.info(f"技能匹配: '{user_input[:50]}' -> {best_match.name} (分数: {matched_skills[0][0]})")
        if len(matched_skills) > 1:
            logger.debug(f"其他候选技能: {[(s.name, score) for score, s in matched_skills[1:3]]}")
        
        return best_match

