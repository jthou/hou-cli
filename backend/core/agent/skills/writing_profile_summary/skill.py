#!/usr/bin/env python3
"""写作画像总结技能 - 从用户过往文章自动提炼写作画像"""

from typing import Dict, Any, Optional
from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.writing_profile import (
    WritingProfile,
    SampleArticle,
    save_writing_profile,
    get_profile_path,
)


def _extract_user_question(task: str) -> str:
    """从 task 中提取【用户本次提问】后的内容"""
    marker = "【用户本次提问】"
    idx = task.find(marker)
    if idx >= 0:
        return task[idx + len(marker) :].strip()
    return task.strip()


class WritingProfileSummarySkill(Skill):
    """写作画像总结技能 - 从用户提供的文章分析并提炼写作画像"""

    def __init__(self):
        super().__init__(
            name="writing_profile_summary",
            description=(
                "根据用户提供的多篇过往文章，分析并提炼写作画像（喜好、表述习惯、风格特点）。"
                "适用于写作助手场景：用户说「生成写作画像」「分析我的风格」「总结我的写作习惯」等。"
            ),
            version="1.0.0",
            category="writing",
            priority="P1",
            parameters=[
                SkillParameter(name="input", type="string", description="用户输入（含待分析的文章内容）", required=True),
            ],
        )

    async def execute(
        self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        try:
            if context is None:
                context = {}
            if context.get("progress_callback"):
                self.set_progress_callback(context["progress_callback"])
            llm_service = context.get("llm_service")
            if llm_service is None:
                from backend.services.llm.llm_service import LLMService
                llm_service = LLMService()

            task = parameters.get("input", "")
            user_question = _extract_user_question(task)

            self.report_progress("正在分析文章风格...")

            prompt = f"""
请分析以下用户提供的文章，提炼其写作画像。输出格式为 JSON：

{{
  "preferences": ["喜好1", "喜好2", ...],
  "style_notes": "习惯的表述方式、用词特点、句式风格等（一段话）",
  "summary": "风格总结（一句话概括）"
}}

用户输入：
{user_question}

待分析的文章：
{task}

要求：
1. preferences：列出 3-10 条写作偏好（如：善用类比、结论先行、段落开头点题等）
2. style_notes：综合描述表述习惯、用词、句式、语气（200-500 字）
3. summary：一句话概括整体风格
4. 只输出 JSON，不要输出其它内容
"""
            response = await llm_service.chat([{"role": "user", "content": prompt}])
            import json
            import re
            text = (response or "").strip()
            json_match = re.search(r"\{[\s\S]*\}", text)
            if not json_match:
                return SkillResult(
                    success=False,
                    error="LLM 未能返回有效的 JSON 格式，请重试。",
                )
            try:
                parsed = json.loads(json_match.group())
            except json.JSONDecodeError:
                return SkillResult(success=False, error="解析写作画像 JSON 失败")

            preferences = parsed.get("preferences") or []
            style_notes = parsed.get("style_notes") or ""
            summary = parsed.get("summary") or ""

            profile = WritingProfile(
                preferences=preferences if isinstance(preferences, list) else [str(p) for p in preferences],
                style_notes=str(style_notes),
                sample_articles=[],  # 不自动添加范文，用户可后续手动添加
                extra={"summary": summary},
            )
            path = save_writing_profile(profile)
            self.report_progress("写作画像已保存")

            return SkillResult(
                success=True,
                data={
                    "preferences": profile.preferences,
                    "style_notes": profile.style_notes,
                    "summary": summary,
                    "profile_path": str(path),
                },
            )
        except Exception as e:
            from backend.services.llm.user_facing_error import llm_error_message_for_user

            friendly = llm_error_message_for_user(e)
            detail = friendly if friendly else str(e)
            self.report_progress(f"执行过程中发生错误: {detail}")
            return SkillResult(
                success=False,
                error=f"写作画像总结失败: {detail}",
            )


skill_instance = WritingProfileSummarySkill()
