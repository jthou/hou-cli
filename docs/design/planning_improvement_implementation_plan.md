# Planning 系统改进实施计划

## 目标

让 Planning 系统真正起到设计作用，而不仅仅是记录错误和进度。

## 当前问题

1. Planning 文件是空模板，没有实际的设计内容
2. LLM 没有主动使用规划文件来指导设计决策
3. 系统优先使用预定义的技能，而不是根据规划文件来设计工作流

## 解决方案

### 方案 1: 创建 Planning Tool（核心）

让 LLM 可以主动读取和更新规划文件。

**实施步骤**：
1. 创建 `backend/core/agent/tools/builtin/planning_tool.py`
2. 实现 9 个操作：read_task_plan, read_findings, read_progress, update_phase_status, add_decision, answer_question, add_finding, update_goal, query_planning
3. 在 `PlanningManager` 中添加对应的方法支持
4. 在 `Orchestrator._register_tools` 中注册该工具

**预期效果**：
- LLM 可以在任务开始前读取规划文件
- LLM 可以记录技术决策和设计思路
- LLM 可以回答问题并更新规划文件

### 方案 2: 增强 Planning Manager

添加结构化更新方法，支持解析和更新 Markdown 表格。

**实施步骤**：
1. 添加 `read_findings()` 方法
2. 添加 `read_progress()` 方法
3. 添加 `update_phase_status_by_name()` 方法（根据阶段名称更新）
4. 添加 `add_decision()` 方法（更新 Technical Decisions 表格）
5. 添加 `answer_question()` 方法（更新 Key Questions 部分）
6. 添加 `update_goal()` 方法（更新 Goal 部分）
7. 添加 `query_planning()` 方法（智能查询）

**技术细节**：
- 使用正则表达式解析 Markdown 表格
- 支持增量更新（不覆盖现有内容）
- 使用缓存机制提高性能

### 方案 3: 改进 System Prompt

增强规划上下文提示，引导 LLM 主动使用 planning_tool。

**实施步骤**：
1. 在 `orchestrator.py` 的 `stream_process` 方法中增强 `planning_context`
2. 添加详细的规划文件使用指南
3. 强调在任务开始前必须读取规划文件并回答问题
4. 强调在做出技术决策前必须记录决策和理由

**示例内容**：
```python
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

### 方案 4: 技能选择增强

让规划文件中的技能选择决策影响实际的技能匹配。

**实施步骤**：
1. 在 `orchestrator.py` 中添加 `_match_skill_with_planning()` 方法
2. 添加 `_extract_skill_decision_from_planning()` 方法
3. 在 `stream_process` 中，技能匹配时调用 `_match_skill_with_planning()`

**实现逻辑**：
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
            skill = self.skill_registry.get(skill_decision["skill_name"])
            if skill:
                logger.info(f"根据规划文件选择技能: {skill_decision['skill_name']}")
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

### 方案 5: 工作流调整（可选）

让规划文件中的工作流调整影响技能的执行。

**实施步骤**：
1. 在 `SkillExecutor` 中添加 `execute_workflow_with_planning()` 方法
2. 添加 `_extract_workflow_adjustments()` 方法
3. 添加 `_apply_workflow_adjustments()` 方法
4. 在技能执行时调用 `execute_workflow_with_planning()`

**注意**：这个功能比较复杂，可以放在 Phase 2 实现。

## 实施优先级

### Phase 1: 核心功能（必须）

1. ✅ 创建 Planning Tool
2. ✅ 增强 Planning Manager（添加缺失的方法）
3. ✅ 注册 Planning Tool 到 ToolRegistry
4. ✅ 改进 System Prompt

**预期时间**：2-3 小时

### Phase 2: 技能选择增强（重要）

1. ✅ 实现 `_match_skill_with_planning()` 方法
2. ✅ 实现 `_extract_skill_decision_from_planning()` 方法
3. ✅ 在 `stream_process` 中集成

**预期时间**：1-2 小时

### Phase 3: 工作流调整（可选）

1. ⏳ 实现工作流调整逻辑
2. ⏳ 测试和验证

**预期时间**：2-3 小时

## 测试计划

### 单元测试

1. PlanningTool 的每个操作
2. PlanningManager 的新增方法
3. 技能选择增强逻辑

### 集成测试

1. LLM 使用 planning_tool 记录决策
2. 规划文件影响技能选择
3. 端到端测试：复杂任务 → 创建规划 → LLM 记录决策 → 技能选择 → 执行

## 预期效果

### 改进前

- Planning 文件是空模板
- LLM 不主动使用规划文件
- 技能选择不受规划文件影响

### 改进后

- Planning 文件有实际的设计内容
- LLM 主动读取和更新规划文件
- 技能选择会参考规划文件中的决策
- 所有设计决策都有记录和理由

## 风险与缓解

### 风险 1: LLM 不主动使用 planning_tool

**缓解措施**：
- 在 system_prompt 中明确要求使用 planning_tool
- 在任务开始前强制要求读取规划文件
- 提供清晰的使用示例

### 风险 2: 规划文件解析失败

**缓解措施**：
- 使用正则表达式时添加错误处理
- 提供降级方案（如果解析失败，使用常规匹配）
- 记录详细的错误日志

### 风险 3: 性能问题

**缓解措施**：
- 使用缓存机制（已有）
- 批量更新机制（已有）
- 限制规划文件内容长度（已有，2000 字符）

## 后续优化

1. **LLM 辅助规划**：让 LLM 在创建规划文件时自动填充初始内容
2. **规划文件模板**：根据任务类型使用不同的模板
3. **规划文件验证**：验证规划文件的格式和完整性
4. **规划文件可视化**：提供规划文件的图形化展示

