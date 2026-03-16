import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import PageHeader from '../components/PageHeader'

const PAGE_SIZE = 20
function todayUTC() {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}
const DIRECTION_LABEL = { request: '请求', response: '响应', response_error: '错误' }
const DIRECTION_CLASS = {
  request: 'bg-cyan-500/20 text-cyan-400',
  response: 'bg-emerald-500/20 text-emerald-400',
  response_error: 'bg-red-500/20 text-red-400',
}

const SOURCE_LABEL = { writing_suggestions: '写作建议' }

function RecordCard({ record }) {
  const { ts, direction, model, payload, audit_id, session_id, source, usage, ...rest } = record
  const dirClass = DIRECTION_CLASS[direction] || 'bg-slate-500/20 text-slate-400'
  const label = DIRECTION_LABEL[direction] ?? direction

  const renderPayload = () => {
    if (!payload || typeof payload !== 'object') return <pre className="text-xs text-muted whitespace-pre-wrap">{String(payload)}</pre>
    if (payload.message_count != null && payload.messages) {
      return (
        <div className="space-y-2">
          <p className="text-xs text-muted">消息数: {payload.message_count}</p>
          {payload.messages.map((m, i) => (
            <div key={i} className="bg-black/20 rounded p-2 text-sm">
              <span className="text-cyan-400 font-medium">[{m.role}]</span>
              <span className="text-muted ml-1">长度 {m.content_length}</span>
              <pre className="mt-1 text-muted whitespace-pre-wrap break-words">{m.content_preview || ''}</pre>
            </div>
          ))}
        </div>
      )
    }
    if (payload.content_preview != null) {
      return <pre className="text-sm text-muted whitespace-pre-wrap break-words bg-black/20 rounded p-3">{payload.content_preview}</pre>
    }
    if (payload.error != null) {
      return (
        <div className="text-sm">
          <p className="text-red-400 font-medium">{payload.error_type || 'Error'}</p>
          <pre className="text-muted whitespace-pre-wrap mt-1 bg-black/20 rounded p-2">{payload.error}</pre>
          {payload.cause && <p className="text-amber-400/80 text-xs mt-2">底层原因: {payload.cause}</p>}
          {payload.hint && <p className="text-amber-400/90 text-xs mt-2">{payload.hint}</p>}
          {payload.partial_preview && <p className="text-xs text-muted mt-2">局部输出: {payload.partial_preview.slice(0, 200)}...</p>}
        </div>
      )
    }
    if (payload.type === 'tool_calls' && payload.names) {
      return <p className="text-sm text-muted">工具调用: {payload.names.join(', ')}</p>
    }
    return <pre className="text-xs text-muted whitespace-pre-wrap break-words">{JSON.stringify(payload, null, 2)}</pre>
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-white/5">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b border-border">
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${dirClass}`}>{label}</span>
        <span className="text-xs text-muted">{ts}</span>
        <span className="text-xs text-muted">{model}</span>
        {usage && (usage.prompt_tokens != null || usage.completion_tokens != null || usage.total_tokens != null) && (
          <span className="text-xs text-amber-400/90" title="输入/输出/合计 tokens">
            {[usage.prompt_tokens ?? '-', usage.completion_tokens ?? '-', usage.total_tokens ?? '-'].join(' / ')} tokens
          </span>
        )}
        {audit_id && <span className="text-xs text-muted">audit_id: {audit_id}</span>}
        {session_id && <span className="text-xs text-violet-400">session: {session_id.slice(0, 8)}…</span>}
        {source && SOURCE_LABEL[source] && (
          <span className="text-xs text-amber-400/90">{SOURCE_LABEL[source]}</span>
        )}
      </div>
      <div className="p-4 text-sm">
        {renderPayload()}
        {Object.keys(rest).length > 0 && (
          <details className="mt-2">
            <summary className="text-xs text-muted cursor-pointer">其他字段</summary>
            <pre className="text-xs text-muted mt-1 whitespace-pre-wrap">{JSON.stringify(rest, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

export default function SettingsLlmAudit() {
  const [dates, setDates] = useState([])
  const [fromDate, setFromDate] = useState(todayUTC())
  const [toDate, setToDate] = useState(todayUTC())
  const [showFilter, setShowFilter] = useState(false)
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dailyStats, setDailyStats] = useState([])
  const [chartMode, setChartMode] = useState('day') // 'day' | 'week' | 'month'

  const chartData = useMemo(() => {
    if (!Array.isArray(dailyStats) || dailyStats.length === 0) return []
    const toD = new Date((toDate || '') + 'T12:00:00')
    const windowDays = chartMode === 'week' ? 7 : chartMode === 'month' ? 30 : null
    const fromD = windowDays ? new Date(toD) : null
    if (fromD && windowDays) fromD.setDate(fromD.getDate() - windowDays + 1)
    const windowStart = fromD ? fromD.toISOString().slice(0, 10) : null
    const filtered = windowStart
      ? dailyStats.filter((s) => (s.date || '') >= windowStart && (s.date || '') <= (toDate || ''))
      : dailyStats
    return filtered.map((s) => ({
      name: (s.date || '').slice(5) || '-',
      fullName: s.date,
      total_tokens: s.total_tokens ?? 0,
      prompt_tokens: s.prompt_tokens ?? 0,
      completion_tokens: s.completion_tokens ?? 0,
      call_count: s.call_count ?? 0,
    })).reverse()
  }, [dailyStats, chartMode, toDate])

  useEffect(() => {
    fetch('/api/settings/llm-audit/dates')
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.dates) && d.dates.length > 0) {
          setDates(d.dates)
          setFromDate(d.dates[d.dates.length - 1])
          setToDate(d.dates[0])
        }
      })
      .catch(() => {})
  }, [])

  const loadDailyStats = useCallback(() => {
    if (!fromDate || !toDate) return
    setDailyStats([])
    fetch(`/api/settings/llm-audit/daily-stats?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.stats)) setDailyStats(d.stats)
      })
      .catch(() => {})
  }, [fromDate, toDate])

  const loadRecords = useCallback(() => {
    if (!fromDate || !toDate) return
    setLoading(true)
    setError(null)
    loadDailyStats()
    const params = new URLSearchParams({
      from_date: fromDate,
      to_date: toDate,
      offset: String((page - 1) * PAGE_SIZE),
      limit: String(PAGE_SIZE),
    })
    fetch(`/api/settings/llm-audit/list?${params}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          setRecords(d.records || [])
          setTotal(d.total ?? 0)
        } else {
          setError(d.error || '加载失败')
          setRecords([])
          setTotal(0)
        }
      })
      .catch((e) => {
        setError(e?.message || '加载失败')
        setRecords([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [fromDate, toDate, page, loadDailyStats])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="LLM 审计" subtitle="所有 LLM 调用的输入与输出，按时间倒序。" />

      <div className="flex-1 overflow-y-auto p-6 max-w-4xl">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-medium text-white">全部记录</h2>
            {total > 0 && (
              <span className="text-sm text-muted">共 {total} 条</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowFilter((s) => !s)}
              className="text-sm text-muted hover:text-fg"
            >
              {showFilter ? '收起筛选' : '按日期筛选'}
            </button>
            {dates.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setFromDate(dates[dates.length - 1])
                  setToDate(dates[0])
                  setPage(1)
                }}
                className="px-2 py-1 text-sm border border-border rounded text-cyan-400 hover:bg-white/5"
              >
                全部
              </button>
            )}
          </div>
        </div>

        {showFilter && (
          <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-white/5 rounded-lg">
            <input
              type="date"
              value={fromDate}
              onChange={(e) => { setFromDate(e.target.value); setPage(1) }}
              className="bg-black/20 border border-border rounded px-3 py-1.5 text-sm text-white [color-scheme:dark]"
            />
            <span className="text-muted">～</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => { setToDate(e.target.value); setPage(1) }}
              className="bg-black/20 border border-border rounded px-3 py-1.5 text-sm text-white [color-scheme:dark]"
            />
          </div>
        )}

        {dailyStats.length > 0 && (
          <div className="mb-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <h3 className="text-sm font-medium text-amber-400/90">Token 消耗</h3>
              <div className="flex gap-1">
                {['day', 'week', 'month'].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setChartMode(m)}
                    className={`px-2 py-1 text-xs rounded ${chartMode === m ? 'bg-amber-500/30 text-amber-200' : 'text-muted hover:bg-white/5'}`}
                  >
                    {m === 'day' ? '全部' : m === 'week' ? '近7天' : '近30天'}
                  </button>
                ))}
              </div>
            </div>
            {chartData.length > 0 && (
              <div className="space-y-4 mb-4">
                {[
                  { key: 'prompt_tokens', label: '输入 tokens', color: '#22d3ee' },
                  { key: 'completion_tokens', label: '输出 tokens', color: '#34d399' },
                  { key: 'total_tokens', label: '合计 tokens', color: '#f59e0b' },
                ].map(({ key, label, color }) => (
                  <div key={key} className="h-[140px] w-full">
                    <p className="text-xs text-muted mb-1">{label}</p>
                    <ResponsiveContainer width="100%" height="90%">
                      <LineChart data={chartData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.08)" vertical={false} />
                        <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => v >= 1000 ? (v / 1000) + 'k' : v} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(30,41,59,0.95)', border: '1px solid #475569', borderRadius: 8 }}
                          labelStyle={{ color: '#94a3b8' }}
                          formatter={(val) => [(val ?? 0).toLocaleString(), label]}
                          labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName || payload?.[0]?.payload?.name || ''}
                        />
                        <Line type="monotone" dataKey={key} stroke={color} strokeWidth={2} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ))}
              </div>
            )}
            <h4 className="text-xs font-medium text-amber-400/70 mb-2">明细</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted border-b border-border/50">
                    <th className="py-1.5 pr-4">日期</th>
                    <th className="py-1.5 pr-4">调用次数</th>
                    <th className="py-1.5 pr-4">输入 tokens</th>
                    <th className="py-1.5 pr-4">输出 tokens</th>
                    <th className="py-1.5">合计 tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyStats.map((s) => (
                    <tr key={s.date} className="border-b border-border/30">
                      <td className="py-1.5 pr-4">{(s.date || '').slice(0, 10)}</td>
                      <td className="py-1.5 pr-4">{s.call_count ?? 0}</td>
                      <td className="py-1.5 pr-4">{s.prompt_tokens?.toLocaleString() ?? '-'}</td>
                      <td className="py-1.5 pr-4">{s.completion_tokens?.toLocaleString() ?? '-'}</td>
                      <td className="py-1.5">{s.total_tokens?.toLocaleString() ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {error && <p className="text-amber-400 text-sm mb-3">{error}</p>}
        {loading && <p className="text-muted text-sm mb-3">加载中…</p>}

        {!loading && (
          <>
            {records.length === 0 ? (
              <p className="text-muted text-sm py-8">暂无审计记录，进行对话后会在此显示。</p>
            ) : (
              <div className="space-y-4">
                {records.map((rec, i) => (
                  <RecordCard key={`${rec.ts}-${rec.direction}-${i}`} record={rec} />
                ))}
              </div>
            )}
            {total > 0 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                <span className="text-sm text-muted">第 {page} / {totalPages} 页</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="px-3 py-1.5 text-sm border border-border rounded-lg text-muted hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    上一页
                  </button>
                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="px-3 py-1.5 text-sm border border-border rounded-lg text-muted hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    下一页
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        <details className="mt-8 text-sm text-muted">
          <summary className="cursor-pointer hover:text-muted">存储与关闭审计</summary>
          <p className="mt-2">
            审计数据：<code className="bg-white/5 px-1 rounded">databases/llm_audit.db</code>。设置环境变量 <code className="bg-white/5 px-1 rounded">LLM_AUDIT_DISABLED=1</code> 可关闭写入。
          </p>
        </details>
      </div>
    </div>
  )
}
