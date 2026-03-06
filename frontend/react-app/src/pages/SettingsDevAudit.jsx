import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import PageHeader from '../components/PageHeader'

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-border bg-white/5 p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="text-2xl font-semibold text-white mt-1">{value ?? '—'}</p>
      {sub != null && <p className="text-xs text-muted mt-1">{sub}</p>}
    </div>
  )
}

export default function SettingsDevAudit() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch('/api/audit/report')
      .then((r) => r.json())
      .then((d) => {
        if (d.ok && d.data) {
          setReport(d.data)
        } else {
          setError(d.detail || '加载失败')
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="开发审计" subtitle="代码统计、开发历史、API 审计" />
        <div className="flex-1 overflow-y-auto p-6 flex items-center justify-center">
          <p className="text-muted">加载中…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="开发审计" subtitle="代码统计、开发历史、API 审计" />
        <div className="flex-1 overflow-y-auto p-6">
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4 text-amber-200">
            <p className="font-medium">无法加载审计报告</p>
            <p className="text-sm mt-1">{error}</p>
            <p className="text-xs text-muted mt-2">请先执行 make start 生成报告。</p>
          </div>
        </div>
      </div>
    )
  }

  const code = report?.code_stats || {}
  const dev = report?.dev_history || {}
  const api = report?.api_audit || {}
  const generatedAt = report?.generated_at

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="开发审计"
        subtitle={generatedAt ? `报告生成于 ${new Date(generatedAt).toLocaleString()}` : '代码统计、开发历史、API 审计'}
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {/* 摘要卡片 */}
        <section>
          <h2 className="text-lg font-medium text-white mb-4">摘要</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard label="总行数" value={code.total_lines?.toLocaleString()} />
            <StatCard label="总文件数" value={code.total_files?.toLocaleString()} />
            <StatCard label="总提交数" value={dev.total_commits?.toLocaleString()} />
            <StatCard label="后端路由数" value={api.backend_path_count} />
            <StatCard label="前端 fetch 数" value={api.frontend_fetch_count} />
          </div>
        </section>

        {/* 代码统计 - 按语言（饼图 + 柱状图） */}
        {code.by_language && Object.keys(code.by_language).length > 0 && (
          <section>
            <h2 className="text-lg font-medium text-white mb-4">代码统计（按语言）</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-lg border border-border bg-white/5 p-4 h-72">
                <p className="text-sm text-muted mb-2">行数占比</p>
                <ResponsiveContainer width="100%" height="90%">
                  <PieChart>
                    <Pie
                      data={Object.entries(code.by_language).map(([name, v]) => ({ name, value: v.lines || 0 }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {Object.keys(code.by_language).map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => v?.toLocaleString()} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-lg border border-border bg-white/5 p-4 h-72">
                <p className="text-sm text-muted mb-2">各语言行数</p>
                <ResponsiveContainer width="100%" height="90%">
                  <BarChart
                    data={Object.entries(code.by_language)
                      .map(([name, v]) => ({ name, lines: v.lines || 0 }))
                      .sort((a, b) => b.lines - a.lines)}
                    margin={{ top: 8, right: 8, left: 8, bottom: 8 }}
                  >
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)} />
                    <Tooltip formatter={(v) => v?.toLocaleString()} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                    <Bar dataKey="lines" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="rounded-lg border border-border overflow-hidden mt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/5">
                    <th className="text-left px-4 py-2 text-muted font-medium">语言</th>
                    <th className="text-right px-4 py-2 text-muted font-medium">文件数</th>
                    <th className="text-right px-4 py-2 text-muted font-medium">行数</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(code.by_language).map(([lang, v]) => (
                    <tr key={lang} className="border-t border-border">
                      <td className="px-4 py-2 text-white">{lang}</td>
                      <td className="px-4 py-2 text-right text-muted">{v.files}</td>
                      <td className="px-4 py-2 text-right text-muted">{v.lines?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* API 审计 */}
        {api.backend_routes && api.backend_routes.length > 0 && (
          <section>
            <h2 className="text-lg font-medium text-white mb-4">后端路由</h2>
            <div className="rounded-lg border border-border overflow-hidden max-h-64 overflow-y-auto">
              <pre className="p-4 text-xs text-muted font-mono whitespace-pre-wrap">
                {api.backend_routes.join('\n')}
              </pre>
            </div>
          </section>
        )}

        {api.unused_by_frontend && api.unused_by_frontend.length > 0 && (
          <section>
            <h2 className="text-lg font-medium text-amber-400 mb-4">后端有但前端未使用</h2>
            <ul className="list-disc list-inside text-sm text-muted space-y-1">
              {api.unused_by_frontend.slice(0, 20).map((p) => (
                <li key={p}>{p}</li>
              ))}
              {api.unused_by_frontend.length > 20 && (
                <li className="text-muted">… 共 {api.unused_by_frontend.length} 条</li>
              )}
            </ul>
          </section>
        )}

        {api.possibly_missing && api.possibly_missing.length > 0 && (
          <section>
            <h2 className="text-lg font-medium text-amber-400 mb-4">前端调用但可能未实现（需人工核对）</h2>
            <ul className="list-disc list-inside text-sm text-muted space-y-1">
              {api.possibly_missing.slice(0, 20).map((p) => (
                <li key={p}>{p}</li>
              ))}
              {api.possibly_missing.length > 20 && (
                <li className="text-muted">… 共 {api.possibly_missing.length} 条</li>
              )}
            </ul>
          </section>
        )}
      </div>
    </div>
  )
}
