import { useState, useEffect } from 'react'

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
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">系统提示词审计</h1>
        <p className="text-[#94a3b8] text-sm mt-1">按 agent 展示当前使用的系统提示，便于核对与审计。</p>
      </header>

      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {loading && (
          <div className="p-6 text-[#94a3b8]">加载中…</div>
        )}
        {error && (
          <div className="p-6 text-red-400">{error}</div>
        )}
        {!loading && !error && agents.length === 0 && (
          <div className="p-6 text-[#94a3b8]">暂无系统提示数据</div>
        )}
        {!loading && !error && agents.length > 0 && (
          <div className="flex-1 flex min-h-0 overflow-hidden">
            <div className="w-56 shrink-0 border-r border-border overflow-y-auto p-2">
              {agents.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setExpandedId(a.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    expandedId === a.id
                      ? 'bg-accent/20 text-accent border border-accent/40'
                      : 'text-[#94a3b8] hover:bg-white/5 hover:text-white border border-transparent'
                  }`}
                >
                  {a.name}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto p-6 min-w-0">
              {agents.map((a) => (
                <div
                  key={a.id}
                  className={expandedId === a.id ? '' : 'hidden'}
                >
                  <h2 className="text-lg font-semibold text-white mb-2">{a.name}</h2>
                  <p className="text-xs text-[#64748b] mb-3">agent id: {a.id}</p>
                  <pre className="whitespace-pre-wrap break-words text-sm text-[#94a3b8] bg-white/5 border border-border rounded-lg p-4 font-sans overflow-x-auto">
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
