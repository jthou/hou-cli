import { useState, useEffect, useCallback } from 'react'

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

function RecordCard({ record }) {
  const { ts, direction, model, payload, audit_id, session_id, ...rest } = record
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
        {audit_id && <span className="text-xs text-muted">audit_id: {audit_id}</span>}
        {session_id && <span className="text-xs text-violet-400">session: {session_id.slice(0, 8)}…</span>}
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

  const loadRecords = useCallback(() => {
    if (!fromDate || !toDate) return
    setLoading(true)
    setError(null)
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
  }, [fromDate, toDate, page])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">LLM 审计</h1>
        <p className="text-muted text-sm mt-1">所有 LLM 调用的输入与输出，按时间倒序。</p>
      </header>

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
