/**
 * 任务列表/卡片共用常量与工具，供 TaskCard、TaskManagement 等复用。
 */
export const STATUS_MAP = {
  queued: { text: '待执行', cls: 'bg-cyan-500/15 text-cyan-400' },
  running: { text: '运行中', cls: 'bg-cyan-500/20 text-cyan-300' },
  completed: { text: '已完成', cls: 'bg-green-500/15 text-green-400' },
  failed: { text: '失败', cls: 'bg-red-500/15 text-red-400' },
  cancelled: { text: '已取消', cls: 'bg-slate-500/20 text-slate-400' },
}

export function formatDateTime(s) {
  if (!s) return '-'
  const d = new Date(s)
  return isNaN(d) ? '-' : d.toLocaleString('zh-CN')
}
