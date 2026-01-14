# Planning 系统改进设计方案

## 目标

让 Planning 系统真正起到设计作用，而不仅仅是记录错误和进度。

## 核心问题

当前 Planning 系统的问题：
1. Planning 文件是空模板，没有实际的设计内容
2. LLM 没有主动使用规划文件来指导设计决策
3. 系统优先使用预定义的技能，而不是根据规划文件来设计工作流

## 改进方案

### 1. 创建 Planning Tool - 让 LLM 主动读写规划文件

#### 1.1 设计思路

创建一个专门的 `planning_tool`，让 LLM 可以：
- 读取规划文件（task_plan.md, findings.md, progress.md）
- 更新规划文件（记录技术决策、回答问题、更新阶段状态）
- 查询规划文件（检查当前阶段、查看已做的决策）

#### 1.2 工具定义

```python
class PlanningTool(Tool):
    """规划文件操作工具
    
    允许 LLM 主动读取和更新规划文件，记录技术决策和设计思路。
    """
    
    operations = [
        "read_task_plan",      # 读取任务规划
        "read_findings",       # 读取研究发现
        "read_progress",       # 读取进度日志
        "update_phase_status", # 更新阶段状态
        "add_decision",        # 添加技术决策
        "answer_question",     # 回答问题
        "add_finding",        # 添加研究发现
        "update_goal",        # 更新目标
    ]
```

### 2. 增强 Planning Manager - 支持结构化更新

#### 2.1 新增方法

```python
class PlanningManager:
    # 现有方法...
    
    def add_decision(self, decision: str, rationale: str, session_id: Optional[str] = None):
        """添加技术决策到 findings.md"""
        
    def answer_question(self, question: str, answer: str, session_id: Optional[str] = None):
        """回答问题并更新到 task_plan.md"""
        
    def update_phase_status(self, phase: str, status: str, session_id: Optional[str] = None):
        """更新阶段状态"""
        
    def add_finding(self, finding: str, category: str = "Research Findings", session_id: Optional[str] = None):
        """添加研究发现"""
```

### 3. 改进 System Prompt - 引导 LLM 使用规划文件

#### 3.1 增强规划上下文

在 system_prompt 中添加更详细的指导：

```python
planning_context = f"""
【重要】任务规划文件已创建，请遵循以下规划执行任务：

{task_plan_content[:2000]}

**规划文件使用指南：**

1. **任务开始前**：
   - 使用 planning_tool 读取 task_plan.md，了解任务目标和阶段
   - 使用 planning_tool 读取 findings.md，查看已有的研究和决策
   - 回答 task_plan.md 中的 "Key Questions"

2. **设计阶段**：
   - 在做出技术决策前，使用 planning_tool 记录决策和理由
   - 例如：选择使用 video_extract_srt 技能而不是 video_summary，因为只需要字幕提取
   - 将研究发现记录到 findings.md

3. **执行阶段**：
   - 完成每个阶段后，使用 planning_tool 更新阶段状态
   - 遇到错误时，记录到 task_plan.md 的错误表
   - 将操作记录到 progress.md

4. **技能选择**：
   - 如果规划文件中记录了技能选择决策，优先使用该技能
   - 如果规划文件中记录了工作流调整，按照规划执行

**规划文件路径：**
- task_plan.md: {planning_files.task_plan}
- findings.md: {planning_files.findings}
- progress.md: {planning_files.progress}
"""
```

### 4. 技能选择增强 - 让规划文件影响技能选择

#### 4.1 设计思路

在技能匹配时，检查规划文件中是否有技能选择决策：

```python
def _match_skill_with_planning(self, user_input: str, planning_files: Optional[PlanningFiles]) -> Optional[Skill]:
    """考虑规划文件的技能匹配"""
    
    # 1. 先进行常规匹配
    matched_skill = self.skill_registry.match(user_input)
    
    # 2. 如果有规划文件，检查是否有技能选择决策
    if planning_files:
        decision = self._extract_skill_decision_from_planning(planning_files)
        if decision:
            # 优先使用规划文件中指定的技能
            skill = self.skill_registry.get(decision.skill_name)
            if skill:
                logger.info(f"根据规划文件选择技能: {decision.skill_name}")
                return skill
    
    return matched_skill

def _extract_skill_decision_from_planning(self, planning_files: PlanningFiles) -> Optional[SkillDecision]:
    """从规划文件中提取技能选择决策"""
    findings_content = planning_files.findings.read_text()
    
    # 解析 Technical Decisions 部分
    # 查找格式：| 使用 video_extract_srt 技能 | 只需要字幕提取，不需要摘要 |
    # ...
```

### 5. 工作流调整 - 让规划文件影响工作流执行

#### 5.1 设计思路

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
    
    # 3. 执行工作流
    return await self.execute_workflow(workflow, parameters)
```

## 实现步骤

### Phase 1: 创建 Planning Tool

1. 创建 `backend/core/agent/tools/builtin/planning_tool.py`
2. 实现读取、更新规划文件的操作
3. 注册到 ToolRegistry

### Phase 2: 增强 Planning Manager

1. 添加结构化更新方法（add_decision, answer_question 等）
2. 支持解析和更新 Markdown 表格
3. 添加规划文件查询方法

### Phase 3: 改进 System Prompt

1. 增强规划上下文提示
2. 添加规划文件使用指南
3. 引导 LLM 主动使用 planning_tool

### Phase 4: 技能选择增强

1. 实现 `_match_skill_with_planning` 方法
2. 实现 `_extract_skill_decision_from_planning` 方法
3. 在 orchestrator 中集成

### Phase 5: 工作流调整

1. 实现 `_extract_workflow_adjustments` 方法
2. 实现 `_apply_workflow_adjustments` 方法
3. 在 SkillExecutor 中集成

## 使用示例

### 示例 1: LLM 主动记录决策

```python
# LLM 调用 planning_tool
planning_tool.execute(
    operation="add_decision",
    decision="使用 video_extract_srt 技能而不是 video_summary",
    rationale="用户只需要字幕提取，不需要摘要和文章生成，video_extract_srt 更简单高效"
)
```

### 示例 2: LLM 回答问题

```python
# LLM 调用 planning_tool
planning_tool.execute(
    operation="answer_question",
    question="应该使用哪个技能来处理字幕提取？",
    answer="使用 video_extract_srt 技能，因为它专门用于字幕提取，工作流更简单"
)
```

### 示例 3: 规划文件影响技能选择

```markdown
## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 video_extract_srt 技能 | 只需要字幕提取，不需要摘要和文章生成 |
```

系统会自动选择 `video_extract_srt` 技能。

## 预期效果

1. **规划文件有实际内容**：LLM 会主动记录技术决策和设计思路
2. **规划文件指导执行**：技能选择和工作流调整会参考规划文件
3. **规划文件持续更新**：LLM 会在执行过程中不断更新规划文件
4. **设计思路可追溯**：所有设计决策都有记录和理由

## 注意事项

1. **性能考虑**：规划文件读写需要缓存和批量更新
2. **错误处理**：规划文件更新失败不应影响主流程
3. **格式规范**：需要定义清晰的 Markdown 格式规范
4. **向后兼容**：现有规划文件应该能够正常工作

