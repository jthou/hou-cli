/**
 * 气象预警展示
 * @param {Object} props
 * @param {Array} props.warningList - 预警列表
 * @param {boolean} [props.compact] - 紧凑模式（作为 current/forecast 的附加块时）
 */
import { formatUpdateTime } from './weatherUtils'

export default function WarningBlock({ warningList, compact = false }) {
  if (!Array.isArray(warningList)) return null
  if (warningList.length === 0) return compact ? null : <p className="text-[#64748b]">暂无预警</p>
  const items = compact ? warningList.slice(0, 5) : warningList
  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      {items.map((w, i) => (
        <div key={i} className={compact ? 'p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-sm' : 'p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-sm'}>
          <span className="text-amber-400">{w.title ?? w.typeName ?? '预警'}</span>
          {w.text && (
            compact
              ? <span className="text-[#94a3b8] ml-2 truncate">{String(w.text).slice(0, 60)}{String(w.text).length > 60 ? '…' : ''}</span>
              : <p className="mt-1 text-[#94a3b8] whitespace-pre-wrap">{w.text}</p>
          )}
          {!compact && (w.pubTime || w.startTime || w.endTime) && (
            <div className="mt-1 text-xs text-[#64748b]">
              {w.pubTime && <span>发布 {formatUpdateTime(w.pubTime)}</span>}
              {w.startTime && w.endTime && ` · ${w.startTime} - ${w.endTime}`}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
