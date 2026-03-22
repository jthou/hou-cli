/**
 * 从 Markdown 正文中提取首个 ATX 标题文本（# … ## …）。
 * 时间：2026-03-13；理由：写作助手「同步到公众号」预填标题需与正文首行标题一致；方法：逐行匹配 ^#{1,6}\\s+。
 *
 * @param {string} md
 * @param {number} [maxLen=64] - 预填截断上限（微信标题 API 另有约束，提交侧再处理）
 * @returns {string}
 */
export function extractFirstMarkdownAtxTitle(md, maxLen = 64) {
  if (!md || typeof md !== 'string') return ''
  const lines = md.split(/\r?\n/)
  for (const line of lines) {
    const m = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*$/)
    if (m) {
      const t = (m[2] || '').trim()
      if (!t) continue
      return maxLen > 0 && t.length > maxLen ? t.slice(0, maxLen) : t
    }
  }
  return ''
}
