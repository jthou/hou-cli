/**
 * 分区概览：从 /api/system/disk 获取并展示各分区 total/used/free
 */
import { useState, useEffect } from 'react'

export default function DiskPartitionOverview() {
  const [partitions, setPartitions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 10000)
    fetch('/api/system/disk', { signal: ctrl.signal })
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return
        if (d.success && Array.isArray(d.data)) {
          setPartitions(
            d.data.map((p) => ({
              device: p.device,
              mountpoint: p.mountpoint,
              total_gb: (p.total || 0) / (1024 ** 3),
              used_gb: (p.used || 0) / (1024 ** 3),
              free_gb: (p.free || 0) / (1024 ** 3),
              percent: p.percent ?? 0,
            }))
          )
        } else {
          setPartitions([])
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.name === 'AbortError' ? '请求超时' : e.message || '加载失败')
      })
      .finally(() => {
        clearTimeout(t)
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ctrl.abort()
    }
  }, [])

  if (loading) {
    return (
      <div className="mb-4 p-4 border border-border rounded-xl bg-surface/40">
        <span className="text-xs text-muted">分区概览加载中…</span>
      </div>
    )
  }
  if (error) {
    return (
      <div className="mb-4 p-4 border border-border rounded-xl bg-surface/40">
        <span className="text-xs text-red-400">分区概览：{error}</span>
      </div>
    )
  }
  if (partitions.length === 0) {
    return null
  }

  const fmt = (n) => (typeof n === 'number' ? `${n.toFixed(1)} GB` : '—')

  return (
    <div className="mb-4 p-4 border border-border rounded-xl bg-surface/40">
      <h3 className="text-sm font-medium text-white mb-2">分区概览</h3>
      <p className="text-xs text-muted mb-2">
        各分区总容量、已用、可用（无需扫描即可查看）
      </p>
      <ul className="space-y-1.5">
        {partitions.map((p, i) => (
          <li key={i} className="flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono text-accent shrink-0">
              {fmt(p.total_gb)} 总 · {fmt(p.used_gb)} 已用 · {fmt(p.free_gb)} 可用
            </span>
            <span className="text-muted">
              {p.mountpoint || p.device}
              {typeof p.percent === 'number' && (
                <span className="ml-1">({p.percent.toFixed(0)}%)</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
