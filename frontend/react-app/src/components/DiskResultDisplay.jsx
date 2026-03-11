/**
 * 磁盘扫描结果展示卡片：分区概览、占用排行、可清理项
 */
export default function DiskResultDisplay({ result }) {
  const res = result?.result || result
  if (!res) return null

  const totalUsed = res.total_used_gb ?? res.total_used ?? 0
  const scannedTotal = res.scanned_total_gb ?? res.scanned_total ?? 0
  const userOnly = res.user_only
  const largeItems = res.large_items || []
  const allItems = res.items || largeItems
  const partitions = res.partitions || []

  const fmt = (n) => (typeof n === 'number' ? `${n.toFixed(1)} GB` : String(n ?? ''))
  const total = scannedTotal > 0 ? scannedTotal : (allItems.reduce((s, i) => s + (i.size_gb || 0), 0) || 1)

  // 可清理项关键词（与脚本一致）
  const CLEANUP_KEYWORDS = [
    ['Caches', '缓存'], ['Cache', '缓存'], ['Logs', '日志'], ['Log', '日志'],
    ['Downloads', '下载'], ['node_modules', '依赖'], ['.Trash', '废纸篓'], ['Trash', '废纸篓'],
    ['tmp', '临时'], ['temp', '临时'], ['Xcode', 'Xcode'], ['Developer', '开发'],
    ['Docker', 'Docker'], ['npm', 'npm'], ['yarn', 'yarn'], ['pip', 'pip'], ['conda', 'conda'],
    ['Homebrew', 'brew'],
  ]
  const getCleanupTag = (path) => {
    for (const [kw, tag] of CLEANUP_KEYWORDS) {
      if (path.includes(kw)) return tag
    }
    return null
  }

  // 路径简短显示：取最后两段或最后一段
  const shortPath = (path) => {
    if (!path) return ''
    const parts = path.replace(/\/$/, '').split('/').filter(Boolean)
    if (parts.length <= 2) return path
    return '…/' + parts.slice(-2).join('/')
  }

  const topItems = allItems.slice(0, 12)
  const cleanupItems = allItems
    .map((i) => ({ ...i, tag: getCleanupTag(i.path) }))
    .filter((i) => i.tag && (i.size_gb || 0) >= 0.1)
    .sort((a, b) => (b.size_gb || 0) - (a.size_gb || 0))
    .slice(0, 6)

  const mainPartition = partitions.find((p) =>
    (p.mountpoint || '').includes('Data') || (p.mountpoint || '') === '/'
  ) || partitions[0]
  const usedPercent = mainPartition?.percent ?? (totalUsed > 0 && totalUsed < 1000 ? (totalUsed / 10) : 0)

  return (
    <div className="space-y-4 text-sm">
      {/* 1. 摘要条：全盘已用 + 进度条 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-white">
            全盘已用 {fmt(totalUsed)}
            {typeof scannedTotal === 'number' && scannedTotal > 0 && (
              <span className="ml-2 text-muted font-normal">· 统计 {fmt(scannedTotal)}</span>
            )}
          </span>
          {userOnly && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
              仅用户目录
            </span>
          )}
        </div>
        {typeof usedPercent === 'number' && usedPercent > 0 && (
          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-accent/80 transition-all"
              style={{ width: `${Math.min(100, usedPercent)}%` }}
            />
          </div>
        )}
      </div>

      {/* 2. 分区概览（若有） */}
      {partitions.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
          {partitions.map((p, i) => (
            <span key={i}>
              {p.mountpoint || p.device}: {fmt(p.used_gb)} / {fmt(p.total_gb)}
              {typeof p.percent === 'number' && ` (${p.percent.toFixed(0)}%)`}
            </span>
          ))}
        </div>
      )}

      {/* 3. Top 占用 */}
      {topItems.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-muted mb-2">占用排行</h4>
          <ul className="space-y-2 max-h-64 overflow-y-auto">
            {topItems.map((item, i) => {
              const size = item.size_gb ?? 0
              const pct = total > 0 ? (100 * size / total) : 0
              const tag = getCleanupTag(item.path)
              return (
                <li key={i} className="flex items-center gap-2 group">
                  <span className="shrink-0 w-12 text-right font-mono text-accent text-xs">
                    {size.toFixed(1)} GB
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="truncate text-muted text-xs group-hover:text-white/80 transition-colors"
                        title={item.path}
                      >
                        {shortPath(item.path)}
                      </span>
                      {tag && (
                        <span className="shrink-0 text-[10px] px-1 rounded bg-cyan-500/20 text-cyan-400">
                          {tag}
                        </span>
                      )}
                    </div>
                    {pct >= 1 && (
                      <div className="mt-0.5 h-0.5 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-white/20"
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* 4. 可清理项（若有） */}
      {cleanupItems.length > 0 && (
        <div className="pt-2 border-t border-border/60">
          <h4 className="text-xs font-medium text-muted mb-2">可清理 ({cleanupItems.length} 项)</h4>
          <ul className="space-y-1.5">
            {cleanupItems.map((item, i) => (
              <li key={i} className="flex items-baseline gap-2 text-xs">
                <span className="shrink-0 w-10 text-right font-mono text-cyan-400">
                  {(item.size_gb || 0).toFixed(1)} GB
                </span>
                <span className="truncate text-muted" title={item.path}>
                  {shortPath(item.path)}
                </span>
                <span className="shrink-0 text-[10px] text-cyan-400/80">{item.tag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {userOnly && (
        <p className="text-[11px] text-muted pt-1">
          全盘细分需在终端执行 <code className="px-1 rounded bg-white/10">make disk-scan</code>
        </p>
      )}
    </div>
  )
}
