# Planning Tool 设计文档

## 概述

创建一个专门的 `PlanningTool`，让 LLM 可以主动读取和更新规划文件，记录技术决策和设计思路。

## 工具接口设计

### 工具名称
`planning`

### 操作类型

```python
operations = [
    "read_task_plan",      # 读取任务规划
    "read_findings",       # 读取研究发现
    "read_progress",       # 读取进度日志
    "update_phase_status", # 更新阶段状态
    "add_decision",         # 添加技术决策
    "answer_question",     # 回答问题
    "add_finding",         # 添加研究发现
    "update_goal",        # 更新目标
    "query_planning",     # 查询规划文件（综合查询）
]
```

### 参数定义

```python
parameters = [
    ToolParameter(
        name="operation",
        type="string",
        description="操作类型",
        required=True,
        enum=operations
    ),
    ToolParameter(
        name="session_id",
        type="string",
        description="会话 ID（可选，默认使用当前会话）",
        required=False
    ),
    # 以下参数根据 operation 类型可选
    ToolParameter(
        name="phase",
        type="string",
        description="阶段名称（用于 update_phase_status）",
        required=False
    ),
    ToolParameter(
        name="status",
        type="string",
        description="状态值（pending/in_progress/complete，用于 update_phase_status）",
        required=False,
        enum=["pending", "in_progress", "complete"]
    ),
    ToolParameter(
        name="decision",
        type="string",
        description="技术决策（用于 add_decision）",
        required=False
    ),
    ToolParameter(
        name="rationale",
        type="string",
        description="决策理由（用于 add_decision）",
        required=False
    ),
    ToolParameter(
        name="question",
        type="string",
        description="问题（用于 answer_question）",
        required=False
    ),
    ToolParameter(
        name="answer",
        type="string",
        description="答案（用于 answer_question）",
        required=False
    ),
    ToolParameter(
        name="finding",
        type="string",
        description="研究发现（用于 add_finding）",
        required=False
    ),
    ToolParameter(
        name="category",
        type="string",
        description="分类（Research Findings/Technical Decisions/Resources，用于 add_finding）",
        required=False,
        enum=["Research Findings", "Technical Decisions", "Resources"]
    ),
    ToolParameter(
        name="goal",
        type="string",
        description="更新后的目标（用于 update_goal）",
        required=False
    ),
    ToolParameter(
        name="query",
        type="string",
        description="查询内容（用于 query_planning，如 '当前阶段'、'已做的决策'）",
        required=False
    ),
]
```

## 实现细节

### 1. PlanningTool 类

```python
class PlanningTool(Tool):
    """规划文件操作工具"""
    
    def __init__(self, planning_manager: PlanningManager):
        self.planning_manager = planning_manager
        # ... 初始化参数 ...
    
    async def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        session_id = kwargs.get("session_id")
        
        try:
            if operation == "read_task_plan":
                content = self.planning_manager.read_task_plan(session_id)
                return ToolResult(success=True, data={"content": content})
            
            elif operation == "read_findings":
                content = self.planning_manager.read_findings(session_id)
                return ToolResult(success=True, data={"content": content})
            
            elif operation == "read_progress":
                content = self.planning_manager.read_progress(session_id)
                return ToolResult(success=True, data={"content": content})
            
            elif operation == "update_phase_status":
                phase = kwargs.get("phase")
                status = kwargs.get("status")
                success = self.planning_manager.update_phase_status_by_name(phase, status, session_id)
                return ToolResult(success=success, data={"message": f"阶段 {phase} 状态已更新为 {status}"})
            
            elif operation == "add_decision":
                decision = kwargs.get("decision")
                rationale = kwargs.get("rationale")
                success = self.planning_manager.add_decision(decision, rationale, session_id)
                return ToolResult(success=success, data={"message": "技术决策已记录"})
            
            elif operation == "answer_question":
                question = kwargs.get("question")
                answer = kwargs.get("answer")
                success = self.planning_manager.answer_question(question, answer, session_id)
                return ToolResult(success=success, data={"message": "问题已回答"})
            
            elif operation == "add_finding":
                finding = kwargs.get("finding")
                category = kwargs.get("category", "Research Findings")
                success = self.planning_manager.add_finding(finding, category, session_id)
                return ToolResult(success=success, data={"message": "研究发现已记录"})
            
            elif operation == "update_goal":
                goal = kwargs.get("goal")
                success = self.planning_manager.update_goal(goal, session_id)
                return ToolResult(success=success, data={"message": "目标已更新"})
            
            elif operation == "query_planning":
                query = kwargs.get("query")
                result = self.planning_manager.query_planning(query, session_id)
                return ToolResult(success=True, data={"result": result})
            
            else:
                return ToolResult(success=False, error=f"未知操作: {operation}")
        
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

### 2. PlanningManager 增强方法

需要在 `PlanningManager` 中添加以下方法：

```python
def read_findings(self, session_id: Optional[str] = None) -> Optional[str]:
    """读取 findings.md"""
    
