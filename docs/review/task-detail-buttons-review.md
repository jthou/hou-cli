# 任务详情按钮 Review

## 一、入口点汇总

### 1. 「查看详情」按钮（TaskCard）

| 使用场景 | onShowDetail 来源 | 行为 | 合理性 |
|---------|------------------|------|--------|
| **任务管理页**（普通/管道/已删除） | `setDetailTaskId` | 本页打开 TaskDetailModal | ✅ 合理 |
| **TaskTypePage**（网文抓取、视频下载、网页搜索等） | `setDetailTaskId` | 本页打开 TaskDetailModal | ✅ 合理 |
| **PipelineOrchestration**（管道编排） | 无，fallback 到 `navigate('/tasks', { state: { detailTaskId } })` | 跳转到任务管理页并打开详情 | ✅ 合理 |
| **WechatDraftPage**（公众号草稿） | 无，同上 fallback | 跳转到任务管理页并打开详情 | ✅ 合理 |
| **ScheduledTaskRunsModal**（定时任务执行记录） | `onShowDetail` 传入 | **但 inRunsModal=true 时按钮被隐藏** | ⚠️ 见下文 |

### 2. 「查看任务」链接（创建任务后）

| 位置 | 行为 | 合理性 |
|-----|------|--------|
| MarkdownDraftActions（网文抓取草稿） | `Link to="/tasks" state={{ detailTaskId }}` | ✅ 合理 |
| SubtitlePreviewActions（字幕预览） | 同上 | ✅ 合理 |
| ArticleWriting（写文章 → 同步公众号） | `navigate('/tasks', { state: { detailTaskId } })` | ✅ 合理 |
| MarkdownActionButtons（写入 MediaWiki） | 同上 | ✅ 合理 |

### 3. TaskDetailModal 底部按钮

| 按钮 | 显示条件 | 依赖 | 合理性 |
|-----|---------|------|--------|
| **补全 result（供下游衔接）** | completed + output_dir 有值 + output_file 无 | 无 | ✅ 合理 |
| **重新入队** | failed + depends_on_task_id | 无 | ✅ 合理 |
| **编辑后重新执行** / **编辑管道** | completed / failed | `onEditBeforeRestart` | ✅ 已修复（TaskTypePage 跳转 /tasks） |
| **重新执行** | completed / failed | 无 | ✅ 合理 |
| **恢复** / **彻底删除** | deleted_at 有值 | 无 | ✅ 合理 |
| **删除** | 未删除 | 无 | ✅ 合理 |

---

## 二、不合理或待改进点

### 1. ScheduledTaskRunsModal 中隐藏「查看详情」

**现状**：`TaskCard` 在 `inRunsModal=true` 时**不渲染**「查看详情」按钮。

```jsx
// TaskCard.jsx L121-127
{!inRunsModal && (
  <button onClick={() => onShowDetail?.(task.task_id)} ...>
    查看详情
  </button>
)}
```

**影响**：在定时任务执行记录弹窗中，用户无法查看某次运行的任务详情，只能看到卡片内联的 result 摘要。

**建议**：
- **方案 A**：移除 `inRunsModal` 对「查看详情」的隐藏，让执行记录也能打开详情弹窗（会叠在 runs 弹窗之上，可接受）。
- **方案 B**：若刻意简化 runs 弹窗，可在文案或 tooltip 中说明「可到任务管理页查看详情」。

### 2. TaskCard 在 onShowDetail 未传入时的表现

**现状**：`TaskListByTypePanel` 始终传入 `onShowDetail`（要么来自父组件，要么用 `navigate` fallback），因此不会出现 `onShowDetail` 为 `undefined` 的情况。

但若将来有地方直接使用 `TaskCard` 且未传 `onShowDetail`，按钮会渲染，点击 `onShowDetail?.(task.task_id)` 无效果。

**建议**：在 `TaskCard` 中，当 `onShowDetail` 为 `undefined` 时隐藏「查看详情」按钮，避免无效点击：

```jsx
{!inRunsModal && onShowDetail && (
  <button ...>查看详情</button>
)}
```

### 3. 编辑后重新执行：跨页跳转体验

**现状**：在网文抓取、视频下载等 TaskTypePage 中点击「编辑后重新执行」会跳转到 `/tasks` 并打开编辑弹窗。

**评估**：实现简单、逻辑清晰，但会离开当前页面。若希望「留在当前页编辑」需在 TaskTypePage 内增加 EditTaskModal，改动较大。当前方案可接受。

---

## 三、架构与一致性

| 维度 | 评价 |
|-----|------|
| **入口统一** | TaskListByTypePanel 的 fallback 保证所有列表都有可用的「查看详情」 | ✅ |
| **详情展示** | TaskDetailModal 统一展示，TaskResultDisplay 按 task_type 渲染 | ✅ |
| **编辑流程** | 编辑后重新执行统一走 TaskManagement 的 CreateTaskModal | ✅ |
| **跨页导航** | 使用 `navigate(..., { state })` 传递 detailTaskId / editTask | ✅ |

---

## 四、建议修改项（按优先级）

1. **P1**：ScheduledTaskRunsModal 中恢复「查看详情」——去掉 `inRunsModal` 对按钮的隐藏，或明确说明为何隐藏。
2. **P2**：TaskCard 在 `onShowDetail` 未传入时隐藏「查看详情」按钮，避免无效点击。
3. **P3**：若产品上希望「编辑后重新执行」不离开当前页，再考虑在 TaskTypePage 内增加编辑弹窗。
