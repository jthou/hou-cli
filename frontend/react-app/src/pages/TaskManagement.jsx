import { useState, useEffect, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import TaskDetailModal from '../components/task/TaskDetailModal'
import TaskCard from '../components/TaskCard'
import HtmlPreview from '../components/HtmlPreview'
import { useToast } from '../components/ToastModal'
import { STATUS_MAP, formatDateTime } from '../utils/taskConstants'
import { prepareMetadataForSubmitAsync, htmlToMd } from '../utils/mdToHtml'
import { requestCookiesFromExtension } from '../utils/extensionCookies'
import { getDefaultMetadata, getApiErrorMessage, migrateWeatherMetadata, getDateCategoryStrings } from '../components/task/taskFormUtils'
import TaskMetadataFormFields from '../components/task/TaskMetadataFormFields'
import TaskParamsForm from '../components/task/TaskParamsForm'
import WikiTitlePreviewHint from '../components/task/WikiTitlePreviewHint'
import ScheduleConfigFields from '../components/task/ScheduleConfigFields'
import { PIPELINE_TEMPLATES } from '../config/pipelineTemplates'

/**
 * 任务管理与展示机制
 * - 列表：GET /api/task-queue/tasks 返回任务列表，已完成任务带 result_summary（一句摘要）
 * - 详情：GET /api/task-queue/tasks/:id 按需拉取，返回完整 result（含 summary + data/result）
 * - 列表展示：状态、进度、错误、result_summary；详情弹层按 task_type 渲染完整结果
 */

const TASK_API = {
  list: (params) => {
    const q = new URLSearchParams({ limit: 100, offset: 0 })
    if (params?.status) q.set('status', params.status)
    if (params?.deleted) q.set('deleted', params.deleted)
    if (params?.created_by_schedule_id) q.set('created_by_schedule_id', params.created_by_schedule_id)
    return fetch(`/api/task-queue/tasks?${q}`).then(r => r.json())
  },
  get: (taskId) => fetch(`/api/task-queue/tasks/${taskId}`).then(r => r.json()),
  patch: (taskId, body) => fetch(`/api/task-queue/tasks/${taskId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()),
  cancel: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/cancel`, { method: 'POST' }).then(r => r.json()),
  restart: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/restart`, { method: 'POST' }).then(r => r.json()),
  softDelete: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/soft-delete`, { method: 'POST' }).then(r => r.json()),
  restore: (taskId) => fetch(`/api/task-queue/tasks/${taskId}/restore`, { method: 'POST' }).then(r => r.json()),
  delete: (taskId) => fetch(`/api/task-queue/tasks/${taskId}`, { method: 'DELETE' }).then(r => r.json()),
  create: (payload) => fetch('/api/task-queue/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(r => r.json()),
}

const WECHAT_MP_API = {
  drafts: (params = {}) => {
    const q = new URLSearchParams({ offset: String(params.offset ?? 0), count: String(params.count ?? 20), no_content: String(params.no_content ?? 1) })
    return fetch(`/api/wechat-mp/drafts?${q}`).then(r => r.json())
  },
  draftDetail: (mediaId) => fetch(`/api/wechat-mp/drafts/detail?media_id=${encodeURIComponent(mediaId)}`).then(r => r.json()),
  uploadCover: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch('/api/wechat-mp/upload-cover', { method: 'POST', body: form }).then(r => r.json())
  },
}

/** 将秒数转为可读的时分秒，如 3600 → "1小时"，3661 → "1小时 1分 1秒" */
function formatIntervalSecondsReadable(sec) {
  if (!sec || sec < 60) return null
  const parts = []
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h) parts.push(`${h}小时`)
  if (m) parts.push(`${m}分`)
  if (s || parts.length === 0) parts.push(`${s}秒`)
  return parts.join(' ')
}

/** 距离下次执行的剩余时间描述 */
function formatTimeUntil(nextRunTime) {
  if (!nextRunTime) return ''
  const next = new Date(nextRunTime)
  if (isNaN(next)) return ''
  const now = Date.now()
  const diffMs = next - now
  if (diffMs <= 0) return '即将执行'
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)
  if (diffMin < 1) return '还剩 1 分钟内'
  if (diffMin < 60) return `还剩 ${diffMin} 分钟`
  if (diffHour < 24) return diffMin % 60 === 0 ? `还剩 ${diffHour} 小时` : `还剩 ${diffHour} 小时 ${diffMin % 60} 分钟`
  if (diffDay < 7) return `还剩 ${diffDay} 天`
  return `${formatDateTime(nextRunTime)}`
}

/** 距离上次执行的时间差描述（用于定时任务卡片「上次」） */
function formatTimeSince(lastRunTime) {
  if (!lastRunTime) return ''
  const last = new Date(lastRunTime)
  if (isNaN(last)) return ''
  const now = Date.now()
  const diffMs = now - last.getTime()
  if (diffMs <= 0) return '刚刚'
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffHour < 24) {
    const h = diffHour
    const m = diffMin % 60
    return m === 0 ? `${h} 小时前` : `${h} 小时 ${m} 分钟前`
  }
  if (diffDay < 7) return `${diffDay} 天前`
  return formatDateTime(lastRunTime)
}

