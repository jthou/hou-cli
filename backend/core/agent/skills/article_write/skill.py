#!/usr/bin/env python3
"""撰写正文技能 - 根据大纲/参考块/用户指令撰写文章"""

from typing import Dict, Any, Optional
from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.agents.article_writing_agent import get_article_writing_agent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


def _extract_user_question(task: str) -> str:
    """从 task 中提取【用户本次提问】后的内容"""
    marker = "【用户本次提问】"
    idx = task.find(marker)
    if idx >= 0:
        return task[idx + len(marker) :].strip()
    return task.strip()


class ArticleWriteSkill(Skill):
    """撰写正文技能 - 根据大纲、参考块、当前草稿生成文章"""

    def __init__(self):
        super().__init__(
            name="article_write",
            description=(
                "根据用户提供的主题、大纲、参考块和当前草稿，撰写完整文章或续写。"
                "适用于写作助手场景：用户说「写」「撰写」「续写」「根据大纲写」等。"
            ),
            version="1.0.0",
            category="writing",
            priority="P1",
            parameters=[
                SkillParameter(name="input", type="string", description="用户输入（含参考块和提问）", required=True),
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
            tool_registry = context.get("tool_registry")
            context_manager = context.get("context_manager")
            session_id = context.get("session_id")

            if llm_service is None:
                llm_service = LLMService()
            if tool_registry is None:
                tool_registry = ToolRegistry()

            task = parameters.get("input", "")
            current_article = ""
            if context_manager and session_id:
                current_article = context_manager.get_current_article(session_id) or ""

            if current_article.strip():
                task = f"{task}\n\n【当前文章草稿（请在此基础上续写或修改）】\n{current_article}"

            self.report_progress("正在撰写文章...")

            agent = get_article_writing_agent(
                llm_service=llm_service,
                tool_registry=tool_registry,
            )
            result = await agent.execute({"task": task, "context": {}})

            if result["success"]:
                self.report_progress("文章撰写完成")
                return SkillResult(
                    success=True,
                    data={
                        "article": result.get("article", ""),
                        "outline": result.get("outline"),
                        "mediawiki_content": result.get("mediawiki_content"),
                    },
                )
            self.report_progress("文章撰写失败")
            return SkillResult(success=False, error="撰写任务执行失败")
        except Exception as e:
            self.report_progress(f"执行过程中发生错误: {str(e)}")
            return SkillResult(success=False, error=f"撰写失败: {str(e)}")


skill_instance = ArticleWriteSkill()
