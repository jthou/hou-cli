# CLI 与测试脚本执行路径差异分析

## 问题描述

同样的任务，通过 CLI 执行和通过 `scripts/test_autonomous_executor.py` 测试脚本执行，结果完全不同：

- **CLI执行**：使用技能系统（`video_extract_srt`），通过 `SkillExecutor` 执行
- **测试脚本**：使用自主执行器（`AutonomousExecutor`），直接调用工具

## 执行路径对比

### CLI 执行路径（`orchestrator.stream_process`）

```
1. 复杂度分析（line 859-909）
   ├─ 如果 is_complex = True
   │  ├─ 检查 ENABLE_AUTONOMOUS_EXECUTION
   │  │  ├─ 如果启用 → 使用 AutonomousExecutor（line 917-937）
   │  │  └─ 如果未启用 → 创建规划文件（line 948-976）
   │  └─ 如果 is_complex = False → 跳过自主执行
   │
2. 技能匹配（line 1171-1188）
   ├─ 如果匹配到技能 → 使用 SkillExecutor（line 1188-1203）
   └─ 如果未匹配 → 使用传统 LLM 对话模式
```

**关键问题**：
- 如果任务被判定为**不复杂**（`is_complex = False`），就不会使用自主执行
- 即使启用了 `ENABLE_AUTONOMOUS_EXECUTION`，如果任务不复杂，也会跳过自主执行
- 然后进行技能匹配，如果匹配到技能（如 `video_extract_srt`），就使用技能执行

### 测试脚本执行路径

```
1. 直接创建 AutonomousExecutor 实例
2. 直接调用 executor.execute()
3. 不经过 orchestrator.stream_process
4. 不进行技能匹配
5. 不进行复杂度分析
```

## 根本原因

1. **复杂度判断可能不准确**：
   - 任务 "下载视频...并从音频中提取字幕" 可能被判定为不复杂
   - 导致跳过了自主执行逻辑

2. **技能匹配优先级问题**：
   - 技能匹配在复杂度分析之后进行
   - 如果任务不复杂，即使启用了自主执行，也会进行技能匹配
   - 技能匹配成功后会使用技能执行，而不是自主执行

3. **执行顺序问题**：
   - 自主执行只在 `is_complex = True` 时才会被考虑
   - 技能匹配在所有情况下都会进行（除非任务复杂且自主执行成功）

## 解决方案

### 方案1：调整执行顺序（推荐）

如果启用了 `ENABLE_AUTONOMOUS_EXECUTION`，应该在技能匹配之前检查：

```python
# 在技能匹配之前
if autonomous_execution_enabled and self.autonomous_executor:
    # 使用自主执行模式（不依赖复杂度）
    async for output in self.autonomous_executor.execute(...):
        yield output
    return

# 然后才进行技能匹配
matched_skill = self.skill_registry.match(task)
```

### 方案2：技能匹配时跳过自主执行

在技能匹配时，如果启用了自主执行，跳过技能匹配：

```python
# 在技能匹配之前
if autonomous_execution_enabled and self.autonomous_executor:
    # 跳过技能匹配，直接使用自主执行
    pass
else:
    matched_skill = self.skill_registry.match(task)
```

### 方案3：添加配置选项

添加配置选项，允许用户选择：
- `AUTONOMOUS_EXECUTION_PRIORITY`: 自主执行的优先级（高于技能匹配或低于技能匹配）

## 当前行为

从终端日志看：
1. 任务被匹配到 `video_extract_srt` 技能
2. 使用 `SkillExecutor` 执行
3. 技能执行失败（HTTP 412 错误）
4. 没有使用自主执行器

这说明：
- 任务可能被判定为不复杂（`is_complex = False`）
- 或者自主执行未启用（`ENABLE_AUTONOMOUS_EXECUTION=false`）
- 技能匹配成功，优先使用了技能执行

## 建议

1. **检查环境变量**：确认 CLI 执行时 `ENABLE_AUTONOMOUS_EXECUTION=true`
2. **调整执行顺序**：如果启用了自主执行，应该在技能匹配之前检查
3. **改进复杂度判断**：确保复杂任务能被正确识别
4. **添加调试日志**：记录执行路径选择的原因

