"""深度研究管理器"""
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from backend.core.agent.research.models import (
    ResearchFinding,
    ResearchAnalysis,
    ResearchReport,
    ResearchPlan,
    ResearchStep,
    ResearchDepth
)
from backend.services.llm.model_config import get_model_config_manager

logger = logging.getLogger(__name__)


class ResearchManager:
    """深度研究管理器
    
    负责协调整个研究流程，包括：
    1. 制定研究计划
    2. 多轮信息收集
    3. 信息分析和综合
    4. 生成研究报告
    """
    
    def __init__(
        self,
        llm_service,
        tool_registry,
        planning_manager=None
    ):
        """
        初始化研究管理器
        
        Args:
            llm_service: LLM 服务实例
            tool_registry: 工具注册表
            planning_manager: 规划管理器（可选，用于记录研究发现）
        """
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.planning_manager = planning_manager
        
        # 研究工具列表
        self.research_tools = [
            "google_search",
            "wikipedia",
            "browser",
            "zhihu_zhida"
        ]
    
    async def conduct_research(
        self,
        research_question: str,
        depth: str = "medium",
        max_iterations: int = 5,
        session_id: Optional[str] = None
    ) -> ResearchReport:
        """
        执行深度研究
        
        Args:
            research_question: 研究问题
            depth: 研究深度（"shallow", "medium", "deep"）
            max_iterations: 最大迭代次数
            session_id: 会话 ID（用于规划文件）
            
        Returns:
            ResearchReport: 研究报告
        """
        logger.info(f"开始深度研究: {research_question}, 深度: {depth}")
        
        # 1. 制定研究计划
        research_plan = await self._create_research_plan(research_question, depth)
        
        # 2. 执行研究计划（迭代式）
        findings = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"研究迭代 {iteration}/{max_iterations}")
            
            # 分析当前状态
            current_analysis = await self._analyze_findings(findings, research_question)
            
            # 判断是否需要继续
            if current_analysis.confidence > 0.8 and not current_analysis.gaps:
                logger.info("信息充分，结束研究")
                break
            
            # 确定下一步研究重点
            if iteration == 1:
                # 第一轮：执行研究计划
                next_steps = research_plan.steps[:3]  # 先执行前3个步骤
            else:
                # 后续轮次：基于分析结果确定重点
                next_steps = await self._determine_next_steps(
                    research_question,
                    findings,
                    current_analysis,
                    research_plan
                )
            
            # 执行研究步骤
            for step in next_steps:
                step_findings = await self._collect_step_information(
                    step,
                    research_question,
                    session_id
                )
                findings.extend(step_findings)
                step.completed = True
        
        # 3. 深度分析
        final_analysis = await self._deep_analyze(findings, research_question)
        
        # 4. 生成报告
        report = await self._generate_report(
            research_question,
            findings,
            final_analysis
        )
        
        logger.info(f"研究完成，共收集 {len(findings)} 个发现")
        return report
    
    async def _create_research_plan(
        self,
        question: str,
        depth: str
    ) -> ResearchPlan:
        """使用推理模型制定研究计划"""
        
        depth_map = {
            "shallow": "浅层研究（1-2轮搜索，快速回答）",
            "medium": "中等研究（3-5轮搜索，多角度分析）",
            "deep": "深度研究（5+轮搜索，全面分析，生成详细报告）"
        }
        
        prompt = f"""分析以下研究问题，制定详细的研究计划：

研究问题：{question}
研究深度：{depth_map.get(depth, depth_map['medium'])}

请考虑：
1. 需要从哪些角度研究这个问题？
2. 需要收集哪些类型的信息？
3. 应该使用哪些工具（搜索、浏览器、维基百科等）？
4. 研究的优先级和顺序是什么？

返回 JSON 格式的研究计划：
{{
    "research_angles": ["角度1", "角度2", ...],
    "information_needs": ["信息类型1", "信息类型2", ...],
    "steps": [
        {{
            "name": "步骤名称",
            "description": "步骤描述",
            "tools": ["工具名称"],
            "tool_params": {{}},
            "priority": 1
        }}
    ]
}}
"""
        
        # 使用推理模型
        config_manager = get_model_config_manager()
        reasoning_model = config_manager.get_reasoning_model()
        self.llm_service.set_model(reasoning_model)
        
        try:
            response = await self.llm_service.chat(
                system_prompt="你是一个研究计划专家，擅长制定详细的研究计划。",
                user_prompt=prompt
            )
            
            # 解析 JSON 响应
            plan_data = self._parse_json_response(response)
            
            return ResearchPlan(
                question=question,
                depth=ResearchDepth(depth),
                steps=[ResearchStep.from_dict(step_data) for step_data in plan_data.get("steps", [])],
                research_angles=plan_data.get("research_angles", []),
                information_needs=plan_data.get("information_needs", [])
            )
        except Exception as e:
            logger.error(f"创建研究计划失败: {e}")
            # 返回默认计划
            return ResearchPlan(
                question=question,
                depth=ResearchDepth(depth),
                steps=[
                    ResearchStep(
                        name="基础搜索",
                        description="搜索基本信息",
                        tools=["google_search"],
                        priority=1
                    )
                ]
            )
    
    async def _collect_step_information(
        self,
        step: ResearchStep,
        question: str,
        session_id: Optional[str] = None
    ) -> List[ResearchFinding]:
        """收集步骤信息"""
        
        findings = []
        
        # 构建搜索查询
        query = await self._build_search_query(step, question)
        
        # 根据步骤选择工具
        for tool_name in step.tools:
            if tool_name not in self.research_tools:
                continue
            
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                logger.warning(f"工具 {tool_name} 不存在")
                continue
            
            try:
                # 执行工具
                if tool_name == "google_search":
                    result = await self.tool_registry.execute_async(
                        tool_name,
                        query=query
                    )
                elif tool_name == "wikipedia":
                    result = await self.tool_registry.execute_async(
                        tool_name,
                        query=query
                    )
                elif tool_name == "browser":
                    result = await self.tool_registry.execute_async(
                        tool_name,
                        url=query if query.startswith("http") else f"https://www.google.com/search?q={query}"
                    )
                else:
                    result = await self.tool_registry.execute_async(
                        tool_name,
                        query=query,
                        **step.tool_params
                    )
                
                if result.success:
                    content = str(result.data)
                    finding = ResearchFinding(
                        source=tool_name,
                        content=content,
                        relevance_score=0.0,  # 后续计算
                        metadata={
                            "step": step.name,
                            "query": query,
                            "tool_params": step.tool_params
                        }
                    )
                    findings.append(finding)
                    
                    # 记录到 findings.md
                    if self.planning_manager and session_id:
                        try:
                            self.planning_manager.add_finding(
                                f"[{tool_name}] {query}\n{content[:500]}",
                                category="Research Findings",
                                session_id=session_id
                            )
                        except Exception as e:
                            logger.warning(f"记录研究发现失败: {e}")
                
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {e}")
        
        # 计算相关性分数
        for finding in findings:
            finding.relevance_score = await self._calculate_relevance(
                finding.content,
                question
            )
        
        return findings
    
    async def _build_search_query(
        self,
        step: ResearchStep,
        question: str
    ) -> str:
        """构建搜索查询"""
        
        # 如果步骤有描述，结合描述和问题构建查询
        if step.description:
            # 使用推理模型优化查询
            prompt = f"""基于以下信息，生成一个精确的搜索查询：

研究问题：{question}
研究步骤：{step.description}

请生成一个简洁、精确的搜索查询（不超过10个词）。
只返回搜索查询，不要返回其他内容。
"""
            
            try:
                config_manager = get_model_config_manager()
                chat_model = config_manager.get_chat_model()
                self.llm_service.set_model(chat_model)
                
                query = await self.llm_service.chat(user_prompt=prompt)
                return query.strip()
            except Exception as e:
                logger.warning(f"生成搜索查询失败: {e}")
        
        # 降级：直接使用问题
        return question
    
    async def _calculate_relevance(
        self,
        content: str,
        question: str
    ) -> float:
        """计算内容与问题的相关性"""
        
        # 简单实现：基于关键词匹配
        question_keywords = set(question.lower().split())
        content_lower = content.lower()
        
        matches = sum(1 for kw in question_keywords if kw in content_lower)
        relevance = min(matches / max(len(question_keywords), 1), 1.0)
        
        return relevance
    
    async def _analyze_findings(
        self,
        findings: List[ResearchFinding],
        question: str
    ) -> ResearchAnalysis:
        """分析研究发现"""
        
        if not findings:
            return ResearchAnalysis(
                confidence=0.0,
                gaps=["尚未收集到任何信息"]
            )
        
        # 筛选高相关性发现
        relevant_findings = [f for f in findings if f.relevance_score > 0.3]
        
        if not relevant_findings:
            return ResearchAnalysis(
                confidence=0.0,
                gaps=["收集的信息相关性较低"]
            )
        
        prompt = f"""分析以下研究发现，回答研究问题：

研究问题：{question}

研究发现：
{self._format_findings(relevant_findings[:10])}  # 限制数量

请分析：
1. 关键发现和要点（列表）
2. 信息中的矛盾或不一致之处（列表）
3. 还缺少哪些信息（信息缺口，列表）
4. 当前分析的置信度（0-1之间的数字）
5. 建议下一步研究重点（列表）

返回 JSON 格式：
{{
    "key_points": ["要点1", "要点2", ...],
    "contradictions": ["矛盾1", ...],
    "gaps": ["缺口1", ...],
    "confidence": 0.8,
    "next_steps": ["建议1", ...]
}}
"""
        
        # 使用推理模型
        config_manager = get_model_config_manager()
        reasoning_model = config_manager.get_reasoning_model()
        self.llm_service.set_model(reasoning_model)
        
        try:
            response = await self.llm_service.chat(
                system_prompt="你是一个研究分析专家，擅长分析和综合信息。",
                user_prompt=prompt
            )
            
            analysis_data = self._parse_json_response(response)
            
            return ResearchAnalysis(
                key_points=analysis_data.get("key_points", []),
                contradictions=analysis_data.get("contradictions", []),
                gaps=analysis_data.get("gaps", []),
                confidence=float(analysis_data.get("confidence", 0.0)),
                next_steps=analysis_data.get("next_steps", [])
            )
        except Exception as e:
            logger.error(f"分析研究发现失败: {e}")
            return ResearchAnalysis(
                confidence=0.5,
                gaps=["分析过程出错"]
            )
    
    async def _deep_analyze(
        self,
        findings: List[ResearchFinding],
        question: str
    ) -> ResearchAnalysis:
        """深度分析（最终分析）"""
        
        return await self._analyze_findings(findings, question)
    
    async def _determine_next_steps(
        self,
        question: str,
        findings: List[ResearchFinding],
        analysis: ResearchAnalysis,
        plan: ResearchPlan
    ) -> List[ResearchStep]:
        """确定下一步研究步骤"""
        
        # 基于分析结果创建新的研究步骤
        next_steps = []
        
        for gap in analysis.gaps[:2]:  # 最多处理2个缺口
            step = ResearchStep(
                name=f"补充研究：{gap[:30]}",
                description=gap,
                tools=["google_search"],
                priority=1
            )
            next_steps.append(step)
        
        # 如果没有缺口，使用计划中的剩余步骤
        if not next_steps:
            remaining_steps = [s for s in plan.steps if not s.completed]
            next_steps = remaining_steps[:2]
        
        return next_steps
    
    async def _generate_report(
        self,
        question: str,
        findings: List[ResearchFinding],
        analysis: ResearchAnalysis
    ) -> ResearchReport:
        """生成研究报告"""
        
        prompt = f"""基于以下研究信息，生成一份完整的研究报告：

研究问题：{question}

研究发现：
{self._format_findings(findings[:20])}  # 限制数量

分析结果：
- 关键点：{', '.join(analysis.key_points[:5])}
- 信息缺口：{', '.join(analysis.gaps[:3])}
- 置信度：{analysis.confidence}

请生成一份结构化的研究报告，包括：
1. 执行摘要（2-3句话）
2. 主要发现（按重要性排序）
3. 详细分析
4. 结论和建议
5. 信息来源列表

报告应该：
- 清晰、准确、全面
- 基于研究发现，不要编造信息
- 指出信息的不确定性
- 提供可操作的建议

只返回报告内容，使用 Markdown 格式。
"""
        
        # 使用推理模型
        config_manager = get_model_config_manager()
        reasoning_model = config_manager.get_reasoning_model()
        self.llm_service.set_model(reasoning_model)
        
        try:
            response = await self.llm_service.chat(
                system_prompt="你是一个研究报告撰写专家，擅长生成高质量的研究报告。",
                user_prompt=prompt
            )
            
            # 提取摘要和结论
            summary = self._extract_summary(response)
            conclusion = self._extract_conclusion(response)
            
            return ResearchReport(
                question=question,
                summary=summary,
                findings=findings,
                analysis=analysis,
                conclusion=conclusion,
                sources=list(set(f.source for f in findings))
            )
        except Exception as e:
            logger.error(f"生成研究报告失败: {e}")
            return ResearchReport(
                question=question,
                summary="研究报告生成失败",
                findings=findings,
                analysis=analysis,
                conclusion="",
                sources=list(set(f.source for f in findings))
            )
    
    def _format_findings(self, findings: List[ResearchFinding]) -> str:
        """格式化研究发现"""
        formatted = []
        for i, finding in enumerate(findings, 1):
            formatted.append(
                f"{i}. [{finding.source}] (相关性: {finding.relevance_score:.2f})\n"
                f"   {finding.content[:300]}..."
            )
        return "\n\n".join(formatted)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
        # 尝试提取 JSON 部分
        response = response.strip()
        
        # 如果响应是代码块，提取内容
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果解析失败，尝试查找 JSON 对象
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise
    
    def _extract_summary(self, report: str) -> str:
        """提取摘要"""
        # 简单实现：提取前3句话
        sentences = report.split('。')[:3]
        return '。'.join(sentences) + '。'
    
    def _extract_conclusion(self, report: str) -> str:
        """提取结论"""
        # 查找结论部分
        if "## 结论" in report or "## 总结" in report:
            parts = report.split("## 结论") if "## 结论" in report else report.split("## 总结")
            if len(parts) > 1:
                conclusion = parts[1].split("\n\n")[0].strip()
                return conclusion[:500]  # 限制长度
        
        # 降级：提取最后一段
        paragraphs = report.split("\n\n")
        if paragraphs:
            return paragraphs[-1][:500]
        
        return ""

