/**
 * 天气任务结果展示（和风 API：实时/预报/预警/空气质量，多选组合）
 * 统一布局：按数据存在性渲染各块，compact/standalone 由块数量决定
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

  const hasCur = cur && (cur.text != null || cur.temp != null)
  const hasDaily = daily && daily.length > 0
  const hasAirQuality = airQuality && (airQuality.aqi != null || airQuality.category || airQuality.pm2p5 != null)
  const hasWarningData = Array.isArray(warningList)
  const multiBlock = hasCur || hasDaily || hasAirQuality
  const airStandalone = !hasCur && !hasDaily && (!hasWarningData || warningList.length === 0)

  return (
    <div className="space-y-4 text-muted">
      {result.summary && <p className="text-green-400 text-sm">{result.summary}</p>}
      {hasCur && (
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <CurrentWeatherBlock cur={cur} />
          {hasAirQuality && (airQuality.aqi != null || airQuality.category) && (
            <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-sm">
              <span className="text-muted">AQI</span>
              <span className="text-white font-medium">{airQuality.aqi ?? '-'}</span>
              {airQuality.category && <span className="text-muted">{airQuality.category}</span>}
            </div>
          )}
        </div>
      )}
      {hasDaily ? (
        <div>
          <div className="text-muted text-xs mb-1.5 font-medium">未来预报</div>
          <ForecastBlock daily={daily} />
        </div>
      ) : Array.isArray(daily) && daily.length === 0 ? (
        <div>
          <div className="text-muted text-xs mb-1.5 font-medium">预报</div>
          <p className="text-muted text-sm">暂无预报数据（若应为多日预报，请重新执行任务）</p>
        </div>
      ) : null}
      {hasWarningData && (
        <div className="rounded-xl border border-amber-600 bg-amber-600/20 overflow-hidden">
          {multiBlock && (
            <div className="px-3 py-2 text-white text-sm font-semibold border-b border-amber-400 bg-amber-600">
              灾害预警
            </div>
          )}
          <div className="p-3">
            <WarningBlock warningList={warningList || []} compact={multiBlock} />
          </div>
        </div>
      )}
      {hasAirQuality && (
        <div>
          {multiBlock && <div className="text-muted text-xs mb-1.5 font-medium">空气质量</div>}
          <AirQualityBlock airQuality={airQuality} standalone={airStandalone} />
        </div>
      )}
      {updateTime && <div className="text-muted text-xs">更新: {formatUpdateTime(updateTime)}</div>}
    </div>
  )
}
