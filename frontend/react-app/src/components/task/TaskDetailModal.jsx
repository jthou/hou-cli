/**
 * 任务详情弹层（组件化）：按 taskId 拉取任务并展示结果与操作。
 * 供任务管理页、网文抓取/视频下载等按类型列表页复用，点击「查看详情」时在本页打开弹层而非跳转。
 */
import { useState, useEffect } from 'react'
import { useToast } from '../ToastModal'
import TaskResultDisplay from '../TaskResultDisplay'
import { STATUS_MAP, formatDateTime } from '../../utils/taskConstants'

const TASK_API = {
  get: (taskId) => fetch(`/api/task-queue/tasks/${taskId}`).then((r) => r.json()),
  restart: (taskId) =>
    fetch(`/api/task-queue/tasks/${taskId}/restart`, { method: 'POST' }).then((r) => r.json()),
  restore: (taskId) =>
    fetch(`/api/task-queue/tasks/${taskId}/restore`, { method: 'POST' }).then((r) => r.json()),
  delete: (taskId) =>
    fetch(`/api/task-queue/tasks/${taskId}`, { method: 'DELETE' }).then((r) => r.json()),
  softDelete: (taskId) =>
    fetch(`/api/task-queue/tasks/${taskId}/soft-delete`, { method: 'POST' }).then((r) => r.json()),
}

