import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../components/ToastModal'

export default function WeatherQuery() {
  const toast = useToast()
  const [location, setLocation] = useState('')
  const [queryType, setQueryType] = useState('current')
  const [includeWarning, setIncludeWarning] = useState(false)
  const [includeAirQuality, setIncludeAirQuality] = useState(false)
  const [days, setDays] = useState(7)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!location.trim()) {
      toast.warning('请输入城市名称')
      return
    }
    setSubmitting(true)
    setResult(null)
    const metadata = {
      location: location.trim(),
      query_type: queryType,
      include_warning: includeWarning,
      include_air_quality: includeAirQuality,
    }
    if (queryType === 'forecast') metadata.days = days
    try {
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'weather_query',
          metadata,
        }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ taskId: data.task_id, success: true })
      } else {
        throw new Error(data.detail || data.message || '创建任务失败')
      }
    } catch (err) {
      setResult({ error: err.message, success: false })
    }
    setSubmitting(false)
  }

  const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
  const labelCls = 'block text-sm font-medium text-[#94a3b8] mb-1'
  const checkboxCls = 'flex items-center gap-3 text-[#94a3b8] cursor-pointer'

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">天气查询</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <p className="text-[#94a3b8] mb-6">
          查询指定地点的实时天气、预报、预警或空气质量。提交后任务将加入队列，可在
          <Link to="/" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看结果。
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelCls}>城市名称 <span className="text-red-400">*</span></label>
            <input
              type="text"
              value={location}
              onChange={e => setLocation(e.target.value)}
              placeholder="如：北京、上海、深圳"
              className={inputCls}
              required
            />
          </div>

          <div>
            <label className={labelCls}>查询类型</label>
            <select value={queryType} onChange={e => setQueryType(e.target.value)} className={inputCls}>
              <option value="current">实时天气</option>
              <option value="forecast">天气预报</option>
              <option value="warning">仅查预警</option>
              <option value="air_quality">仅查空气质量</option>
            </select>
          </div>

          {queryType === 'forecast' && (
            <div>
              <label className={labelCls}>预报天数</label>
              <select value={days} onChange={e => setDays(Number(e.target.value))} className={inputCls}>
                <option value={3}>3 天</option>
                <option value={7}>7 天</option>
                <option value={15}>15 天</option>
              </select>
            </div>
          )}

          {(queryType === 'current' || queryType === 'forecast') && (
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <label className={checkboxCls}>
                <input type="checkbox" checked={includeWarning} onChange={e => setIncludeWarning(e.target.checked)} className="rounded" />
                同时拉取预警
              </label>
              <label className={checkboxCls}>
                <input type="checkbox" checked={includeAirQuality} onChange={e => setIncludeAirQuality(e.target.checked)} className="rounded" />
                同时拉取空气质量
              </label>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {submitting ? '提交中...' : '提交查询'}
          </button>
        </form>

        {result && (
          <div className={`mt-6 p-4 rounded-lg ${result.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {result.success ? (
              <p>
                任务已创建：<Link to="/" className="underline">{result.taskId}</Link>
                ，请在任务管理中查看结果。
              </p>
            ) : (
              <p>失败：{result.error}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
