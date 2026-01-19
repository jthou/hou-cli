# 深度研究功能设计

## 功能概述

深度研究功能允许 AI 进行多轮、深入的信息收集、分析和综合，生成高质量的研究报告。

## 核心能力

1. **多轮信息收集**：通过多轮搜索和工具调用收集信息
2. **信息分析**：使用推理模型分析和综合信息
3. **研究报告生成**：生成结构化的研究报告
4. **持续改进**：基于新信息迭代优化研究

## 架构设计

### 1. 研究管理器（ResearchManager）

负责协调整个研究流程。

```python
class ResearchManager:
    """深度研究管理器"""
    
    def __init__(self, llm_service, tool_registry, planning_manager):
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.planning_manager = planning_manager
        self.research_tools = ["google_search", "wikipedia", "browser", "zhihu_zhida"]
    
    async def conduct_research(
        self,
        research_question: str,
        max_iterations: int = 5,
        depth: str = "medium"  # "shallow", "medium", "deep"
    ) -> ResearchResult:
        """执行深度研究"""
        pass
```

### 2. 研究策略（ResearchStrategy）

定义不同的研究策略。

```python
class ResearchStrategy:
    """研究策略基类"""
    
    async def collect_information(self, question: str, context: Dict) -> List[ResearchFinding]:
        """收集信息"""
        pass
    
    async def analyze_information(self, findings: List[ResearchFinding]) -> Analysis:
        """分析信息"""
        pass
    
    async def synthesize_report(self, analysis: Analysis, question: str) -> ResearchReport:
        """综合生成报告"""
        pass


class ShallowResearchStrategy(ResearchStrategy):
    """浅层研究：1-2轮搜索，快速回答"""
    pass


class MediumResearchStrategy(ResearchStrategy):
    """中等研究：3-5轮搜索，多角度分析"""
    pass


class DeepResearchStrategy(ResearchStrategy):
    """深度研究：5+轮搜索，全面分析，生成详细报告"""
    pass
```

### 3. 研究数据模型

```python
@dataclass
class ResearchFinding:
    """研究发现"""
    source: str  # 信息来源（工具名称）
    content: str  # 内容
    relevance_score: float  # 相关性分数（0-1）
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class ResearchAnalysis:
    """研究分析"""
    key_points: List[str]  # 关键点
    contradictions: List[str]  # 矛盾点
    gaps: List[str]  # 信息缺口
    confidence: float  # 置信度（0-1）
    next_steps: List[str]  # 下一步研究建议


@dataclass
class ResearchReport:
    """研究报告"""
    question: str  # 研究问题
    summary: str  # 摘要
    findings: List[ResearchFinding]  # 研究发现
    analysis: ResearchAnalysis  # 分析结果
    conclusion: str  # 结论
    sources: List[str]  # 信息来源
    generated_at: datetime
```

## 实现方案

### 方案1：基于任务分解的研究流程

将研究任务分解为多个子任务，逐步完成。

```python
async def conduct_research(self, question: str, depth: str = "medium") -> ResearchReport:
    """执行深度研究"""
    
    # 1. 使用推理模型制定研究计划
    research_plan = await self._create_research_plan(question, depth)
    
    # 2. 执行研究计划（多轮迭代）
    findings = []
    for step in research_plan.steps:
        # 收集信息
        step_findings = await self._collect_step_information(step, question)
        findings.extend(step_findings)
        
        # 分析当前信息
        analysis = await self._analyze_findings(findings, question)
        
        # 判断是否需要继续研究
        if analysis.confidence > 0.8 and not analysis.gaps:
            break  # 信息充分，可以结束
    
    # 3. 综合分析
    final_analysis = await self._deep_analyze(findings, question)
    
    # 4. 生成报告
    report = await self._generate_report(question, findings, final_analysis)
    
    return report
```

### 方案2：迭代式研究流程

基于当前信息不断迭代，直到满足条件。

