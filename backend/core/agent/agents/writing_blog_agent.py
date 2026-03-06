#!/usr/bin/env python3
"""写作博客文章的智能Agent - 基于用户提供的主题和草稿"""

import asyncio
import json
import re
from typing import Dict, Optional, Any
from datetime import datetime

from backend.core.agent.base_agent import BaseAgent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.base import ToolResult


def _extract_urls(text: str) -> list[str]:
    """从文本中提取 http/https URL"""
    if not text:
        return []
    pattern = r"https?://[^\s\)\]\"']+"
    return list(dict.fromkeys(re.findall(pattern, text)))


async def _run_tool_sync(tool, **kwargs) -> ToolResult:
    """在线程池中运行同步工具，避免阻塞事件循环"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: tool.execute(**kwargs))


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
        """解析用户输入的任务和上下文；若含 URL 或 MediaWiki 参考页则拉取内容"""
        ctx = context or {}
        reference_content: list[str] = []

        # 1. web_fetch：用户提供 URL 时抓取
        urls = _extract_urls(task)
        urls.extend(_extract_urls(str(ctx.get("reference_url", ""))))
        urls.extend(_extract_urls(str(ctx.get("url", ""))))
        web_fetch_tool = self.tool_registry.get_tool("web_fetch") if self.tool_registry else None
        for url in urls[:3]:  # 最多 3 个 URL
            if web_fetch_tool:
                try:
                    res = await _run_tool_sync(web_fetch_tool, url=url, max_length=15000)
                    if res.success and res.data:
                        ref = f"【参考：{res.data.get('title', url)}\n{res.data.get('content', '')[:12000]}】"
                        reference_content.append(ref)
                except Exception:
                    pass

        # 2. mediawiki：用户指定参考页面时读取
        mw_titles = ctx.get("mediawiki_page") or ctx.get("mw_source_titles")
        if mw_titles and not isinstance(mw_titles, (list, tuple)):
            mw_titles = [mw_titles]
        mediawiki_tool = self.tool_registry.get_tool("mediawiki") if self.tool_registry else None
        if mediawiki_tool and mw_titles:
            for title in (mw_titles or [])[:3]:
                try:
                    res = await _run_tool_sync(
                        mediawiki_tool, operation="read", title=str(title).strip()
                    )
                    if res.success and res.data and res.data.get("content"):
                        ref = f"【参考 MediaWiki 页面：{title}\n{res.data['content'][:12000]}】"
                        reference_content.append(ref)
                except Exception:
                    pass

        ref_block = "\n\n".join(reference_content) if reference_content else ""

        # 3. LLM 分析用户输入
        prompt = f"""
        请分析以下用户输入并提取关键信息：
        用户输入: {task}
        上下文: {ctx}
        {f'参考材料（请纳入分析）:\n{ref_block}' if ref_block else ''}
        
        提取以下信息：
        1. 文章主题
        2. 目标读者群体
        3. 文章类型（教程、分析、评论等）
        4. 已有的草稿或要点
        5. 特殊要求或重点
        
        请以JSON格式返回结果。
        """
        response = await self.llm_service.chat([{"role": "user", "content": prompt}])
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                result.setdefault("topic", task)
                result.setdefault("target_audience", "general")
                result.setdefault("article_type", "tutorial")
                result.setdefault("draft_points", [])
                result.setdefault("special_requirements", [])
                result["_reference_content"] = ref_block
                return result
            except json.JSONDecodeError:
                pass
        return {
            "topic": task,
            "target_audience": "general",
            "article_type": "tutorial",
            "draft_points": [],
            "special_requirements": [],
            "_reference_content": ref_block,
        }
    
    async def _create_outline(
        self, parsed_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于用户输入创建文章大纲；可选接入 google_search、mediawiki 获取参考"""
        topic = parsed_input.get("topic", "未知")
        ref_block = parsed_input.get("_reference_content", "")
        outline_refs: list[str] = []

        # google_search：搜索同类文章结构、SEO 标题
        google_tool = self.tool_registry.get_tool("google_search") if self.tool_registry else None
        if google_tool:
            try:
                res = await _run_tool_sync(
                    google_tool, query=str(topic)[:80], num_results=5
                )
                if res.success and res.data and res.data.get("results"):
                    snippets = [
                        f"- {r.get('title', '')}: {r.get('snippet', '')[:150]}"
                        for r in res.data["results"][:5]
                    ]
                    outline_refs.append("【同类文章参考】\n" + "\n".join(snippets))
            except Exception:
                pass

        # mediawiki search_read：拉取同主题已有文章大纲
        mediawiki_tool = self.tool_registry.get_tool("mediawiki") if self.tool_registry else None
        if mediawiki_tool:
            try:
                res = await _run_tool_sync(
                    mediawiki_tool,
                    operation="search_read",
                    terms=str(topic)[:50],
                    per_term_limit=2,
                )
                if res.success and res.data and res.data.get("results"):
                    pages = []
                    for r in res.data["results"]:
                        pages.extend(r.get("pages", [])[:2])
                    pages = pages[:3]
                    if pages:
                        texts = [
                            f"【{p.get('title', '')}】\n{p.get('content', '')[:2000]}"
                            for p in pages
                        ]
                        outline_refs.append("【MediaWiki 同主题文章】\n" + "\n\n".join(texts))
            except Exception:
                pass

        ref_section = "\n\n".join(outline_refs) if outline_refs else ""
        if ref_block:
            ref_section = (ref_section + "\n\n" + ref_block) if ref_section else ref_block

        prompt = f"""
        基于以下用户输入创建结构化文章大纲：
        主题: {topic}
        类型: {parsed_input.get('article_type', '通用')}
        已有草稿要点: {parsed_input.get('draft_points', [])}
        特殊要求: {parsed_input.get('special_requirements', [])}
        {f'参考材料（可借鉴结构与表述）:\n{ref_section}' if ref_section else ''}
        
        大纲应包含：
        1. 吸引人的标题（考虑SEO）
        2. 简洁有力的引言
        3. 逻辑清晰的主体部分（建议3-5个主要章节）
        4. 总结性结论
        5. 可能的后续行动或思考问题
        
        请返回结构化的JSON格式大纲，包含每个部分的简要描述。
        """
        response = await self.llm_service.chat([{"role": "user", "content": prompt}])
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                outline = json.loads(json_match.group())
                outline["_reference_content"] = ref_block
                return outline
            except json.JSONDecodeError:
                pass
        base = {
            "title": topic if isinstance(topic, str) else "博客文章",
            "introduction": "文章引言部分",
            "sections": [
                {"title": "第一部分", "description": "主要内容第一部分", "content_hint": ""},
                {"title": "第二部分", "description": "主要内容第二部分", "content_hint": ""},
                {"title": "第三部分", "description": "主要内容第三部分", "content_hint": ""},
            ],
            "conclusion": "文章结论部分",
            "call_to_action": "可能的后续行动或思考",
        }
        base["_reference_content"] = ref_block
        return base
    
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
        
        ref_block = outline.get("_reference_content", "")
        ref_note = f"\n参考材料（可引用或借鉴，勿照抄）:\n{ref_block[:8000]}" if ref_block else ""

        # 生成引言
        intro_prompt = f"""
        请为"{outline.get('title', '')}"这个主题撰写引言部分。
        要求：
        1. 吸引读者注意力
        2. 简要介绍主题重要性
        3. 预告文章主要内容
        4. 长度约150-200字
        {ref_note}
        
        返回纯文本格式的引言。
        """
        introduction = await self.llm_service.chat([{"role": "user", "content": intro_prompt}])
        article["introduction"] = introduction.strip()
        
        # 生成各个部分
        sections = outline.get("sections", [])
        for i, section in enumerate(sections):
            sec = dict(section)
            sec["_reference_content"] = ref_block
            section_content = await self._write_section(sec, i + 1, len(sections))
            article["sections"].append({
                "title": section.get("title", f"第{i+1}部分"),
                "content": section_content,
            })
        
        # 生成结论
        conclusion_prompt = f"""
        请为"{outline.get('title', '')}"这篇文章撰写结论部分。
        要求：
        1. 总结文章主要观点
        2. 提供价值或建议
        3. 与引言呼应
        4. 长度约100-150字
        {ref_note}
        
        返回纯文本格式的结论。
        """
        conclusion = await self.llm_service.chat([{"role": "user", "content": conclusion_prompt}])
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
        call_to_action = await self.llm_service.chat([{"role": "user", "content": cta_prompt}])
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
        total_sections: int,
    ) -> str:
        """撰写单个章节"""
        ref_block = section_info.get("_reference_content", "")
        ref_note = (
            f"\n参考材料（可引用或借鉴，勿照抄）:\n{ref_block[:6000]}"
            if ref_block
            else ""
        )
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
        {ref_note}
        
        当前是第{section_num}部分，共{total_sections}部分。
        
        返回该章节的完整内容。
        """
        response = await self.llm_service.chat([{"role": "user", "content": prompt}])
        return response.strip()
    
    async def _optimize_article(
        self, article: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 LLM 优化文章：语法、流畅度、可读性"""
        full_text = (
            article.get("introduction", "")
            + "\n\n"
            + "\n\n".join(
                s.get("content", "") for s in article.get("sections", [])
            )
            + "\n\n"
            + article.get("conclusion", "")
            + "\n\n"
            + article.get("call_to_action", "")
        )
        if len(full_text) > 12000:
            # 过长时仅优化引言+前两节+结论，避免超 token
            intro = article.get("introduction", "")
            secs = article.get("sections", [])
            concl = article.get("conclusion", "")
            cta = article.get("call_to_action", "")
            to_opt = intro + "\n\n"
            for s in secs[:2]:
                to_opt += s.get("content", "") + "\n\n"
            to_opt += concl + "\n\n" + cta
        else:
            to_opt = full_text

        prompt = f"""
        请优化以下博客文章，保持原有结构和章节标题，只修改正文表述。

        【原文】
        {to_opt[:10000]}

        优化要求：
        1. 检查语法和表达的清晰度
        2. 确保段落之间逻辑流畅
        3. 优化句子结构，提高可读性
        4. 确保标题和内容的一致性

        请按以下 JSON 格式返回（仅返回 JSON，不要其他说明）：
        {{"introduction": "优化后的引言", "sections": [{{"title": "章节标题", "content": "优化后的内容"}}, ...], "conclusion": "优化后的结论", "call_to_action": "优化后的行动号召"}}
        """
        try:
            response = await self.llm_service.chat([{"role": "user", "content": prompt}])
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                opt = json.loads(json_match.group())
                if opt.get("introduction"):
                    article["introduction"] = opt["introduction"]
                if opt.get("sections"):
                    for i, sec_opt in enumerate(opt["sections"][: len(article.get("sections", []))]):
                        if i < len(article["sections"]) and sec_opt.get("content"):
                            article["sections"][i]["content"] = sec_opt["content"]
                if opt.get("conclusion"):
                    article["conclusion"] = opt["conclusion"]
                if opt.get("call_to_action"):
                    article["call_to_action"] = opt["call_to_action"]
        except Exception:
            pass
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