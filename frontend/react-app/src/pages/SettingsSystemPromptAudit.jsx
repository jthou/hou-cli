import { useState, useEffect } from 'react'
import PageHeader from '../components/PageHeader'

export default function SettingsSystemPromptAudit() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch('/api/settings/system-prompt-audit/prompts')
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.agents)) {
          setAgents(d.agents)
          if (d.agents.length > 0) setExpandedId((prev) => prev || d.agents[0].id)
        } else {
          setError(d.error || '加载失败')
          setAgents([])
        }
      })
      .catch((e) => {
        setError(e?.message || '加载失败')
        setAgents([])
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="提示词审计" subtitle="按 agent 展示当前使用的系统提示，便于核对与审计。" />

      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {loading && (
          <div className="p-6 text-muted">加载中…</div>
        )}
        {error && (
          <div className="p-6 text-red-400">{error}</div>
        )}
        {!loading && !error && agents.length === 0 && (
          <div className="p-6 text-muted">暂无系统提示数据</div>
        )}
        {!loading && !error && agents.length > 0 && (
          <div className="flex-1 flex min-h-0 overflow-hidden">
            <div className="w-56 shrink-0 border-r border-border overflow-y-auto p-2">
              {['agent', 'orchestrator'].map((cat) => {
                const items = agents.filter((a) => (a.category || 'agent') === cat)
                if (items.length === 0) return null
                const label = cat === 'agent' ? 'Agent' : '编排 / 选择器'
                return (
                  <div key={cat} className="mb-3">
                    <div className="px-2 py-1.5 text-xs font-medium text-muted/80 uppercase tracking-wider">
                      {label}
                    </div>
                    {items.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => setExpandedId(a.id)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors mt-0.5 ${
                          expandedId === a.id
                            ? 'bg-accent/20 text-accent border border-accent/40'
                            : 'text-muted hover:bg-white/5 hover:text-fg border border-transparent'
                        }`}
                      >
                        {a.name}
                      </button>
                    ))}
                  </div>
                )
              })}
            </div>
            <div className="flex-1 overflow-y-auto p-6 min-w-0">
              {agents.map((a) => (
                <div
                  key={a.id}
                  className={expandedId === a.id ? '' : 'hidden'}
                >
                  <h2 className="text-lg font-semibold text-white mb-2">{a.name}</h2>
                  <p className="text-xs text-muted mb-3">agent id: {a.id}</p>
                  {Array.isArray(a.tools) && a.tools.length > 0 && (
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-muted mb-2">配备工具</h3>
                      <div className="flex flex-wrap gap-2">
                        {a.tools.map((t) => (
                          <span
                            key={t}
                            className="px-2.5 py-1 text-xs rounded-md bg-accent/15 text-accent border border-accent/30"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <h3 className="text-sm font-medium text-muted mb-2">系统提示</h3>
                  <pre className="whitespace-pre-wrap break-words text-sm text-muted bg-white/5 border border-border rounded-lg p-4 font-sans overflow-x-auto">
                    {a.prompt || ''}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
