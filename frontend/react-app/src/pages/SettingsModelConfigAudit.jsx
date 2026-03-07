import { useState, useEffect } from 'react'
import PageHeader from '../components/PageHeader'

const API_KEY_LABELS = {
  DEEPSEEK_API_KEY: 'DeepSeek API Key',
  BAILIAN_API_KEY: '百炼平台 API Key',
  DASHSCOPE_API_KEY: 'DASHScope API Key',
  TURBOGATEWAY_API_KEY: 'TheTurbo.ai 网关 API Key',
  OPENAI_API_KEY: 'OpenAI API Key',
  ANTHROPIC_API_KEY: 'Anthropic API Key',
  GOOGLE_API_KEY: 'Google API Key',
}

function getModelForProbe(item) {
  const v = item.value
  if (v != null && typeof v === 'string' && v.trim()) return v.trim()
  const m = (item.display || '').match(/（默认:\s*([^）]+)）/)
  return m ? m[1].trim() : null
}

export default function SettingsModelConfigAudit() {
  const [data, setData] = useState(null)
  const [availability, setAvailability] = useState({ models: [], unique_models: [] })
  const [modelStats, setModelStats] = useState([])
  const [statsDays, setStatsDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryKey, setRetryKey] = useState(0)
  const [singleProbe, setSingleProbe] = useState({})
  const [probing, setProbing] = useState(false)
  const [probeResults, setProbeResults] = useState([])

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      fetch('/api/settings/model-config-audit').then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      }),
      fetch('/api/settings/model-availability-audit/models').then((r) => r.json()),
      fetch(`/api/settings/model-stats?days=${statsDays}`).then((r) => r.json()),
    ])
      .then(([configRes, availRes, statsRes]) => {
        if (configRes.success) {
          setData(configRes)
        } else {
          setError(configRes.error || '加载失败')
          setData(null)
        }
        if (statsRes.success && Array.isArray(statsRes.stats)) {
          setModelStats(statsRes.stats)
        } else {
          setModelStats([])
        }
        if (availRes.success) {
          let byProvider = availRes.models_by_provider || {}
          if (Object.keys(byProvider).length === 0 && (availRes.models || []).length > 0) {
            byProvider = (availRes.models || []).reduce((acc, m) => {
              const p = m.provider || 'deepseek'
              if (!acc[p]) acc[p] = []
              acc[p].push(m)
              return acc
            }, {})
          }
          setAvailability({
            models: availRes.models || [],
            unique_models: availRes.unique_models || [],
            models_by_provider: byProvider,
            provider_labels: availRes.provider_labels || {},
            bailian_category_order: availRes.bailian_category_order || [],
          })
        }
      })
      .catch((e) => {
        const msg = e?.message || ''
        const friendly =
          msg.includes('Failed to fetch') || msg.includes('NetworkError')
            ? '无法连接后端，请确认后端服务已启动（默认端口 8081）'
            : msg || '加载失败'
        setError(friendly)
        setData(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [retryKey, statsDays])

  const handleProbeOne = (model) => {
    if (!model) return
    setSingleProbe((prev) => ({ ...prev, [model]: { loading: true } }))
    fetch('/api/settings/model-availability-audit/probe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ models: [model] }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.results?.[0]) {
          const r = d.results[0]
          setSingleProbe((prev) => ({
            ...prev,
            [model]: {
              loading: false,
              ok: r.ok,
              response: r.response,
              error: r.error,
              duration_ms: r.duration_ms,
            },
          }))
        } else {
          setSingleProbe((prev) => ({
            ...prev,
            [model]: { loading: false, ok: false, error: d.error || '探测失败' },
          }))
        }
      })
      .catch((e) => {
        setSingleProbe((prev) => ({
          ...prev,
          [model]: { loading: false, ok: false, error: e?.message || '探测失败' },
        }))
      })
  }

  const handleProbeAll = () => {
    setProbing(true)
    setProbeResults([])
    setSingleProbe({})
    fetch('/api/settings/model-availability-audit/probe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.success) setProbeResults(d.results || [])
        else setError(d.error || '探测失败')
      })
      .catch((e) => setError(e?.message || '探测失败'))
      .finally(() => setProbing(false))
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="模型审计"
        subtitle="配置信息、Agent 映射、模型可用性探测（API Key 仅显示是否已设置，不暴露原文）"
      />

      <div className="flex-1 overflow-y-auto p-6 max-w-4xl min-w-0">
        {loading && <div className="text-muted">加载中…</div>}
        {error && (
          <div className="flex flex-col gap-2">
            <span className="text-red-400">{error}</span>
            <button
              onClick={() => setRetryKey((k) => k + 1)}
              className="self-start px-3 py-1.5 rounded bg-accent/20 text-accent text-sm hover:bg-accent/30"
            >
              重试
            </button>
          </div>
        )}
        {!loading && !error && data && (
          <div className="space-y-8">
            <section>
              <div className="flex items-center justify-between gap-4 mb-3">
                <h2 className="text-base font-medium text-white">模型使用统计与排名</h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted">统计范围</span>
                  <select
                    value={statsDays}
                    onChange={(e) => setStatsDays(Number(e.target.value))}
                    className="text-xs rounded border border-border bg-white/5 px-2 py-1.5 text-fg focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value={7}>最近 7 天</option>
                    <option value={30}>最近 30 天</option>
                    <option value={90}>最近 90 天</option>
                  </select>
                </div>
              </div>
              <p className="text-xs text-muted mb-3">
                响应时间来自 LLM 审计；接受次数为写文章场景点击「接受修改」的次数。综合得分 = 接受次数×10 + 速度得分（响应越快越高）。
              </p>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <table className="w-full text-sm table-fixed">
                  <colgroup>
                    <col style={{ width: '60px' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '14%' }} />
                    <col style={{ width: '14%' }} />
                    <col style={{ width: '14%' }} />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">排名</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">模型</th>
                      <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">调用次数</th>
                      <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">平均响应</th>
                      <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">接受次数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelStats.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-6 text-center text-muted text-sm">
                          暂无统计（需有 LLM 调用记录）
                        </td>
                      </tr>
                    ) : (
                      modelStats.map((s, i) => (
                        <tr key={s.model} className="border-b border-border/50 last:border-0">
                          <td className="px-4 py-2.5 text-center text-muted font-medium tabular-nums">
                            {i + 1}
                          </td>
                          <td className="px-4 py-2.5 align-middle font-mono text-cyan-400/90 text-xs">
                            {s.model}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-right text-muted tabular-nums">
                            {s.call_count ?? '—'}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-right text-muted tabular-nums">
                            {s.avg_response_ms != null ? `${Math.round(s.avg_response_ms)} ms` : '—'}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-right tabular-nums">
                            <span className={s.accepted_count > 0 ? 'text-emerald-400' : 'text-muted'}>
                              {s.accepted_count ?? 0}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">API Key 状态</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <table className="w-full text-sm table-fixed">
                  <colgroup>
                    <col style={{ width: '45%' }} />
                    <col />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">变量名</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.api_keys || {}).map(([key, info]) => (
                      <tr key={key} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5 align-middle">
                          <code className="text-cyan-400/90">{key}</code>
                          <span className="text-muted ml-2 text-xs">
                            {API_KEY_LABELS[key] || key}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 align-middle">
                          <span
                            className={
                              info.set ? 'text-emerald-400' : 'text-muted'
                            }
                          >
                            {info.display}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">用户可选模型（模型选择下拉）</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <table className="w-full text-sm table-fixed">
                  <colgroup>
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '80px' }} />
                    <col />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">配置项</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">当前值</th>
                      <th className="px-4 py-2.5 text-center text-muted font-medium align-middle w-20">操作</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.model_selection || []).map((item) => {
                      const model = item.value || getModelForProbe(item)
                      const pr = model ? singleProbe[model] : null
                      return (
                        <tr key={item.key} className="border-b border-border/50 last:border-0">
                          <td className="px-4 py-2.5 align-middle">
                            <code className="text-cyan-400/90">{item.key}</code>
                            <span className="text-muted ml-2 text-xs">{item.label}</span>
                          </td>
                          <td className="px-4 py-2.5 align-middle text-emerald-400/90 font-mono text-xs">
                            {item.value || '（未设置）'}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-center">
                            {model ? (
                              <button
                                onClick={() => handleProbeOne(model)}
                                disabled={pr?.loading}
                                className="px-2 py-1 rounded bg-accent/20 text-accent text-xs hover:bg-accent/30 disabled:opacity-50"
                              >
                                {pr?.loading ? '测试中…' : '测试'}
                              </button>
                            ) : (
                              <span className="text-muted text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-xs break-words overflow-hidden">
                            {pr?.loading && <span className="text-muted">请求中…</span>}
                            {pr && !pr.loading && pr.ok && (
                              <span className="text-emerald-400/90 break-words" title={pr.response}>
                                {pr.response || '（空）'}
                              </span>
                            )}
                            {pr && !pr.loading && !pr.ok && (
                              <span className="text-red-400/90 break-all" title={pr.error}>
                                {pr.error}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-muted mt-2">
                CHAT_MODEL、CODE_MODEL、REASONING_MODEL 对应写文章、工作助手等页面的模型选择下拉。
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">Agent → 模型映射</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <table className="w-full text-sm table-fixed">
                  <colgroup>
                    <col style={{ width: '22%' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '22%' }} />
                    <col style={{ width: '80px' }} />
                    <col />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">Agent / 组件</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">使用的模型</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">说明</th>
                      <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">操作</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.agent_model_mapping || []).map((item) => {
                      const firstModel = (item.models_resolved || '')
                        .split(',')[0]
                        ?.trim()
                      const pr = firstModel ? singleProbe[firstModel] : null
                      return (
                        <tr key={item.agent_id} className="border-b border-border/50 last:border-0">
                          <td className="px-4 py-2.5 align-middle">
                            <code className="text-cyan-400/90">{item.agent_id}</code>
                            <span className="text-muted ml-2 text-xs">{item.name}</span>
                          </td>
                          <td className="px-4 py-2.5 align-middle text-emerald-400/90 font-mono text-xs">
                            {item.models_resolved}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-muted text-xs">{item.description}</td>
                          <td className="px-4 py-2.5 align-middle text-center">
                            {firstModel ? (
                              <button
                                onClick={() => handleProbeOne(firstModel)}
                                disabled={pr?.loading}
                                className="px-2 py-1 rounded bg-accent/20 text-accent text-xs hover:bg-accent/30 disabled:opacity-50"
                                title={`测试首个模型: ${firstModel}`}
                              >
                                {pr?.loading ? '…' : '测试'}
                              </button>
                            ) : (
                              <span className="text-muted text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-xs break-words overflow-hidden">
                            {pr?.loading && <span className="text-muted">请求中…</span>}
                            {pr && !pr.loading && pr.ok && (
                              <span className="text-emerald-400/90 break-words" title={pr.response}>
                                {pr.response || '（空）'}
                              </span>
                            )}
                            {pr && !pr.loading && !pr.ok && (
                              <span className="text-red-400/90 break-all" title={pr.error}>
                                {pr.error}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">模型配置</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <table className="w-full text-sm table-fixed">
                  <colgroup>
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '80px' }} />
                    <col />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">配置项</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">当前值</th>
                      <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">操作</th>
                      <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.model_config || []).map((item) => {
                      const isModelKey = item.key?.endsWith('_MODEL')
                      const model = isModelKey ? (item.value || getModelForProbe(item)) : null
                      const pr = model ? singleProbe[model] : null
                      return (
                        <tr key={item.key} className="border-b border-border/50 last:border-0">
                          <td className="px-4 py-2.5 align-middle">
                            <code className="text-cyan-400/90">{item.key}</code>
                            <span className="text-muted ml-2 text-xs">{item.label}</span>
                          </td>
                          <td className="px-4 py-2.5 align-middle text-muted font-mono text-xs break-all">
                            {item.display}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-center">
                            {model ? (
                              <button
                                onClick={() => handleProbeOne(model)}
                                disabled={pr?.loading}
                                className="px-2 py-1 rounded bg-accent/20 text-accent text-xs hover:bg-accent/30 disabled:opacity-50"
                              >
                                {pr?.loading ? '测试中…' : '测试'}
                              </button>
                            ) : (
                              <span className="text-muted text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 align-middle text-xs break-words overflow-hidden">
                            {pr?.loading && <span className="text-muted">请求中…</span>}
                            {pr && !pr.loading && pr.ok && (
                              <span className="text-emerald-400/90 break-words" title={pr.response}>
                                {pr.response || '（空）'}
                              </span>
                            )}
                            {pr && !pr.loading && !pr.ok && (
                              <span className="text-red-400/90 break-all" title={pr.error}>
                                {pr.error}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-medium text-white">模型可用性（.env 解析）</h2>
                <button
                  onClick={handleProbeAll}
                  disabled={probing || availability.unique_models.length === 0}
                  className="px-4 py-2 rounded-lg bg-accent/20 text-accent hover:bg-accent/30 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                  {probing ? '检测中…' : '检测全部'}
                </button>
              </div>
              <p className="text-xs text-muted mb-3">
                共 {availability.unique_models.length} 个模型（来自 .env 配置行与注释）
              </p>

              {probeResults.length > 0 && (() => {
                const byProvider = {}
                probeResults.forEach((r) => {
                  const p = r.provider || 'other'
                  if (!byProvider[p]) byProvider[p] = []
                  byProvider[p].push(r)
                })
                const providerOrder = ['deepseek', 'bailian', 'theturbogateway', 'other']
                const labels = availability.provider_labels || {}
                return (
                  <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto mb-4 min-w-[720px]">
                    <h3 className="text-sm font-medium text-white/90 mb-2 px-4 pt-3">探测结果</h3>
                    {providerOrder.concat(Object.keys(byProvider).filter((k) => !providerOrder.includes(k))).map((provider) => {
                      const rows = byProvider[provider] || []
                      if (rows.length === 0) return null
                      return (
                        <div key={provider} className="border-t border-border first:border-t-0">
                          <div className="px-4 py-2 bg-white/[0.03] text-xs font-medium text-muted">
                            {labels[provider] || provider}
                          </div>
                          <table className="w-full text-sm table-fixed min-w-[720px]">
                            <colgroup>
                              <col style={{ width: '28%' }} />
                              <col style={{ width: '80px' }} />
                              <col style={{ width: '80px' }} />
                              <col />
                              <col style={{ width: '80px' }} />
                            </colgroup>
                            <thead>
                              <tr className="border-b border-border">
                                <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">模型</th>
                                <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">状态</th>
                                <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">耗时</th>
                                <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈 / 错误</th>
                                <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">操作</th>
                              </tr>
                            </thead>
                            <tbody>
                              {rows.map((r) => {
                                const pr = singleProbe[r.model]
                                const display =
                                  pr && !pr.loading
                                    ? pr.ok ? pr.response : pr.error
                                    : r.ok ? r.response : r.error
                                const duration = pr?.duration_ms ?? r.duration_ms
                                return (
                                  <tr key={r.model} className="border-b border-border/50 last:border-0">
                                    <td className="px-4 py-2.5 align-middle font-mono text-cyan-400/90 text-xs">
                                      {r.model}
                                    </td>
                                    <td className="px-4 py-2.5 align-middle text-center">
                                      <span
                                        className={
                                          (pr && !pr.loading ? pr.ok : r.ok)
                                            ? 'text-emerald-400'
                                            : 'text-red-400'
                                        }
                                      >
                                        {pr?.loading ? '测试中…' : r.ok ? '可用' : '不可用'}
                                      </span>
                                    </td>
                                    <td className="px-4 py-2.5 align-middle text-right text-xs text-muted tabular-nums">
                                      {pr?.loading ? '—' : duration != null ? `${duration} ms` : '—'}
                                    </td>
                                    <td className="px-4 py-2.5 align-middle text-xs break-words overflow-hidden">
                                      {pr?.loading ? '—' : (display || '—')}
                                    </td>
                                    <td className="px-4 py-2.5 align-middle text-center">
                                      <button
                                        onClick={() => handleProbeOne(r.model)}
                                        disabled={pr?.loading}
                                        className="px-2 py-1 rounded bg-accent/20 text-accent text-xs hover:bg-accent/30 disabled:opacity-50"
                                      >
                                        {pr?.loading ? '…' : '测试'}
                                      </button>
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      )
                    })}
                  </div>
                )
              })()}

              <div className="rounded-lg border border-border bg-white/[0.02] overflow-x-auto min-w-[720px]">
                <h3 className="text-sm font-medium text-white/90 mb-2 px-4 pt-3">解析详情（按提供商）</h3>
                {['deepseek', 'bailian', 'theturbogateway', 'other'].concat(
                  Object.keys(availability.models_by_provider || {}).filter(
                    (k) => !['deepseek', 'bailian', 'theturbogateway', 'other'].includes(k)
                  )
                ).map((provider) => {
                  const models = (availability.models_by_provider || {})[provider] || []
                  if (models.length === 0) return null
                  const label = (availability.provider_labels || {})[provider] || provider
                  const categoryOrder = availability.bailian_category_order || []
                  const byCategory =
                    provider === 'bailian'
                      ? models.reduce((acc, m) => {
                          const cat = m.category || '其他百炼平台'
                          if (!acc[cat]) acc[cat] = []
                          acc[cat].push(m)
                          return acc
                        }, {})
                      : null

                  const renderModelRow = (m) => {
                    const pr = singleProbe[m.model]
                    const keysDisplay = (m.keys && m.keys.length)
                      ? <span className="text-cyan-400/90 font-mono text-xs">{m.keys.join(', ')}</span>
                      : m.key
                        ? <code className="text-cyan-400/90">{m.key}</code>
                        : null
                    return (
                      <tr key={`${provider}-${m.model}`} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5 align-middle font-mono text-emerald-400/90 text-xs">
                          {m.model}
                        </td>
                        <td className="px-4 py-2.5 align-middle">
                          {keysDisplay ?? <span className="text-muted">—</span>}
                        </td>
                        <td className="px-4 py-2.5 align-middle text-center text-muted text-xs">
                          {m.source || '—'}
                        </td>
                        <td className="px-4 py-2.5 align-middle text-center">
                          <button
                            onClick={() => handleProbeOne(m.model)}
                            disabled={pr?.loading}
                            className="px-2 py-1 rounded bg-accent/20 text-accent text-xs hover:bg-accent/30 disabled:opacity-50"
                          >
                            {pr?.loading ? '测试中…' : '测试'}
                          </button>
                        </td>
                        <td className="px-4 py-2.5 align-middle text-right text-xs text-muted tabular-nums">
                          {pr?.loading ? '—' : pr?.duration_ms != null ? `${pr.duration_ms} ms` : '—'}
                        </td>
                        <td className="px-4 py-2.5 align-middle text-xs break-words overflow-hidden">
                          {pr?.loading && <span className="text-muted">请求中…</span>}
                          {pr && !pr.loading && pr.ok && (
                            <span className="text-emerald-400/90 break-words" title={pr.response}>
                              {pr.response || '（空）'}
                            </span>
                          )}
                          {pr && !pr.loading && !pr.ok && (
                            <span className="text-red-400/90 break-all" title={pr.error}>
                              {pr.error}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  }

                  return (
                    <div key={provider} className="border-t border-border first:border-t-0">
                      <div className="px-4 py-2 bg-white/[0.03] text-xs font-medium text-muted">
                        {label}
                      </div>
                      {provider === 'bailian' && byCategory ? (
                        (categoryOrder.length ? categoryOrder : Object.keys(byCategory)).map((cat) => {
                          const catModels = byCategory[cat] || []
                          if (catModels.length === 0) return null
                          return (
                            <div key={cat} className="border-t border-border/50">
                              <div className="px-4 py-1.5 bg-white/[0.02] text-[11px] text-muted/90">
                                {cat}
                              </div>
                              <table className="w-full text-sm table-fixed">
                                <colgroup>
                                  <col style={{ width: '28%' }} />
                                  <col style={{ width: '22%' }} />
                                  <col style={{ width: '10%' }} />
                                  <col style={{ width: '80px' }} />
                                  <col style={{ width: '80px' }} />
                                  <col />
                                </colgroup>
                                <thead>
                                  <tr className="border-b border-border">
                                    <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">模型</th>
                                    <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">配置项</th>
                                    <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">来源</th>
                                    <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">操作</th>
                                    <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">耗时</th>
                                    <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈</th>
                                  </tr>
                                </thead>
                                <tbody>{catModels.map(renderModelRow)}</tbody>
                              </table>
                            </div>
                          )
                        })
                      ) : (
                        <table className="w-full text-sm table-fixed">
                          <colgroup>
                            <col style={{ width: '28%' }} />
                            <col style={{ width: '22%' }} />
                            <col style={{ width: '10%' }} />
                            <col style={{ width: '80px' }} />
                            <col style={{ width: '80px' }} />
                            <col />
                          </colgroup>
                          <thead>
                            <tr className="border-b border-border">
                              <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">模型</th>
                              <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">配置项</th>
                              <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">来源</th>
                              <th className="px-4 py-2.5 text-center text-muted font-medium align-middle">操作</th>
                              <th className="px-4 py-2.5 text-right text-muted font-medium align-middle tabular-nums">耗时</th>
                              <th className="px-4 py-2.5 text-left text-muted font-medium align-middle">反馈</th>
                            </tr>
                          </thead>
                          <tbody>{models.map(renderModelRow)}</tbody>
                        </table>
                      )}
                    </div>
                  )
                })}
              </div>
            </section>

            <p className="text-xs text-muted">
              配置来源：<code className="bg-white/5 px-1 rounded">.env</code> 或{' '}
              <code className="bg-white/5 px-1 rounded">env.example</code>。
              修改配置后需重启后端服务生效。探测发送 "hello" 请求，超时 15 秒。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
