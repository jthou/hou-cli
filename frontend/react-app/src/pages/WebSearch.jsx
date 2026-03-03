import { useState } from 'react'
import TaskFormPage from '../components/task/TaskFormPage'
import TaskListByTypePanel from '../components/TaskListByTypePanel'
import TaskDetailModal from '../components/task/TaskDetailModal'

export default function WebSearch() {
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(undefined)

  return (
    <TaskFormPage
      taskType="web_search"
      title="网页搜索"
      description="使用 DuckDuckGo 执行关键词搜索，支持定时执行。提交后任务将加入队列，可在"
      submitLabel="提交搜索"
      rightContent={
        <>
          <TaskListByTypePanel
            taskType="web_search"
            title="网页搜索任务"
            emptyText="暂无网页搜索任务"
            onShowDetail={setDetailTaskId}
            refreshTrigger={refreshTrigger}
          />
          {detailTaskId && (
            <TaskDetailModal
              taskId={detailTaskId}
              onClose={() => setDetailTaskId(null)}
              onRefresh={() => {
                setDetailTaskId(null)
                setRefreshTrigger((t) => (t ?? 0) + 1)
              }}
              taskTypes={[]}
            />
          )}
        </>
      }
    />
  )
}