export default function TaskDetailModal({
  taskId,
  taskTypes = [],
  onClose,
  onRefresh,
  onGoToSchedule,
  onEditBeforeRestart,
}) {
  const toast = useToast()
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [restarting, setRestarting] = useState(false)
  const [requeueing, setRequeueing] = useState(false)
  const [patchingResult, setPatchingResult] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [queueStatus, setQueueStatus] = useState(null)

  useEffect(() => {
    if (!taskId) return
    setLoading(true)
    setErr(null)
    setQueueStatus(null)
    TASK_API.get(taskId)
      .then((d) => {
        if (d.success && d.task) setTask(d.task)
        else setErr(d.detail || '加载失败')
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [taskId])

  useEffect(() => {
    if (!taskId || !task || task.status !== 'queued' || !task.depends_on_task_id) return
    fetch(`/api/task-queue/tasks/${taskId}/queue-status`)
      .then((r) => r.json())
      .then((d) => d.success && setQueueStatus(d))
      .catch(() => {})
  }, [taskId, task?.status, task?.depends_on_task_id])

  useEffect(() => {
    if (!taskId || !task || task.status !== 'running') return
    const t = setInterval(() => {
      TASK_API.get(taskId)
        .then((d) => {
          if (d.success && d.task) setTask(d.task)
        })
        .catch(() => {})
    }, 2500)
    return () => clearInterval(t)
  }, [taskId, task?.status])

  if (!taskId) return null
  const status = task ? (STATUS_MAP[task.status] || { text: task.status, cls: '' }) : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-xl shadow-xl max-w-5xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-fg">任务详情</h2>
          <button onClick={onClose} className="text-muted hover:text-fg">
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 text-sm">
          {loading && <p className="text-muted">加载中...</p>}
          {err && <p className="text-red-400">{err}</p>}
          {!loading && !err && task && (
            <div className="space-y-4">
              {task.result != null && task.status === 'completed' && (
                <div>
                  <div className="text-muted text-xs mb-2">执行结果</div>
                  <TaskResultDisplay taskType={task.task_type} result={task.result} />
                </div>
              )}
              {(task.error || task.error_message) && (
                <div className="p-3 bg-red-500/10 rounded-lg text-red-400">
                  <strong>错误：</strong> {task.error || task.error_message}
                </div>
              )}
              {task.status === 'queued' && task.depends_on_task_id && (
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10">
                  <div className="text-amber-400/90 text-xs font-medium mb-1">
                    衔接诊断（为何仍待执行）
                  </div>
                  {queueStatus ? (
                    <>
                      <p className="text-sm text-amber-200/90">{queueStatus.message}</p>
                      {queueStatus.upstream && (
                        <p className="text-xs text-muted mt-2">
                          上游 #{queueStatus.upstream.task_id?.slice(0, 8)}：状态=
                          {queueStatus.upstream.status}，result 非空=
                          {String(queueStatus.upstream.has_result)}
                          {queueStatus.upstream.missing_bindings?.length
                            ? `，绑定缺失: ${queueStatus.upstream.missing_bindings.join(', ')}`
                            : ''}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted">加载中...</p>
                  )}
                </div>
              )}
              {task.status === 'running' && (
                <div className="p-3 rounded-lg border border-cyan-500/30 bg-cyan-500/10">
                  <div className="text-cyan-400/90 text-xs font-medium mb-2">当前进度</div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex-1 h-2 bg-white/10 rounded overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded transition-all"
                        style={{ width: `${task.progress ?? 0}%` }}
                      />
                    </div>
                    <span className="text-xs text-cyan-300 w-10 text-right">
                      {(task.progress ?? 0)}%
                    </span>
                  </div>
                  {task.message && (
                    <p className="text-sm text-cyan-200/90">{task.message}</p>
                  )}
                </div>
              )}
              <div className="pt-4 border-t border-border">
                <div className="text-muted text-xs mb-2">任务信息（仅供参考）</div>
                <div className="space-y-1.5 text-muted text-xs">
                  {(task.depends_on_task_id ||
                    (task.input_bindings &&
                      Object.keys(task.input_bindings).length > 0)) && (
                    <>
                      {task.depends_on_task_id && (
                        <div>
                          <span className="text-muted">依赖任务 </span>
                          <code className="text-cyan-400">{task.depends_on_task_id}</code>
                        </div>
                      )}
                      {task.input_bindings &&
                        Object.keys(task.input_bindings).length > 0 && (
                          <div>
                            <span className="text-muted">输入绑定 </span>
                            {Object.entries(task.input_bindings).map(([k, v]) => (
                              <span key={k} className="block ml-2">
                                {k} ← {v}
                              </span>
                            ))}
                          </div>
                        )}
                    </>
                  )}
                  {task.resolved_metadata &&
                    Object.keys(task.resolved_metadata).length > 0 && (
                      <div>
                        <span className="text-muted">解析后 metadata </span>
                        {Object.entries(task.resolved_metadata).map(([k, v]) => (
                          <span key={k} className="block ml-2">
                            {k} ={' '}
                            {typeof v === 'string' ? v : JSON.stringify(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  {task.created_by_schedule_id && (
                    <div>
                      <span className="text-muted">来自定时任务 </span>
                      {onGoToSchedule ? (
                        <button
                          type="button"
                          onClick={() => onGoToSchedule(task.created_by_schedule_id)}
                          className="text-cyan-400 hover:text-cyan-300 hover:underline focus:outline-none"
                        >
                          #{task.created_by_schedule_id.slice(0, 8)}
                        </button>
                      ) : (
                        <code className="text-cyan-400">
                          #{task.created_by_schedule_id.slice(0, 8)}
                        </code>
                      )}
                    </div>
                  )}
                  <div>
                    <span className="text-muted">任务名称 </span>
                    {task.task_name || '未命名'}
                  </div>
                  <div>
                    <span className="text-muted">类型 </span>
                    {task.task_type}
                  </div>
                  <div>
                    <span className="text-muted">状态 </span>
                    <span className={status?.cls}>{status?.text}</span>
                  </div>
                  <div>
                    <span className="text-muted">创建 </span>
                    {formatDateTime(task.created_at)}
                  </div>
                  {task.started_at && (
                    <div>
                      <span className="text-muted">开始 </span>
                      {formatDateTime(task.started_at)}
                    </div>
                  )}
                  {task.completed_at && (
                    <div>
                      <span className="text-muted">完成 </span>
                      {formatDateTime(task.completed_at)}
                      {task.duration != null && (
                        <span className="ml-2">耗时 {Number(task.duration).toFixed(1)}s</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
        {!loading && task && task.status !== 'running' && (
          <div className="shrink-0 px-6 py-4 border-t border-border flex flex-wrap gap-2 justify-end">
            {task.status === 'completed' &&
              task.result?.data?.output_dir &&
              !task.result?.data?.output_file && (
                <button
                  disabled={patchingResult}
                  onClick={async () => {
                    setPatchingResult(true)
                    try {
                      const res = await fetch(
                        `/api/task-queue/tasks/${task.task_id}/patch-result-output-file`,
                        { method: 'PATCH' }
                      ).then((r) => r.json())
                      if (res.success) {
                        const updated = await TASK_API.get(task.task_id)
                        if (updated.success && updated.task) setTask(updated.task)
                        if (onRefresh) onRefresh()
                      } else {
                        toast.error(res.detail || res.message || '补全失败')
                      }
                    } catch (e) {
                      toast.error('补全失败: ' + (e.message || String(e)))
                    }
                    setPatchingResult(false)
                  }}
                  className="px-4 py-2 text-sm border border-amber-500/50 rounded-lg text-amber-400 hover:bg-amber-500/10 disabled:opacity-50"
                >
                  {patchingResult ? '补全中...' : '补全 result（供下游衔接）'}
                </button>
              )}
            {task.status === 'failed' && task.depends_on_task_id && (
              <button
                disabled={requeueing}
                onClick={async () => {
                  setRequeueing(true)
                  try {
                    const res = await fetch(
                      `/api/task-queue/tasks/${task.task_id}/requeue`,
                      { method: 'POST' }
                    ).then((r) => r.json())
                    if (res.success) {
                      if (onRefresh) onRefresh()
                      onClose()
                    } else {
                      toast.error(res.detail || res.message || '重新入队失败')
                    }
                  } catch (e) {
                    toast.error('重新入队失败: ' + (e.message || String(e)))
                  }
                  setRequeueing(false)
                }}
                className="px-4 py-2 text-sm border border-amber-500/50 rounded-lg text-amber-400 hover:bg-amber-500/10 disabled:opacity-50"
                title="用上游最新 result 再执行一次（上游若已补全 result 请先补全）"
              >
                {requeueing ? '入队中...' : '重新入队'}
              </button>
            )}
            {['failed', 'completed'].includes(task.status) && (
              <>
                <button
                  type="button"
                  onClick={() => onEditBeforeRestart?.(task)}
                  className="px-4 py-2 text-sm border border-cyan-500/50 rounded-lg text-cyan-400 hover:bg-cyan-500/10"
                  title={task.pipeline_id ? '整体编辑管道内所有任务后重新执行' : '复用新建任务 UI 修改参数后重新执行'}
                >
                  {task.pipeline_id ? '编辑管道' : '编辑后重新执行'}
                </button>
                <button
                  disabled={restarting}
                  onClick={async () => {
                    setRestarting(true)
                    try {
                      const res = await TASK_API.restart(task.task_id)
                      if (res.success) {
                        if (onRefresh) onRefresh()
                        else onClose()
                      } else {
                        toast.error(res.detail || res.message || '重置失败')
                      }
                    } catch (e) {
                      toast.error('重置失败: ' + e.message)
                    }
                    setRestarting(false)
                  }}
                  className="px-4 py-2 text-sm border border-cyan-500/50 rounded-lg text-cyan-400 hover:bg-cyan-500/10 disabled:opacity-50"
                  title="将任务重新加入队列，可再次执行"
                >
                  {restarting ? '重新执行中...' : '重新执行'}
                </button>
              </>
            )}
            {task.deleted_at ? (
              <>
                <button
                  disabled={deleting}
                  onClick={async () => {
                    setDeleting(true)
                    try {
                      const res = await TASK_API.restore(task.task_id)
                      if (res.success) {
                        if (onRefresh) onRefresh()
                        onClose()
                      } else toast.error(res.detail || res.message || '恢复失败')
                    } catch (e) {
                      toast.error('恢复失败: ' + (e.message || String(e)))
                    }
                    setDeleting(false)
                  }}
                  className="px-4 py-2 text-sm border border-green-500/50 rounded-lg text-green-400 hover:bg-green-500/10 disabled:opacity-50"
                >
                  {deleting ? '恢复中...' : '恢复'}
                </button>
                <button
                  disabled={deleting}
                  onClick={async () => {
                    const ok = await toast.confirm('确定彻底删除？不可恢复。')
                    if (!ok) return
                    setDeleting(true)
                    try {
                      const res = await TASK_API.delete(task.task_id)
                      if (res.success) {
                        if (onRefresh) onRefresh()
                        onClose()
                      } else
                        toast.error(res.detail || res.message || '彻底删除失败')
                    } catch (e) {
                      toast.error('彻底删除失败: ' + (e.message || String(e)))
                    }
                    setDeleting(false)
                  }}
                  className="px-4 py-2 text-sm border border-red-500/50 rounded-lg text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                >
                  {deleting ? '删除中...' : '彻底删除'}
                </button>
              </>
            ) : (
              <button
                disabled={deleting}
                onClick={async () => {
                  const ok = await toast.confirm(
                    '移入回收站？可在「已删除」Tab 中恢复或彻底删除。'
                  )
                  if (!ok) return
                  setDeleting(true)
                  try {
                    const res = await TASK_API.softDelete(task.task_id)
                    if (res.success) {
                      if (onRefresh) onRefresh()
                      onClose()
                    } else {
                      toast.error(res.detail || res.message || '移入回收站失败')
                    }
                  } catch (e) {
                    toast.error('移入回收站失败: ' + (e.message || String(e)))
                  }
                  setDeleting(false)
                }}
                className="px-4 py-2 text-sm border border-amber-500/50 rounded-lg text-amber-400 hover:bg-amber-500/10 disabled:opacity-50"
                title="移入回收站，可恢复"
              >
                {deleting ? '删除中...' : '删除'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
