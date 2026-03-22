import { useEffect, useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import WeatherResultDisplay from '../components/WeatherResultDisplay'
import DiskResultDisplay from '../components/DiskResultDisplay'
import TaskResultDisplay from '../components/TaskResultDisplay'
import MarkdownPreview from '../components/MarkdownPreview'
import { useToast } from '../components/ToastModal'
import { parseApiResponseJson } from '../utils/parseApiResponse'

const FETCH_TIMEOUT_MS = 15000

function useLatestTask(taskType) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          task_type: taskType,
          limit: '1',
          include_result: 'true',
        })
        const ctrl = new AbortController()
        const timeout = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS)
        const res = await fetch(`/api/task-queue/tasks?${params.toString()}`, { signal: ctrl.signal })
        clearTimeout(timeout)
        const json = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(json.detail || json.error || `请求失败: HTTP ${res.status}`)
        }
        if (!json.success) {
          throw new Error(json.detail || json.error || '获取任务失败')
        }
        const tasks = Array.isArray(json.tasks) ? json.tasks : []
        const completed = tasks.filter((t) => t.status === 'completed' && t.result)
        if (completed.length > 0) {
          completed.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
          if (!cancelled) setTask(completed[0])
        } else if (!cancelled) {
          setTask(null)
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e.name === 'AbortError' ? '请求超时，请检查后端是否正常运行' : (e.message || String(e))
          setError(msg)
        }
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [taskType])

  return { task, loading, error }
}

/** make disk-scan 生成的全盘报告（docs/disk_report.json） */
function useDiskScanReport() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const ctrl = new AbortController()
    const timeout = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS)
    fetch('/api/system/disk-scan-report', { signal: ctrl.signal })
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return
        if (d.success && d.data) setReport(d.data)
        else setReport(null)
      })
      .catch((e) => {
        if (!cancelled) setError(e.name === 'AbortError' ? '请求超时' : e.message || '加载失败')
      })
      .finally(() => {
        clearTimeout(timeout)
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ctrl.abort()
    }
  }, [])

  return { report, loading, error }
}

/** 最新定时网文抓取任务（created_by_schedule_id 有值） */
function useLatestScheduledUrlToWiki() {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          task_type: 'url_to_wiki',
          status: 'completed',
          limit: '30',
          include_result: 'true',
        })
        const ctrl = new AbortController()
        const timeout = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS)
        const res = await fetch(`/api/task-queue/tasks?${params.toString()}`, { signal: ctrl.signal })
        clearTimeout(timeout)
        const json = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(json.detail || json.error || `请求失败: HTTP ${res.status}`)
        }
        if (!json.success) {
          throw new Error(json.detail || json.error || '获取任务失败')
        }
        const tasks = Array.isArray(json.tasks) ? json.tasks : []
        const scheduled = tasks.filter(
          (t) => t.status === 'completed' && t.result && t.created_by_schedule_id
        )
        if (scheduled.length > 0) {
          scheduled.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
          if (!cancelled) setTask(scheduled[0])
        } else if (!cancelled) {
          setTask(null)
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e.name === 'AbortError' ? '请求超时，请检查后端是否正常运行' : (e.message || String(e))
          setError(msg)
        }
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [])

  return { task, loading, error }
}