def read_progress(self, session_id: Optional[str] = None) -> Optional[str]:
    """读取 progress.md"""
    
def update_phase_status_by_name(self, phase_name: str, status: str, session_id: Optional[str] = None) -> bool:
    """根据阶段名称更新状态（如 'Phase 1', 'Phase 2'）"""
    
def add_decision(self, decision: str, rationale: str, session_id: Optional[str] = None) -> bool:
    """添加技术决策到 findings.md 的 Technical Decisions 部分"""
    
def answer_question(self, question: str, answer: str, session_id: Optional[str] = None) -> bool:
    """回答问题并更新到 task_plan.md 的 Key Questions 部分"""
    
def update_goal(self, goal: str, session_id: Optional[str] = None) -> bool:
    """更新任务目标"""
    
def query_planning(self, query: str, session_id: Optional[str] = None) -> str:
    """查询规划文件（智能查询）"""
```

## 使用示例

### 示例 1: LLM 读取规划文件

```python
# LLM 调用
planning_tool.execute(
    operation="read_task_plan",
    session_id="5f58322f"
)

# 返回
{
    "success": true,
    "data": {
        "content": "# Task Plan: ...\n## Goal\n..."
    }
}
```

### 示例 2: LLM 记录技术决策

```python
# LLM 调用
planning_tool.execute(
    operation="add_decision",
    decision="使用 video_extract_srt 技能而不是 video_summary",
    rationale="用户只需要字幕提取，不需要摘要和文章生成，video_extract_srt 更简单高效",
    session_id="5f58322f"
)

# 更新 findings.md
## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 video_extract_srt 技能而不是 video_summary | 用户只需要字幕提取，不需要摘要和文章生成，video_extract_srt 更简单高效 |
```

### 示例 3: LLM 回答问题

```python
# LLM 调用
planning_tool.execute(
    operation="answer_question",
    question="应该使用哪个技能来处理字幕提取？",
    answer="使用 video_extract_srt 技能，因为它专门用于字幕提取，工作流更简单",
    session_id="5f58322f"
)

# 更新 task_plan.md
## Key Questions
1. 应该使用哪个技能来处理字幕提取？ → 使用 video_extract_srt 技能，因为它专门用于字幕提取，工作流更简单
```

## 集成到 Orchestrator

### 1. 注册 Planning Tool

```python
def _register_tools(self):
    # ... 现有工具注册 ...
    
    # 注册规划工具（如果启用规划功能）
    if self.enable_planning and self.planning_manager:
        from backend.core.agent.tools.builtin.planning_tool import PlanningTool
        planning_tool = PlanningTool(self.planning_manager)
        self.tool_registry.register(planning_tool)
