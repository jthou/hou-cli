/**
 * 多日预报展示（和风官网风格）
 * 官网：今天 02月27日 6° 0° | 周六 02月28日 4° 0° | ...
 */
import { getWeatherIcon } from './weatherUtils'
import TemperatureTrendChart from './TemperatureTrendChart'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function formatForecastDate(dateStr) {
  if (!dateStr) return { text: '-', isToday: false }
  const d = new Date(dateStr + 'T12:00:00')
  if (isNaN(d)) return { text: dateStr, isToday: false }
  const today = new Date()
  const isToday = d.toDateString() === today.toDateString()
  const md = dateStr.slice(5).replace('-', '月') + '日'
  const text = isToday ? `今天 ${md}` : `${WEEKDAYS[d.getDay()]} ${md}`
  return { text, isToday }
}

export default function ForecastBlock({ daily }) {
  if (!Array.isArray(daily) || daily.length === 0) return null
  return (
    <div className="min-w-0">
      <TemperatureTrendChart daily={daily} />
      <div className="flex gap-2 mt-3 overflow-x-auto overflow-y-hidden pb-2 flex-nowrap forecast-scroll min-w-0">
      {daily.map((d, i) => {
        const { text, isToday } = formatForecastDate(d.date ?? d.fxDate)
        return (
        <div key={i} className={`flex flex-col items-center gap-1 py-3 px-4 min-w-[100px] shrink-0 rounded-xl border ${isToday ? 'bg-accent/10 border-accent/50' : 'bg-white/5 border-white/10'}`}>
          <span className={`text-xs ${isToday ? 'text-accent font-medium' : 'text-muted'}`}>{text}</span>
          <span className="text-2xl">{getWeatherIcon(d.icon_day)}</span>
          <span className="text-white text-sm font-medium">{d.text_day ?? '-'}</span>
          <span className="text-cyan-300 font-medium">{d.temp_min ?? '-'}° ~ {d.temp_max ?? '-'}°</span>
          {(d.sunrise || d.sunset) && (
            <span className="text-xs text-muted">日出{d.sunrise ?? '-'} 日落{d.sunset ?? '-'}</span>
          )}
          {d.uv_index != null && d.uv_index !== '' && (
            <span className="text-xs text-muted">紫外线 {d.uv_index}</span>
          )}
        </div>
        )
      })}
      </div>
    </div>
  )
}
