#!/usr/bin/env python3
"""大纲生成技能 - 从主题/草稿生成结构化文章大纲"""

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


class ArticleOutlineSkill(Skill):
    """大纲生成技能 - 根据主题和参考块生成结构化大纲"""

    def __init__(self):
        super().__init__(
            name="article_outline",
            description=(
                "根据用户提供的主题、草稿或参考资料，生成结构化文章大纲。"
                "适用于写作助手场景：用户说「生成大纲」「写个提纲」「帮我列个大纲」等。"
            ),
            version="1.0.0",
            category="writing",
            priority="P1",
            parameters=[
                SkillParameter(
                    name="input",
                    type="string",
                    description="用户输入（含参考块和提问）",
                    required=True,
                ),
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

            self.report_progress("正在生成大纲...")

            prompt = f"""
基于以下用户输入和参考资料，生成结构化文章大纲。

用户输入/主题：{user_question}

{task}

{profile_block}

要求：
1. 大纲应包含：标题、引言、主体（3-5 章，每章有小节）、结论
2. 使用 Markdown 格式：## 标题、### 小节
3. 每节可简要注明要点（1-2 句）
4. 风格与表述需符合上述作者画像（若有）

请直接输出结构化的 Markdown 大纲，不要输出 JSON 或其它格式。
"""
            response = await llm_service.chat([{"role": "user", "content": prompt}])
            outline = (response or "").strip()

            self.report_progress("大纲生成完成")
            return SkillResult(
                success=True,
                data={"outline": outline, "user_question": user_question},
            )
        except Exception as e:
            self.report_progress(f"执行过程中发生错误: {str(e)}")
            return SkillResult(
                success=False,
                error=f"大纲生成失败: {str(e)}",
            )


skill_instance = ArticleOutlineSkill()
