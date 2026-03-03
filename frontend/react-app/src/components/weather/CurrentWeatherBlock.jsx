/**
 * 实时天气展示（和风官网风格）
 * 参考 https://www.qweather.com/weather/beijing-101010100.html
 */
import { getWeatherIcon, formatUpdateTime } from './weatherUtils'

export default function CurrentWeatherBlock({ cur }) {
  if (!cur || typeof cur !== 'object') return null
  const windStr = [cur.windDir, cur.windScale != null ? cur.windScale + '级' : ''].filter(Boolean).join(' ')
  const items = [
    cur.feelsLike != null && { label: '体感', value: `${cur.feelsLike}°C` },
    cur.humidity != null && { label: '相对湿度', value: `${cur.humidity}%` },
    windStr && { label: '风向', value: windStr },
    cur.vis != null && { label: '能见度', value: `${cur.vis}km` },
    cur.precip != null && { label: '降水量', value: `${cur.precip} mm` },
    cur.pressure != null && { label: '大气压', value: `${cur.pressure} hPa` },
    cur.obsTime != null && { label: '观测', value: formatUpdateTime(cur.obsTime) },
  ].filter(Boolean)
  return (
    <div className="space-y-3">
      {/* 主标题：温度 + 天气现象（官网风格） */}
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-light text-white">
          {getWeatherIcon(cur.icon)} {cur.temp ?? '-'}°
        </span>
        <span className="text-lg text-muted">{cur.text ?? ''}</span>
      </div>
      {/* 详情网格（官网：体感、湿度、风向、能见度、降水、气压、观测） */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-muted shrink-0">{item.label}</span>
            <span className="text-white">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
