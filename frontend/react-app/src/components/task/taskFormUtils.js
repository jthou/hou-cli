/**
 * 任务表单通用工具，供 TaskManagement 弹窗与各任务页面共用
 */

/** 从 metadata_schema 生成默认 metadata */
export function getDefaultMetadata(schema) {
  if (!schema || typeof schema !== 'object') return {}
  const meta = {}
  for (const [key, spec] of Object.entries(schema)) {
    if (spec && typeof spec === 'object') {
      if (spec.default !== undefined) meta[key] = spec.default
      else if (Array.isArray(spec.enum) && spec.enum.length) meta[key] = spec.enum[0].value
      else if (spec.type === 'boolean') meta[key] = false
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
