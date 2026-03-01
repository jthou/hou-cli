/**
 * 任务卡片组件：与任务管理页一致的卡片样式与操作，可复用于列表、视频下载页右侧等。
 * 依赖：task（含 task_id, task_name, status, priority, created_at 等）, onRefresh, onShowDetail, onGoToSchedule（可选）, recycleBin, inRunsModal
 */
import { useToast } from './ToastModal'
import TaskResultDisplay from './TaskResultDisplay'
import { STATUS_MAP, formatDateTime } from '../utils/taskConstants'

const TASK_API = {
  cancel: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/cancel`, { method: 'POST' }).then(r => r.json()),
  restart: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/restart`, { method: 'POST' }).then(r => r.json()),
  softDelete: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/soft-delete`, { method: 'POST' }).then(r => r.json()),
  restore: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/restore`, { method: 'POST' }).then(r => r.json()),
  delete: (taskId) => fetch(`/api/task-queue/tasks/${taskId}`, { method: 'DELETE' }).then(r => r.json()),
}

export default function TaskCard({
  task,
  onRefresh,
  onShowDetail,
  onGoToSchedule,
  recycleBin = false,
  inRunsModal = false,
}) {
  const toast = useToast()
  const status = STATUS_MAP[task.status] || { text: task.status, cls: 'bg-slate-500/20 text-slate-400' }

  return (
    <div className="p-5 bg-white/5 border border-border rounded-xl hover:border-cyan-500/25 transition-colors">
      <div className="flex justify-between items-start gap-4 mb-3">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-sm text-cyan-400/90 font-mono shrink-0">#{task.task_id?.slice(0, 8)}</span>
          <span className="font-medium text-white truncate">{task.task_name || '未命名任务'}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${status.cls}`}>{status.text}</span>
          <span className="px-2 py-0.5 rounded text-xs bg-cyan-500/15 text-cyan-400">
            P{task.priority ?? 2}
          </span>
          {['running', 'queued'].includes(task.status) && (
            <button
              onClick={async () => {
                const ok = await toast.confirm('确定要取消？')
                if (!ok) return
                try {
                  await TASK_API.cancel(task.task_id)
                  onRefresh?.()
                } catch (e) {
                  toast.error('取消失败: ' + e.message)
                }
              }}
              className="px-2 py-0.5 text-xs text-red-400 hover:bg-red-500/15 rounded"
            >
              取消
            </button>
          )}
        </div>
      </div>
      {(task.depends_on_task_id || (task.input_bindings && Object.keys(task.input_bindings).length) || task.created_by_schedule_id) ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-cyan-400/90 mb-2">
          {task.created_by_schedule_id && (
            onGoToSchedule ? (
              <button
                type="button"
                onClick={() => onGoToSchedule(task.created_by_schedule_id)}
                className="text-cyan-400/90 hover:text-cyan-300 hover:underline focus:outline-none"
                title={`跳转到定时任务 ${task.created_by_schedule_id}`}
              >
                定时: #{task.created_by_schedule_id.slice(0, 8)}
              </button>
            ) : (
              <span title={`来自定时任务 ${task.created_by_schedule_id}`}>定时: #{task.created_by_schedule_id.slice(0, 8)}</span>
            )
          )}
          {task.depends_on_task_id && (
            <span>依赖: #{task.depends_on_task_id.slice(0, 8)}</span>
          )}
          {task.input_bindings && Object.keys(task.input_bindings).length > 0 && (
            <span>绑定: {Object.entries(task.input_bindings).map(([k, v]) => `${k} ← ${v}`).join(', ')}</span>
          )}
          {task.status === 'queued' && task.depends_on_task_id && (
            <span className="text-amber-400/90">（等待上游完成后执行）</span>
          )}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-[#94a3b8] mb-3">
        <span>类型: {task.task_type}</span>
        <span>创建: {formatDateTime(task.created_at)}</span>
        {task.started_at && <span>开始: {formatDateTime(task.started_at)}</span>}
        {task.completed_at && <span>完成: {formatDateTime(task.completed_at)}</span>}
      </div>
      {task.status === 'running' && (
        <div className="mb-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-white/10 rounded overflow-hidden">
              <div className="h-full bg-cyan-500 rounded" style={{ width: `${task.progress ?? 0}%` }} />
            </div>
            <span className="text-xs text-[#94a3b8] w-9 text-right">{(task.progress ?? 0)}%</span>
          </div>
          {task.message && <p className="text-xs text-cyan-400/90 mt-1 truncate" title={task.message}>{task.message}</p>}
        </div>
      )}
      {(task.error || task.error_message) && (
        <div className="p-3 bg-red-500/10 rounded-lg text-sm text-red-400 mb-3">
          <strong>错误:</strong> {task.error || task.error_message}
        </div>
      )}
      {task.status === 'completed' && task.result != null && (
        <div className="p-3 bg-green-500/5 rounded-lg border border-green-500/20 mb-3">
          <TaskResultDisplay taskType={task.task_type} result={task.result} />
        </div>
      )}
      {task.status === 'completed' && task.result == null && task.result_summary && (
        <div className="p-3 bg-green-500/10 rounded-lg text-sm text-green-400 mb-3">
          {task.result_summary}
        </div>
      )}
      <div className="flex gap-2">
        {!inRunsModal && (
          <button
            onClick={() => onShowDetail?.(task.task_id)}
            className="px-3 py-1.5 text-sm border border-border rounded-lg text-[#94a3b8] hover:text-white hover:bg-white/5"
          >
            查看详情
          </button>
        )}
        {recycleBin ? (
          <>
            <button
              onClick={async () => {
                try {
                  const res = await TASK_API.restore(task.task_id)
                  if (res.success) onRefresh?.()
                  else toast.error(res.detail || res.message || '恢复失败')
                } catch (e) {
                  toast.error('恢复失败: ' + (e.message || String(e)))
                }
              }}
              className="px-3 py-1.5 text-sm border border-green-500/50 rounded-lg text-green-400 hover:bg-green-500/10"
              title="恢复任务到普通列表"
            >
              恢复
            </button>
            <button
              onClick={async () => {
                const ok = await toast.confirm('确定要彻底删除该任务？删除后不可恢复。')
                if (!ok) return
                try {
                  const res = await TASK_API.delete(task.task_id)
                  if (res.success) onRefresh?.()
                  else toast.error(res.detail || res.message || '删除失败')
                } catch (e) {
                  toast.error('删除失败: ' + (e.message || String(e)))
                }
              }}
              className="px-3 py-1.5 text-sm border border-red-500/50 rounded-lg text-red-400 hover:bg-red-500/10"
              title="彻底删除，不可恢复"
            >
              彻底删除
            </button>
          </>
        ) : (
          <>
            {['failed', 'completed'].includes(task.status) && (
              <button
                onClick={async () => {
                  try {
                    const res = await TASK_API.restart(task.task_id)
                    if (res.success) onRefresh?.()
                    else toast.error(res.detail || res.message || '重置失败')
                  } catch (e) {
                    toast.error('重置失败: ' + e.message)
                  }
                }}
                className="px-3 py-1.5 text-sm border border-cyan-500/50 rounded-lg text-cyan-400 hover:bg-cyan-500/10"
                title="将任务重新加入队列，可再次执行"
              >
                重新执行
              </button>
            )}
            {task.status !== 'running' && (
              <button
                onClick={async () => {
                  const ok = await toast.confirm('移入回收站？可在「已删除」中恢复或彻底删除。')
                  if (!ok) return
                  try {
                    const res = await TASK_API.softDelete(task.task_id)
                    if (res.success) onRefresh?.()
                    else toast.error(res.detail || res.message || '移入回收站失败')
                  } catch (e) {
                    toast.error('移入回收站失败: ' + (e.message || String(e)))
                  }
                }}
                className="px-3 py-1.5 text-sm border border-amber-500/50 rounded-lg text-amber-400 hover:bg-amber-500/10"
                title="移入回收站，可恢复"
              >
                删除
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
