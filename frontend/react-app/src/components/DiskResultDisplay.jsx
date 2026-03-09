/**
 * 磁盘扫描结果展示：显示 total_used、large_items（≥1GB）
 */
export default function DiskResultDisplay({ result }) {
  const res = result?.result || result
  if (!res) return null

  const totalUsed = res.total_used_gb ?? res.total_used
  const scannedTotal = res.scanned_total_gb ?? res.scanned_total
  const userOnly = res.user_only
  const largeItems = res.large_items || []

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2 text-muted">
        <span>全盘已用: {typeof totalUsed === 'number' ? `${totalUsed.toFixed(1)} GB` : totalUsed}</span>
        {typeof scannedTotal === 'number' && (
          <span>· 本次统计: {scannedTotal.toFixed(1)} GB</span>
        )}
        {userOnly && <span>· 仅用户主目录</span>}
      </div>
      {largeItems.length > 0 ? (
        <div>
          <h4 className="text-xs font-medium text-muted mb-2">≥1 GB 目录 ({largeItems.length} 个)</h4>
          <ul className="space-y-1.5 max-h-80 overflow-y-auto">
            {largeItems.map((item, i) => (
              <li key={i} className="flex items-baseline gap-2 text-xs">
                <span className="shrink-0 w-16 text-right font-mono text-accent">
                  {typeof item.size_gb === 'number' ? `${item.size_gb.toFixed(1)} GB` : item.size_gb}
                </span>
                <span className="truncate text-muted" title={item.path}>
                  {item.path}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-muted text-xs">无 ≥1 GB 的目录</p>
      )}
    </div>
  )
}
