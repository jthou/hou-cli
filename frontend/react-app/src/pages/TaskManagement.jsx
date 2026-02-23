import { useState, useEffect, useCallback } from 'react'

/**
 * 任务管理与展示机制
 * - 列表：GET /api/task-queue/tasks 返回任务列表，已完成任务带 result_summary（一句摘要）
 * - 详情：GET /api/task-queue/tasks/:id 按需拉取，返回完整 result（含 summary + data/result）
 * - 列表展示：状态、进度、错误、result_summary；详情弹层按 task_type 渲染完整结果
 */

const TASK_API = {
  list: (params) => fetch(`/api/task-queue/tasks?limit=100&offset=0${params?.status ? `&status=${params.status}` : ''}`).then(r => r.json()),
  get: (taskId) => fetch(`/api/task-queue/tasks/${taskId}`).then(r => r.json()),
  cancel: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/cancel`, { method: 'POST' }).then(r => r.json()),
}

const STATUS_MAP = {
  queued: { text: '待执行', cls: 'bg-cyan-500/15 text-cyan-400' },
  running: { text: '运行中', cls: 'bg-cyan-500/20 text-cyan-300' },
  completed: { text: '已完成', cls: 'bg-green-500/15 text-green-400' },
  failed: { text: '失败', cls: 'bg-red-500/15 text-red-400' },
  cancelled: { text: '已取消', cls: 'bg-slate-500/20 text-slate-400' },
}

function formatDateTime(s) {
  if (!s) return '-'
  const d = new Date(s)
  return isNaN(d) ? '-' : d.toLocaleString('zh-CN')
}

export default function TaskManagement() {
  const [tab, setTab] = useState('tasks')
  const [tasks, setTasks] = useState([])
  const [scheduledTasks, setScheduledTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [heartbeat, setHeartbeat] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [taskTypes, setTaskTypes] = useState([])

  const loadHeartbeat = useCallback(async () => {
    try {
      const res = await fetch('/api/heartbeat/status')
      const data = await res.json()
      if (data.success && data.status) setHeartbeat(data.status)
    } catch {}
  }, [])

  const loadTasks = useCallback(async () => {
    setLoading(true)
    try {
      const data = await TASK_API.list({ status: statusFilter || undefined })
      if (data.success && data.tasks) setTasks(data.tasks)
      else setTasks([])
    } catch (e) {
      setTasks([])
    }
    setLoading(false)
  }, [statusFilter])

  const loadScheduledTasks = useCallback(async () => {
    try {
      const res = await fetch('/api/task-queue/scheduled-tasks?active_only=false')
      const data = await res.json()
      setScheduledTasks(data.scheduled_tasks || data.tasks || [])
    } catch {
      setScheduledTasks([])
    }
  }, [])

  useEffect(() => {
    loadHeartbeat()
    const id = setInterval(loadHeartbeat, 10000)
    return () => clearInterval(id)
  }, [loadHeartbeat])

  useEffect(() => {
    if (tab === 'tasks') loadTasks()
    else loadScheduledTasks()
  }, [tab, loadTasks, loadScheduledTasks])

  useEffect(() => {
    if (showCreateModal && taskTypes.length === 0) {
      fetch('/api/task-queue/task-types')
        .then(r => r.json())
        .then(d => setTaskTypes(d.task_types || []))
        .catch(() => setTaskTypes([]))
    }
  }, [showCreateModal, taskTypes.length])

  const stats = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'queued').length,
    running: tasks.filter(t => t.status === 'running').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  }

  const filteredTasks = tasks.filter(t => {
    if (!search) return true
    const s = search.toLowerCase()
    return (t.task_name || '').toLowerCase().includes(s) || (t.task_id || '').toLowerCase().includes(s)
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">任务管理</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full">
        {/* 心跳条 */}
        <div className="flex items-center gap-2 px-4 py-2 mb-6 text-xs bg-cyan-500/5 border border-cyan-500/15 rounded-lg text-[#94a3b8]">
          <span className={`w-2 h-2 rounded-full ${heartbeat?.is_running ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="font-medium text-white">{heartbeat?.is_running ? '运行中' : '已停止'}</span>
          <span>·</span>
          <span>最近: {heartbeat?.last_heartbeat ? new Date(heartbeat.last_heartbeat).toLocaleTimeString('zh-CN') : '-'}</span>
          <span>·</span>
          <span>
            {heartbeat?.uptime_seconds >= 3600
              ? `${Math.floor(heartbeat.uptime_seconds / 3600)}h ${Math.floor((heartbeat.uptime_seconds % 3600) / 60)}m`
              : heartbeat?.uptime_seconds >= 60
              ? `${Math.floor(heartbeat.uptime_seconds / 60)}m`
              : `${heartbeat?.uptime_seconds ?? 0}s`}
          </span>
          {heartbeat?.metrics?.cpu_percent != null && (
            <>
              <span>·</span>
              <span>{heartbeat.metrics.cpu_percent.toFixed(1)}% / {heartbeat.metrics.memory_percent?.toFixed(1)}%</span>
            </>
          )}
        </div>

        {/* 标签 + 创建按钮 */}
        <div className="flex justify-between items-center mb-6 flex-wrap gap-4">
          <div className="flex gap-1 p-1 bg-white/5 rounded-lg border border-border">
            <button
              onClick={() => setTab('tasks')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === 'tasks' ? 'bg-accent text-white' : 'text-[#94a3b8] hover:text-white'
              }`}
            >
              普通任务
            </button>
            <button
              onClick={() => setTab('scheduled')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === 'scheduled' ? 'bg-accent text-white' : 'text-[#94a3b8] hover:text-white'
              }`}
            >
              定时任务
            </button>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors"
          >
            + {tab === 'tasks' ? '创建普通任务' : '创建定时任务'}
          </button>
        </div>

        {tab === 'tasks' ? (
          <>
            {/* 统计卡片 */}
            <div className="grid grid-cols-5 gap-4 mb-6">
              {[
                { label: '总任务', value: stats.total, cls: '' },
                { label: '待处理', value: stats.pending, cls: 'text-amber-400' },
                { label: '运行中', value: stats.running, cls: 'text-cyan-400' },
                { label: '已完成', value: stats.completed, cls: 'text-green-400' },
                { label: '失败', value: stats.failed, cls: 'text-red-400' },
              ].map(({ label, value, cls }) => (
                <div
                  key={label}
                  className="p-4 bg-white/5 border border-border rounded-xl flex flex-col gap-1 hover:border-cyan-500/30 transition-colors"
                >
                  <span className={`text-2xl font-bold ${cls}`}>{value}</span>
                  <span className="text-xs text-[#94a3b8]">{label}</span>
                </div>
              ))}
            </div>

            {/* 工具栏 */}
            <div className="flex gap-4 mb-4 flex-wrap">
              <input
                type="text"
                placeholder="搜索任务..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="px-3 py-2 bg-white/5 border border-border rounded-lg text-sm text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
              />
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="px-3 py-2 bg-white/5 border border-border rounded-lg text-sm text-white focus:border-accent focus:outline-none"
              >
                <option value="">全部状态</option>
                <option value="queued">待执行</option>
                <option value="running">运行中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
                <option value="cancelled">已取消</option>
              </select>
              <button
                onClick={loadTasks}
                className="px-3 py-2 border border-border rounded-lg text-sm text-[#94a3b8] hover:text-white hover:bg-white/5 transition-colors"
                title="刷新"
              >
                ↻
              </button>
              <button
                onClick={async () => {
                  if (!confirm('确定要清理超时任务吗？')) return
                  try {
                    const res = await fetch('/api/task-queue/cleanup?max_idle_minutes=30', { method: 'POST' })
                    const data = await res.json()
                    if (data.success) {
                      alert(`清理完成，共清理了 ${data.cleaned_count} 个超时任务`)
                      loadTasks()
                    }
                  } catch (e) {
                    alert('清理失败: ' + e.message)
                  }
                }}
                className="px-3 py-2 border border-border rounded-lg text-sm text-[#94a3b8] hover:text-white hover:bg-white/5 transition-colors"
              >
                清理超时
              </button>
            </div>

            {/* 任务列表 */}
            <div className="space-y-3">
              {loading ? (
                <div className="py-12 text-center text-[#94a3b8]">加载中...</div>
              ) : filteredTasks.length === 0 ? (
                <div className="py-12 text-center text-[#94a3b8]">暂无任务</div>
              ) : (
                filteredTasks.map(task => (
                  <TaskCard key={task.task_id} task={task} onRefresh={loadTasks} onShowDetail={setDetailTaskId} />
                ))
              )}
            </div>
          </>
        ) : (
          <div className="space-y-3">
            {scheduledTasks.length === 0 ? (
              <div className="py-12 text-center text-[#94a3b8]">暂无定时任务</div>
            ) : (
              scheduledTasks.map(t => (
                <div
                  key={t.schedule_id}
                  className="p-5 bg-white/5 border border-border rounded-xl hover:border-cyan-500/25 transition-colors"
                >
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <span className="font-medium text-white">{t.task_name || '未命名'}</span>
                      <span className="text-sm text-[#64748b] ml-2">#{t.schedule_id}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${t.is_active ? 'bg-green-500/15 text-green-400' : 'bg-slate-500/20 text-slate-400'}`}>
                      {t.is_active ? '激活' : '已禁用'}
                    </span>
                  </div>
                  <div className="mt-3 text-sm text-[#94a3b8]">
                    {t.task_type} · {typeof t.schedule_config === 'string' ? t.schedule_config : JSON.stringify(t.schedule_config || {})}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {showCreateModal && (
        <CreateTaskModal
          taskTypes={taskTypes}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            loadTasks()
          }}
        />
      )}
      {detailTaskId && (
        <TaskDetailModal taskId={detailTaskId} onClose={() => setDetailTaskId(null)} />
      )}
    </div>
  )
}

function TaskDetailModal({ taskId, onClose }) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!taskId) return
    setLoading(true)
    setErr(null)
    TASK_API.get(taskId)
      .then(d => {
        if (d.success && d.task) setTask(d.task)
        else setErr(d.detail || '加载失败')
      })
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false))
  }, [taskId])

  if (!taskId) return null
  const status = task ? (STATUS_MAP[task.status] || { text: task.status, cls: '' }) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-white">任务详情</h2>
          <button onClick={onClose} className="text-[#94a3b8] hover:text-white">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 text-sm">
          {loading && <p className="text-[#94a3b8]">加载中...</p>}
          {err && <p className="text-red-400">{err}</p>}
          {!loading && !err && task && (
            <div className="space-y-4">
              <div>
                <span className="text-[#64748b]">任务名称 </span>
                <span className="text-white">{task.task_name || '未命名'}</span>
              </div>
              <div>
                <span className="text-[#64748b]">类型 </span>
                <span className="text-white">{task.task_type}</span>
              </div>
              <div>
                <span className="text-[#64748b]">状态 </span>
                <span className={status?.cls}>{status?.text}</span>
              </div>
              <div>
                <span className="text-[#64748b]">创建 </span>
                <span className="text-white">{formatDateTime(task.created_at)}</span>
              </div>
              {task.started_at && (
                <div>
                  <span className="text-[#64748b]">开始 </span>
                  <span className="text-white">{formatDateTime(task.started_at)}</span>
                </div>
              )}
              {task.completed_at && (
                <div>
                  <span className="text-[#64748b]">完成 </span>
                  <span className="text-white">{formatDateTime(task.completed_at)}</span>
                  {task.duration != null && <span className="text-[#64748b] ml-2">耗时 {Number(task.duration).toFixed(1)}s</span>}
                </div>
              )}
              {(task.error || task.error_message) && (
                <div className="p-3 bg-red-500/10 rounded-lg text-red-400">
                  <strong>错误：</strong> {task.error || task.error_message}
                </div>
              )}
              {task.result && task.status === 'completed' && (
                <div className="pt-3 border-t border-border">
                  <div className="text-[#64748b] mb-2">执行结果</div>
                  <TaskResultDisplay taskType={task.task_type} result={task.result} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TaskResultDisplay({ taskType, result }) {
  if (!result || result.status !== 'success') {
    return <pre className="text-[#94a3b8] text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
  }
  if (taskType === 'video_download' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.title && <p><span className="text-[#64748b]">标题 </span>{d.title}</p>}
        {d.output_dir && <p><span className="text-[#64748b]">保存位置 </span><code className="text-cyan-300 break-all">{d.output_dir}</code></p>}
      </div>
    )
  }
  if (taskType === 'weather_query' && result.result) {
    const r = result.result
    const cur = r.current_weather
    const forecast = r.forecast
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {cur && (
          <div>
            <span className="text-[#64748b]">当前 </span>
            {typeof cur === 'object' ? `${cur.temp ?? ''}°C ${cur.text ?? ''}` : String(cur)}
          </div>
        )}
        {forecast && <pre className="text-xs whitespace-pre-wrap mt-2">{JSON.stringify(forecast, null, 2)}</pre>}
      </div>
    )
  }
  return <pre className="text-[#94a3b8] text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
}

function TaskCard({ task, onRefresh, onShowDetail }) {
  const status = STATUS_MAP[task.status] || { text: task.status, cls: 'bg-slate-500/20 text-slate-400' }

  return (
    <div className="p-5 bg-white/5 border border-border rounded-xl hover:border-cyan-500/25 transition-colors">
      <div className="flex justify-between items-start gap-4 mb-3">
        <div>
          <span className="font-medium text-white">{task.task_name || '未命名任务'}</span>
          <span className="text-sm text-[#64748b] ml-2">#{task.task_id?.slice(0, 8)}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${status.cls}`}>{status.text}</span>
          <span className="px-2 py-0.5 rounded text-xs bg-cyan-500/15 text-cyan-400">
            P{task.priority ?? 2}
          </span>
          {['running', 'queued'].includes(task.status) && (
            <button
              onClick={async () => {
                if (!confirm('确定要取消？')) return
                try {
                  await TASK_API.cancel(task.task_id)
                  onRefresh()
                } catch (e) {
                  alert('取消失败: ' + e.message)
                }
              }}
              className="px-2 py-0.5 text-xs text-red-400 hover:bg-red-500/15 rounded"
            >
              取消
            </button>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-[#94a3b8] mb-3">
        <span>类型: {task.task_type}</span>
        <span>创建: {formatDateTime(task.created_at)}</span>
        {task.started_at && <span>开始: {formatDateTime(task.started_at)}</span>}
        {task.completed_at && <span>完成: {formatDateTime(task.completed_at)}</span>}
      </div>
      {task.status === 'running' && (
        <div className="flex items-center gap-2 mb-3">
          <div className="flex-1 h-1.5 bg-white/10 rounded overflow-hidden">
            <div className="h-full bg-cyan-500 rounded" style={{ width: `${task.progress ?? 0}%` }} />
          </div>
          <span className="text-xs text-[#94a3b8] w-9 text-right">{(task.progress ?? 0)}%</span>
        </div>
      )}
      {(task.error || task.error_message) && (
        <div className="p-3 bg-red-500/10 rounded-lg text-sm text-red-400 mb-3">
          <strong>错误:</strong> {task.error || task.error_message}
        </div>
      )}
      {task.status === 'completed' && task.result_summary && (
        <div className="p-3 bg-green-500/10 rounded-lg text-sm text-green-400 mb-3">
          {task.result_summary}
        </div>
      )}
      <button
        onClick={() => onShowDetail(task.task_id)}
        className="px-3 py-1.5 text-sm border border-border rounded-lg text-[#94a3b8] hover:text-white hover:bg-white/5"
      >
        查看详情
      </button>
    </div>
  )
}

function CreateTaskModal({ taskTypes, onClose, onSuccess }) {
  const [type, setType] = useState('')
  const [name, setName] = useState('')
  const [priority, setPriority] = useState(2)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!type) {
      alert('请选择任务类型')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: type, task_name: name || undefined, priority, max_retries: 3 }),
      })
      const data = await res.json()
      if (data.success) {
        alert('任务创建成功: ' + data.task_id)
        onSuccess()
      } else {
        throw new Error(data.detail || data.message || '创建失败')
      }
    } catch (err) {
      alert('创建失败: ' + err.message)
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-lg w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">创建新任务</h3>
          <button onClick={onClose} className="text-2xl text-[#94a3b8] hover:text-white">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">任务类型 *</label>
            <select
              value={type}
              onChange={e => setType(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
              required
            >
              <option value="">请选择任务类型</option>
              {taskTypes.map(t => (
                <option key={t.type} value={t.type}>{t.name} - {t.description}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">任务名称</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="留空自动生成"
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">优先级</label>
            <select
              value={priority}
              onChange={e => setPriority(Number(e.target.value))}
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
            >
              <option value={1}>低 (1)</option>
              <option value={2}>普通 (2)</option>
              <option value={3}>高 (3)</option>
              <option value={4}>紧急 (4)</option>
            </select>
          </div>
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-[#94a3b8] hover:text-white">
              取消
            </button>
            <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">
              {submitting ? '创建中...' : '创建普通任务'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
