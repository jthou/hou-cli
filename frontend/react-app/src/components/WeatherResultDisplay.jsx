/**
 * 天气任务结果展示（和风 API：实时/预报/预警/空气质量）
 * 路由组件：按 query_type 分发到对应子组件
 */
import { normalizeWeatherResult, formatUpdateTime } from './weather/weatherUtils'
import CurrentWeatherBlock from './weather/CurrentWeatherBlock'
import ForecastBlock from './weather/ForecastBlock'
import WarningBlock from './weather/WarningBlock'
import AirQualityBlock from './weather/AirQualityBlock'

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

  // 预警（独立查询）
  if (r.query_type === 'warning') {
    return (
      <div className="space-y-3 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        <WarningBlock warningList={warningList} />
        {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
      </div>
    )
  }

  // 空气质量（独立查询）
  if (r.query_type === 'air_quality') {
    return (
      <div className="space-y-3 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        <AirQualityBlock airQuality={airQuality} standalone />
        {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
      </div>
    )
  }

  // 实时天气 或 多日预报（可附加预警、空气质量）
  return (
    <div className="space-y-4 text-[#94a3b8]">
      {result.summary && <p className="text-green-400 text-sm">{result.summary}</p>}
      {cur && (
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <CurrentWeatherBlock cur={cur} />
          {airQuality && (airQuality.aqi != null || airQuality.category) && (
            <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-sm">
              <span className="text-[#64748b]">AQI</span>
              <span className="text-white font-medium">{airQuality.aqi ?? '-'}</span>
              {airQuality.category && <span className="text-[#94a3b8]">{airQuality.category}</span>}
            </div>
          )}
        </div>
      )}
      {(daily && daily.length > 0) ? (
        <div>
          <div className="text-[#64748b] text-xs mb-1.5 font-medium">未来预报</div>
          <ForecastBlock daily={daily} />
        </div>
      ) : r.query_type === 'forecast' ? (
        <div className="mt-2">
          <div className="text-[#64748b] text-xs mb-1.5">预报</div>
          <p className="text-[#64748b] text-sm">暂无预报数据（若应为多日预报，请重新执行任务）</p>
        </div>
      ) : null}
      {Array.isArray(warningList) && warningList.length > 0 && (
        <div>
          <div className="text-[#64748b] text-xs mb-1.5 font-medium">灾害预警</div>
          <WarningBlock warningList={warningList} compact />
        </div>
      )}
      {airQuality && (airQuality.aqi != null || airQuality.pm2p5 != null) && (
        <div>
          <div className="text-[#64748b] text-xs mb-1.5 font-medium">空气质量</div>
          <AirQualityBlock airQuality={airQuality} />
        </div>
      )}
      {updateTime && <div className="text-[#64748b] text-xs">更新: {formatUpdateTime(updateTime)}</div>}
    </div>
  )
}