function WechatDraftsPanel({ drafts, loading, onRefresh, onShowDetail }) {
  return (
    <div className="space-y-3">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted">公众号草稿箱（只读），点击查看详情，可「编辑」创建更新草稿任务。</p>
        <button onClick={onRefresh} className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:bg-white/5" title="从微信公众号服务器同步最新草稿列表">↻</button>
      </div>
      {loading ? (
        <div className="py-12 text-center text-muted">加载中...</div>
      ) : !drafts.length ? (
        <div className="py-12 text-center text-muted">暂无草稿</div>
      ) : (
        <div className="space-y-2">
          {drafts.map((item) => {
            const title = item?.content?.news_item?.[0]?.title || item?.media_id || '无标题'
            return (
              <div
                key={item?.media_id}
                onClick={() => onShowDetail(item)}
                className="px-4 py-3 rounded-lg border border-border bg-white/[0.02] hover:bg-white/5 cursor-pointer text-left"
              >
                <div className="font-medium text-white">{title}</div>
                <div className="text-xs text-muted mt-1">media_id: {item?.media_id}</div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function DraftDetailModal({ draftDetail, onClose, onEdit }) {
  const { loading, draft } = draftDetail
  const news = draft?.news_item?.[0]
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-white">草稿详情</h2>
          <button onClick={onClose} className="text-muted hover:text-white">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 text-sm">
          {loading && <p className="text-muted">加载中...</p>}
          {!loading && draft && (
            <div className="space-y-4">
              <div>
                <div className="text-muted text-xs mb-1">标题</div>
                <div className="text-white">{news?.title ?? '-'}</div>
              </div>
              {news?.author && (
                <div>
                  <div className="text-muted text-xs mb-1">作者</div>
                  <div className="text-muted">{news.author}</div>
                </div>
              )}
              {news?.digest && (
                <div>
                  <div className="text-muted text-xs mb-1">摘要</div>
                  <div className="text-muted">{news.digest}</div>
                </div>
              )}
              <div>
                <div className="text-muted text-xs mb-1">正文</div>
                <div className="max-h-60 overflow-y-auto rounded bg-white/5 p-3">
                  <HtmlPreview html={news?.content ?? ''} />
                </div>
              </div>
              <div className="pt-4 border-t border-border flex justify-end">
                <button
                  type="button"
                  onClick={onEdit}
                  className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium"
                >
                  编辑（创建更新草稿任务）
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function TaskManagement() {
  const toast = useToast()
  const [tab, setTab] = useState('tasks')
  const [tasks, setTasks] = useState([])
  const [scheduledTasks, setScheduledTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [heartbeat, setHeartbeat] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showPipelineModal, setShowPipelineModal] = useState(false)
  const [showCreatePipelineModal, setShowCreatePipelineModal] = useState(false)
  const [detailTaskId, setDetailTaskId] = useState(null)
  const [taskTypes, setTaskTypes] = useState([])
  const [runsModalSchedule, setRunsModalSchedule] = useState(null)
  const [runsModalRefreshTrigger, setRunsModalRefreshTrigger] = useState(0)
  const [editScheduleTask, setEditScheduleTask] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [draftsLoading, setDraftsLoading] = useState(false)
  const [draftDetail, setDraftDetail] = useState(null)
  const [editDraftPreFill, setEditDraftPreFill] = useState(null)
  const [createModalEditTask, setCreateModalEditTask] = useState(null)
  const [editPipelineGroup, setEditPipelineGroup] = useState(null) // { pipelineId, tasks }

  const location = useLocation()
  useEffect(() => {
    const id = location.state?.detailTaskId
    if (id) setDetailTaskId(id)
  }, [location.state?.detailTaskId])

  const handleGoToSchedule = useCallback((scheduleId) => {
    setDetailTaskId(null)
    setTab('scheduled')
    setRunsModalSchedule({ scheduleId, taskName: '', nextRunTime: null })
  }, [])

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

  const loadDeletedTasks = useCallback(async () => {
    setLoading(true)
    try {
      const data = await TASK_API.list({ deleted: 'only' })
      if (data.success && data.tasks) setTasks(data.tasks)
      else setTasks([])
    } catch (e) {
      setTasks([])
    }
    setLoading(false)
  }, [])

  const loadDrafts = useCallback(async () => {
    setDraftsLoading(true)
    try {
      const data = await WECHAT_MP_API.drafts({ offset: 0, count: 20, no_content: 1 })
      if (data.success && Array.isArray(data.item)) setDrafts(data.item)
      else setDrafts([])
    } catch (e) {
      setDrafts([])
    }
    setDraftsLoading(false)
  }, [])

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
    if (tab === 'tasks' || tab === 'pipeline') {
      loadTasks()
    } else if (tab === 'deleted') {
      loadDeletedTasks()
    } else {
      loadScheduledTasks()
    }
  }, [tab, loadTasks, loadDeletedTasks, loadScheduledTasks])

  useEffect(() => {
    if (showCreateModal || editScheduleTask || editPipelineGroup) {
      fetch('/api/task-queue/task-types')
        .then(r => r.json())
        .then(d => setTaskTypes(d.task_types || []))
        .catch(() => setTaskTypes([]))
    }
  }, [showCreateModal, editScheduleTask, editPipelineGroup])

  const filteredTasks = tasks.filter(t => {
    if (!search) return true
    const s = search.toLowerCase()
    return (t.task_name || '').toLowerCase().includes(s) || (t.task_id || '').toLowerCase().includes(s) || (t.created_by_schedule_id || '').toLowerCase().includes(s)
  })

  // 按 pipeline_id 分组：仅有 pipeline_id 的才放入组框；无 pipeline_id 的单独列出、不套框
  const { pipelineGroups, ungroupedTasks } = (() => {
    const groups = new Map() // pipeline_id -> tasks
    const ungrouped = []
    for (const t of filteredTasks) {
      const pid = (t.pipeline_id && String(t.pipeline_id).trim()) || null
      if (pid) {
        if (!groups.has(pid)) groups.set(pid, [])
        groups.get(pid).push(t)
      } else {
        ungrouped.push(t)
      }
    }
    const pipelineGroups = Array.from(groups.entries()).map(([pipelineId, list]) => ({
      pipelineId,
      tasks: list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)),
    }))
    pipelineGroups.sort((a, b) => {
      const aMin = Math.min(...a.tasks.map(t => new Date(t.created_at || 0)))
      const bMin = Math.min(...b.tasks.map(t => new Date(t.created_at || 0)))
      return bMin - aMin
    })
    ungrouped.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    return { pipelineGroups, ungroupedTasks: ungrouped }
  })()

  const tasksForStats = tab === 'tasks' ? ungroupedTasks : tab === 'pipeline'
    ? pipelineGroups.flatMap(g => g.tasks)
    : tasks
  const stats = {
    total: tasksForStats.length,
    pending: tasksForStats.filter(t => t.status === 'queued').length,
    running: tasksForStats.filter(t => t.status === 'running').length,
    completed: tasksForStats.filter(t => t.status === 'completed').length,
    failed: tasksForStats.filter(t => t.status === 'failed').length,
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">任务中心</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full">
        {/* 心跳条 */}
        <div className="flex items-center gap-2 px-4 py-2 mb-6 text-xs bg-cyan-500/5 border border-cyan-500/15 rounded-lg text-muted">
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
                tab === 'tasks' ? 'bg-accent text-white' : 'text-muted hover:text-white'
              }`}
            >
              普通任务
            </button>
            <button
              onClick={() => setTab('pipeline')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === 'pipeline' ? 'bg-accent text-white' : 'text-muted hover:text-white'
              }`}
            >
              组合任务
            </button>
            <button
              onClick={() => setTab('scheduled')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === 'scheduled' ? 'bg-accent text-white' : 'text-muted hover:text-white'
              }`}
            >
              定时任务
            </button>
            <button
              onClick={() => setTab('deleted')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === 'deleted' ? 'bg-accent text-white' : 'text-muted hover:text-white'
              }`}
            >
              已删除
            </button>
          </div>
          <div className="flex gap-2">
            {(tab === 'tasks' || tab === 'pipeline') && (
              <>
                <button
                  onClick={() => setShowCreatePipelineModal(true)}
                  className="px-4 py-2 border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 rounded-lg text-sm font-medium transition-colors"
                >
                  创建管道
                </button>
                <button
                  onClick={() => setShowPipelineModal(true)}
                  className="px-3 py-2 text-muted hover:text-white text-sm"
                  title="快捷：音频提取 → 字幕提取"
                >
                  快捷模板
                </button>
              </>
            )}
            {tab !== 'deleted' && (
              <button
                onClick={() => {
                  setEditDraftPreFill(null)
                  if (tab === 'pipeline') setShowCreatePipelineModal(true)
                  else setShowCreateModal(true)
                }}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors"
              >
                + {tab === 'tasks' ? '创建普通任务' : tab === 'pipeline' ? '创建管道' : '创建定时任务'}
              </button>
            )}
          </div>
        </div>

        {tab === 'deleted' ? (
          <>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-muted">回收站：可恢复任务到普通列表，或彻底删除。</p>
              <button
                onClick={loadDeletedTasks}
                className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:bg-white/5"
                title="刷新"
              >
                ↻
              </button>
            </div>
            <div className="space-y-6">
              {loading ? (
                <div className="py-12 text-center text-muted">加载中...</div>
              ) : pipelineGroups.length === 0 && ungroupedTasks.length === 0 ? (
                <div className="py-12 text-center text-muted">暂无已删除任务</div>
              ) : (
                <>
                  {pipelineGroups.map(({ pipelineId, tasks: groupTasks }) => (
                    <div
                      key={pipelineId}
                      className="rounded-xl border border-border bg-white/[0.02] overflow-hidden"
                    >
                      <div className="px-4 py-2.5 border-b border-border bg-white/5 flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-cyan-400 font-medium">{`管道 #${pipelineId.slice(0, 8)}`}</span>
                          <span className="text-xs text-muted">{groupTasks.length} 个任务</span>
                        </div>
                        <button
                          onClick={() => setEditPipelineGroup({ pipelineId, tasks: groupTasks })}
                          className="px-3 py-1 rounded border border-border text-xs text-muted hover:text-white hover:bg-white/5"
                        >
                          编辑管道
                        </button>
                      </div>
                      <div className="p-3 space-y-3">
                        {groupTasks.map(task => (
                          <TaskCard
                            key={task.task_id}
                            task={task}
                            onRefresh={loadDeletedTasks}
                            onShowDetail={setDetailTaskId}
                            onGoToSchedule={handleGoToSchedule}
                            recycleBin
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                      {ungroupedTasks.length > 0 && (
                    <div className="space-y-3">
                      {ungroupedTasks.map(task => (
                        <TaskCard
                          key={task.task_id}
                          task={task}
                          onRefresh={loadDeletedTasks}
                          onShowDetail={setDetailTaskId}
                          onGoToSchedule={handleGoToSchedule}
                          recycleBin
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        ) : tab === 'tasks' || tab === 'pipeline' ? (
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
                  <span className="text-xs text-muted">{label}</span>
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
                className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:bg-white/5 transition-colors"
                title="刷新"
              >
                ↻
              </button>
              <button
                onClick={async () => {
                  const ok = await toast.confirm('确定要清理超时任务吗？')
                  if (!ok) return
                  try {
                    const res = await fetch('/api/task-queue/cleanup?max_idle_minutes=30', { method: 'POST' })
                    const data = await res.json()
                    if (data.success) {
                      toast.info(`清理完成，共清理了 ${data.cleaned_count} 个超时任务`)
                      loadTasks()
                    }
                  } catch (e) {
                    toast.error('清理失败: ' + e.message)
                  }
                }}
                className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:bg-white/5 transition-colors"
              >
                清理超时
              </button>
            </div>

            {/* 任务列表：普通任务仅展示无 pipeline_id 的；组合任务仅展示管道组 */}
            <div className="space-y-6">
              {loading ? (
                <div className="py-12 text-center text-muted">加载中...</div>
              ) : tab === 'pipeline' ? (
                pipelineGroups.length === 0 ? (
                  <div className="py-12 text-center text-muted">暂无组合任务，点击「创建管道」添加</div>
                ) : (
                  pipelineGroups.map(({ pipelineId, tasks: groupTasks }) => (
                    <div
                      key={pipelineId}
                      className="rounded-xl border border-border bg-white/[0.02] overflow-hidden"
                    >
                      <div className="px-4 py-2.5 border-b border-border bg-white/5 flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-cyan-400 font-medium">
                            {`管道 #${pipelineId.slice(0, 8)}`}
                          </span>
                          <span className="text-xs text-muted">
                            {groupTasks.length} 个任务
                          </span>
                        </div>
                        <button
                          onClick={() => setEditPipelineGroup({ pipelineId, tasks: groupTasks })}
                          className="px-3 py-1 rounded border border-border text-xs text-muted hover:text-white hover:bg-white/5"
                        >
                          编辑管道
                        </button>
                      </div>
                      <div className="p-3 space-y-3">
                        {groupTasks.map(task => (
                          <TaskCard
                            key={task.task_id}
                            task={task}
                            onRefresh={loadTasks}
                            onShowDetail={setDetailTaskId}
                            onGoToSchedule={handleGoToSchedule}
                          />
                        ))}
                      </div>
                    </div>
                  ))
                )
              ) : (
                ungroupedTasks.length === 0 ? (
                  <div className="py-12 text-center text-muted">暂无普通任务</div>
                ) : (
                  <div className="space-y-3">
                    {ungroupedTasks.map(task => (
                      <TaskCard
                        key={task.task_id}
                        task={task}
                        onRefresh={loadTasks}
                        onShowDetail={setDetailTaskId}
                        onGoToSchedule={handleGoToSchedule}
                      />
                    ))}
                  </div>
                )
              )}
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-muted">定时任务到期后由心跳创建普通任务入队执行。</p>
              <button onClick={loadScheduledTasks} className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:bg-white/5" title="刷新">↻</button>
            </div>
            {scheduledTasks.length === 0 ? (
              <div className="py-12 text-center text-muted">暂无定时任务</div>
            ) : (
              scheduledTasks.map(t => (
                <ScheduledTaskCard
                  key={t.schedule_id}
                  task={t}
                  onRefresh={loadScheduledTasks}
                  onViewRuns={() => setRunsModalSchedule({ scheduleId: t.schedule_id, taskName: t.task_name, nextRunTime: t.next_run_time })}
                  onEdit={() => setEditScheduleTask(t)}
                />
              ))
            )}
          </div>
        )}
      </div>

      {showCreateModal && tab === 'scheduled' && (
        <CreateScheduledTaskModal
          taskTypes={taskTypes}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            loadScheduledTasks()
          }}
        />
      )}
      {editScheduleTask && (
        <EditScheduledTaskModal
          task={editScheduleTask}
          taskTypes={taskTypes}
          onClose={() => setEditScheduleTask(null)}
          onSuccess={() => {
            setEditScheduleTask(null)
            loadScheduledTasks()
          }}
        />
      )}
      {showCreateModal && tab !== 'scheduled' && (
        <CreateTaskModal
          taskTypes={taskTypes}
          initialType={editDraftPreFill?.initialType}
          initialMetadata={editDraftPreFill?.initialMetadata}
          initialName={editDraftPreFill?.initialName}
          editTask={createModalEditTask}
          onClose={() => {
            setShowCreateModal(false)
            setEditDraftPreFill(null)
            setCreateModalEditTask(null)
          }}
          onSuccess={() => {
            setShowCreateModal(false)
            setEditDraftPreFill(null)
            setCreateModalEditTask(null)
            loadTasks()
            if (tab === 'wechat-drafts') loadDrafts()
          }}
        />
      )}
      {draftDetail && (
        <DraftDetailModal
          draftDetail={draftDetail}
          onClose={() => setDraftDetail(null)}
          onEdit={() => {
            const d = draftDetail.draft
            const news = d?.news_item?.[0]
            const mediaId = (draftDetail.media_id ?? d?.media_id ?? '').toString().trim()
            setEditDraftPreFill({
              initialType: 'wechat_mp_draft',
              initialMetadata: {
                operation: 'update',
                media_id: mediaId,
                title: news?.title ?? '',
                content: htmlToMd(news?.content ?? ''),
                author: news?.author ?? '',
                digest: news?.digest ?? '',
                content_source_url: news?.content_source_url ?? '',
                thumb_media_id: news?.thumb_media_id ?? '',
              },
              initialName: '',
            })
            setDraftDetail(null)
            setShowCreateModal(true)
          }}
        />
      )}
      {showCreatePipelineModal && (
        <CreatePipelineModal
          api={TASK_API}
          onClose={() => setShowCreatePipelineModal(false)}
          onSuccess={() => {
            setShowCreatePipelineModal(false)
            loadTasks()
          }}
        />
      )}
      {showPipelineModal && (
        <PipelineTemplateModal
          onClose={() => setShowPipelineModal(false)}
          onSuccess={() => {
            setShowPipelineModal(false)
            loadTasks()
          }}
        />
      )}
      {editPipelineGroup && (
        <EditPipelineModal
          pipelineId={editPipelineGroup.pipelineId}
          tasks={editPipelineGroup.tasks}
          taskTypes={taskTypes}
          onClose={() => setEditPipelineGroup(null)}
          onSuccess={() => {
            setEditPipelineGroup(null)
            loadTasks()
          }}
        />
      )}
      {detailTaskId && (
        <TaskDetailModal
          taskId={detailTaskId}
          taskTypes={taskTypes}
          onClose={() => setDetailTaskId(null)}
          onRefresh={() => {
            loadTasks()
            loadDeletedTasks()
            setDetailTaskId(null)
            if (runsModalSchedule) setRunsModalRefreshTrigger(t => t + 1)
          }}
          onGoToSchedule={handleGoToSchedule}
          onEditBeforeRestart={(task) => {
            const pid = (task.pipeline_id || '').trim()
            if (pid) {
              // 管道任务：整体编辑，而非单独编辑
              const groupTasks = (tasks || [])
                .filter(t => (t.pipeline_id || '').trim() === pid)
                .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
              setEditPipelineGroup({ pipelineId: pid, tasks: groupTasks })
            } else {
              setCreateModalEditTask(task)
              setShowCreateModal(true)
            }
            setDetailTaskId(null)
          }}
        />
      )}
      {runsModalSchedule && (
        <ScheduledTaskRunsModal
          scheduleId={runsModalSchedule.scheduleId}
          taskName={runsModalSchedule.taskName}
          nextRunTime={runsModalSchedule.nextRunTime}
          onClose={() => setRunsModalSchedule(null)}
          onShowDetail={setDetailTaskId}
          refreshTrigger={runsModalRefreshTrigger}
        />
      )}
    </div>
  )
}

/**
 * 编辑管道：整体编辑管道内所有任务的参数，保存后可选全部重新执行
 */
function EditPipelineModal({ pipelineId, tasks, taskTypes, onClose, onSuccess }) {
  const toast = useToast()
  const [taskEdits, setTaskEdits] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [restartAfterSave, setRestartAfterSave] = useState(false)

  useEffect(() => {
    const edits = {}
    for (const t of tasks) {
      edits[t.task_id] = {
        task_name: t.task_name || '',
        metadata: { ...(t.metadata || {}) },
      }
    }
    setTaskEdits(edits)
  }, [tasks])

  const sortedTasks = [...tasks].sort((a, b) => {
    const aDep = a.depends_on_task_id || ''
    const bDep = b.depends_on_task_id || ''
    if (!aDep && bDep) return -1
    if (aDep && !bDep) return 1
    return (a.created_at || '').localeCompare(b.created_at || '')
  })

  const setTaskEdit = (taskId, field, value) => {
    setTaskEdits(prev => ({
      ...prev,
      [taskId]: { ...prev[taskId], [field]: value },
    }))
  }

  const handleSave = async () => {
    setSubmitting(true)
    try {
      for (const task of tasks) {
        const edit = taskEdits[task.task_id]
        if (!edit) continue
        let meta = await prepareMetadataForSubmitAsync(task.task_type, edit.metadata)
        const res = await TASK_API.patch(task.task_id, {
          task_name: (edit.task_name || '').trim() || undefined,
          metadata: meta,
        })
        if (!res.success) throw new Error(res.detail || res.message || '保存失败')
      }
      if (restartAfterSave) {
        for (const task of sortedTasks) {
          await TASK_API.restart(task.task_id)
        }
        toast.info('已保存并全部重新执行')
      } else {
        toast.info('已保存')
      }
      onSuccess()
    } catch (e) {
      toast.error(e?.message || '保存失败')
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-white">编辑管道 #{pipelineId?.slice(0, 8)}</h3>
          <button onClick={onClose} className="text-muted hover:text-white">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {sortedTasks.map((task, idx) => {
            const typeInfo = taskTypes.find(t => t.type === task.task_type)
            const schema = typeInfo?.metadata_schema || {}
            const edit = taskEdits[task.task_id]
            if (!edit) return null
            const isInputFile = task.task_type === 'speech_to_text' || task.task_type === 'video_extract_audio'
            const inputAccept = task.task_type === 'speech_to_text' ? '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*' : '.mp4,.mkv,.avi,.mov,.webm,video/*'
            const fileUploadFields = isInputFile ? { input_file: inputAccept } : {}
            return (
              <details key={task.task_id} open={idx === 0} className="rounded-lg border border-border bg-white/[0.02] overflow-hidden">
                <summary className="px-4 py-3 cursor-pointer hover:bg-white/5 flex items-center justify-between">
                  <span className="font-medium text-white">步骤 {idx + 1}：{task.task_type}</span>
                  <span className="text-xs text-muted">#{task.task_id?.slice(0, 8)}</span>
                </summary>
                <div className="px-4 pb-4 pt-1 space-y-3">
                  <div>
                    <label className="block text-sm text-muted mb-1">任务名称</label>
                    <input
                      type="text"
                      value={edit.task_name}
                      onChange={e => setTaskEdit(task.task_id, 'task_name', e.target.value)}
                      className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
                      placeholder="留空自动生成"
                    />
                  </div>
                  <TaskMetadataFormFields
                    schema={schema}
                    metadata={edit.metadata}
                    setMetadata={m => setTaskEdit(task.task_id, 'metadata', m)}
                    fieldIdPrefix={`pipe-edit-${task.task_id}`}
                    isInputFileTask={isInputFile}
                    fileUploadFields={fileUploadFields}
                  />
                </div>
              </details>
            )
          })}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={restartAfterSave}
              onChange={e => setRestartAfterSave(e.target.checked)}
              className="rounded text-accent"
            />
            <span className="text-sm text-muted">保存后全部重新执行</span>
          </label>
        </div>
        <div className="shrink-0 flex justify-end gap-3 px-6 py-4 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 border border-border rounded-lg text-muted hover:text-white">
            取消
          </button>
          <button onClick={handleSave} disabled={submitting} className="px-4 py-2 bg-accent hover:opacity-90 text-white rounded-lg disabled:opacity-50">
            {submitting ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * 创建管道（先选链路，再填任务细节）
 * Step 1: 选择管道模板
 * Step 2: 只填该链路需要用户提供的参数（如第一步的输入文件、可选任务名）
 */
function CreatePipelineModal({ api, onClose, onSuccess }) {
  const toast = useToast()
  const [step, setStep] = useState('choose') // 'choose' | 'fill'
  const [selectedId, setSelectedId] = useState(null)
  const [formValues, setFormValues] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const template = PIPELINE_TEMPLATES.find(t => t.id === selectedId)
  const fields = template?.form?.fields || []

  const getInitialFormValues = (t) => {
    const fds = t?.form?.fields || []
    return Object.fromEntries(fds.map(f => [f.id, '']))
  }

  const handleSelectTemplate = (id) => {
    const t = PIPELINE_TEMPLATES.find(x => x.id === id)
    setSelectedId(id)
    setStep('fill')
    setFormValues(getInitialFormValues(t))
  }

  const handleBack = () => {
    setStep('choose')
    setSelectedId(null)
  }

  const setField = (fieldId, value) => {
    setFormValues(prev => ({ ...prev, [fieldId]: value }))
  }

  const handleUpload = async (e, fieldId) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/task-queue/upload-input-file', { method: 'POST', body: form })
      const data = await res.json()
      if (data.success && data.path) setField(fieldId, data.path)
      else throw new Error(data.detail || '上传失败')
    } catch (err) {
      toast.error('上传失败: ' + (err?.message || String(err)))
    }
    setUploading(false)
    e.target.value = ''
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!template?.createTasks) return
    setSubmitting(true)
    try {
      const result = await template.createTasks(formValues, api)
      const ids = Object.entries(result || {})
        .filter(([k]) => k.startsWith('task') && k.endsWith('Id'))
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, v]) => v?.slice(0, 8))
        .join(' / ')
      toast.info(`管道已创建：${ids || '完成'}`)
      onSuccess()
      onClose()
    } catch (err) {
      toast.error('创建失败: ' + (err?.message || String(err)))
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center p-6 pb-4">
          <h3 className="text-lg font-semibold text-white">
            {step === 'choose' ? '创建管道 - 选择链路' : `填写参数 - ${template?.name || ''}`}
          </h3>
          <button type="button" onClick={onClose} className="text-2xl text-muted hover:text-white">&times;</button>
        </div>

        {step === 'choose' && (
          <div className="px-6 pb-6 space-y-3">
            <p className="text-sm text-muted mb-4">先选择一条管道链路，下一步只需填写该链路需要的输入参数。</p>
            {PIPELINE_TEMPLATES.map(t => (
              <button
                key={t.id}
                type="button"
                onClick={() => handleSelectTemplate(t.id)}
                className="w-full text-left p-4 rounded-xl border border-border bg-white/5 hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-colors"
              >
                <div className="font-medium text-white">{t.name}</div>
                <div className="text-sm text-muted mt-1">{t.description}</div>
              </button>
            ))}
          </div>
        )}

        {step === 'fill' && template && (
          <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-4">
            <p className="text-sm text-muted">以下仅需填写<strong className="text-white">第一步</strong>的输入；后续步骤的输入将按链路自动绑定。</p>
            {fields.map(field => (
              <div key={field.id}>
                <label className="block text-sm text-muted mb-1">
                  {field.label}{field.required ? ' *' : ''}
                </label>
                {field.type === 'file' ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formValues[field.id] ?? ''}
                      onChange={e => setField(field.id, e.target.value)}
                      placeholder={field.placeholder || ''}
                      className="flex-1 px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
                    />
                    <input
                      type="file"
                      accept={field.accept || '*'}
                      className="hidden"
                      ref={fileInputRef}
                      onChange={e => handleUpload(e, field.id)}
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="px-3 py-2 rounded-lg border border-border text-muted hover:text-white whitespace-nowrap disabled:opacity-50"
                    >
                      {uploading ? '上传中…' : '上传'}
                    </button>
                  </div>
                ) : (
                  <input
                    type="text"
                    value={formValues[field.id] ?? ''}
                    onChange={e => setField(field.id, e.target.value)}
                    placeholder={field.placeholder || ''}
                    className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
                  />
                )}
              </div>
            ))}
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={handleBack} className="px-4 py-2 border border-border rounded-lg text-muted hover:text-white">
                上一步
              </button>
              <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-white">
                取消
              </button>
              <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">
                {submitting ? '创建中...' : '创建管道'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

/** 管道模板：一键创建「音频提取 → 字幕提取」两个任务，第二个依赖第一个的 result.data.output_file */
function PipelineTemplateModal({ onClose, onSuccess }) {
  const toast = useToast()
  const [inputFile, setInputFile] = useState('')
  const [name1, setName1] = useState('')
  const [name2, setName2] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/task-queue/upload-input-file', { method: 'POST', body: form })
      const data = await res.json()
      if (data.success && data.path) setInputFile(data.path)
      else throw new Error(data.detail || '上传失败')
    } catch (err) {
      toast.error('上传失败: ' + (err?.message || String(err)))
    }
    setUploading(false)
    e.target.value = ''
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const path = (inputFile || '').trim()
    if (!path) {
      toast.warning('请填写或上传视频文件路径')
      return
    }
    setSubmitting(true)
    try {
      const res1 = await TASK_API.create({
        task_type: 'video_extract_audio',
        task_name: name1.trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: { input_file: path },
      })
      if (!res1.success) throw new Error(res1.detail || res1.message || '创建第一步任务失败')
      const task1Id = res1.task_id

      const res2 = await TASK_API.create({
        task_type: 'speech_to_text',
        task_name: name2.trim() || undefined,
        priority: 2,
        max_retries: 3,
        metadata: {},
        depends_on_task_id: task1Id,
        input_bindings: { input_file: 'result.data.output_file' },
      })
      if (!res2.success) throw new Error(res2.detail || res2.message || '创建第二步任务失败')
      toast.info(`管道已创建：\n1. 音频提取 ${task1Id?.slice(0, 8)}\n2. 字幕提取（依赖上一步） ${res2.task_id?.slice(0, 8)}`)
      onSuccess()
      onClose()
    } catch (err) {
      toast.error('创建失败: ' + (err?.message || String(err)))
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-md w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">管道：音频提取 → 字幕提取</h3>
          <button onClick={onClose} className="text-2xl text-muted hover:text-white">&times;</button>
        </div>
        <p className="text-sm text-muted mb-4">将依次创建两个任务，第二步自动使用第一步的输出音频作为输入。</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">视频文件路径（第一步输入）*</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputFile}
                onChange={e => setInputFile(e.target.value)}
                placeholder="本地路径或上传"
                className="flex-1 px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
              />
              <input type="file" accept=".mp4,.mkv,.avi,.mov,.webm,video/*" className="hidden" ref={fileInputRef} onChange={handleUpload} />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-3 py-2 rounded-lg border border-border text-muted hover:text-white whitespace-nowrap disabled:opacity-50"
              >
                {uploading ? '上传中…' : '上传'}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">第一步任务名称（可选）</label>
            <input
              type="text"
              value={name1}
              onChange={e => setName1(e.target.value)}
              placeholder="留空自动生成"
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">第二步任务名称（可选）</label>
            <input
              type="text"
              value={name2}
              onChange={e => setName2(e.target.value)}
              placeholder="留空自动生成"
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-white">
              取消
            </button>
            <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">
              {submitting ? '创建中...' : '创建管道'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ScheduledTaskRunsModal({ scheduleId, taskName, nextRunTime, onClose, onShowDetail, refreshTrigger }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  const loadRuns = useCallback(async () => {
    if (!scheduleId) return
    setLoading(true)
    try {
      const data = await TASK_API.list({ created_by_schedule_id: scheduleId })
      if (data.success && data.tasks) setTasks(data.tasks)
      else setTasks([])
    } catch (e) {
      setTasks([])
    }
    setLoading(false)
  }, [scheduleId])

  useEffect(() => {
    loadRuns()
  }, [loadRuns, refreshTrigger])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-5xl w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-white">
            {taskName || '定时任务'} 执行记录
          </h2>
          <div className="flex gap-2">
            <button onClick={loadRuns} disabled={loading} className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white hover:bg-white/5 disabled:opacity-50" title="刷新">↻</button>
            <button onClick={onClose} className="text-muted hover:text-white text-2xl leading-none">×</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="py-12 text-center text-muted">加载中...</div>
          ) : tasks.length === 0 ? (
            <div className="py-12 text-center text-muted space-y-2">
              <p>暂无执行记录</p>
              <p className="text-xs">定时任务到期后由心跳创建任务，执行记录会显示在此处。</p>
              {nextRunTime && (
                <p className="text-xs">下次运行: {formatDateTime(nextRunTime)}</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map(task => (
                <TaskCard
                  key={task.task_id}
                  task={task}
                  onRefresh={loadRuns}
                  onShowDetail={onShowDetail}
                  inRunsModal
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ScheduledTaskCard({ task, onRefresh, onViewRuns, onEdit }) {
  const toast = useToast()
  const [toggling, setToggling] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [running, setRunning] = useState(false)
  const cfg = task.schedule_config || {}
  const scheduleLabel = task.schedule_type === 'cron'
    ? `cron: ${cfg.cron || ''}`
    : (() => {
        const sec = cfg.interval_seconds || 0
        const readable = formatIntervalSecondsReadable(sec)
        return readable ? `每 ${sec} 秒（${readable}）` : `每 ${sec} 秒`
      })()

  const handleToggle = async () => {
    setToggling(true)
    try {
      const res = await fetch(`/api/task-queue/scheduled-tasks/${task.schedule_id}/toggle?is_active=${!task.is_active}`, {
        method: 'PUT',
      })
      const data = await res.json()
      if (data.success) onRefresh()
      else throw new Error(data.detail || '操作失败')
    } catch (err) {
      toast.error('操作失败: ' + (err.message || String(err)))
    }
    setToggling(false)
  }

  const handleRunNow = async () => {
    setRunning(true)
    try {
      const res = await fetch(`/api/task-queue/scheduled-tasks/${task.schedule_id}/run-now`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        onRefresh()
        if (data.task_id) toast.info(`已创建任务 #${data.task_id.slice(0, 8)}，可在执行记录中查看`)
      } else throw new Error(data.detail || '执行失败')
    } catch (err) {
      toast.error('立即执行失败: ' + (err?.message || String(err)))
    }
    setRunning(false)
  }

  const handleDelete = async () => {
    const ok = await toast.confirm('确定删除该定时任务？')
    if (!ok) return
    setDeleting(true)
    try {
      const res = await fetch(`/api/task-queue/scheduled-tasks/${task.schedule_id}`, { method: 'DELETE' })
      const data = await res.json()
      if (data.success) onRefresh()
      else throw new Error(data.detail || '删除失败')
    } catch (err) {
      toast.error('删除失败: ' + (err.message || String(err)))
    }
    setDeleting(false)
  }

  return (
    <div className="p-5 bg-white/5 border border-border rounded-xl hover:border-cyan-500/25 transition-colors">
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <span className="font-medium text-white">{task.task_name || '未命名'}</span>
          <span className="text-sm text-muted ml-2">#{task.schedule_id?.slice(0, 8)}</span>
          <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${task.is_active ? 'bg-green-500/15 text-green-400' : 'bg-slate-500/20 text-slate-400'}`}>
            {task.is_active ? '激活' : '已禁用'}
          </span>
        </div>
        <div className="flex gap-2 shrink-0">
          {onEdit && (
            <button onClick={onEdit} className="px-3 py-1.5 rounded-lg border border-border text-muted hover:text-white hover:bg-white/5 text-sm">
              编辑
            </button>
          )}
          {onViewRuns && (
            <button onClick={onViewRuns} className="px-3 py-1.5 rounded-lg border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 text-sm">
              查看执行记录
            </button>
          )}
          <button onClick={handleRunNow} disabled={running} className="px-3 py-1.5 rounded-lg border border-green-500/50 text-green-400 hover:bg-green-500/10 text-sm disabled:opacity-50">
            {running ? '执行中...' : '立即执行'}
          </button>
          <button onClick={handleToggle} disabled={toggling} className="px-3 py-1.5 rounded-lg border border-border text-sm text-muted hover:text-white hover:bg-white/5 disabled:opacity-50">
            {toggling ? '...' : task.is_active ? '禁用' : '启用'}
          </button>
          <button onClick={handleDelete} disabled={deleting} className="px-3 py-1.5 rounded-lg border border-red-500/50 text-amber-400 hover:bg-red-500/10 disabled:opacity-50"
          >
            {deleting ? '...' : '删除'}
          </button>
        </div>
      </div>
      <div className="mt-3 text-sm text-muted">
        {task.task_type} · {scheduleLabel}
      </div>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
        <span>下次: {formatDateTime(task.next_run_time)}</span>
        {task.is_active && task.next_run_time && (
          <span className="text-cyan-400/90">{formatTimeUntil(task.next_run_time)}</span>
        )}
        {task.last_run_time && (
          <span>
            上次: {formatDateTime(task.last_run_time)}
            {' '}
            <span className="text-cyan-400/90">（{formatTimeSince(task.last_run_time)}）</span>
          </span>
        )}
        {task.consecutive_errors > 0 && (
          <span className="text-amber-400">连续失败 {task.consecutive_errors} 次</span>
        )}
      </div>
      {task.last_error && (
        <div className="mt-2 text-xs text-muted truncate max-w-full" title={task.last_error}>
          错误: {task.last_error}
        </div>
      )}
    </div>
  )
}

function EditScheduledTaskModal({ task, taskTypes, onClose, onSuccess }) {
  const toast = useToast()
  const typeInfo = taskTypes.find(t => t.type === task.task_type) || null
  let defaultMeta = getDefaultMetadata(typeInfo?.metadata_schema)
  if ((task.task_type === 'url_to_wiki' || task.task_type === 'pdf_to_wiki') && Array.isArray(defaultMeta.categories)) {
    defaultMeta = { ...defaultMeta, categories: [...defaultMeta.categories, ...getDateCategoryStrings()] }
  }
  const cfg = task.schedule_config || {}
  const [name, setName] = useState(task.task_name || '')
  const [scheduleType, setScheduleType] = useState(task.schedule_type || 'interval')
  const [intervalSeconds, setIntervalSeconds] = useState(cfg.interval_seconds ?? 3600)
  const [cronExpr, setCronExpr] = useState(cfg.cron || '0 2 * * *')
  const [cronTz, setCronTz] = useState(cfg.tz || '')
  const type = task.task_type
  const initialMeta = type === 'weather_query' ? migrateWeatherMetadata(task.metadata || {}) : (task.metadata || {})
  const [metadata, setMetadata] = useState({ ...defaultMeta, ...initialMeta })
  const [submitting, setSubmitting] = useState(false)
  const schema = typeInfo?.metadata_schema || {}
  const isInputFileTask = type === 'speech_to_text' || type === 'video_extract_audio'
  const inputFileAccept = type === 'speech_to_text'
    ? '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*'
    : type === 'video_extract_audio'
      ? '.mp4,.mkv,.avi,.mov,.webm,video/*'
      : '*'
  const fileUploadFields = type === 'pdf_to_wiki' ? { file_path: '.pdf,application/pdf' } : undefined

  const handleSubmit = async (e) => {
    e.preventDefault()
    for (const [key, spec] of Object.entries(schema)) {
      if (spec?.required) {
        const v = metadata[key]
        if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
          toast.warning(`请填写必填项: ${spec.description || key}`)
          return
        }
      }
    }
    const scheduleConfig = scheduleType === 'interval'
      ? { interval_seconds: Number(intervalSeconds) }
      : { cron: cronExpr.trim(), ...(cronTz.trim() ? { tz: cronTz.trim() } : {}) }
    if (scheduleType === 'interval' && (intervalSeconds < 60 || !Number.isFinite(intervalSeconds))) {
      toast.warning('执行间隔至少 1 分钟')
      return
    }
    if (scheduleType === 'cron' && !cronExpr.trim()) {
      toast.warning('请填写 cron 表达式')
      return
    }
    setSubmitting(true)
    try {
      const meta = await prepareMetadataForSubmitAsync(task.task_type, metadata)
      const res = await fetch(`/api/task-queue/scheduled-tasks/${task.schedule_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_name: name?.trim() || task.task_name,
          schedule_type: scheduleType,
          schedule_config: scheduleConfig,
          metadata: meta,
        }),
      })
      const data = await res.json()
      if (data.success) {
        toast.info('定时任务已更新')
        onSuccess()
        onClose()
      } else {
        throw new Error(getApiErrorMessage(data))
      }
    } catch (err) {
      toast.error('更新失败: ' + (err?.message || String(err)))
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">编辑定时任务</h3>
          <button onClick={onClose} className="text-2xl text-muted hover:text-white">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">任务类型</label>
            <input type="text" value={type} readOnly disabled className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-muted cursor-not-allowed" />
          </div>
          {Object.keys(schema).length > 0 && (
            <div className="pt-2 border-t border-border">
              <div className="text-sm font-medium text-muted mb-3">任务参数（城市、查询类型等）</div>
              <TaskMetadataFormFields
                schema={schema}
                metadata={metadata}
                setMetadata={setMetadata}
                fieldIdPrefix="edit-sched"
                isInputFileTask={isInputFileTask}
                inputFileAccept={inputFileAccept}
                fileUploadFields={fileUploadFields}
              />
              {type === 'mediawiki_write' && (
                <label className="flex items-center gap-2 cursor-pointer mt-3">
                  <input
                    type="checkbox"
                    checked={!!metadata._contentIsMarkdown}
                    onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
                    className="text-accent focus:ring-accent rounded"
                  />
                  <span className="text-sm text-muted">正文为 Markdown（提交时转为 Wiki 语法）</span>
                </label>
              )}
              {(type === 'url_to_wiki' || type === 'pdf_to_wiki') && (
                <p className="mt-2 text-xs text-amber-400/90">下方分类即写入 Wiki 的标签，可添加、可删除；日、周、月按执行日期自动追加。</p>
              )}
              {(type === 'url_to_wiki' || type === 'pdf_to_wiki') && (
                <WikiTitlePreviewHint taskType={type} metadata={metadata} />
              )}
            </div>
          )}
          <ScheduleConfigFields
            taskName={name}
            onTaskNameChange={setName}
            scheduleType={scheduleType}
            onScheduleTypeChange={setScheduleType}
            intervalSeconds={intervalSeconds}
            onIntervalSecondsChange={setIntervalSeconds}
            cronExpr={cronExpr}
            onCronExprChange={setCronExpr}
            cronTz={cronTz}
            onCronTzChange={setCronTz}
          />
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-white">取消</button>
            <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">{submitting ? '保存中...' : '保存'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateScheduledTaskModal({ taskTypes, onClose, onSuccess }) {
  const toast = useToast()
  const [type, setType] = useState('')
  const [name, setName] = useState('')
  const [scheduleType, setScheduleType] = useState('interval')
  const [intervalSeconds, setIntervalSeconds] = useState(3600)
  const [cronExpr, setCronExpr] = useState('0 2 * * *')
  const [cronTz, setCronTz] = useState('')
  const [metadata, setMetadata] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const typeInfo = taskTypes.find(t => t.type === type) || null
  const schema = typeInfo?.metadata_schema || {}
  const isInputFileTask = type === 'speech_to_text' || type === 'video_extract_audio'
  const inputFileAccept = type === 'speech_to_text'
    ? '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*'
    : type === 'video_extract_audio'
      ? '.mp4,.mkv,.avi,.mov,.webm,video/*'
      : '*'
  const fileUploadFields = type === 'pdf_to_wiki' ? { file_path: '.pdf,application/pdf' } : undefined

  const setTypeAndResetMetadata = (newType) => {
    setType(newType)
    const info = taskTypes.find(t => t.type === newType)
    let meta = getDefaultMetadata(info?.metadata_schema)
    if ((newType === 'url_to_wiki' || newType === 'pdf_to_wiki') && Array.isArray(meta.categories)) {
      meta = { ...meta, categories: [...meta.categories, ...getDateCategoryStrings()] }
    }
    setMetadata(meta)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!type) { toast.warning('请选择任务类型'); return }
    for (const [key, spec] of Object.entries(schema)) {
      if (spec?.required) {
        const v = metadata[key]
        if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
          toast.warning(`请填写必填项: ${spec.description || key}`)
          return
        }
      }
    }
    const scheduleConfig = scheduleType === 'interval'
      ? { interval_seconds: Number(intervalSeconds) }
      : { cron: cronExpr.trim(), ...(cronTz.trim() ? { tz: cronTz.trim() } : {}) }
    if (scheduleType === 'interval' && (intervalSeconds < 60 || !Number.isFinite(intervalSeconds))) {
      toast.warning('执行间隔至少 1 分钟')
      return
    }
    if (scheduleType === 'cron' && !cronExpr.trim()) {
      toast.warning('请填写 cron 表达式')
      return
    }
    setSubmitting(true)
    try {
      const meta = await prepareMetadataForSubmitAsync(type, metadata)
      const res = await fetch('/api/task-queue/scheduled-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: type,
          task_name: name?.trim() || "",
          schedule_type: scheduleType,
          schedule_config: scheduleConfig,
          metadata: meta,
        }),
      })
      const data = await res.json()
      if (data.success) {
        onSuccess()
        onClose()
      } else {
        throw new Error(getApiErrorMessage(data))
      }
    } catch (err) {
      toast.error('创建失败: ' + (err?.message || String(err)))
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">创建定时任务</h3>
          <button onClick={onClose} className="text-2xl text-muted hover:text-white">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">任务类型 *</label>
            <select
              value={type}
              onChange={e => setTypeAndResetMetadata(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
              required
            >
              <option value="">请选择任务类型</option>
              {taskTypes.map(t => (
                <option key={t.type} value={t.type}>{t.name} - {t.description}</option>
              ))}
            </select>
          </div>
              <TaskMetadataFormFields
                schema={schema}
                metadata={metadata}
                setMetadata={setMetadata}
                fieldIdPrefix="create-sched"
                isInputFileTask={isInputFileTask}
                inputFileAccept={inputFileAccept}
                fileUploadFields={fileUploadFields}
              />
          {type === 'mediawiki_write' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!metadata._contentIsMarkdown}
                onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
                className="text-accent focus:ring-accent rounded"
              />
              <span className="text-sm text-muted">正文为 Markdown（提交时转为 Wiki 语法）</span>
            </label>
          )}
          {(type === 'url_to_wiki' || type === 'pdf_to_wiki') && (
            <p className="text-xs text-amber-400/90">下方分类即写入 Wiki 的标签，可添加、可删除；日、周、月按执行日期自动追加。</p>
          )}
          {(type === 'url_to_wiki' || type === 'pdf_to_wiki') && (
            <WikiTitlePreviewHint taskType={type} metadata={metadata} />
          )}
          <ScheduleConfigFields
            taskName={name}
            onTaskNameChange={setName}
            scheduleType={scheduleType}
            onScheduleTypeChange={setScheduleType}
            intervalSeconds={intervalSeconds}
            onIntervalSecondsChange={setIntervalSeconds}
            cronExpr={cronExpr}
            onCronExprChange={setCronExpr}
            cronTz={cronTz}
            onCronTzChange={setCronTz}
          />
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-white">取消</button>
            <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">{submitting ? '创建中...' : '创建'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateTaskModal({ taskTypes, initialType, initialMetadata, initialName, editTask, onClose, onSuccess }) {
  const toast = useToast()
  const isEditMode = !!editTask
  const [type, setType] = useState('')
  const [name, setName] = useState('')
  const [priority, setPriority] = useState(2)
  const [maxRetries, setMaxRetries] = useState(3)
  const [metadata, setMetadata] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [inputSource, setInputSource] = useState('manual') // 'manual' | 'from_task'
  const [completedTasks, setCompletedTasks] = useState([])
  const [linkableUpstreams, setLinkableUpstreams] = useState({ linkable_task_types: [], suggested_bindings: {} })
  const [dependsOnTaskId, setDependsOnTaskId] = useState('')
  const [inputBindings, setInputBindings] = useState({}) // { fieldKey: 'result.data.output_file' }
  const typeInfo = taskTypes.find(t => t.type === type) || null
  const schema = typeInfo?.metadata_schema || {}

  useEffect(() => {
    if (editTask?.task_id) {
      setType(editTask.task_type || '')
      setName(editTask.task_name || '')
      setPriority(editTask.priority ?? 2)
      setMaxRetries(editTask.max_retries ?? 3)
      setMetadata({ ...(editTask.metadata || {}) })
      setInputSource('manual')
    } else if (initialType != null && initialType !== '') {
      setType(initialType)
      setMetadata({ ...(initialMetadata || {}) })
      setName(initialName != null ? String(initialName) : '')
      setInputSource('manual')
    }
  }, [editTask?.task_id, initialType, initialMetadata, initialName])

  const inputFileAccept = type === 'speech_to_text'
    ? '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*'
    : type === 'video_extract_audio'
      ? '.mp4,.mkv,.avi,.mov,.webm,video/*'
      : ''
  const contentFileAccept = '.txt,.md,.markdown,.wiki,text/*'
  const fileUploadFields = {}
  if (type === 'speech_to_text') fileUploadFields.input_file = inputFileAccept
  if (type === 'video_extract_audio') fileUploadFields.input_file = inputFileAccept
  if (type === 'mediawiki_write') fileUploadFields.content_file = contentFileAccept
  if (type === 'pdf_to_wiki') fileUploadFields.file_path = '.pdf,application/pdf'

  const setTypeAndResetMetadata = (newType) => {
    setType(newType)
    const info = taskTypes.find(t => t.type === newType)
    let meta = getDefaultMetadata(info?.metadata_schema)
    if ((newType === 'url_to_wiki' || newType === 'pdf_to_wiki') && Array.isArray(meta.categories)) {
      meta = { ...meta, categories: [...meta.categories, ...getDateCategoryStrings()] }
    }
    setMetadata(meta)
    setInputBindings({})
    setDependsOnTaskId('')
    setLinkableUpstreams({ linkable_task_types: [], suggested_bindings: {} })
  }

  useEffect(() => {
    if (!type) return
    fetch(`/api/task-queue/task-types/${encodeURIComponent(type)}/linkable-upstreams`)
      .then(r => r.json())
      .then(d => {
        if (d.success && d.linkable_task_types) setLinkableUpstreams({ linkable_task_types: d.linkable_task_types || [], suggested_bindings: d.suggested_bindings || {} })
        else setLinkableUpstreams({ linkable_task_types: [], suggested_bindings: {} })
      })
      .catch(() => setLinkableUpstreams({ linkable_task_types: [], suggested_bindings: {} }))
  }, [type])

  useEffect(() => {
    if (inputSource !== 'from_task') return
    TASK_API.list({ status: 'completed' })
      .then(d => { if (d.success && d.tasks) setCompletedTasks(d.tasks); else setCompletedTasks([]) })
      .catch(() => setCompletedTasks([]))
  }, [inputSource])

  const tasksForUpstream = linkableUpstreams.linkable_task_types?.length > 0
    ? completedTasks.filter(t => linkableUpstreams.linkable_task_types.includes(t.task_type))
    : completedTasks

  const onDependsOnTaskChange = (taskId) => {
    setDependsOnTaskId(taskId)
    if (!taskId) { setInputBindings({}); return }
    const selected = completedTasks.find(t => t.task_id === taskId)
    if (!selected?.task_type) return
    const suggested = linkableUpstreams.suggested_bindings?.[selected.task_type]
    if (Array.isArray(suggested) && suggested.length) {
      const next = {}
      suggested.forEach(({ downstream_field, upstream_path }) => { if (downstream_field && upstream_path) next[downstream_field] = upstream_path })
      setInputBindings(next)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!type) {
      toast.warning('请选择任务类型')
      return
    }
    for (const [key, spec] of Object.entries(schema)) {
      if (spec?.required) {
        const v = metadata[key]
        if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
          toast.warning(`请填写必填项: ${spec.description || key}`)
          return
        }
      }
    }
    if (type === 'mediawiki_write') {
      const hasContent = metadata.content != null && String(metadata.content).trim()
      const hasContentFile = metadata.content_file != null && String(metadata.content_file).trim()
      if (!hasContent && !hasContentFile) {
        toast.warning('请填写页面内容或内容文件路径（二选一）')
        return
      }
    }
    if (type === 'wechat_mp_draft' && (metadata?.operation || '').toString().toLowerCase() === 'update') {
      const mid = (metadata?.media_id ?? '').toString().trim()
      if (!mid) {
        toast.warning('请从当前草稿列表选择要更新的草稿')
        return
      }
    }
    if (inputSource === 'from_task') {
      if (!dependsOnTaskId || !dependsOnTaskId.trim()) {
        toast.warning('请选择要依赖的已完成任务')
        return
      }
    }
    setSubmitting(true)
    try {
      let meta = { ...metadata }
      if (type === 'video_download' && metadata.cookies_from_extension) {
        const url = (metadata.url || '').trim().toLowerCase()
        const domain = url.includes('youtube.com') || url.includes('youtu.be') ? 'youtube.com'
          : url.includes('bilibili.com') || url.includes('b23.tv') ? 'bilibili.com'
          : 'youtube.com'
        const res = await requestCookiesFromExtension(domain)
        if (res.success && res.content) {
          meta = { ...meta, cookies_content: res.content }
        } else {
          toast.warning(res.error || '未能从扩展获取 cookies')
          setSubmitting(false)
          return
        }
        delete meta.cookies_from_extension
      }
      const prepared = await prepareMetadataForSubmitAsync(type, meta)
      if (isEditMode && editTask?.task_id) {
        const patchRes = await TASK_API.patch(editTask.task_id, {
          metadata: prepared,
          task_name: (name || '').trim() || undefined,
          priority,
          max_retries: maxRetries,
        })
        if (!patchRes.success) throw new Error(patchRes.detail || patchRes.message || '更新失败')
        const restartRes = await TASK_API.restart(editTask.task_id)
        if (!restartRes.success) throw new Error(restartRes.detail || restartRes.message || '重新执行失败')
        toast.info('已更新并重新入队')
        onSuccess()
        onClose()
      } else {
        const payload = { task_type: type, task_name: name || undefined, priority, max_retries: maxRetries, metadata: prepared }
        if (inputSource === 'from_task' && dependsOnTaskId?.trim()) {
          payload.depends_on_task_id = dependsOnTaskId.trim()
          const bindings = {}
          Object.entries(inputBindings || {}).forEach(([k, v]) => { if (v && String(v).trim()) bindings[k] = String(v).trim() })
          if (Object.keys(bindings).length) payload.input_bindings = bindings
        }
        const res = await fetch('/api/task-queue/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const data = await res.json()
        if (data.success) {
          toast.info('任务创建成功: ' + data.task_id)
          onSuccess()
          onClose()
        } else {
          throw new Error(data.detail || data.message || '创建失败')
        }
      }
    } catch (err) {
      toast.error('创建失败: ' + (err.message || String(err)))
    }
    setSubmitting(false)
  }

  const isWechatDraft = type === 'wechat_mp_draft'
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className={`bg-surface border border-border rounded-xl shadow-xl w-full mx-4 max-h-[95vh] overflow-hidden flex flex-col ${isWechatDraft ? 'max-w-5xl h-[95vh]' : 'max-w-lg'}`}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-white">{isEditMode ? '编辑后重新执行' : '创建新任务'}</h3>
          <button onClick={onClose} className="text-2xl text-muted hover:text-white">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">任务类型 *</label>
            {isEditMode ? (
              <input type="text" readOnly value={typeInfo ? `${typeInfo.name} - ${typeInfo.description}` : type} className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-muted cursor-not-allowed" />
            ) : (
            <select
              value={type}
              onChange={e => setTypeAndResetMetadata(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
              required
            >
              <option value="">请选择任务类型</option>
              {taskTypes.map(t => (
                <option key={t.type} value={t.type}>{t.name} - {t.description}</option>
              ))}
            </select>
            )}
            {(type === 'speech_to_text' || type === 'video_extract_audio') && (
              <p className="mt-1 text-xs text-amber-400/90">
                可点击「选择文件」上传，或填写用户主目录下的本地路径
              </p>
            )}
            {type === 'mediawiki_write' && (
              <p className="mt-1 text-xs text-amber-400/90">
                页面内容与内容文件二选一：可直接填写下方内容，或填写/选择本地文本文件路径
              </p>
            )}
          </div>
          {type && !isEditMode && (
            <div>
              <label className="block text-sm text-muted mb-2">输入来源</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="inputSource"
                    checked={inputSource === 'manual'}
                    onChange={() => { setInputSource('manual'); setDependsOnTaskId(''); setInputBindings({}) }}
                    className="text-accent focus:ring-accent"
                  />
                  <span className="text-white">手动填写</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="inputSource"
                    checked={inputSource === 'from_task'}
                    onChange={() => setInputSource('from_task')}
                    className="text-accent focus:ring-accent"
                  />
                  <span className="text-white">来自已有任务</span>
                </label>
              </div>
              {inputSource === 'from_task' && (
                <div className="mt-3 p-3 bg-white/5 border border-border rounded-lg space-y-3">
                  <div>
                    <label className="block text-xs text-muted mb-1">
                      选择已完成任务
                      {linkableUpstreams.linkable_task_types?.length > 0 && (
                        <span className="ml-2 text-cyan-400/90">（仅显示可链接类型）</span>
                      )}
                    </label>
                    <select
                      value={dependsOnTaskId}
                      onChange={e => onDependsOnTaskChange(e.target.value)}
                      className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none text-sm"
                    >
                      <option value="">请选择</option>
                      {tasksForUpstream.map(t => (
                        <option key={t.task_id} value={t.task_id}>
                          {t.task_name || t.task_id?.slice(0, 8)} · {t.task_type} · {t.result_summary ? t.result_summary.slice(0, 30) + '…' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-2">字段映射（本任务字段 ← 上游 result 路径）</div>
                    {Object.keys(schema).map(fieldKey => (
                      <div key={fieldKey} className="flex items-center gap-2 mb-2">
                        <span className="text-muted text-sm w-28 shrink-0">{schema[fieldKey]?.description || fieldKey}</span>
                        <input
                          type="text"
                          value={inputBindings[fieldKey] ?? ''}
                          onChange={e => setInputBindings(b => ({ ...b, [fieldKey]: e.target.value }))}
                          placeholder="如 result.data.output_file"
                          className="flex-1 px-2 py-1.5 bg-white/5 border border-border rounded text-white placeholder-[#64748b] text-sm focus:border-accent focus:outline-none"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {(inputSource === 'manual' || isEditMode) && type && (
            <TaskParamsForm
              taskType={type}
              schema={schema}
              metadata={metadata}
              setMetadata={setMetadata}
              fieldIdPrefix="create-task"
              fileUploadFields={Object.keys(fileUploadFields).length ? fileUploadFields : undefined}
              isInputFileTask={type === 'speech_to_text' || type === 'video_extract_audio'}
              inputFileAccept={type === 'speech_to_text' ? '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*' : type === 'video_extract_audio' ? '.mp4,.mkv,.avi,.mov,.webm,video/*' : '*'}
              taskName={name}
              onTaskNameChange={setName}
              taskNamePlaceholder={isEditMode ? '留空则保持原样' : '留空自动生成'}
              priority={priority}
              onPriorityChange={setPriority}
              maxRetries={isEditMode ? maxRetries : undefined}
              onMaxRetriesChange={isEditMode ? setMaxRetries : undefined}
              onCoverUpload={type === 'wechat_mp_draft' ? (file) => WECHAT_MP_API.uploadCover(file) : undefined}
            />
          )}
          </div>
          <div className="shrink-0 flex gap-3 px-6 py-4 border-t border-border bg-surface">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-white">
              取消
            </button>
            <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50">
              {isEditMode ? (submitting ? '保存并入队中...' : '保存并重新执行') : (submitting ? '创建中...' : '创建')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
