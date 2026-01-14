# 规划文件管理模块（方案2：集成到 Orchestrator）

## 概述

本模块实现了 Manus 风格的持久化规划模式，通过 3 个 Markdown 文件来管理复杂任务：
- `task_plan.md`: 任务规划和进度跟踪
- `findings.md`: 研究和发现
- `progress.md`: 会话日志和测试结果

## 功能特性

### 1. 自动检测复杂任务
- 基于任务描述长度、关键词、历史对话等判断任务复杂度
- 自动创建规划文件

### 2. 自动更新规划文件
- 工具调用前：读取规划文件，注入到 LLM 上下文
- 工具调用后：自动更新进度、发现、错误记录

### 3. 配置项支持
- `ENABLE_PLANNING`: 是否启用规划功能（默认：true）
- `PLANNING_WORK_DIR`: 规划文件工作目录（默认：项目根目录/plans）
- `PLANNING_MIN_TASK_LENGTH`: 最小任务长度（默认：20）
- `PLANNING_COMPLEXITY_THRESHOLD`: 复杂度阈值（默认：0.3）

## 使用方法

### 环境变量配置

在 `.env` 文件中添加：

```bash
# 启用规划功能
ENABLE_PLANNING=true

# 规划文件工作目录（可选）
PLANNING_WORK_DIR=./plans

# 复杂度判断参数（可选）
PLANNING_MIN_TASK_LENGTH=20
PLANNING_COMPLEXITY_THRESHOLD=0.3
```

### 自动触发

当用户提交复杂任务时，系统会自动：
1. 检测任务复杂度
2. 创建规划文件（如果任务复杂）
3. 在工具调用前后自动更新规划文件

### 规划文件位置

规划文件默认保存在 `项目根目录/plans/` 目录下，文件名格式：
- `{session_id}_task_plan.md`
- `{session_id}_findings.md`
- `{session_id}_progress.md`

## 实现细节

### PlanningManager
- 负责规划文件的创建、读取、更新
- 支持阶段状态更新、错误记录、发现记录等

### TaskComplexityAnalyzer
- 分析任务复杂度
- 基于多个维度计算复杂度分数

### Orchestrator 集成
- 在 `stream_process` 开始时检测复杂任务
- 在工具调用前后自动更新规划文件

## 注意事项

1. 规划文件会占用磁盘空间，建议定期清理
2. 复杂度判断可能不准确，需要根据实际情况调整阈值
3. 规划文件更新是异步的，不会阻塞主流程

## 后续优化

- [ ] 与对话评估功能集成
- [ ] 支持规划文件版本管理
- [ ] 优化复杂度判断算法
- [ ] 添加规划文件清理机制