```

### 2. 增强 System Prompt

在 `stream_process` 中，当检测到复杂任务时，增强 system_prompt：

```python
if planning_files and task_plan_content:
    planning_context = f"""
【重要】任务规划文件已创建，请遵循以下规划执行任务：

{task_plan_content[:2000]}

**规划文件使用指南：**

1. **任务开始前**（必须执行）：
   - 使用 planning 工具的 read_task_plan 操作，读取任务规划
   - 使用 planning 工具的 read_findings 操作，查看已有的研究和决策
   - 使用 planning 工具的 answer_question 操作，回答 task_plan.md 中的 "Key Questions"

2. **设计阶段**（必须执行）：
   - 在做出技术决策前，使用 planning 工具的 add_decision 操作，记录决策和理由
   - 例如：选择使用 video_extract_srt 技能而不是 video_summary，因为只需要字幕提取
   - 将研究发现使用 add_finding 操作记录到 findings.md

3. **执行阶段**：
   - 完成每个阶段后，使用 planning 工具的 update_phase_status 操作，更新阶段状态
   - 遇到错误时，系统会自动记录到 task_plan.md 的错误表
   - 将操作记录到 progress.md（系统自动完成）

4. **技能选择**：
   - 如果规划文件中记录了技能选择决策，优先使用该技能
   - 如果规划文件中记录了工作流调整，按照规划执行

**规划文件路径：**
- task_plan.md: {planning_files.task_plan}
- findings.md: {planning_files.findings}
- progress.md: {planning_files.progress}

**重要**：在开始执行任务前，必须先使用 planning 工具读取规划文件并回答问题！
"""
```

## 技能选择增强

### 实现思路

在 `_match_skill` 方法中，检查规划文件中的技能选择决策：

```python
def _match_skill_with_planning(
    self, 
    user_input: str, 
    planning_files: Optional[PlanningFiles] = None
) -> Optional[Skill]:
    """考虑规划文件的技能匹配"""
    
    # 1. 先进行常规匹配
    matched_skill = self.skill_registry.match(user_input)
    
    # 2. 如果有规划文件，检查是否有技能选择决策
    if planning_files and planning_files.findings.exists():
        skill_decision = self._extract_skill_decision_from_planning(planning_files)
        if skill_decision:
            # 优先使用规划文件中指定的技能
            skill = self.skill_registry.get(skill_decision.skill_name)
            if skill:
                logger.info(f"根据规划文件选择技能: {skill_decision.skill_name} (理由: {skill_decision.rationale})")
                return skill
    
    return matched_skill

def _extract_skill_decision_from_planning(self, planning_files: PlanningFiles) -> Optional[Dict]:
    """从规划文件中提取技能选择决策"""
    try:
        findings_content = planning_files.findings.read_text(encoding='utf-8')
        
        # 解析 Technical Decisions 部分
        # 查找格式：| 使用 video_extract_srt 技能 | ... |
        import re
        
        # 匹配技能决策模式
        pattern = r'\|.*?(video_\w+|使用\s+(\w+)\s+技能).*?\|(.*?)\|'
        matches = re.finditer(pattern, findings_content, re.IGNORECASE)
        
        for match in matches:
            decision_text = match.group(0)
            rationale = match.group(3).strip()
            
            # 提取技能名称
            skill_name_match = re.search(r'video_(\w+)', decision_text, re.IGNORECASE)
            if skill_name_match:
                skill_name = f"video_{skill_name_match.group(1)}"
                return {
                    "skill_name": skill_name,
                    "rationale": rationale,
                    "decision_text": decision_text
                }
        
        return None
    except Exception as e:
        logger.warning(f"从规划文件提取技能决策失败: {e}")
        return None
```

## 工作流调整

### 实现思路

在技能执行时，检查规划文件中是否有工作流调整：

```python
async def execute_workflow_with_planning(
    self,
    workflow: Dict[str, Any],
    parameters: Dict[str, Any],
    planning_files: Optional[PlanningFiles] = None
):
    """执行工作流，考虑规划文件的调整"""
    
    # 1. 读取规划文件中的工作流调整
    workflow_adjustments = None
    if planning_files:
        workflow_adjustments = self._extract_workflow_adjustments(planning_files)
    
    # 2. 应用调整
    if workflow_adjustments:
        workflow = self._apply_workflow_adjustments(workflow, workflow_adjustments)
        logger.info(f"根据规划文件调整工作流: {workflow_adjustments}")
    
    # 3. 执行工作流
    return await self.execute_workflow(workflow, parameters)

def _extract_workflow_adjustments(self, planning_files: PlanningFiles) -> Optional[Dict]:
    """从规划文件中提取工作流调整"""
    # 例如：跳过某个步骤、修改参数等
    # 可以从 findings.md 或 task_plan.md 中解析
    pass
```

## 测试计划

### 单元测试

1. PlanningTool 的每个操作
2. PlanningManager 的新增方法
3. 技能选择增强逻辑
4. 工作流调整逻辑

### 集成测试

1. LLM 使用 planning_tool 记录决策
2. 规划文件影响技能选择
3. 规划文件影响工作流执行

## 实施优先级

1. **Phase 1（高优先级）**：创建 Planning Tool 和增强 Planning Manager
2. **Phase 2（中优先级）**：改进 System Prompt，引导 LLM 使用
3. **Phase 3（中优先级）**：技能选择增强
4. **Phase 4（低优先级）**：工作流调整

