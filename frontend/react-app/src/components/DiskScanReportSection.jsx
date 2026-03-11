/**
 * 全盘扫描报告：从 make disk-scan 生成的 docs/disk_report.json 读取并展示
 */
import { useState, useEffect } from 'react'
import DiskResultDisplay from './DiskResultDisplay'

export default function DiskScanReportSection() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 10000)
    fetch('/api/system/disk-scan-report', { signal: ctrl.signal })
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return
        if (d.success && d.data) setReport(d.data)
        else setReport(null)
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
        <span className="text-xs text-muted">全盘报告加载中…</span>
      </div>
    )
  }
  if (error || !report) {
    return (
      <div className="mb-4 p-4 border border-border rounded-xl bg-surface/40">
        <h3 className="text-sm font-medium text-white mb-2">全盘报告</h3>
        <p className="text-xs text-muted">
          {error ? `加载失败：${error}` : '暂无全盘报告。执行 make disk-scan 生成。'}
        </p>
      </div>
    )
  }

  return (
    <div className="mb-4 p-4 border border-border rounded-xl bg-surface/40">
      <h3 className="text-sm font-medium text-white mb-2">全盘报告 (make disk-scan)</h3>
      <DiskResultDisplay result={report} />
    </div>
  )
}
