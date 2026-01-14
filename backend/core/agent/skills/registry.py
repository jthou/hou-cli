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
        
        # 检测是否为本地文件路径（优先于 URL 检测）
        import re
        from pathlib import Path
        
        # 检测本地文件路径模式
        local_file_patterns = [
            r'^[~/]',  # 以 ~ 或 / 开头
            r'\.mp4\b',  # 包含 .mp4 扩展名
            r'\.avi\b',  # 包含 .avi 扩展名
            r'\.mkv\b',  # 包含 .mkv 扩展名
            r'\.mov\b',  # 包含 .mov 扩展名
            r'^[a-z]:\\',  # Windows 路径（如 C:\）
            r'/home/',  # Linux 路径
            r'/Users/',  # macOS 路径
        ]
        
        is_local_file = any(re.search(pattern, user_input, re.IGNORECASE) for pattern in local_file_patterns)
        
        # 检测 URL 模式
        url_patterns = [
            r'https?://',  # HTTP/HTTPS URL
            r'www\.',  # www. 开头
            r'bilibili\.com',  # Bilibili 域名
            r'youtube\.com',  # YouTube 域名
        ]
        
        is_url = any(re.search(pattern, user_input, re.IGNORECASE) for pattern in url_patterns)
        
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
            audio_keywords = ["音频", "audio", "分离", "提取"]
            subtitle_keywords = ["字幕", "subtitle", "srt", "转成", "转"]
            ffmpeg_keywords = ["ffmpeg"]
            whisper_keywords = ["whisper"]
            
            has_download = any(kw in user_input_lower for kw in download_keywords)
            has_summary = any(kw in user_input_lower for kw in summary_keywords)
            has_video = any(kw in user_input_lower for kw in video_keywords)
            has_audio = any(kw in user_input_lower for kw in audio_keywords)
            has_subtitle = any(kw in user_input_lower for kw in subtitle_keywords)
            has_ffmpeg = any(kw in user_input_lower for kw in ffmpeg_keywords)
            has_whisper = any(kw in user_input_lower for kw in whisper_keywords)
            
            # 3. 检查技能描述中的关键词
            skill_desc_lower = skill.description.lower()
            skill_has_download = any(kw in skill_desc_lower for kw in download_keywords)
            skill_has_summary = any(kw in skill_desc_lower for kw in summary_keywords)
            skill_has_video = any(kw in skill_desc_lower for kw in video_keywords)
            skill_has_audio = any(kw in skill_desc_lower for kw in audio_keywords)
            skill_has_subtitle = any(kw in skill_desc_lower for kw in subtitle_keywords)
            skill_has_ffmpeg = any(kw in skill_desc_lower for kw in ffmpeg_keywords)
            skill_has_whisper = any(kw in skill_desc_lower for kw in whisper_keywords)
            
            # 4. 本地文件路径特殊处理
            if is_local_file:
                # 如果是本地文件路径，优先匹配支持本地文件的技能
                if skill.name == 'video_extract_srt':
                    # video_extract_srt 专门用于提取字幕，最高优先级
                    score += 1000  # 最高优先级
                    # 如果用户明确提到字幕、srt、提取等关键词，额外加分
                    if has_subtitle or has_ffmpeg or has_whisper:
                        score += 500
                elif skill.name == 'video_downloader':
                    # video_downloader 只处理 URL，不处理本地文件
                    score -= 500  # 降低优先级
                elif skill.name in ['video_cut', 'video_merge', 'video_subtitle_overlay']:
                    # 其他视频编辑技能不支持音频提取和字幕生成，降低优先级
                    if has_audio or has_subtitle or has_ffmpeg or has_whisper:
                        score -= 300  # 降低优先级
            
            # 5. URL 特殊处理
            if is_url:
                # 如果是 URL，优先匹配下载技能
                if skill.name == 'video_downloader':
                    score += 300
                elif skill.name == 'video_extract_srt':
                    # video_extract_srt 支持 URL，但需要先下载
                    score += 200
                    # 如果用户明确提到字幕、srt、提取等关键词，额外加分
                    if has_subtitle or has_ffmpeg or has_whisper:
                        score += 300
            
            # 6. 计算匹配分数
            # 如果用户只要求下载，优先匹配专门的下载技能（但本地文件除外）
            if has_download and not has_summary and not has_subtitle and not is_local_file:
                if skill_has_download and not skill_has_summary and not skill_has_subtitle:
                    # 专门的下载技能（如 video_downloader）
                    score += 500
                elif skill_has_download and (skill_has_summary or skill_has_subtitle):
                    # 复合技能（如 video_extract_srt），分数较低
                    score += 100

            # 如果用户要求字幕提取（不要求摘要），优先匹配 video_extract_srt
            if has_subtitle and not has_summary:
                if skill.name == 'video_extract_srt':
                    score += 600  # 高优先级
                elif skill_has_subtitle and not skill_has_summary:
                    score += 400
                elif skill_has_subtitle and skill_has_summary:
                    score += 200  # 复合技能优先级较低

            # 如果用户要求摘要/分析，匹配摘要技能
            if has_summary:
                if skill_has_summary:
                    score += 300

            # 如果用户要求音频提取/ffmpeg/whisper（但不要求摘要），匹配字幕提取技能
            if (has_audio or has_ffmpeg or has_whisper) and not has_summary:
                if skill.name == 'video_extract_srt':
                    score += 400
                elif skill_has_audio or skill_has_ffmpeg or skill_has_whisper:
                    score += 200
            
            # 视频相关关键词匹配
            if has_video and skill_has_video:
                score += 50
            
            # 7. 优先级加分（P0 > P1 > P2）
            priority = getattr(skill, 'priority', 'P1')
            if priority == 'P0':
                score += 100
            elif priority == 'P1':
                score += 50
            
            # 8. 如果分数大于 0，添加到匹配列表
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

