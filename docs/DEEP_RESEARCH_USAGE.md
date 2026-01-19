# 深度研究功能使用指南

## 概述

深度研究功能允许 AI 进行多轮、深入的信息收集、分析和综合，生成高质量的研究报告。

## 快速开始

### 1. 基本使用

```python
from backend.core.agent.research import ResearchManager
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.planning.manager import PlanningManager

# 初始化组件
llm_service = LLMService()
tool_registry = ToolRegistry()
planning_manager = PlanningManager()

# 创建研究管理器
research_manager = ResearchManager(
    llm_service=llm_service,
    tool_registry=tool_registry,
    planning_manager=planning_manager
)

# 执行深度研究
report = await research_manager.conduct_research(
    research_question="Python 异步编程的最佳实践",
    depth="deep",  # shallow, medium, deep
    max_iterations=5
)

# 查看报告
print("摘要:", report.summary)
print("结论:", report.conclusion)
print("信息来源:", report.sources)
print("置信度:", report.analysis.confidence if report.analysis else "N/A")
```

### 2. 集成到 Orchestrator

在 `orchestrator.py` 中添加：

```python
from backend.core.agent.research import ResearchManager

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
        session_id = context.get("session_id") if context else None
        return await self.research_manager.conduct_research(
            question,
            depth=depth,
            session_id=session_id
        )
```

### 3. 在 stream_process 中自动检测

```python
async def stream_process(self, task: str, context: Optional[Dict] = None):
    """流式处理任务"""
    
    # 检测是否是研究任务
    research_keywords = ["研究", "调研", "分析", "调查", "深度", "详细", "report"]
    is_research_task = any(kw in task.lower() for kw in research_keywords)
    
    if is_research_task:
        # 使用深度研究功能
        yield "开始深度研究...\n"
        
        report = await self.deep_research(
            task,
            depth="medium",
            context=context
        )
        
        yield f"\n# 研究报告\n\n"
        yield f"## 摘要\n{report.summary}\n\n"
        yield f"## 主要发现\n"
        for finding in report.findings[:5]:
            yield f"- [{finding.source}] {finding.content[:100]}...\n"
        yield f"\n## 结论\n{report.conclusion}\n"
    else:
        # 正常流程
        async for chunk in self._stream_normal_process(task, context):
            yield chunk
```

## 研究深度级别

### Shallow（浅层）

- **轮次**：1-2 轮搜索
- **用途**：快速回答简单问题
- **示例**："Python 是什么？"

```python
report = await research_manager.conduct_research(
    "Python 是什么？",
    depth="shallow"
)
```

### Medium（中等）

- **轮次**：3-5 轮搜索
- **用途**：多角度分析，生成基本报告
- **示例**："Python 异步编程的最佳实践"

```python
report = await research_manager.conduct_research(
    "Python 异步编程的最佳实践",
    depth="medium"
)
```

### Deep（深度）

- **轮次**：5+ 轮搜索
- **用途**：全面分析，生成详细报告
- **示例**："深度研究量子计算的最新进展"

```python
report = await research_manager.conduct_research(
    "深度研究量子计算的最新进展",
    depth="deep",
    max_iterations=8
)
```

## 配置选项

在 `.env` 文件中添加：

```bash
# 深度研究配置
ENABLE_DEEP_RESEARCH=true
DEEP_RESEARCH_MAX_ITERATIONS=5
DEEP_RESEARCH_DEFAULT_DEPTH=medium
DEEP_RESEARCH_MIN_CONFIDENCE=0.8
```

## 研究报告结构

```python
@dataclass
class ResearchReport:
    question: str              # 研究问题
    summary: str               # 执行摘要
    findings: List[ResearchFinding]  # 研究发现列表
    analysis: ResearchAnalysis  # 分析结果
    conclusion: str            # 结论
    sources: List[str]        # 信息来源
    generated_at: datetime     # 生成时间
```

### ResearchFinding（研究发现）

```python
finding = ResearchFinding(
    source="google_search",           # 信息来源
    content="...",                    # 内容
    relevance_score=0.85,            # 相关性分数（0-1）
    timestamp=datetime.now(),         # 时间戳
    metadata={}                       # 元数据
)
```

### ResearchAnalysis（分析结果）

```python
analysis = ResearchAnalysis(
    key_points=["要点1", "要点2"],    # 关键点
    contradictions=["矛盾1"],         # 矛盾点
    gaps=["信息缺口1"],               # 信息缺口
    confidence=0.85,                  # 置信度（0-1）
    next_steps=["下一步建议"]         # 下一步研究建议
)
```

## 使用示例

### 示例1：技术研究

```python
report = await research_manager.conduct_research(
    "React 18 的新特性和最佳实践",
    depth="medium"
)

print(f"研究问题: {report.question}")
print(f"摘要: {report.summary}")
print(f"置信度: {report.analysis.confidence}")
print(f"信息来源: {', '.join(report.sources)}")
```

### 示例2：市场调研

```python
report = await research_manager.conduct_research(
    "2024年人工智能市场趋势分析",
    depth="deep",
    max_iterations=8
)

# 查看关键发现
for finding in report.findings:
    if finding.relevance_score > 0.7:
        print(f"[{finding.source}] {finding.content[:200]}")
```

### 示例3：学术研究

```python
report = await research_manager.conduct_research(
    "深度学习在自然语言处理中的应用",
    depth="deep"
)

# 查看分析结果
if report.analysis:
    print("关键点:")
    for point in report.analysis.key_points:
        print(f"  - {point}")
    
    print("\n信息缺口:")
    for gap in report.analysis.gaps:
        print(f"  - {gap}")
```

## 与规划文件集成

深度研究功能会自动将研究发现记录到 `findings.md`：

```python
# 如果提供了 session_id，研究发现会自动记录
report = await research_manager.conduct_research(
    "研究问题",
    depth="medium",
    session_id="session_123"
)

# 研究发现已记录到 {session_id}_findings.md
```

## 最佳实践

1. **选择合适的研究深度**
   - 简单问题使用 `shallow`
   - 一般问题使用 `medium`
   - 复杂问题使用 `deep`

2. **设置合理的迭代次数**
   - `shallow`: 1-2 次
   - `medium`: 3-5 次
   - `deep`: 5-8 次

3. **检查置信度**
   - 如果置信度 < 0.6，可能需要增加迭代次数
   - 如果置信度 > 0.9，可以提前结束

4. **查看信息缺口**
   - 如果 `analysis.gaps` 不为空，可能需要继续研究
   - 可以根据缺口调整研究策略

## 注意事项

1. **API 调用成本**：深度研究会进行多轮 LLM 调用和工具调用，可能产生较高成本
2. **执行时间**：深度研究可能需要较长时间（几分钟）
3. **信息准确性**：研究结果基于搜索工具返回的信息，需要验证准确性
4. **工具可用性**：确保研究工具（google_search, wikipedia 等）已配置并可用

## 故障排除

### 问题1：研究计划创建失败

**原因**：LLM 返回格式不正确

**解决**：检查 `_parse_json_response()` 方法，可能需要改进 JSON 解析逻辑

### 问题2：工具调用失败

**原因**：工具未配置或 API Key 无效

**解决**：检查工具配置和 API Key

### 问题3：研究报告质量不高

**原因**：收集的信息不足或相关性低

**解决**：
- 增加迭代次数
- 改进搜索查询生成逻辑
- 调整相关性计算算法

