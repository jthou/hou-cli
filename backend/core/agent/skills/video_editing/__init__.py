"""视频编辑技能模块"""
from backend.core.agent.skills.video_editing.video_cut_skill import VideoCutSkill

# 为了兼容 orchestrator 的自动加载机制，导出 VideoEditingSkill
# orchestrator 会从目录名 video_editing 推导类名 VideoEditingSkill
VideoEditingSkill = VideoCutSkill

__all__ = ['VideoCutSkill', 'VideoEditingSkill']

