/**
 * Markdown → HTML 核心转换（纯函数，无 DOM/网络依赖，便于单元测试）。
 * 负责：marked 解析 + 空列表项过滤。
 * 公众号样式注入、公式转图等由 mdToHtml.js 上层处理。
 */
import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * 移除 HTML 中的空列表项（如 <li></li>、<li> </li>、<li><br></li>、<li><p></p></li>），避免公众号显示空 bullet。
 * @param {string} html - HTML 字符串
 * @returns {string} 移除空 li 后的 HTML
 */
export function removeEmptyListItems(html) {
  if (typeof html !== 'string') return html
  return html.replace(/<li(?:\s[^>]*)?>(\s|&nbsp;|<br\s*\/?>|<p>\s*<\/p>)*<\/li>/gi, '')
}

/**
 * Markdown 转 HTML 核心逻辑（marked 解析 + 空列表项过滤）。
 * @param {string} md - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function mdToHtmlCore(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''
  let out = marked.parse(trimmed)
  out = typeof out === 'string' ? out : String(out)
  return removeEmptyListItems(out)
}
