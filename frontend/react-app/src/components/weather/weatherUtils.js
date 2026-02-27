/**
 * 天气展示共享工具（和风 API 结构）
 */

export const WEATHER_ICON_MAP = {
  '100': '☀️', '150': '☀️', '101': '⛅', '151': '⛅', '102': '🌤', '152': '🌤',
  '103': '🌤', '153': '🌤', '104': '☁️', '154': '☁️',
  '300': '🌦', '301': '⛈', '302': '⛈', '303': '⛈', '305': '🌧', '306': '🌧', '307': '🌧', '308': '🌧', '309': '🌧', '310': '🌧', '399': '🌧',
  '400': '🌨', '401': '❄️', '404': '❄️', '405': '❄️', '406': '❄️', '407': '❄️', '499': '❄️',
  '500': '🌫', '501': '🌫', '502': '🌫', '503': '💨', '504': '💨', '507': '🌪', '509': '🌫', '510': '🌫',
}

export function getWeatherIcon(code) {
  if (code == null) return ''
  const s = String(code)
  return WEATHER_ICON_MAP[s] || WEATHER_ICON_MAP[s.replace(/^0+/, '')] || '🌡'
}

export function formatUpdateTime(s) {
  if (!s) return ''
  return s.replace('T', ' ').replace('+08:00', '')
}

/**
 * 兼容两种结构：1) 后端封装 result.result 2) 和风原始 JSON
 */
export function normalizeWeatherResult(result) {
  if (!result) return null
  const r = result.result || result
  if (!r || typeof r !== 'object') return null
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
