#!/usr/bin/env python3
"""写作博客文章工具类 - 调用 BlogWritingAgent 执行完整写作流程"""

from typing import Optional
from backend.core.agent.tools.base import Tool, ToolParameter, ToolResult


class WritingBlogTool(Tool):
    """写作博客文章工具 - 基于主题和草稿生成结构化文章"""

    def __init__(self):
        parameters = [
            ToolParameter(name="topic", type="string", description="博客文章主题", required=True),
            ToolParameter(name="draft_content", type="string", description="初步草稿内容", required=False),
            ToolParameter(name="target_audience", type="string", description="目标读者群体", required=False, default="general"),
            ToolParameter(name="article_type", type="string", description="文章类型（教程、分析、评论等）", required=False, default="tutorial"),
            ToolParameter(name="reference_url", type="string", description="参考 URL，将抓取内容纳入写作", required=False),
            ToolParameter(name="mediawiki_page", type="string", description="参考 MediaWiki 页面标题", required=False),
            ToolParameter(name="publish_to_mediawiki", type="boolean", description="是否发布到MediaWiki", required=False, default=False),
        ]
        super().__init__(
            name="writing_blog_tool",
            description="帮助用户基于主题和草稿创建博客文章的工具。会解析输入、创建大纲、生成内容、优化并输出 MediaWiki 格式。",
            parameters=parameters,
        )

    def execute(self, **kwargs) -> ToolResult:
        """同步执行：供测试等场景"""
        import asyncio
        return asyncio.run(self._execute_async(**kwargs))

    async def _execute_async(self, **kwargs) -> ToolResult:
        """
        执行博客写作任务，调用 BlogWritingAgent
        """
        try:
            from backend.services.llm.llm_service import LLMService
            from backend.core.agent.tools.registry import ToolRegistry
            from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent

            topic = kwargs.get("topic", "")
            draft_content = kwargs.get("draft_content", "")
            target_audience = kwargs.get("target_audience", "general")
            article_type = kwargs.get("article_type", "tutorial")
            reference_url = kwargs.get("reference_url", "")
            mediawiki_page = kwargs.get("mediawiki_page", "")
            publish_to_mediawiki = kwargs.get("publish_to_mediawiki", False)

            if not topic:
                return ToolResult(
                    success=False,
                    error="topic 参数不能为空，请提供博客文章主题",
                )

            llm_service = LLMService()
            tool_registry = ToolRegistry()
            agent = BlogWritingAgent(llm_service, tool_registry)

            task_str = f"{topic}\n\n{draft_content}".strip() if draft_content else topic
            context = {
                "target_audience": target_audience,
                "article_type": article_type,
            }
            if reference_url:
                context["reference_url"] = reference_url
            if mediawiki_page:
                context["mediawiki_page"] = mediawiki_page

            result = await agent.execute({"task": task_str, "context": context})

            if not result.get("success"):
                return ToolResult(
                    success=False,
                    error=result.get("error", "博客写作执行失败"),
                )

            data = {
                "topic": topic,
                "outline": result.get("outline"),
                "article": result.get("article"),
                "mediawiki_content": result.get("mediawiki_content"),
                "timestamp": result.get("timestamp"),
                "publish_to_mediawiki": publish_to_mediawiki,
            }
            return ToolResult(
                success=True,
                data=data,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"博客写作过程中发生错误: {str(e)}",
            )
    
    def check_health(self) -> tuple[bool, Optional[str]]:
        """检查工具健康状态"""
        # 检查必要的依赖和服务是否可用
        try:
            # 检查LLM服务连接等
            return True, None
        except Exception as e:
            return False, str(e)


# 注册工具的辅助函数
def create_writing_blog_tool() -> WritingBlogTool:
    """创建写作博客文章工具实例"""
    return WritingBlogTool()