export default function Home() {
  const toast = useToast()
  const [briefing, setBriefing] = useState(null)
  const [briefingShowDegraded, setBriefingShowDegraded] = useState(false)
  const [briefingLastAttempt, setBriefingLastAttempt] = useState(null)
  const [briefingPending, setBriefingPending] = useState(false)
  const [briefingLoading, setBriefingLoading] = useState(true)
  const [briefingError, setBriefingError] = useState(null)
  const [briefingGenerating, setBriefingGenerating] = useState(false)
  const pollRef = useRef(null)

  const applyBriefingPayload = useCallback((data) => {
    setBriefing(data?.briefing ?? null)
    setBriefingShowDegraded(Boolean(data?.show_degraded_banner))
    setBriefingLastAttempt(data?.last_attempt ?? null)
    setBriefingPending(Boolean(data?.pending_in_queue))
  }, [])

  const loadBriefing = useCallback(async () => {
    setBriefingLoading(true)
    setBriefingError(null)
    try {
      const res = await fetch('/api/home-briefing/latest')
      const data = await parseApiResponseJson(res)
      applyBriefingPayload(data)
    } catch (e) {
      setBriefingError(e?.message || String(e))
      setBriefing(null)
      setBriefingShowDegraded(false)
      setBriefingLastAttempt(null)
      setBriefingPending(false)
    } finally {
      setBriefingLoading(false)
    }
  }, [applyBriefingPayload])

  useEffect(() => {
    loadBriefing()
  }, [loadBriefing])

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }, [])

  const handleGenerateBriefing = async () => {
    if (briefingGenerating) return
    setBriefingGenerating(true)
    try {
      const res = await fetch('/api/home-briefing/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const data = await parseApiResponseJson(res)
      toast.info(data?.message || '已加入队列')
      const taskId = data?.task_id
      if (!taskId) {
        setBriefingGenerating(false)
        return
      }
      let n = 0
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        n += 1
        try {
          const tr = await fetch(`/api/task-queue/tasks/${encodeURIComponent(taskId)}`)
          const td = await parseApiResponseJson(tr)
          const st = td?.task?.status
          if (st === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setBriefingGenerating(false)
            await loadBriefing()
            toast.info('简报已更新')
            return
          }
          if (st === 'failed' || st === 'cancelled') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setBriefingGenerating(false)
            const err = td?.task?.error || td?.task?.message || '任务失败'
            toast.error(err)
            await loadBriefing()
            return
          }
        } catch {
          /* ignore */
        }
        if (n >= 90) {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setBriefingGenerating(false)
          toast.warning('等待超时，请稍后在首页刷新或到任务中心查看')
          await loadBriefing()
        }
      }, 2000)
    } catch (e) {
      toast.error(e?.message || '提交失败')
      setBriefingGenerating(false)
    }
  }

  const { task: weatherTask, loading, error } = useLatestTask('weather_query')
  const { report: diskScanReport, loading: diskReportLoading, error: diskReportError } = useDiskScanReport()
  const { task: diskScanTask, loading: diskScanLoading, error: diskScanError } = useLatestTask('disk_scan')
  const { task: urlToWikiTask, loading: urlToWikiLoading, error: urlToWikiError } = useLatestScheduledUrlToWiki()
  const { task: webSearchTask, loading: webSearchLoading, error: webSearchError } = useLatestTask('web_search')

  const quickLinks = [
    { to: '/web-reader', icon: '🌐', label: '网页阅读' },
    { to: '/mediawiki-reader', icon: '📖', label: 'Wiki阅读' },
    { to: '/general-chat', icon: '💬', label: '通用对话' },
    { to: '/tasks', icon: '📋', label: '任务中心' },
  ]

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="首页" />
      {/* 时间：2026-03-21；理由：P0 简报 + P1 任务轮询与失败降级横幅 */}
      <div className="shrink-0 px-6 py-3 border-b border-border">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
          <h2 className="text-sm font-semibold text-white">简报与研判</h2>
          <button
            type="button"
            onClick={handleGenerateBriefing}
            disabled={briefingGenerating}
            className="text-xs px-3 py-1.5 rounded-lg border border-accent/60 text-accent hover:bg-accent/10 disabled:opacity-50"
          >
            {briefingGenerating ? '生成中…' : '生成最新简报'}
          </button>
        </div>
        {briefingLoading && <p className="text-xs text-muted">加载简报…</p>}
        {briefingError && <p className="text-xs text-red-400">简报加载失败：{briefingError}</p>}
        {!briefingLoading && !briefingError && briefingShowDegraded && briefing?.markdown && (
          <div className="mb-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/95">
            本期简报生成失败，以下为上一期内容。
            {briefingLastAttempt?.display_error && (
              <span className="block mt-1 text-amber-200/80">原因：{briefingLastAttempt.display_error}</span>
            )}
            <Link to="/tasks" className="ml-2 text-accent underline">任务中心</Link>
          </div>
        )}
        {!briefingLoading && !briefingError && briefingPending && !briefingGenerating && (
          <p className="text-xs text-cyan-400/90 mb-2">有简报任务正在排队或执行中，请稍候…</p>
        )}
        {!briefingLoading && !briefingError && !briefing && briefingLastAttempt?.status === 'failed' && (
          <p className="text-xs text-red-400">
            最近一次简报生成失败：{briefingLastAttempt.display_error || '未知错误'}
          </p>
        )}
        {!briefingLoading && !briefingError && !briefing && !(briefingLastAttempt?.status === 'failed') && (
          <p className="text-xs text-muted">
            暂无已生成的简报。请先完成一些<strong>天气查询</strong>或<strong>网页搜索</strong>任务，再点击「生成最新简报」。
          </p>
        )}
        {!briefingLoading && briefing?.meta && (
          <p className="text-[11px] text-muted mb-2">
            {briefing.meta.title || '简报'}
            {briefing.meta.generated_at && (
              <span className="ml-2">· 生成于 {briefing.meta.generated_at}</span>
            )}
            {briefing.meta.used_count != null && (
              <span className="ml-2">· 依据 {briefing.meta.used_count} 条事实</span>
            )}
          </p>
        )}
        {!briefingLoading && briefing?.markdown && (
          <div className="rounded-xl border border-cyan-500/20 bg-surface/50 p-4 max-h-[min(420px,50vh)] overflow-y-auto">
            <div className="prose prose-invert prose-sm max-w-none text-muted">
              <MarkdownPreview markdown={briefing.markdown} theme="dark" />
            </div>
          </div>
        )}
        {!briefingLoading && briefing?.fact_refs?.length > 0 && (
          <details className="mt-2 text-xs text-muted">
            <summary className="cursor-pointer text-cyan-300/80 hover:text-cyan-200">
              事实索引（补充；正文已含主要来源链接）
            </summary>
            <ul className="mt-2 space-y-1 pl-4 list-disc">
              {briefing.fact_refs.map((r) => (
                <li key={r.id}>
                  <span className="text-fg/90">{r.id}</span>
                  {r.title && <span className="ml-1">{r.title}</span>}
                  {r.url && (
                    <a href={r.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-accent break-all">
                      链接
                    </a>
                  )}
                  {r.task_id && (
                    <Link to="/tasks" className="ml-2 text-muted hover:text-accent">
                      任务 {r.task_id.slice(0, 8)}…
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <div className="shrink-0 px-6 py-2 flex flex-wrap gap-2">
        {quickLinks.map(({ to, icon, label }) => (
          <Link
            key={to}
            to={to}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface/60 border border-border text-sm text-muted hover:text-accent hover:border-accent/50 transition-colors"
          >
            <span>{icon}</span>
            <span>{label}</span>
          </Link>
        ))}
      </div>
      <div className="flex-1 flex overflow-hidden">
        {/* 左栏：天气预报、定时网文抓取 */}
        <div className="w-full lg:w-1/2 border-r border-border overflow-y-auto p-6 space-y-4">
          <section className="border border-border rounded-xl bg-surface/40 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">最近一次天气预报</h2>
              {loading && <span className="text-xs text-muted">加载中…</span>}
            </div>
            {error && (
              <p className="text-xs text-red-400">
                加载失败：{error}
              </p>
            )}
            {!loading && !error && !weatherTask && (
              <p className="text-xs text-muted">
                暂无已完成的天气查询任务。
              </p>
            )}
            {!loading && !error && weatherTask && (
              <div className="space-y-3">
                <div className="text-xs text-muted">
                  任务 ID #{weatherTask.task_id?.slice(0, 8)} · 创建于 {weatherTask.created_at}
                </div>
                <WeatherResultDisplay result={weatherTask.result} />
              </div>
            )}
          </section>

          <section className="border border-border rounded-xl bg-surface/40 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">最近一次磁盘扫描</h2>
              <Link
                to="/disk-scan"
                className="text-xs text-muted hover:text-accent"
              >
                更多 →
              </Link>
            </div>
            {(diskReportLoading || diskScanLoading) && <span className="text-xs text-muted">加载中…</span>}
            {(diskReportError || diskScanError) && (
              <p className="text-xs text-red-400">加载失败：{diskReportError || diskScanError}</p>
            )}
            {!diskReportLoading && !diskScanLoading && !diskScanReport && !diskScanTask && (
              <p className="text-xs text-muted">暂无磁盘扫描数据。执行 make disk-scan 生成全盘报告。</p>
            )}
            {!diskReportLoading && !diskScanLoading && (diskScanReport || diskScanTask) && (
              <div className="space-y-3">
                <div className="text-xs text-muted">
                  {diskScanReport?.source?.startsWith?.('make disk-scan') ? (
                    <>全盘扫描 (make disk-scan)</>
                  ) : (
                    <>任务 ID #{diskScanTask.task_id?.slice(0, 8)} · 创建于 {diskScanTask.created_at}</>
                  )}
                </div>
                <DiskResultDisplay
                  result={diskScanReport || diskScanTask?.result?.result || diskScanTask?.result}
                />
              </div>
            )}
          </section>

          <section className="border border-border rounded-xl bg-surface/40 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">最近一次定时网文抓取</h2>
              <Link
                to="/url-to-wiki"
                className="text-xs text-muted hover:text-accent"
              >
                更多 →
              </Link>
            </div>
            {urlToWikiLoading && <span className="text-xs text-muted">加载中…</span>}
            {urlToWikiError && (
              <p className="text-xs text-red-400">加载失败：{urlToWikiError}</p>
            )}
            {!urlToWikiLoading && !urlToWikiError && !urlToWikiTask && (
              <p className="text-xs text-muted">暂无已完成的定时网文抓取任务。</p>
            )}
            {!urlToWikiLoading && !urlToWikiError && urlToWikiTask && (
              <div className="space-y-3">
                <div className="text-xs text-muted">
                  任务 ID #{urlToWikiTask.task_id?.slice(0, 8)} · 创建于 {urlToWikiTask.created_at}
                  {urlToWikiTask.created_by_schedule_id && (
                    <span className="ml-2">· 定时 #{urlToWikiTask.created_by_schedule_id.slice(0, 8)}</span>
                  )}
                </div>
                <TaskResultDisplay
                  taskType="url_to_wiki"
                  result={urlToWikiTask.result}
                  taskId={urlToWikiTask.task_id}
                />
              </div>
            )}
          </section>
        </div>

        {/* 右栏：最近一次网页搜索 */}
        <div className="w-full lg:w-1/2 overflow-y-auto p-6 space-y-4">
          <section className="border border-border rounded-xl bg-surface/40 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">最近一次网页搜索</h2>
              <Link
                to="/web-search"
                className="text-xs text-muted hover:text-accent"
              >
                更多 →
              </Link>
            </div>
            {webSearchLoading && <span className="text-xs text-muted">加载中…</span>}
            {webSearchError && (
              <p className="text-xs text-red-400">加载失败：{webSearchError}</p>
            )}
            {!webSearchLoading && !webSearchError && !webSearchTask && (
              <p className="text-xs text-muted">暂无已完成的网页搜索任务。</p>
            )}
            {!webSearchLoading && !webSearchError && webSearchTask && (
              <div className="space-y-3">
                <div className="text-xs text-muted">
                  任务 ID #{webSearchTask.task_id?.slice(0, 8)} · 创建于 {webSearchTask.created_at}
                  {webSearchTask.metadata?.query && (
                    <span className="ml-2">· 关键词「{webSearchTask.metadata.query}」</span>
                  )}
                </div>
                <TaskResultDisplay
                  taskType="web_search"
                  result={webSearchTask.result}
                  taskId={webSearchTask.task_id}
                />
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

