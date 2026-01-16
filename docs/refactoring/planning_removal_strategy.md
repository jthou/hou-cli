# Planning 架构移除与简化重构策略

## 问题分析

### 当前 Planning 架构的实际问题

1. **没有实际价值**
   - Planning 文件是空模板，没有实际的设计内容
   - LLM 没有主动使用规划文件来指导设计决策（没有 `planning_tool`）
   - 只是被动地将规划内容注入到 system_prompt（限制2000字符）
   - 只是被动地写入规划文件（记录进度、错误、发现）

2. **增加复杂性**
   - 需要维护 PlanningManager、TaskComplexityAnalyzer 等组件
   - 需要创建和管理 3 个 Markdown 文件
   - 需要判断任务复杂度
   - 增加了代码复杂度和维护成本

3. **与设计理念冲突**
   - 系统优先使用预定义的技能，而不是根据规划文件来设计工作流
   - 限制了 LLM 的自由推理和工具选择能力
   - 现代 LLM 已经有很强的推理能力，不需要预先规划

### 设计理念转变

**从**：预先规划 → 执行规划 → 记录进度
**到**：推理模型自由选择工具 → 多轮对话决策调整 → 完成任务

## 重构策略

### 阶段 1：移除 Planning 架构（保留任务管理）

#### 1.1 移除 Planning 相关代码

**文件删除/禁用**：
- `backend/core/agent/planning/` 目录（可选：保留但禁用）
- 或通过环境变量 `ENABLE_PLANNING=false` 禁用

**代码修改**：
- `backend/core/agent/orchestrator.py`：
  - 移除 `PlanningManager` 和 `TaskComplexityAnalyzer` 的初始化
  - 移除规划文件创建逻辑（第837-862行）
  - 移除 `planning_context` 注入到 system_prompt（第865-879行）
  - 移除规划文件更新逻辑（第1080-1086行、第1198-1203行、第1224-1230行、第1266-1311行、第1533-1580行、第1583-1598行、第2199-2227行）

#### 1.2 保留任务管理（TaskManager）

**保留原因**：
- 任务管理用于长任务的实时进度监控（如视频下载）
- 提供 SSE 进度推送，解决前端超时问题
- 与 Planning 解耦，独立运行

**保留内容**：
- `backend/core/agent/task_manager.py` - 完整保留
- `backend/api/task_routes.py` - 完整保留
- `backend/api/stream_sender.py` 中的 `LongTaskMonitor` - 完整保留
- `orchestrator.py` 中的任务创建和进度更新逻辑 - 保留

#### 1.3 简化进度回调

**修改**：`integrated_progress_callback` → `progress_callback`

```python
# 简化前（同时更新任务管理和规划文件）
def integrated_progress_callback(progress_or_message, message: str = ""):
    # 更新任务管理器
    task_manager.update_task_progress(...)
    # 更新规划文件
    planning_manager.add_progress(...)
    # 放入队列
    progress_queue.put_nowait(...)

# 简化后（只更新任务管理）
def progress_callback(progress_or_message, message: str = ""):
    # 更新任务管理器
    task_manager.update_task_progress(...)
    # 放入队列
    progress_queue.put_nowait(...)
```

### 阶段 2：增强 LLM 工具选择能力

#### 2.1 优化 System Prompt

**移除**：
- Planning 相关的上下文提示
- 复杂的规划文件使用指南

**增强**：
- 强调 LLM 应该根据任务需求自由选择工具
- 强调多轮对话的重要性
- 强调根据工具执行结果调整策略

**新的 System Prompt 结构**：
```python
system_prompt = f"""你是一个智能助手，能够帮助用户解决各种问题。

【核心原则】
1. 根据任务需求，自由选择合适的工具
2. 通过多轮对话，根据执行结果调整策略
3. 如果工具执行失败，尝试其他方法
4. 保持对话上下文，记住之前的操作和结果

【工具选择指南】
- 浏览器工具（browser）：访问网站、查看网页内容
- Google 搜索（google_search）：搜索网络信息
- 文件搜索（file_search）：查找本地文件
- 代码执行（execute_code）：执行代码、运行脚本
- ...（列出所有可用工具）

【多轮对话策略】
- 第一轮：分析任务，选择初始工具
- 根据结果：调整策略，选择下一个工具
- 持续迭代：直到任务完成或明确无法完成
"""
```

