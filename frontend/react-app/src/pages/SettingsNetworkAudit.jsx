import { useCallback, useEffect, useState } from 'react'
import { useExtensionReady } from '../hooks/useExtensionReady'

const STATUS_CLASS = {
  ok: 'bg-emerald-500/20 text-emerald-400',
  reachable: 'bg-amber-500/20 text-amber-400',
  fail: 'bg-red-500/20 text-red-400',
  skip: 'bg-slate-500/20 text-slate-400',
  pending: 'bg-slate-500/20 text-slate-400',
}
const STATUS_LABEL = {
  ok: '正常',
  reachable: '可达',
  fail: '失败',
  skip: '跳过',
  pending: '检测中',
}

function formatTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function SettingsNetworkAudit() {
  const [targets, setTargets] = useState([])
  const [results, setResults] = useState(null)
  const [createdAt, setCreatedAt] = useState(null)
  const [envInfo, setEnvInfo] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const extensionReady = useExtensionReady({ timeoutMs: 2500, initialNull: true })

  const loadEnv = useCallback(async () => {
    try {
      const res = await fetch('/api/network/audit/env')
      const json = await res.json()
      if (json.success) {
        setEnvInfo({
          local_ips: json.local_ips || [],
          proxy_settings: json.proxy_settings || {},
        })
      }
    } catch {
      setEnvInfo(null)
    }
  }, [])

  const loadTargets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/network/audit/targets')
      const json = await res.json()
      if (!json.success) throw new Error(json.error || '获取目标列表失败')
      setTargets(json.targets || [])
    } catch (e) {
      setError(e.message || String(e))
      setTargets([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTargets()
    loadEnv()
  }, [loadTargets, loadEnv])

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch('/api/network/audit/history')
      const json = await res.json()
      if (json.success && Array.isArray(json.history)) {
        setHistory(json.history)
      }
    } catch {
      setHistory([])
    }
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const runAudit = async () => {
    setRunning(true)
    setError(null)
    setResults(null)
    setCreatedAt(null)
    setEnvInfo(null)
    try {
      const res = await fetch('/api/network/audit/run', { method: 'POST' })
      const json = await res.json()
      if (!json.success) throw new Error(json.error || '检测失败')
      setResults(json.results || [])
      setCreatedAt(json.created_at || null)
      setEnvInfo(json.env || null)
      loadHistory()
    } catch (e) {
      setError(e.message || String(e))
      setResults([])
    } finally {
      setRunning(false)
    }
  }

  const selectHistory = (entry) => {
    setResults(entry.results || [])
    setCreatedAt(entry.created_at || null)
    setEnvInfo(entry.env || null)
  }

  const baseRows = results && results.length > 0
    ? results
    : targets.map((t) => ({
        id: t.id,
        name: t.name,
        url: t.url,
        status: t.configured ? null : 'skip',
        latency_ms: null,
        error: t.configured ? null : '未配置（缺少环境变量）',
      }))
  const extensionRow = {
    id: 'extension',
    name: 'Hou CLI 扩展',
    url: '—',
    status: extensionReady === true ? 'ok' : extensionReady === false ? 'fail' : 'pending',
    latency_ms: null,
    error: extensionReady === false ? '未安装或未启用，chrome://extensions 加载 extension 目录' : null,
  }
  const displayRows = [...baseRows, extensionRow]

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">网络状况审计</h1>
        <p className="text-muted text-sm mt-1">
          检测各外部依赖的连通性，用于排查网络、代理、SSL 等问题。
        </p>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between gap-4 mb-4">
          <button
            type="button"
            onClick={runAudit}
            disabled={loading || running}
            className="px-4 py-2 rounded-lg bg-accent text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? '检测中…' : '立即检测'}
          </button>
          <button
            type="button"
            onClick={loadTargets}
            disabled={loading}
            className="text-sm text-muted hover:text-fg"
          >
            刷新目标列表
          </button>
        </div>

        {createdAt && results?.length > 0 && (
          <p className="text-muted text-sm mb-3">
            检测时间：{formatTime(createdAt)}
          </p>
        )}

        {history.length > 1 && (
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="text-muted text-sm">历史记录：</span>
            {[...history].reverse().map((entry, i) => (
              <button
                key={`${entry.created_at || ''}-${i}`}
                type="button"
                onClick={() => selectHistory(entry)}
                className={`px-2 py-1 text-xs rounded border ${
                  entry.created_at === createdAt
                    ? 'border-accent text-accent bg-accent/10'
                    : 'border-border text-muted hover:bg-white/5'
                }`}
              >
                {formatTime(entry.created_at)}
              </button>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-4">
            {envInfo && (
              <>
            <div className="border border-border rounded-lg px-4 py-3 bg-white/[0.02]">
              <p className="text-muted text-xs mb-1">本机 IP</p>
              <p className="text-sm text-white font-mono">
                {envInfo?.local_ips?.length
                  ? envInfo.local_ips.join(', ')
                  : '—'}
              </p>
            </div>
            <div className="border border-border rounded-lg px-4 py-3 bg-white/[0.02]">
              <p className="text-muted text-xs mb-1">出口 IP</p>
              <p className="text-sm text-white font-mono">
                {envInfo?.outbound_ip ? (
                  <>
                    {envInfo.outbound_ip}
                    {envInfo?.outbound_location &&
                      (envInfo.outbound_location.country ||
                        envInfo.outbound_location.region) && (
                        <span className="text-muted font-sans ml-1">
                          (
                          {[
                            envInfo.outbound_location.country,
                            envInfo.outbound_location.region,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                          )
                        </span>
                      )}
                  </>
                ) : (
                  '—'
                )}
              </p>
            </div>
            <div className="border border-border rounded-lg px-4 py-3 bg-white/[0.02]">
              <p className="text-muted text-xs mb-1">代理设置</p>
              <p className="text-sm text-white break-all">
                {(() => {
                  const ps = envInfo?.proxy_settings
                  if (!ps) return '未配置'
                  const proxies = ps.proxies ?? (ps.source ? {} : ps)
                  const entries = Object.entries(proxies).filter(([k]) => !k.startsWith('_'))
                  if (entries.length === 0) {
                    return ps.source === 'system' ? '从系统设置中获取（无）' : '未配置'
                  }
                  const vals = entries.map(([k, v]) => `${k}=${v}`).join('; ')
                  return ps.source === 'system' ? `从系统设置中获取: ${vals}` : vals
                })()}
              </p>
            </div>
            <div className="border border-border rounded-lg px-4 py-3 bg-white/[0.02]">
                <p className="text-muted text-xs mb-1">网络状况</p>
                <p className="text-sm text-white">
                  {envInfo?.summary || '—'}
                </p>
              </div>
              </>
            )}
            <div className="border border-border rounded-lg px-4 py-3 bg-white/[0.02]">
              <p className="text-muted text-xs mb-1">Hou CLI 扩展</p>
              <p className="text-sm">
                {extensionReady === true ? (
                  <span className="text-emerald-400">已加载</span>
                ) : extensionReady === false ? (
                  <span className="text-amber-400">未检测到</span>
                ) : (
                  <span className="text-muted">检测中…</span>
                )}
              </p>
              <p className="text-[11px] text-muted mt-1">
                网页阅读、PDF 阅读、视频下载
              </p>
              {extensionReady === false && (
                <p className="text-[11px] text-amber-400/90 mt-1">
                  chrome://extensions 加载 extension 目录
                </p>
              )}
            </div>
          </div>

        {error && (
          <p className="text-amber-400 text-sm mb-3">{error}</p>
        )}

        {loading && !results && (
          <p className="text-muted text-sm">加载目标列表…</p>
        )}

        {!loading && displayRows.length > 0 && (
          <div className="border border-border rounded-lg overflow-x-auto w-full min-w-[52rem]">
            <table className="w-full text-sm table-fixed" style={{ minWidth: '52rem' }}>
              <colgroup>
                <col style={{ width: '14rem' }} />
                <col style={{ width: '22rem' }} />
                <col style={{ width: '6rem' }} />
                <col style={{ width: '6rem' }} />
                <col />
              </colgroup>
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  <th className="text-left px-4 py-3 font-medium text-white">名称</th>
                  <th className="text-left px-4 py-3 font-medium text-white">URL</th>
                  <th className="text-left px-4 py-3 font-medium text-white whitespace-nowrap">状态</th>
                  <th className="text-left px-4 py-3 font-medium text-white whitespace-nowrap">耗时</th>
                  <th className="text-left px-4 py-3 font-medium text-white">错误</th>
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row) => (
                  <tr key={row.id} className="border-b border-border/50 last:border-0">
                    <td className="px-4 py-3 text-white align-top">{row.name}</td>
                    <td className="px-4 py-3 text-muted text-xs align-top">
                      <code className="break-all">{row.url || '—'}</code>
                    </td>
                    <td className="px-4 py-3 align-top whitespace-nowrap">
                      {row.status != null ? (
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded ${
                            STATUS_CLASS[row.status] ?? 'bg-slate-500/20 text-slate-400'
                          }`}
                        >
                          {STATUS_LABEL[row.status] ?? row.status}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted align-top whitespace-nowrap">
                      {row.latency_ms != null ? `${row.latency_ms} ms` : '—'}
                    </td>
                    <td className="px-4 py-3 text-muted text-xs align-top break-words">
                      {row.error || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-6 text-sm text-muted">
          <p className="font-medium text-white/80 mb-2">说明</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>固定 URL（DuckDuckGo、出口 IP、LaTeX）无需配置即可检测</li>
            <li>配置型 URL 从环境变量读取，需授权的服务（DeepSeek、百炼、TheTurbo、和风、公众号）使用 .env 中的 API Key / 凭据发起请求</li>
            <li>出口 IP 优先用 ip.skk.moe，失败时尝试 api.ipify 等备用源</li>
            <li>使用 requests 发起请求，超时 6 秒</li>
            <li>「可达」表示网络连通、服务有响应，但返回 4xx（需认证或正确路径）</li>
            <li>「失败」表示超时、连接失败或 5xx</li>
            <li>最近 5 次检测结果保存在内存，进程重启后清空</li>
            <li>「Hou CLI 扩展」状态由前端检测（PING/PONG），用于网页阅读、PDF 阅读、视频下载等</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
