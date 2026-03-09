/**
 * 磁盘空间分布展示（供首页等）
 * 展示：汇总、空间分布（带进度条）、可回收估算、清理建议（含分类与操作提示）
 */
export default function DiskUsageDisplay({ data }) {
  if (!data) return null

  const summary = data.summary || {}
  const largeDirs = data.large_directories || []
  const breakdown = data.directory_breakdown || []
  const systemData = data.system_data_breakdown || []
  const cleanup = data.cleanup_suggestions || []

  const total = summary.total_gb ?? 0
  const used = summary.used_gb ?? 0
  const free = summary.free_gb ?? 0
  const usedPct = summary.used_percent ?? 0
  const reclaimable = summary.reclaimable_gb ?? data.reclaimable_gb ?? 0

  const shortPath = (p) => p.replace(/^\/Users\/[^/]+/, '~')

  return (
    <div className="space-y-4 text-sm">
      {/* 汇总卡片 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg bg-white/5 px-3 py-2">
          <div className="text-xs text-muted">总容量</div>
          <div className="text-white font-semibold">{total.toLocaleString()} GB</div>
        </div>
        <div className="rounded-lg bg-white/5 px-3 py-2">
          <div className="text-xs text-muted">已用</div>
          <div className="text-amber-400 font-semibold">{used.toLocaleString()} GB</div>
          <div className="text-xs text-muted">{usedPct}%</div>
        </div>
        <div className="rounded-lg bg-white/5 px-3 py-2">
          <div className="text-xs text-muted">剩余</div>
          <div className="text-emerald-400 font-semibold">{free.toLocaleString()} GB</div>
        </div>
        {reclaimable > 0 && (
          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-2">
            <div className="text-xs text-emerald-400/90">可回收</div>
            <div className="text-emerald-400 font-semibold">~{reclaimable} GB</div>
            <div className="text-xs text-muted">见下方建议</div>
          </div>
        )}
      </div>

      {/* 使用率条 */}
      <div>
        <div className="flex justify-between text-xs text-muted mb-1">
          <span>使用率</span>
          <span>{usedPct}%</span>
        </div>
        <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              usedPct >= 95 ? 'bg-red-500' : usedPct >= 85 ? 'bg-amber-500' : usedPct >= 75 ? 'bg-amber-400' : 'bg-accent'
            }`}
            style={{ width: `${Math.min(usedPct, 100)}%` }}
          />
        </div>
      </div>

      {/* 系统数据细分（对应 macOS 储存空间里的「系统数据」） */}
      {systemData.length > 0 && (
        <div>
          <div className="text-xs font-medium text-amber-400/90 mb-2">
            系统数据细分（约 {summary.system_data_sum_gb ?? systemData.reduce((s, x) => s + x.size_gb, 0).toFixed(1)} GB）
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {systemData.map((x) => {
              const pct = x.pct_of_total ?? (total > 0 ? (100 * x.size_gb / total) : 0)
              return (
                <div key={x.path} className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 space-y-1">
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-fg text-xs font-medium truncate flex-1 min-w-0" title={x.path}>
                      {x.path}
                    </span>
                    <span className="text-amber-400 shrink-0 font-semibold">{x.size_gb} GB</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted">{x.category}</span>
                    <span className="text-muted">{pct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-amber-500/70"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 空间占用分布（合计 = 已用，含「其他」补齐） */}
      {breakdown.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted mb-2">
            空间占用分布（合计 = {used} GB）
          </div>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {breakdown.map((x) => {
              const pct = x.pct_of_total ?? (total > 0 ? (100 * x.size_gb / total) : 0)
              const isOther = x.category === "未统计"
              return (
                <div key={x.path} className={`rounded-lg border px-3 py-2 space-y-1 ${isOther ? 'bg-amber-500/10 border-amber-500/30' : 'bg-white/5 border-white/10'}`}>
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-fg text-xs font-medium truncate flex-1 min-w-0" title={x.path}>
                      {isOther ? x.path : shortPath(x.path)}
                    </span>
                    <span className={`shrink-0 font-semibold ${isOther ? 'text-amber-400' : 'text-fg'}`}>{x.size_gb} GB</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted">{x.category}</span>
                    <span className="text-muted">{pct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isOther ? 'bg-amber-500' : 'bg-amber-500/70'}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 人工清理建议 */}
      {cleanup.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted mb-2">人工清理建议</div>
          <div className="space-y-2">
            {cleanup.slice(0, 8).map((x) => (
              <div
                key={x.path}
                className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 space-y-1"
              >
                <div className="flex justify-between items-start gap-2">
                  <span className="text-fg text-xs font-medium truncate flex-1 min-w-0" title={x.path}>
                    {shortPath(x.path)}
                  </span>
                  <span className="text-emerald-400 shrink-0 font-medium">{x.size_gb} GB</span>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-white/10 text-muted">{x.category}</span>
                  <span className="text-xs text-muted">{x.suggestion}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
