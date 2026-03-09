"""Orchestrator 技能工具方法测试：_extract_skill_parameters、_format_skill_result"""
import pytest
from unittest.mock import MagicMock
from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.skills.base import SkillResult, SkillParameter


class TestExtractSkillParameters:
    """_extract_skill_parameters 测试"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_extract_single_url(self, orchestrator):
        """从任务中提取单个 URL"""
        skill = MagicMock()
        skill.name = "video_downloader"
        skill.parameters = []
        task = "下载这个视频 https://example.com/video.mp4"
        params = orchestrator._extract_skill_parameters(task, skill)
        assert params.get("url") == "https://example.com/video.mp4"

    def test_extract_no_url_returns_empty(self, orchestrator):
        """无 URL 时返回空参数字典"""
        skill = MagicMock()
        skill.name = "some_skill"
        skill.parameters = []
        task = "随便说点什么"
        params = orchestrator._extract_skill_parameters(task, skill)
        assert isinstance(params, dict)
        assert "url" not in params or params.get("url") is None


class TestFormatSkillResult:
    """_format_skill_result 测试"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_format_failure(self, orchestrator):
        """失败时返回错误信息"""
        skill = MagicMock()
        skill.name = "any_skill"
        result = SkillResult(success=False, error="网络超时")
        text = orchestrator._format_skill_result(skill, result)
        assert "❌" in text or "失败" in text
        assert "网络超时" in text

    def test_format_success_generic(self, orchestrator):
        """通用技能成功时返回 JSON 或完成提示"""
        skill = MagicMock()
        skill.name = "generic_skill"
        result = SkillResult(success=True, data={"key": "value"})
        text = orchestrator._format_skill_result(skill, result)
        assert "value" in text or "完成" in text

    def test_format_success_empty_data(self, orchestrator):
        """成功但无 data 时返回完成提示"""
        skill = MagicMock()
        skill.name = "simple_skill"
        result = SkillResult(success=True, data=None)
        text = orchestrator._format_skill_result(skill, result)
        assert "完成" in text or "✅" in text
