/**
 * 解析 fetch Response：避免非 JSON 正文（如 500 HTML「Internal Server Error」）导致 JSON.parse 抛 SyntaxError。
 *
 * 时间：2026-03-13；理由：封面上传等接口失败时用户看到 Unexpected token 'I'；方法：先 text，再 try JSON；!ok 时拼可读错误。
 */

/**
 * FastAPI HTTPException / 校验错误里 detail 可能是 string | {msg}[] | object
 * @param {unknown} detail
 * @returns {string}
 */
export function normalizeFastApiDetail(detail) {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((x) => (x && typeof x === 'object' && x.msg != null ? String(x.msg) : JSON.stringify(x)))
      .filter(Boolean)
      .join('；')
  }
  if (typeof detail === 'object' && detail.msg != null) return String(detail.msg)
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

/**
 * @param {Response} res
 * @returns {Promise<object>} 解析后的 JSON 对象；无正文时 {}
 * @throws {Error} res.ok 为 false 或业务失败需由调用方再判断时，仍先保证不因 JSON 崩
 */
export async function parseApiResponseJson(res) {
  const text = await res.text()
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }
  if (!res.ok) {
    const fromJson = body && typeof body === 'object' ? normalizeFastApiDetail(body.detail ?? body.message) : ''
    const snippet = (text || '').trim().slice(0, 400)
    const fallback =
      snippet && !snippet.startsWith('<') ? snippet : `服务异常（HTTP ${res.status}）`
    const msg = fromJson || fallback
    throw new Error(msg || `请求失败（HTTP ${res.status}）`)
  }
  return body && typeof body === 'object' ? body : {}
}
