/**
 * 多日预报展示（和风官网风格）
 * 官网：今天 02月27日 6° 0° | 周六 02月28日 4° 0° | ...
 */
import { getWeatherIcon } from './weatherUtils'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function formatForecastDate(dateStr, index) {
  if (!dateStr) return '-'
  const d = new Date(dateStr + 'T12:00:00')
  if (isNaN(d)) return dateStr
  const today = new Date()
  const isToday = d.toDateString() === today.toDateString()
  const md = dateStr.slice(5).replace('-', '月') + '日'
  if (isToday) return `今天 ${md}`
  const wd = WEEKDAYS[d.getDay()]
  return `${wd} ${md}`
}

export default function ForecastBlock({ daily }) {
  if (!Array.isArray(daily) || daily.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2">
      {daily.map((d, i) => (
        <div key={i} className="flex flex-col items-center gap-1 py-3 px-4 min-w-[100px] rounded-xl bg-white/5 border border-white/10">
          <span className="text-[#64748b] text-xs">{formatForecastDate(d.date ?? d.fxDate, i)}</span>
          <span className="text-2xl">{getWeatherIcon(d.icon_day)}</span>
          <span className="text-white text-sm font-medium">{d.text_day ?? '-'}</span>
          <span className="text-cyan-300 font-medium">{d.temp_max ?? '-'}° ~ {d.temp_min ?? '-'}°</span>
          {(d.sunrise || d.sunset) && (
            <span className="text-xs text-[#64748b]">日出{d.sunrise ?? '-'} 日落{d.sunset ?? '-'}</span>
          )}
          {d.uv_index != null && d.uv_index !== '' && (
            <span className="text-xs text-[#64748b]">紫外线 {d.uv_index}</span>
          )}
        </div>
      ))}
    </div>
  )
}
