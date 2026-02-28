/**
 * 任务表单通用工具，供 TaskManagement 弹窗与各任务页面共用
 */

/** 将天气任务旧 metadata（query_type）迁移为新格式（fetch_*） */
export function migrateWeatherMetadata(meta) {
  if (!meta || typeof meta !== 'object') return meta
  const qt = meta.query_type
  if (qt == null || String(qt).trim() === '') return meta
  const _tb = (v) => v === true || v === 'true' || v === '1' || v === 1
  const next = { ...meta }
  delete next.query_type
  delete next.include_warning
  delete next.include_air_quality
  const q = String(qt).trim()
  if (q === 'warning') {
    next.fetch_current = false
    next.fetch_forecast = false
    next.fetch_warning = true
    next.fetch_air_quality = false
  } else if (q === 'air_quality') {
    next.fetch_current = false
    next.fetch_forecast = false
    next.fetch_warning = false
    next.fetch_air_quality = true
  } else {
    next.fetch_current = q === 'current'
    next.fetch_forecast = q === 'forecast'
    next.fetch_warning = _tb(meta.include_warning ?? true)
    next.fetch_air_quality = _tb(meta.include_air_quality ?? true)
  }
  return next
}

/** 当天日/周/月分类标签（与后端格式一致：日、周、月），供网文抓取默认分类用 */
export function getDateCategoryStrings() {
  const d = new Date()
  const y = d.getFullYear()
  const m = d.getMonth() + 1
  const day = d.getDate()
  const 日 = `${y}年${m}月${day}日`
  const 月 = `${y}年${m}月`
  // ISO 周
  const d2 = new Date(d)
  d2.setHours(0, 0, 0, 0)
  d2.setDate(d2.getDate() + 4 - (d2.getDay() || 7))
  const isoYear = d2.getFullYear()
  const start = new Date(isoYear, 0, 1)
  const isoWeek = Math.ceil((((d2 - start) / 86400000) + 1) / 7)
  const 周 = `${isoYear}年第${isoWeek}周`
  return [日, 周, 月]
}

/** 从 metadata_schema 生成默认 metadata */
export function getDefaultMetadata(schema) {
  if (!schema || typeof schema !== 'object') return {}
  const meta = {}
  for (const [key, spec] of Object.entries(schema)) {
    if (spec && typeof spec === 'object') {
      if (spec.default !== undefined) meta[key] = spec.default
      else if (Array.isArray(spec.enum) && spec.enum.length) meta[key] = spec.enum[0].value
      else if (spec.type === 'boolean') meta[key] = false
      else if (spec.type === 'array') meta[key] = []
      else meta[key] = ''
    }
  }
  return meta
}

/** 从 API 错误响应中提取可读错误信息 */
export function getApiErrorMessage(data) {
  const d = data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) {
    return d.map((x) => x?.msg ?? (x?.loc && Array.isArray(x.loc) ? x.loc.join('.') : null) ?? JSON.stringify(x)).filter(Boolean).join('; ')
  }
  if (d && typeof d === 'object') return JSON.stringify(d)
  return data?.message ?? '未知错误'
}

/** 表单样式常量，供各页面保持一致 */
export const formStyles = {
  inputCls: 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none',
  labelCls: 'block text-sm font-medium text-[#94a3b8] mb-1',
  checkboxCls: 'flex items-center gap-3 text-[#94a3b8] cursor-pointer',
}
