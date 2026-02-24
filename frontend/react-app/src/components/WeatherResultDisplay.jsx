/**
 * 天气任务结果展示（和风 API：实时/预报/预警/空气质量）
 * 供任务管理详情弹层按 task.result 渲染，与 backend task_handlers 的 result 结构一致。
 */

// 和风天气 icon 代码 -> emoji（部分常用）
const WEATHER_ICON_MAP = {
  '100': '☀️', '150': '☀️', '101': '⛅', '151': '⛅', '102': '🌤', '152': '🌤',
  '103': '🌤', '153': '🌤', '104': '☁️', '154': '☁️',
  '300': '🌦', '301': '⛈', '302': '⛈', '303': '⛈', '305': '🌧', '306': '🌧', '307': '🌧', '308': '🌧', '309': '🌧', '310': '🌧', '399': '🌧',
  '400': '🌨', '401': '❄️', '404': '❄️', '405': '❄️', '406': '❄️', '407': '❄️', '499': '❄️',
  '500': '🌫', '501': '🌫', '502': '🌫', '503': '💨', '504': '💨', '507': '🌪', '509': '🌫', '510': '🌫',
}

function getWeatherIcon(code) {
  if (code == null) return ''
  const s = String(code)
  return WEATHER_ICON_MAP[s] || WEATHER_ICON_MAP[s.replace(/^0+/, '')] || '🌡'
}

function formatUpdateTime(s) {
  if (!s) return ''
  return s.replace('T', ' ').replace('+08:00', '')
}

// 兼容两种结构：1) 后端封装 result.result（含 query_type, daily[].date 等） 2) 和风原始 JSON（code, daily[].fxDate 等）
function normalizeWeatherResult(result) {
  if (!result) return null
  const r = result.result || result
  if (!r || typeof r !== 'object') return null
  // 和风原始预报：有 code、daily 且 daily[0] 含 fxDate
  const rawDaily = r.daily
  const isRawForecast = String(r.code) === '200' && Array.isArray(rawDaily) && rawDaily.length > 0 && (rawDaily[0].fxDate != null || rawDaily[0].date != null)
  if (isRawForecast && !r.query_type) {
    return {
      status: 'success',
      summary: result.summary || '天气预报',
      result: {
        query_type: 'forecast',
        location: result.location,
        update_time: r.updateTime || r.update_time,
        daily: rawDaily.map((d) => ({
          date: d.date ?? d.fxDate,
          temp_max: d.temp_max ?? d.tempMax,
          temp_min: d.temp_min ?? d.tempMin,
          text_day: d.text_day ?? d.textDay,
          text_night: d.text_night ?? d.textNight,
          icon_day: d.icon_day ?? d.iconDay,
          icon_night: d.icon_night ?? d.iconNight,
          wind_dir_day: d.wind_dir_day ?? d.windDirDay,
          wind_scale_day: d.wind_scale_day ?? d.windScaleDay,
          sunrise: d.sunrise,
          sunset: d.sunset,
          humidity: d.humidity,
          uv_index: d.uvIndex,
        })),
        warning: r.warning,
        air_quality: r.air_quality,
      },
    }
  }
  if (result.status === 'success' && r) return result
  return null
}

