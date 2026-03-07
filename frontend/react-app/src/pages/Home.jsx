import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import WeatherResultDisplay from '../components/WeatherResultDisplay'
import TaskResultDisplay from '../components/TaskResultDisplay'

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
        const res = await fetch(`/api/task-queue/tasks?${params.toString()}`)
        const json = await res.json()
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
        if (!cancelled) setError(e.message || String(e))
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [taskType])

  return { task, loading, error }
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
        const res = await fetch(`/api/task-queue/tasks?${params.toString()}`)
        const json = await res.json()
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
        if (!cancelled) setError(e.message || String(e))
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [])

  return { task, loading, error }
}

export default function Home() {
  const { task: weatherTask, loading, error } = useLatestTask('weather_query')
  const { task: urlToWikiTask, loading: urlToWikiLoading, error: urlToWikiError } = useLatestScheduledUrlToWiki()
  const { task: webSearchTask, loading: webSearchLoading, error: webSearchError } = useLatestTask('web_search')

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="首页" />
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