```python
async def conduct_research_iterative(
    self,
    question: str,
    max_iterations: int = 5
) -> ResearchReport:
    """迭代式研究"""
    
    findings = []
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # 1. 分析当前信息状态
        current_analysis = await self._analyze_current_state(findings, question)
        
        # 2. 判断是否需要继续
        if current_analysis.confidence > 0.8 and not current_analysis.gaps:
            break
        
        # 3. 确定下一步研究重点
        next_focus = await self._determine_next_focus(
            question,
            findings,
            current_analysis
        )
        
        # 4. 执行研究
        new_findings = await self._research_focus(next_focus, question)
        findings.extend(new_findings)
        
        # 5. 更新分析
        updated_analysis = await self._update_analysis(
            findings,
            current_analysis,
            question
        )
    
    # 生成最终报告
    report = await self._generate_final_report(question, findings)
    return report
```

## 关键方法实现

### 1. 制定研究计划

```python
async def _create_research_plan(
    self,
    question: str,
    depth: str
) -> ResearchPlan:
    """使用推理模型制定研究计划"""
    
    prompt = f"""分析以下研究问题，制定详细的研究计划：

研究问题：{question}
研究深度：{depth}

请考虑：
1. 需要从哪些角度研究这个问题？
2. 需要收集哪些类型的信息？
3. 应该使用哪些工具（搜索、浏览器、维基百科等）？
4. 研究的优先级和顺序是什么？

返回 JSON 格式的研究计划，包括：
- research_angles: 研究角度列表
- information_needs: 需要收集的信息类型
- tool_sequence: 工具使用序列
- priority: 优先级
"""
    
    # 使用推理模型
    config_manager = get_model_config_manager()
    reasoning_model = config_manager.get_reasoning_model()
    self.llm_service.set_model(reasoning_model)
    
    response = await self.llm_service.chat(
        system_prompt="你是一个研究计划专家，擅长制定详细的研究计划。",
        user_prompt=prompt
    )
    
    return parse_research_plan(response)
```

### 2. 信息收集

```python
async def _collect_step_information(
    self,
    step: ResearchStep,
    question: str
) -> List[ResearchFinding]:
    """收集步骤信息"""
    
    findings = []
    
    # 根据步骤选择工具
    for tool_name in step.tools:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            continue
        
        # 构建搜索查询
        query = await self._build_search_query(step, question)
        
        # 执行工具
        result = await self.tool_registry.execute_async(
            tool_name,
            query=query,
            **step.tool_params
        )
        
        if result.success:
            finding = ResearchFinding(
                source=tool_name,
                content=str(result.data),
                relevance_score=0.0,  # 后续计算
                timestamp=datetime.now(),
                metadata={"step": step.name, "query": query}
            )
            findings.append(finding)
            
            # 记录到 findings.md
            self.planning_manager.add_finding(
                f"[{tool_name}] {query}\n{str(result.data)[:500]}",
                category="Research Findings"
            )
    
    # 计算相关性分数
    for finding in findings:
        finding.relevance_score = await self._calculate_relevance(
            finding.content,
            question
        )
    
    return findings
```

### 3. 信息分析

```python
async def _analyze_findings(
    self,
    findings: List[ResearchFinding],
    question: str
) -> ResearchAnalysis:
    """分析研究发现"""
    
    # 筛选高相关性发现
    relevant_findings = [f for f in findings if f.relevance_score > 0.5]
    
    prompt = f"""分析以下研究发现，回答研究问题：

研究问题：{question}

研究发现：
{format_findings(relevant_findings)}

请分析：
1. 关键发现和要点
2. 信息中的矛盾或不一致之处
3. 还缺少哪些信息（信息缺口）
4. 当前分析的置信度（0-1）
5. 建议下一步研究重点

返回 JSON 格式的分析结果。
"""
    
    # 使用推理模型
    config_manager = get_model_config_manager()
    reasoning_model = config_manager.get_reasoning_model()
    self.llm_service.set_model(reasoning_model)
    
    response = await self.llm_service.chat(
        system_prompt="你是一个研究分析专家，擅长分析和综合信息。",
        user_prompt=prompt
    )
    
    return parse_analysis(response)
```

