/**
 * 气象预警展示（醒目样式，便于快速识别灾害预警）
 * @param {Object} props
 * @param {Array} props.warningList - 预警列表
 * @param {boolean} [props.compact] - 紧凑模式（作为 current/forecast 的附加块时）
 */
import { formatUpdateTime } from './weatherUtils'

export default function WarningBlock({ warningList, compact = false }) {
  if (!Array.isArray(warningList)) return null
  if (warningList.length === 0) {
    return compact
      ? null
      : <p className="text-amber-500 text-sm font-medium">暂无预警</p>
  }
  const items = compact ? warningList.slice(0, 5) : warningList
  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      {items.map((w, i) => (
        <div
          key={i}
          className={
            compact
              ? 'p-3 bg-slate-900/90 border border-amber-400 rounded-lg text-sm shadow-sm text-amber-50'
              : 'p-4 bg-slate-900 border-2 border-amber-400 rounded-xl text-base shadow-md text-amber-50'
          }
        >
          <div className="font-semibold text-[15px]">
            {w.title ?? w.typeName ?? '预警'}
          </div>
          {w.text && (
            compact ? (
              <p className="mt-1.5 text-sm leading-relaxed line-clamp-2 text-amber-50/90">
                {String(w.text).slice(0, 80)}{String(w.text).length > 80 ? '…' : ''}
              </p>
            ) : (
              <p className="mt-2 text-[15px] leading-relaxed whitespace-pre-wrap font-medium text-amber-50">
                {w.text}
              </p>
            )
          )}
          {!compact && (w.pubTime || w.startTime || w.endTime) && (
            <div className="mt-2 text-xs text-amber-100/80">
              {w.pubTime && <span>发布 {formatUpdateTime(w.pubTime)}</span>}
              {w.startTime && w.endTime && ` · ${w.startTime} - ${w.endTime}`}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
