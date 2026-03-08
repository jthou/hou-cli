/**
 * 调用摘要 API，统一错误处理
 * @param {string} content - 待摘要的正文
 * @param {{ model?: string }} [opts] - 可选参数
 * @returns {Promise<string>} 摘要文本
 */
export async function fetchSummarize(content, opts = {}) {
  const res = await fetch('/api/web-reader/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: content || '', model: opts.model }),
  })
  let json
  try {
    json = await res.json()
  } catch {
    throw new Error(res.ok ? '响应解析失败' : `请求失败 (${res.status})`)
  }
  if (!json.success) {
    throw new Error(json.error || '摘要生成失败')
  }
  return json.summary ?? ''
}