#### 2.2 增强工具调用循环

**当前**：最多 100 轮工具调用循环（已实现）

**优化**：
- 保持多轮对话能力
- 增强错误处理和策略调整
- 记录工具调用历史，避免重复失败

#### 2.3 移除技能优先逻辑（可选）

**当前**：优先匹配技能，技能失败才使用工具

**考虑**：
- 保留技能系统（如 `video_downloader`），但让 LLM 也可以直接选择工具
- 或者：将技能也暴露为工具，让 LLM 自由选择

### 阶段 3：简化评估功能（可选）

#### 3.1 评估功能独立化

**当前**：评估功能与 Planning 耦合

**重构**：
- 将评估功能独立出来
- 不依赖规划文件
- 评估结果可以记录到对话历史或日志

### 阶段 4：清理和优化

#### 4.1 代码清理

- 移除所有 Planning 相关的导入
- 移除所有 `planning_files` 参数
- 移除所有 `planning_manager` 引用
- 简化 `skill_context`（移除 `planning_files` 和 `planning_manager`）

#### 4.2 配置简化

**移除环境变量**：
- `ENABLE_PLANNING`
- `PLANNING_WORK_DIR`
- `PLANNING_MIN_TASK_LENGTH`
- `PLANNING_COMPLEXITY_THRESHOLD`

**保留环境变量**：
- `ENABLE_EVALUATION`（如果保留评估功能）

#### 4.3 文档更新

- 更新架构文档，移除 Planning 相关内容
- 更新 README，说明新的设计理念
- 标记 Planning 相关文档为"已废弃"

## 实施步骤

### 步骤 1：环境变量禁用（快速验证）

```bash
# .env
ENABLE_PLANNING=false
```

验证系统是否正常工作，确认 Planning 确实可以移除。

### 步骤 2：移除 Planning 代码

1. 移除 `orchestrator.py` 中的 Planning 相关代码
2. 简化进度回调
3. 移除规划文件创建和更新逻辑
4. 测试验证

### 步骤 3：优化 System Prompt

1. 移除 Planning 相关提示
2. 增强工具选择指南
3. 强调多轮对话策略
4. 测试验证

### 步骤 4：代码清理

1. 移除未使用的导入
2. 移除未使用的参数
3. 简化函数签名
4. 代码审查和测试

## 预期效果

### 架构简化

- **代码行数**：减少 ~500-800 行 Planning 相关代码
- **复杂度**：降低系统复杂度，更容易理解和维护
- **性能**：减少文件 I/O 操作，提高响应速度

### 功能增强

- **灵活性**：LLM 可以更自由地选择工具和调整策略
- **适应性**：通过多轮对话，更好地适应不同任务需求
- **可扩展性**：更容易添加新工具，不需要修改规划逻辑

### 保留功能

- **任务管理**：长任务进度监控功能完整保留
- **工具调用**：多轮工具调用循环完整保留
- **评估功能**：可以独立保留（可选）

## 风险评估

### 风险 1：复杂任务处理能力下降

**缓解措施**：
- 现代 LLM（如 GPT-4、Claude 3.5）已经有很强的推理能力
- 通过多轮对话，LLM 可以自主分解复杂任务
- 如果确实需要，可以后续添加轻量级的任务分解提示

### 风险 2：失去任务规划记录

**缓解措施**：
- 对话历史已经记录了所有操作
- 如果需要，可以添加简单的任务日志功能（不依赖 Planning 架构）

### 风险 3：回退困难

**缓解措施**：
- 通过环境变量 `ENABLE_PLANNING` 控制，可以快速回退
- 保留 Planning 代码但禁用，而不是删除

## 总结

这个重构策略的核心思想是：
1. **移除 Planning 架构**：减少复杂性，没有实际价值
2. **保留任务管理**：用于长任务进度监控
3. **增强 LLM 自由推理**：通过多轮对话，让 LLM 自主选择工具和调整策略
4. **简化系统**：降低维护成本，提高可扩展性

符合现代 LLM 的能力特点，更灵活、更适应不同任务需求。