export default function WeatherResultDisplay({ result }) {
  const normalized = normalizeWeatherResult(result)
  if (!normalized || normalized.status !== 'success' || !normalized.result) {
    return null
  }

  const r = normalized.result
  const cur = r.current_weather || r.now
  const daily = r.daily
  const updateTime = r.update_time || r.updateTime
  const warningList = r.warning
  const airQuality = r.air_quality

  if (r.query_type === 'warning') {
    return (
      <div className="space-y-3 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {Array.isArray(warningList) && warningList.length > 0 ? (
          <div className="space-y-2">
            {warningList.map((w, i) => (
              <div key={i} className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-sm">
                <div className="font-medium text-amber-400">{w.title ?? w.typeName ?? '预警'}</div>
                {w.text && <p className="mt-1 text-[#94a3b8] whitespace-pre-wrap">{w.text}</p>}
                {(w.pubTime || w.startTime || w.endTime) && (
                  <div className="mt-1 text-xs text-[#64748b]">
                    {w.pubTime && <span>发布 {formatUpdateTime(w.pubTime)}</span>}
                    {w.startTime && w.endTime && ` · ${w.startTime} - ${w.endTime}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[#64748b]">暂无预警</p>
        )}
        {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
      </div>
    )
  }

  if (r.query_type === 'air_quality') {
    const aq = airQuality && typeof airQuality === 'object' ? airQuality : {}
    return (
      <div className="space-y-3 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          {aq.aqi != null && <><span className="text-[#64748b]">AQI</span><span className="text-white font-medium">{aq.aqi}</span></>}
          {aq.category != null && <><span className="text-[#64748b]">等级</span><span>{aq.category}</span></>}
          {aq.pm2p5 != null && <><span className="text-[#64748b]">PM2.5</span><span>{aq.pm2p5} µg/m³</span></>}
          {aq.pm10 != null && <><span className="text-[#64748b]">PM10</span><span>{aq.pm10} µg/m³</span></>}
          {aq.primary != null && <><span className="text-[#64748b]">主要污染物</span><span>{aq.primary}</span></>}
        </div>
        {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
      </div>
    )
  }

  return (
    <div className="space-y-3 text-[#94a3b8]">
      {result.summary && <p className="text-green-400">{result.summary}</p>}
      {cur && typeof cur === 'object' && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <div className="col-span-2 text-white font-medium">
            {getWeatherIcon(cur.icon)} {cur.text ?? ''} {cur.temp ?? ''}°C
          </div>
          {cur.feelsLike != null && <><span className="text-[#64748b]">体感</span><span>{cur.feelsLike}°C</span></>}
          {cur.windDir != null && <><span className="text-[#64748b]">风向</span><span>{cur.windDir} {cur.windScale != null ? cur.windScale + '级' : ''}</span></>}
          {cur.humidity != null && <><span className="text-[#64748b]">湿度</span><span>{cur.humidity}%</span></>}
          {cur.precip != null && <><span className="text-[#64748b]">降水</span><span>{cur.precip} mm</span></>}
          {cur.pressure != null && <><span className="text-[#64748b]">气压</span><span>{cur.pressure} hPa</span></>}
          {cur.obsTime != null && <><span className="text-[#64748b]">观测</span><span className="text-xs">{formatUpdateTime(cur.obsTime)}</span></>}
        </div>
      )}
      {(daily && daily.length > 0) ? (
        <div className="mt-2">
          <div className="text-[#64748b] text-xs mb-1.5">预报</div>
          <div className="space-y-2">
            {daily.map((d, i) => (
              <div key={i} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 px-3 bg-white/5 rounded-lg text-sm">
                <span className="text-[#64748b] w-24">{d.date ?? '-'}</span>
                <span className="text-white">
                  {getWeatherIcon(d.icon_day)} {d.text_day ?? '-'} / {getWeatherIcon(d.icon_night)} {d.text_night ?? '-'}
                </span>
                <span className="text-cyan-300">{d.temp_min ?? '-'} ~ {d.temp_max ?? '-'}°C</span>
                {(d.sunrise || d.sunset) && (
                  <span className="text-xs text-[#64748b]">日出 {d.sunrise ?? '-'} 日落 {d.sunset ?? '-'}</span>
                )}
                {d.wind_dir_day && <span className="text-xs text-[#64748b]">{d.wind_dir_day} {d.wind_scale_day ?? ''}</span>}
              </div>
            ))}
          </div>
        </div>
      ) : r.query_type === 'forecast' ? (
        <div className="mt-2">
          <div className="text-[#64748b] text-xs mb-1.5">预报</div>
          <p className="text-[#64748b] text-sm">暂无预报数据（若应为多日预报，请重新执行任务）</p>
        </div>
      ) : null}
      {Array.isArray(warningList) && warningList.length > 0 && (
        <div className="mt-2">
          <div className="text-[#64748b] text-xs mb-1.5">预警</div>
          <div className="space-y-1.5">
            {warningList.slice(0, 5).map((w, i) => (
              <div key={i} className="p-2 bg-amber-500/10 border border-amber-500/20 rounded text-sm">
                <span className="text-amber-400">{w.title ?? w.typeName ?? '预警'}</span>
                {w.text && <span className="text-[#94a3b8] ml-2 truncate">{String(w.text).slice(0, 60)}{String(w.text).length > 60 ? '…' : ''}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      {airQuality && typeof airQuality === 'object' && (airQuality.aqi != null || airQuality.pm2p5 != null) && (
        <div className="mt-2">
          <div className="text-[#64748b] text-xs mb-1.5">空气质量</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {airQuality.aqi != null && <span>AQI <span className="text-white">{airQuality.aqi}</span></span>}
            {airQuality.category != null && <span>{airQuality.category}</span>}
            {airQuality.pm2p5 != null && <span>PM2.5 {airQuality.pm2p5}</span>}
            {airQuality.pm10 != null && <span>PM10 {airQuality.pm10}</span>}
          </div>
        </div>
      )}
      {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
    </div>
  )
}
