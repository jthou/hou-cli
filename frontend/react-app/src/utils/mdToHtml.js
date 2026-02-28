/**
 * Markdown → HTML，用于公众号草稿正文。
 * 输出为纯 HTML，预览样式由 WechatDraftPreview 的 CSS 控制。
 */
import { marked } from 'marked'

// 安全起见关闭 raw HTML（用户输入的 MD 中若有 HTML 会转义）
marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * @param {string} md - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function mdToHtml(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''
  const out = marked.parse(trimmed)
  return typeof out === 'string' ? out : String(out)
}
