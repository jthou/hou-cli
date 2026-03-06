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

export default function SettingsModelConfigAudit() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch('/api/settings/model-config-audit')
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          setData(d)
        } else {
          setError(d.error || '加载失败')
          setData(null)
        }
      })
      .catch((e) => {
        setError(e?.message || '加载失败')
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="模型审计"
        subtitle="显示 .env 中配置的模型信息及各 Agent 使用的模型（API Key 仅显示是否已设置，不暴露原文）"
      />

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        {loading && <div className="text-muted">加载中…</div>}
        {error && <div className="text-red-400">{error}</div>}
        {!loading && !error && data && (
          <div className="space-y-8">
            <section>
              <h2 className="text-base font-medium text-white mb-3">API Key 状态</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-2.5 text-muted font-medium">变量名</th>
                      <th className="px-4 py-2.5 text-muted font-medium">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.api_keys || {}).map(([key, info]) => (
                      <tr key={key} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5">
                          <code className="text-cyan-400/90">{key}</code>
                          <span className="text-muted ml-2 text-xs">
                            {API_KEY_LABELS[key] || key}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span
                            className={
                              info.set
                                ? 'text-emerald-400'
                                : 'text-muted'
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
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-2.5 text-muted font-medium">配置项</th>
                      <th className="px-4 py-2.5 text-muted font-medium">当前值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.model_selection || []).map((item) => (
                      <tr key={item.key} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5">
                          <code className="text-cyan-400/90">{item.key}</code>
                          <span className="text-muted ml-2 text-xs">{item.label}</span>
                        </td>
                        <td className="px-4 py-2.5 text-emerald-400/90 font-mono text-xs">
                          {item.value || '（未设置）'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-muted mt-2">
                CHAT_MODEL、CODE_MODEL、REASONING_MODEL 对应写文章、工作助手等页面的模型选择下拉。
              </p>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">Agent → 模型映射</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-2.5 text-muted font-medium">Agent / 组件</th>
                      <th className="px-4 py-2.5 text-muted font-medium">使用的模型</th>
                      <th className="px-4 py-2.5 text-muted font-medium">说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.agent_model_mapping || []).map((item) => (
                      <tr key={item.agent_id} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5">
                          <code className="text-cyan-400/90">{item.agent_id}</code>
                          <span className="text-muted ml-2 text-xs">{item.name}</span>
                        </td>
                        <td className="px-4 py-2.5 text-emerald-400/90 font-mono text-xs">
                          {item.models_resolved}
                        </td>
                        <td className="px-4 py-2.5 text-muted text-xs">{item.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-base font-medium text-white mb-3">模型配置</h2>
              <div className="rounded-lg border border-border bg-white/[0.02] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-2.5 text-muted font-medium">配置项</th>
                      <th className="px-4 py-2.5 text-muted font-medium">当前值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.model_config || []).map((item) => (
                      <tr key={item.key} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5">
                          <code className="text-cyan-400/90">{item.key}</code>
                          <span className="text-muted ml-2 text-xs">{item.label}</span>
                        </td>
                        <td className="px-4 py-2.5 text-muted font-mono text-xs break-all">
                          {item.display}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <p className="text-xs text-muted">
              配置来源：<code className="bg-white/5 px-1 rounded">.env</code>。
              修改配置后需重启后端服务生效。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
