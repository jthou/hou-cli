#!/usr/bin/env python3
"""写作博客文章的智能Agent - 基于用户提供的主题和草稿"""

from typing import Dict, Optional, Any
from datetime import datetime

from backend.core.agent.base_agent import BaseAgent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


class BlogWritingAgent(BaseAgent):
    """博客写作智能Agent - 帮助用户梳理大纲、实现细节并生成文章"""
    
    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry):
        # 初始化基类，传入所需参数
        # 为了避免基类初始化时创建新的LLMService实例，我们稍后设置llm_service
        self.name = "BlogWritingAgent"
        self.description = (
            "专门用于基于用户输入的主题和草稿，生成结构化博客文章的智能Agent"
        )
        self.capabilities = [
            "blog_writing",
            "outline_creation",
            "content_generation",
            "mediawiki_format",
        ]
        # BlogWritingAgent使用传入的服务实例
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行博客写作任务
        
        Args:
            task: 任务描述，格式为
                {"task": "主题", "context": {"target_audience": ..., ...}}
            
        Returns:
            包含写作结果的字典
        """
        # 从任务字典中提取信息
        task_str = task.get("task", "")
        context = task.get("context", {})
        
        # 解析用户输入的任务和上下文
        parsed_input = await self._parse_user_input(task_str, context)
        
        # 梳理文章大纲
        outline = await self._create_outline(parsed_input)
        
        # 基于大纲生成详细内容
        detailed_content = await self._generate_detailed_content(outline)
        
        # 优化和润色文章
        optimized_article = await self._optimize_article(detailed_content)
        
        # 准备发布到MediaWiki
        mediawiki_content = await self._format_for_mediawiki(optimized_article)
        
        return {
            "success": True,
            "outline": outline,
            "article": optimized_article,
            "mediawiki_content": mediawiki_content,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _parse_user_input(
        self, task: str, context: Optional[Dict]
    ) -> Dict[str, Any]:
        """解析用户输入的任务和上下文"""
        # 使用LLM分析用户输入，提取关键信息
        prompt = f"""
        请分析以下用户输入并提取关键信息：
        用户输入: {task}
        上下文: {context or {}}
        
        提取以下信息：
        1. 文章主题
        2. 目标读者群体
        3. 文章类型（教程、分析、评论等）
        4. 已有的草稿或要点
        5. 特殊要求或重点
        
        请以JSON格式返回结果。
        """
        
        response = await self.llm_service.chat(
            [{"role": "user", "content": prompt}]
        )

        # 简单解析响应中的JSON部分
        import json
        import re
        
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                # 确保返回的数据结构正确
                result.setdefault("topic", task)
                result.setdefault("target_audience", "general")
                result.setdefault("article_type", "tutorial")
                result.setdefault("draft_points", [])
                result.setdefault("special_requirements", [])
                return result
            except json.JSONDecodeError:
                pass
                
        # 如果无法解析JSON，返回基本结构
        return {
            "topic": task,
            "target_audience": "general",
            "article_type": "tutorial",
            "draft_points": [],
            "special_requirements": []
        }
    
    async def _create_outline(
        self, parsed_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于用户输入创建文章大纲"""
        prompt = f"""
        基于以下用户输入创建结构化文章大纲：
        主题: {parsed_input.get('topic', '未知')}
        类型: {parsed_input.get('article_type', '通用')}
        已有草稿要点: {parsed_input.get('draft_points', [])}
        特殊要求: {parsed_input.get('special_requirements', [])}
        
        大纲应包含：
        1. 吸引人的标题（考虑SEO）
        2. 简洁有力的引言
        3. 逻辑清晰的主体部分（建议3-5个主要章节）
        4. 总结性结论
        5. 可能的后续行动或思考问题
        
        请返回结构化的JSON格式大纲，包含每个部分的简要描述。
        """
        
        response = await self.llm_service.chat(
            [{"role": "user", "content": prompt}]
        )

        # 简单解析响应
        import json
        import re
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # 默认返回
        return {
            "title": parsed_input.get('topic', '博客文章'),
            "introduction": "文章引言部分",
            "sections": [
                {
                    "title": "第一部分",
                    "description": "主要内容第一部分",
                    "content_hint": "",
                },
                {
                    "title": "第二部分",
                    "description": "主要内容第二部分",
                    "content_hint": "",
                },
                {
                    "title": "第三部分",
                    "description": "主要内容第三部分",
                    "content_hint": "",
                },
            ],
            "conclusion": "文章结论部分",
            "call_to_action": "可能的后续行动或思考"
        }
    
    async def _generate_detailed_content(
        self, outline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于大纲生成详细内容"""
        article = {
            "title": outline.get("title", "默认标题"),
            "introduction": "",
            "sections": [],
            "conclusion": "",
            "call_to_action": "",
            "metadata": {
                "tags": [],
                "word_count": 0,
                "reading_time_minutes": 0,
                "generated_sections": len(outline.get("sections", []))
            }
        }
        
        # 生成引言
        intro_prompt = f"""
        请为"{outline.get('title', '')}"这个主题撰写引言部分。
        要求：
        1. 吸引读者注意力
        2. 简要介绍主题重要性
        3. 预告文章主要内容
        4. 长度约150-200字
        
        返回纯文本格式的引言。
        """
        
        introduction = await self.llm_service.chat(
            [{"role": "user", "content": intro_prompt}]
        )
        article["introduction"] = introduction.strip()
        
        # 生成各个部分
        sections = outline.get("sections", [])
        for i, section in enumerate(sections):
            section_content = await self._write_section(
                section, i + 1, len(sections)
            )
            article["sections"].append({
                "title": section.get("title", f"第{i+1}部分"),
                "content": section_content
            })
        
        # 生成结论
        conclusion_prompt = f"""
        请为"{outline.get('title', '')}"这篇文章撰写结论部分。
        要求：
        1. 总结文章主要观点
        2. 提供价值或建议
        3. 与引言呼应
        4. 长度约100-150字
        
        返回纯文本格式的结论。
        """
        
        conclusion = await self.llm_service.chat(
            [{"role": "user", "content": conclusion_prompt}]
        )
        article["conclusion"] = conclusion.strip()
        
        # 生成行动号召或后续思考
        cta_prompt = f"""
        为"{outline.get('title', '')}"这个主题提供一个简短的行动号召或后续思考。
        要求：
        1. 鼓励读者参与（评论、分享、实践等）
        2. 提出进一步探讨的问题
        3. 长度约50-100字
        
        返回纯文本格式的内容。
        """
        
        call_to_action = await self.llm_service.chat(
            [{"role": "user", "content": cta_prompt}]
        )
        article["call_to_action"] = call_to_action.strip()
        
        # 计算统计数据
        sections_content = "".join(s["content"] for s in article["sections"])
        full_text = (
            article["introduction"]
            + sections_content
            + article["conclusion"]
            + article["call_to_action"]
        )
        word_count = len(full_text.split())
        reading_time = max(1, word_count // 200)  # 假设每分钟阅读200词
        
        article["metadata"]["word_count"] = word_count
        article["metadata"]["reading_time_minutes"] = reading_time
        
        # 生成标签
        tags_prompt = f"""
        为"{outline.get('title', '')}"这个主题生成3-5个相关的标签或关键词。
        返回格式：["tag1", "tag2", "tag3"]
        """
        
        tags_response = await self.llm_service.chat(
            [{"role": "user", "content": tags_prompt}]
        )
        # 简单解析标签
        import re
        tag_matches = re.findall(r'"([^"]*)"', tags_response)
        article["metadata"]["tags"] = tag_matches[:5]  # 最多5个标签
        
        return article
    
    async def _write_section(
        self,
        section_info: Dict[str, Any],
        section_num: int,
        total_sections: int
    ) -> str:
        """撰写单个章节"""
        prompt = f"""
        请撰写博客文章的章节：
        章节标题: {section_info.get('title', f'第{section_num}部分')}
        章节描述: {section_info.get('description', '')}
        内容提示: {section_info.get('content_hint', '')}
        
        要求：
        1. 内容具体且有价值
        2. 逻辑清晰，结构合理
        3. 与整体文章主题保持一致
        4. 长度约200-400字
        5. 如适用，可包含小标题、列表或示例
        
        当前是第{section_num}部分，共{total_sections}部分。
        
        返回该章节的完整内容。
        """
        
        response = await self.llm_service.chat(
            [{"role": "user", "content": prompt}]
        )
        return response.strip()
    
    async def _optimize_article(
        self, article: Dict[str, Any]
    ) -> Dict[str, Any]:
        """优化文章内容"""
        # 在实际实现中，这里应该使用LLM来优化内容
        # optimization_prompt = f"""
        # 请优化以下博客文章内容：
        # 标题: {article["title"]}
        # 引言: {article["introduction"]}
        # 主体内容: {[sec["content"] for sec in article["sections"]}
        # }
        # 结论: {article["conclusion"]}
        # 行动号召: {article["call_to_action"]}
        # 
        # 优化要求：
        # 1. 检查语法和表达的清晰度
        # 2. 确保段落之间逻辑流畅
        # 3. 优化句子结构，提高可读性
        # 4. 确保标题和内容的一致性
        # 5. 检查是否符合目标读者的期望
        # 
        # 返回优化后的文章，保持原有结构。
        # """
            
        # 目前直接返回原文章
        # 在实际实现中，这里应该解析优化后的内容
        # 目前简单更新优化时间戳
        article["metadata"]["last_optimized"] = datetime.now().isoformat()
        article["metadata"]["optimized_by"] = self.name
                
        return article
    
    async def _format_for_mediawiki(self, article: Dict[str, Any]) -> str:
        """格式化文章以适应MediaWiki"""
        # 构建MediaWiki格式的文章
        mediawiki_content = f"""== {article["title"]} ==

{article["introduction"]}

"""
        
        # 添加各章节
        for section in article["sections"]:
            mediawiki_content += f"""=== {section["title"]} ===

{section["content"]}

"""
        
        # 添加结论和行动号召
        mediawiki_content += f"""=== 结论 ===

{article["conclusion"]}

=== 后续思考 ===

{article["call_to_action"]}

"""
        
        # 添加标签作为分类
        if article["metadata"]["tags"]:
            mediawiki_content += "\n[[Category:博客文章]]\n"
            for tag in article["metadata"]["tags"]:
                mediawiki_content += f"[[Category:{tag}]]\n"
        
        return mediawiki_content