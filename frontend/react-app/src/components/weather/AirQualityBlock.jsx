/**
 * 空气质量展示（和风官网风格）
 * 官网：良 39 | PM2.5 60 | PM10 33 | O3 0.7 | CO 3 | SO2 26 | NO2
 */
export default function AirQualityBlock({ airQuality, standalone = false }) {
  const aq = airQuality && typeof airQuality === 'object' ? airQuality : {}
  const pm25 = aq.pm2p5 ?? aq.pm25
  if (aq.aqi == null && pm25 == null && aq.pm10 == null && aq.category == null && aq.primary == null) return null
  const items = [
    aq.category && { label: null, value: aq.category, highlight: true },
    aq.aqi != null && { label: null, value: aq.aqi, highlight: true },
    pm25 != null && { label: 'PM2.5', value: pm25 },
    aq.pm10 != null && { label: 'PM10', value: aq.pm10 },
    aq.o3 != null && { label: 'O3', value: aq.o3 },
    aq.co != null && { label: 'CO', value: aq.co },
    aq.so2 != null && { label: 'SO2', value: aq.so2 },
    aq.no2 != null && { label: 'NO2', value: aq.no2 },
    aq.primary != null && { label: '主要污染物', value: aq.primary },
  ].filter(Boolean)
  if (standalone) {
    return (
      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          {items.map((item, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {item.label && <span className="text-muted text-sm">{item.label}</span>}
              <span className={item.highlight ? 'text-fg font-medium' : 'text-muted'}>{item.value}</span>
            </span>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
      {items.map((item, i) => (
        <span key={i} className={item.highlight ? 'text-fg font-medium' : 'text-muted'}>
          {item.label ? `${item.label} ${item.value}` : item.value}
        </span>
      ))}
    </div>
  )
}
