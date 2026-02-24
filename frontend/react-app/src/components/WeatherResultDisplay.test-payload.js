/**
 * 用真实任务结果 payload 验证：原始和风 JSON 是否被识别为可展示并正确归一化。
 * 不依赖 Jest，用 Node 直接跑：node frontend/react-app/src/components/WeatherResultDisplay.test-payload.js
 * 若断言失败则 exit 1，并打印原因。
 */

// 与 WeatherResultDisplay.jsx 中 normalizeWeatherResult 逻辑一致（纯 JS）
function normalizeWeatherResult(result) {
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

// 与 TaskManagement.jsx 中 TaskResultDisplay 的天气分支条件一致（code 兼容数字 200/字符串 "200"）
function wouldShowWeatherComponent(taskType, result) {
  const isSuccess = result?.status === 'success'
  const hasDaily = Array.isArray(result?.daily) || (result?.result && Array.isArray(result?.result?.daily))
  const isRawWeatherForecast = hasDaily && (String(result?.code) === '200' || result?.result?.code == null)
  if (!result || (!isSuccess && !isRawWeatherForecast)) return false
  if (taskType !== 'weather_query') return false
  const hasDisplayable = result.result != null || result.summary || (hasDaily && String(result?.code) === '200')
  return !!hasDisplayable
}

// 用户提供的真实任务结果：北京天气预报 02-24 02:17，原始和风 JSON
const RAW_QWEATHER_PAYLOAD = {
  code: '200',
  updateTime: '2026-02-24T02:15+08:00',
  fxLink: 'https://www.qweather.com/weather/beijing-101010100.html',
  daily: [
    { fxDate: '2026-02-24', sunrise: '06:57', sunset: '18:00', tempMax: '9', tempMin: '-2', iconDay: '100', textDay: '晴', iconNight: '151', textNight: '多云', windDirDay: '南风', windScaleDay: '1-3', humidity: '76', precip: '0.0', pressure: '1013', vis: '25', cloud: '0', uvIndex: '4' },
    { fxDate: '2026-02-25', sunrise: '06:55', sunset: '18:02', tempMax: '11', tempMin: '3', iconDay: '101', textDay: '多云', iconNight: '305', textNight: '小雨', windDirDay: '西南风', windScaleDay: '1-3', humidity: '50', precip: '0.0', pressure: '1015', vis: '24', cloud: '8', uvIndex: '1' },
  ],
  refer: { sources: ['QWeather'], license: ['QWeather Developers License'] },
}

function run() {
  let failed = false
  const taskType = 'weather_query'

  const showComponent = wouldShowWeatherComponent(taskType, RAW_QWEATHER_PAYLOAD)
  if (!showComponent) {
    console.error('FAIL: wouldShowWeatherComponent(taskType, rawPayload) 应为 true，实际为', showComponent)
    console.error('  isSuccess:', RAW_QWEATHER_PAYLOAD?.status === 'success')
    console.error('  code === "200":', RAW_QWEATHER_PAYLOAD?.code === '200', '(code type:', typeof RAW_QWEATHER_PAYLOAD?.code, ')')
    console.error('  Array.isArray(daily):', Array.isArray(RAW_QWEATHER_PAYLOAD?.daily))
    failed = true
  } else {
    console.log('OK: wouldShowWeatherComponent => true')
  }

  const normalized = normalizeWeatherResult(RAW_QWEATHER_PAYLOAD)
  if (!normalized || normalized.status !== 'success' || !normalized.result) {
    console.error('FAIL: normalizeWeatherResult(rawPayload) 应返回可展示对象，实际:', normalized ? 'status=' + normalized.status + ' result=' + !!normalized.result : 'null')
    failed = true
  } else {
    console.log('OK: normalizeWeatherResult => object with status=success and result')
  }

  if (normalized?.result?.daily) {
    if (normalized.result.daily.length < 1) {
      console.error('FAIL: normalized.result.daily 应有至少 1 条，实际 length:', normalized.result.daily.length)
      failed = true
    } else {
      console.log('OK: normalized.result.daily.length =', normalized.result.daily.length)
    }
  } else {
    console.error('FAIL: normalized.result.daily 缺失')
    failed = true
  }

  // code 为数字 200 时（后端 JSON 解析可能得到数字）也必须走组件
  const RAW_WITH_NUMBER_CODE = { ...RAW_QWEATHER_PAYLOAD, code: 200 }
  const showWithNumberCode = wouldShowWeatherComponent(taskType, RAW_WITH_NUMBER_CODE)
  if (!showWithNumberCode) {
    console.error('FAIL: code 为数字 200 时 wouldShowWeatherComponent 也应为 true，实际为', showWithNumberCode)
    failed = true
  } else {
    console.log('OK: code=200 (number) => wouldShowWeatherComponent => true')
  }
  const normNum = normalizeWeatherResult(RAW_WITH_NUMBER_CODE)
  if (!normNum?.result?.daily?.length) {
    console.error('FAIL: code=200 时 normalizeWeatherResult 也应返回含 daily 的对象')
    failed = true
  } else {
    console.log('OK: code=200 (number) => normalizeWeatherResult => daily.length =', normNum.result.daily.length)
  }

  if (failed) process.exit(1)
  console.log('All assertions passed.')
}

run()