### 4. 生成研究报告

```python
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
{format_findings(findings)}

分析结果：
{format_analysis(analysis)}

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
"""
    
    # 使用推理模型
    config_manager = get_model_config_manager()
    reasoning_model = config_manager.get_reasoning_model()
    self.llm_service.set_model(reasoning_model)
    
    response = await self.llm_service.chat(
        system_prompt="你是一个研究报告撰写专家，擅长生成高质量的研究报告。",
        user_prompt=prompt
    )
    
    return ResearchReport(
        question=question,
        summary=extract_summary(response),
        findings=findings,
        analysis=analysis,
        conclusion=extract_conclusion(response),
        sources=[f.source for f in findings],
        generated_at=datetime.now()
    )
```

## 集成到编排系统

### 1. 在 Orchestrator 中添加深度研究方法

```python
class Orchestrator:
    def __init__(self):
        # ... 现有初始化 ...
        self.research_manager = ResearchManager(
            self.llm_service,
            self.tool_registry,
            self.planning_manager
        )
    
    async def deep_research(
        self,
        question: str,
        depth: str = "medium",
        context: Optional[Dict] = None
    ) -> ResearchReport:
        """执行深度研究"""
        return await self.research_manager.conduct_research(
            question,
            depth=depth
        )
```

### 2. 在 stream_process 中检测研究任务

```python
async def stream_process(self, task: str, context: Optional[Dict] = None):
    """流式处理任务"""
    
    # 检测是否是研究任务
    research_keywords = ["研究", "调研", "分析", "调查", "深度", "详细"]
    is_research_task = any(kw in task.lower() for kw in research_keywords)
    
    if is_research_task:
        # 使用深度研究功能
        async for chunk in self._stream_research(task, context):
            yield chunk
    else:
        # 正常流程
        async for chunk in self._stream_normal_process(task, context):
            yield chunk
```

## 使用示例

### 基本使用

```python
# 在 orchestrator 中
orchestrator = Orchestrator()

# 执行深度研究
report = await orchestrator.deep_research(
    "Python 异步编程的最佳实践",
    depth="deep"
)

# 输出报告
print(report.summary)
print(report.conclusion)
for finding in report.findings:
    print(f"- {finding.source}: {finding.content[:100]}")
```

### 流式输出

```python
async for chunk in orchestrator.stream_process(
    "深度研究一下量子计算的最新进展"
):
    if chunk.startswith("__RESEARCH__"):
        # 研究进度更新
        data = json.loads(chunk[12:])
        print(f"研究进度: {data['progress']}")
    else:
        # 正常输出
        print(chunk)
```

## 配置选项

在 `.env` 中添加：

```bash
# 深度研究配置
ENABLE_DEEP_RESEARCH=true
DEEP_RESEARCH_MAX_ITERATIONS=5
DEEP_RESEARCH_DEFAULT_DEPTH=medium  # shallow, medium, deep
DEEP_RESEARCH_MIN_CONFIDENCE=0.8  # 最小置信度阈值
```

## 优势

1. **系统性**：多轮迭代，全面收集信息
2. **智能性**：使用推理模型分析和综合
3. **可追溯**：所有研究发现记录在 findings.md
4. **可配置**：支持不同深度级别
5. **可扩展**：易于添加新的研究策略和工具

## 实施步骤

1. **创建研究管理器**（`backend/core/agent/research/manager.py`）
2. **创建研究数据模型**（`backend/core/agent/research/models.py`）
3. **实现研究策略**（`backend/core/agent/research/strategies.py`）
4. **集成到 Orchestrator**
5. **添加测试**

