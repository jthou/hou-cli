#!/usr/bin/env python3
"""博客写作技能 - 基于用户输入的主题和草稿生成结构化文章"""

from typing import Dict, Any, Optional
from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


class BlogWritingSkill(Skill):
    """博客写作技能 - 将BlogWritingAgent包装为技能"""
    
    def __init__(self):
        super().__init__(
            name="blog_writing",
            description=(
                "基于用户提供的主题和草稿，自动生成结构化博客文章的技能。"
                "能够梳理大纲、实现细节并生成适合发布到MediaWiki的文章。"
            ),
            version="1.0.0",
            category="writing",
            priority="P1",
            parameters=[
                SkillParameter(
                    name="topic",
                    type="string",
                    description="文章主题或标题",
                    required=True
                ),
                SkillParameter(
                    name="draft",
                    type="string",
                    description="文章草稿或要点，可以为空",
                    required=False,
                    default=""
                ),
                SkillParameter(
                    name="target_audience",
                    type="string",
                    description="目标读者群体，如：'Python开发者', '初学者', '专家'",
                    required=False,
                    default="general"
                ),
                SkillParameter(
                    name="article_type",
                    type="string",
                    description="文章类型，如：'技术教程', '分析评论', '指南'",
                    required=False,
                    default="tutorial"
                ),
                SkillParameter(
                    name="desired_length",
                    type="string",
                    description="期望文章长度，如：'short', 'medium', 'long'",
                    required=False,
                    default="medium"
                )
            ]
        )
    
    async def execute(
        self, parameters: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        执行博客写作技能
        
        Args:
            parameters: 技能参数
            context: 执行上下文（包含工具注册表、LLM服务等）
        
        Returns:
            SkillResult: 执行结果
        """
        try:
            # 从上下文中获取必要的服务
            if context is None:
                context = {}
            
            llm_service = context.get("llm_service")
            tool_registry = context.get("tool_registry")
            
            # 如果上下文中没有提供服务，则创建新的实例
            if llm_service is None:
                llm_service = LLMService()
            if tool_registry is None:
                tool_registry = ToolRegistry()
            
            # 创建BlogWritingAgent实例
            blog_agent = BlogWritingAgent(llm_service, tool_registry)
            
            # 构造任务描述
            topic = parameters.get("topic", "")
            draft = parameters.get("draft", "")
            target_audience = parameters.get("target_audience", "general")
            article_type = parameters.get("article_type", "tutorial")
            desired_length = parameters.get("desired_length", "medium")
            
            task_description = f"""
请基于以下主题和草稿，写一篇结构清晰、内容丰富的技术博客文章：

主题：{topic}

草稿内容：
{draft}
            
要求：
1. 面向{target_audience}
2. 文章类型：{article_type}
3. 长度：{desired_length}
4. 包含适当的技术深度
5. 提供实用的见解和建议
"""
            
            # 准备上下文信息
            agent_context = {
                "target_audience": target_audience,
                "article_type": article_type,
                "desired_length": desired_length
            }
            
            # 执行博客写作任务
            self.report_progress(f"开始写作文章: {topic}")
            
            result = await blog_agent.execute({
                "task": task_description,
                "context": agent_context
            })
            
            if result["success"]:
                self.report_progress("文章写作完成")
                return SkillResult(
                    success=True,
                    data={
                        "outline": result["outline"],
                        "article": result["article"],
                        "mediawiki_content": result["mediawiki_content"],
                        "timestamp": result["timestamp"]
                    }
                )
            else:
                self.report_progress("文章写作失败")
                return SkillResult(
                    success=False,
                    error="博客写作任务执行失败"
                )
                
        except Exception as e:
            self.report_progress(f"执行过程中发生错误: {str(e)}")
            return SkillResult(
                success=False,
                error=f"执行博客写作技能时发生错误: {str(e)}"
            )


# 创建技能实例
skill_instance = BlogWritingSkill()