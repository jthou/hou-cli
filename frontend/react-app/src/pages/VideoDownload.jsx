import { useState } from 'react'
import TaskFormPage from '../components/task/TaskFormPage'
import TaskListByTypePanel from '../components/TaskListByTypePanel'
import TaskDetailModal from '../components/task/TaskDetailModal'

export default function VideoDownload() {
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(undefined)

  return (
    <TaskFormPage
      taskType="video_download"
      title="视频下载"
      description="支持 Bilibili、YouTube 等平台。输入视频链接后提交，下载任务将加入队列，可在"
      submitLabel="提交下载任务"
      rightContent={
        <>
          <TaskListByTypePanel
            taskType="video_download"
            title="视频下载任务"
            emptyText="暂无视频下载任务"
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
