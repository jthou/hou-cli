/**
 * 按任务类型展示的任务列表面板：进行中 / 排队 / 已完成，复用 TaskCard。
 * 用于视频下载、音频提取等页右侧。
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import TaskCard from './TaskCard'

const STATUS_LABEL = { queued: '排队', running: '进行中', completed: '已完成', failed: '失败' }

export default function TaskListByTypePanel({
  taskType,
  taskTypes,
  title,
  emptyText,
  pipelineOnly = false,
  onShowDetail,
  refreshTrigger,
}) {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const allowedTypes = Array.isArray(taskTypes) && taskTypes.length ? new Set(taskTypes) : null

  const fetchTasks = () => {
    setLoading(true)
    const params = new URLSearchParams({ limit: '50', include_result: 'true' })
    if (pipelineOnly) params.set('pipeline_only', 'true')
    else if (taskType && !allowedTypes) params.set('task_type', taskType)
    fetch(`/api/task-queue/tasks?${params}`)
      .then(r => r.json())
      .then(d => {
        if (d.success && Array.isArray(d.tasks)) {
          const list = allowedTypes
            ? d.tasks.filter(t => allowedTypes.has(t.task_type))
            : d.tasks
          setTasks(list)
        }
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchTasks()
  }, [taskType, pipelineOnly, taskTypes?.join(',')])

  useEffect(() => {
    if (refreshTrigger === undefined) return
    fetchTasks()
  }, [refreshTrigger])

  const byStatus = {
    running: tasks.filter(t => t.status === 'running'),
    queued: tasks.filter(t => t.status === 'queued'),
    completed: tasks.filter(t => t.status === 'completed'),
    failed: tasks.filter(t => t.status === 'failed'),
  }

  if (loading) {
    return (
      <div className="p-4 text-sm text-muted">
        加载中…
      </div>
    )
  }
  if (tasks.length === 0) {
    return (
      <div className="p-4 text-sm text-muted">
        {emptyText || `暂无${title}`}
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-medium text-white">{title}</h3>
        <button
          type="button"
          onClick={fetchTasks}
          disabled={loading}
          className="text-xs text-muted hover:text-fg disabled:opacity-50"
        >
          刷新
        </button>
      </div>
      {(['running', 'queued', 'failed', 'completed']).map(status => {
        const list = byStatus[status]
        if (!list.length) return null
        return (
          <div key={status}>
            <h4 className="text-xs font-medium text-muted mb-2 px-1">
              {STATUS_LABEL[status]}（{list.length}）
            </h4>
            <ul className="space-y-3">
              {list.map(t => (
                <li key={t.task_id}>
                  <TaskCard
                    task={t}
                    onRefresh={fetchTasks}
                    onShowDetail={
                      onShowDetail
                        ? (taskId) => onShowDetail(taskId)
                        : (taskId) => navigate('/tasks', { state: { detailTaskId: taskId } })
                    }
                    recycleBin={false}
                    inRunsModal={false}
                  />
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
