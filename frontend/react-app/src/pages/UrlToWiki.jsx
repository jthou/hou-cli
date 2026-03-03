import { useState } from 'react'
import TaskFormPage from '../components/task/TaskFormPage'
import TaskListByTypePanel from '../components/TaskListByTypePanel'
import TaskDetailModal from '../components/task/TaskDetailModal'

export default function UrlToWiki() {
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(undefined)

  return (
    <TaskFormPage
      taskType="url_to_wiki"
      title="网文抓取"
      description="抓取指定 URL 正文，翻译成中文后写入 MediaWiki。可在"
      submitLabel="提交任务"
      rightContent={
        <>
          <TaskListByTypePanel
            taskType="url_to_wiki"
            title="网文抓取任务"
            emptyText="暂无网文抓取任务"
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
