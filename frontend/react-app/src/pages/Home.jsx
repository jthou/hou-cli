import { useEffect, useState } from 'react'
import WeatherResultDisplay from '../components/WeatherResultDisplay'

export default function Home() {
  const [weatherTask, setWeatherTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          task_type: 'weather_query',
          limit: '1',
          include_result: 'true',
        })
        // 按创建时间倒序返回，limit=1 即可拿到最新一条；如果后端不保证顺序，可在前端再按 created_at 排序一次
        const res = await fetch(`/api/task-queue/tasks?${params.toString()}`)
        const json = await res.json()
        if (!json.success) {
          throw new Error(json.detail || json.error || '获取天气任务失败')
        }
        const tasks = Array.isArray(json.tasks) ? json.tasks : []
        const completed = tasks.filter((t) => t.status === 'completed' && t.result)
        if (completed.length > 0) {
          // 若返回中有多条（后端未排序），按 created_at 倒序取一条
          completed.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
          if (!cancelled) setWeatherTask(completed[0])
        } else if (!cancelled) {
          setWeatherTask(null)
        }
      } catch (e) {
        if (!cancelled) setError(e.message || String(e))
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">首页</h1>
      </header>
      <div className="flex-1 flex overflow-hidden">
        {/* 左栏 */}
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
        </div>

        {/* 右栏（预留） */}
        <div className="w-full lg:w-1/2 overflow-y-auto p-6 text-sm text-muted">
          {/* 右侧内容后续按你的指令填充 */}
        </div>
      </div>
    </div>
  )
}

