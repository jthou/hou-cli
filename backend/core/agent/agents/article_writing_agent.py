"""
写文章 Agent：按用户要求写文章，并遵循写作画像（喜好、表述习惯、范文）。
"""
from typing import Dict, Any, Optional
from pathlib import Path

from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent
from backend.core.agent.writing_profile import (
    load_writing_profile,
    WritingProfile,
)
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


def _build_profile_block(profile: WritingProfile, include_samples: bool = True) -> str:
    """将写作画像拼成一段注入到提示中的说明"""
    parts = []
    if profile.preferences:
        parts.append("【用户喜好】\n" + "\n".join(f"- {p}" for p in profile.preferences))
    if profile.style_notes:
        parts.append("【习惯的表述方式】\n" + profile.style_notes.strip())
    if include_samples and profile.sample_articles:
        sample_texts = profile.get_sample_contents(max_chars_per_sample=3500)
        if sample_texts:
            parts.append("【范文参考（请模仿其风格与表述）】\n\n" + "\n\n---\n\n".join(sample_texts))
    if not parts:
        return ""
    return "\n\n".join(parts)


class ArticleWritingAgent(BlogWritingAgent):
    """
    写文章 Agent：在 BlogWritingAgent 上加载写作画像，
    在大纲与正文生成中注入用户喜好、表述习惯与范文。
    """

    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        profile_path: Optional[Path] = None,
        profile: Optional[WritingProfile] = None,
    ):
        super().__init__(llm_service, tool_registry)
        self.name = "ArticleWritingAgent"
        self.description = "根据用户要求写文章，并遵循用户喜好、表述习惯与范文风格"
        if profile is not None:
            self._profile = profile
        else:
            self._profile = load_writing_profile(profile_path)

    @property
    def profile(self) -> WritingProfile:
        return self._profile

    def _profile_block(self, include_samples: bool = True) -> str:
        block = _build_profile_block(self._profile, include_samples=include_samples)
        if not block:
            return ""
        head = "\n\n以下为作者画像，请严格遵循其喜好与表述习惯：\n\n"
        return head + block

    async def _parse_user_input(
        self, task: str, context: Optional[Dict]
    ) -> Dict[str, Any]:
        parsed = await super()._parse_user_input(task, context or {})
        # 将画像简要放入 context 供后续步骤使用
        parsed["_profile_block"] = self._profile_block(include_samples=True)
        return parsed

    async def _create_outline(self, parsed_input: Dict[str, Any]) -> Dict[str, Any]:
        profile_block = (
            parsed_input.get("_profile_block", "")
            or self._profile_block(include_samples=True)
        )
        prompt = f"""
基于以下用户输入创建结构化文章大纲。

用户输入/主题: {parsed_input.get('topic', '未知')}
类型: {parsed_input.get('article_type', '通用')}
已有草稿要点: {parsed_input.get('draft_points', [])}
特殊要求: {parsed_input.get('special_requirements', [])}
{profile_block}

大纲应包含：1. 标题 2. 引言 3. 主体（3-5 章）4. 结论 5. 后续思考。
请返回 JSON 格式大纲；风格与表述需符合上述作者画像。
"""  # noqa: E501
        import json
        import re
        response = await self.llm_service.chat([{"role": "user", "content": prompt}])
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                outline = json.loads(json_match.group())
                outline["_profile_block"] = profile_block
                return outline
            except json.JSONDecodeError:
                pass
        base = await super()._create_outline(parsed_input)
        base["_profile_block"] = profile_block
        return base

    async def _write_section(
        self,
        section_info: Dict[str, Any],
        section_num: int,
        total_sections: int,
    ) -> str:
        profile_block = (
            section_info.get("_profile_block")
            or self._profile_block(include_samples=True)
        )
        prompt = f"""
撰写博客章节，需严格符合下方作者画像的风格与表述习惯。

章节标题: {section_info.get('title', f'第{section_num}部分')}
章节描述: {section_info.get('description', '')}
内容提示: {section_info.get('content_hint', '')}
当前第{section_num}部分，共{total_sections}部分。
长度约 200–400 字，可含小标题、列表或示例。
{profile_block}

返回该章节的完整正文。
"""
        return (await self.llm_service.chat([{"role": "user", "content": prompt}])).strip()

    async def _generate_detailed_content(
        self, outline: Dict[str, Any]
    ) -> Dict[str, Any]:
        profile_block = (
            outline.get("_profile_block")
            or self._profile_block(include_samples=True)
        )
        sections = outline.get("sections", [])
        for s in sections:
            s["_profile_block"] = profile_block
        return await super()._generate_detailed_content(outline)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行写文章任务；生成时会注入写作画像。"""
        return await super().execute(task)


def get_article_writing_agent(
    llm_service: Optional[LLMService] = None,
    tool_registry: Optional[ToolRegistry] = None,
    profile_path: Optional[Path] = None,
) -> ArticleWritingAgent:
    """工厂：获取写文章 Agent（若未传 llm/tool_registry 则创建默认）。"""
    if llm_service is None:
        llm_service = LLMService()
    if tool_registry is None:
        tool_registry = ToolRegistry()
    return ArticleWritingAgent(
        llm_service=llm_service,
        tool_registry=tool_registry,
        profile_path=profile_path,
    )
