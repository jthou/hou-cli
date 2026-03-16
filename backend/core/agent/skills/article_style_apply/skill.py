#!/usr/bin/env python3
"""风格模仿技能 - 按写作画像润色、模仿风格"""

from typing import Dict, Any, Optional
from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.writing_profile import get_profile_block_for_prompt


def _extract_user_question(task: str) -> str:
    """从 task 中提取【用户本次提问】后的内容"""
    marker = "【用户本次提问】"
    idx = task.find(marker)
    if idx >= 0:
        return task[idx + len(marker) :].strip()
    return task.strip()


class ArticleStyleApplySkill(Skill):
    """风格模仿技能 - 按写作画像（范文、喜好）润色文本"""

    def __init__(self):
        super().__init__(
            name="article_style_apply",
            description=(
                "根据写作画像中的范文、喜好和表述习惯，对用户提供的文本进行润色或风格模仿。"
                "适用于写作助手场景：用户说「按我的风格润色」「模仿范文风格」「改写成我的风格」等。"
            ),
            version="1.0.0",
            category="writing",
            priority="P1",
            parameters=[
                SkillParameter(name="input", type="string", description="用户输入（含待润色文本和参考块）", required=True),
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
            profile_block = get_profile_block_for_prompt()

            if not profile_block.strip():
                return SkillResult(
                    success=False,
                    error="未配置写作画像。请先在设置中配置喜好、表述习惯或范文，再使用风格模仿。",
                )

            self.report_progress("正在按写作画像润色...")

            prompt = f"""
请根据以下作者画像，对用户提供的文本进行润色或风格模仿。严格遵循画像中的喜好、表述习惯与范文风格。

{profile_block}

用户输入与待润色文本：
{task}

要求：
1. 保持原文核心信息和逻辑
2. 用画像中的表述方式、用词习惯、句式风格改写
3. 不要输出解释，直接输出润色后的完整文本
"""
            response = await llm_service.chat([{"role": "user", "content": prompt}])
            polished = (response or "").strip()

            self.report_progress("风格润色完成")
            return SkillResult(
                success=True,
                data={"polished": polished, "user_question": user_question},
            )
        except Exception as e:
            self.report_progress(f"执行过程中发生错误: {str(e)}")
            return SkillResult(
                success=False,
                error=f"风格润色失败: {str(e)}",
            )


skill_instance = ArticleStyleApplySkill()
