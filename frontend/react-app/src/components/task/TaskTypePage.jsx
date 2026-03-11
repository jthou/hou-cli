/**
 * 任务类型页面：表单 + 右侧任务列表 + 可选详情弹窗
 * 合并 WebSearch、UrlToWiki、VideoDownload 等页面的通用布局与逻辑，避免重复代码。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TaskFormPage from './TaskFormPage'
import TaskListByTypePanel from '../TaskListByTypePanel'
import TaskDetailModal from './TaskDetailModal'

export default function TaskTypePage({
  taskType,
  title,
  description,
  submitLabel = '提交任务',
  listTitle,
  emptyText,
  showDetailModal = true,
  taskTypes = [],
  topContent,
}) {
  const navigate = useNavigate()
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(undefined)

  const resolvedListTitle = listTitle ?? `${title}任务`
  const resolvedEmptyText = emptyText ?? `暂无${resolvedListTitle}`

  const handleEditBeforeRestart = (task) => {
    setDetailTaskId(null)
    navigate('/tasks', { state: { editTask: task } })
  }

  const rightContent = (
    <>
      <TaskListByTypePanel
        taskType={taskType}
        title={resolvedListTitle}
        emptyText={resolvedEmptyText}
        onShowDetail={showDetailModal ? setDetailTaskId : undefined}
        refreshTrigger={refreshTrigger}
      />
      {showDetailModal && detailTaskId && (
        <TaskDetailModal
          taskId={detailTaskId}
          onClose={() => setDetailTaskId(null)}
          onRefresh={() => {
            setDetailTaskId(null)
            setRefreshTrigger((t) => (t ?? 0) + 1)
          }}
          onEditBeforeRestart={handleEditBeforeRestart}
          taskTypes={taskTypes}
        />
      )}
    </>
  )

  return (
    <TaskFormPage
      taskType={taskType}
      title={title}
      description={description}
      submitLabel={submitLabel}
      rightContent={rightContent}
      topContent={topContent}
      onTaskCreated={() => setRefreshTrigger((t) => (t ?? 0) + 1)}
    />
  )
}
