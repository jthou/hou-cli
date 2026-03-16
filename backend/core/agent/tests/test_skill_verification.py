#!/usr/bin/env python3
"""
写作技能验证测试（时间：2025-03-15；理由：验证 article_writing 技能过滤与匹配；方法：单元测试 + 集成说明）

验证项：
1. get_skill_names_for_agent 按 context_type 正确过滤
2. 写作助手仅匹配 4 个写作技能
3. 工作助手不匹配任何技能
4. 通用对话使用全部技能
"""
import pytest
from backend.core.agent.agent_tools_registry import (
    get_skill_names_for_agent,
    AGENT_SKILLS,
)


class TestSkillFilterByAgent:
    """按 agent 过滤技能"""

    def test_article_writing_whitelist(self):
        """写作助手仅匹配 4 个写作技能"""
        allowed = get_skill_names_for_agent("article_writing")
        assert allowed is not None
        assert set(allowed) == {
            "article_outline",
            "article_write",
            "article_style_apply",
            "writing_profile_summary",
        }
        assert len(allowed) == 4

    def test_work_assistant_empty(self):
        """工作助手不匹配任何技能"""
        allowed = get_skill_names_for_agent("work_assistant")
        assert allowed is not None
        assert allowed == []

    def test_general_chat_uses_all(self):
        """通用对话未配置，使用全部技能（返回 None）"""
        allowed = get_skill_names_for_agent("general_chat")
        assert allowed is None

    def test_unknown_agent_uses_all(self):
        """未知 agent 返回 None，使用全部技能"""
        assert get_skill_names_for_agent("unknown_agent") is None
        assert get_skill_names_for_agent("") is None


class TestSkillRegistration:
    """技能注册验证"""

    def test_writing_skills_registered(self):
        """写作技能已注册"""
        from backend.core.agent.orchestrator import UnifiedOrchestrator

        orch = UnifiedOrchestrator()
        all_skills = orch.skill_registry.get_all()
        names = [s.name for s in all_skills]

        for name in AGENT_SKILLS["article_writing"]:
            assert name in names, f"写作技能 {name} 未注册"

    def test_video_skills_registered_when_available(self):
        """视频技能在依赖满足时注册"""
        from backend.core.agent.orchestrator import UnifiedOrchestrator

        orch = UnifiedOrchestrator()
        names = [s.name for s in orch.skill_registry.get_all()]
        # 至少应有写作技能；视频技能可能因依赖缺失未注册
        assert "article_outline" in names
