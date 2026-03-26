/**
 * Markdown 分栏滚动：按源码行号（data-md-line）对齐，优于纯 scrollTop 比例。
 */

const PREVIEW_ROOT_SELECTOR = '.wechat-draft-preview'

/**
 * 用「滚动比例 → 源文字符位置 → 行号」估计当前编辑区顶部对应的源码行（1-based）。
 * @param {HTMLTextAreaElement} ta
 */
export function approxSourceLineFromTextareaScroll(ta) {
  const v = ta.value
  if (!v) return 1
  const maxS = ta.scrollHeight - ta.clientHeight
  if (maxS <= 0) return 1
  const ratio = Math.min(1, Math.max(0, ta.scrollTop / maxS))
  const charIdx = Math.min(Math.max(0, v.length - 1), Math.floor(ratio * v.length))
  return v.slice(0, charIdx).split('\n').length + 1
}

/**
 * 将预览容器滚动到「行号 <= line」的最近块级锚点（data-md-line）。
 * @param {HTMLElement} previewScrollEl
 * @param {number} line
 * @returns {number} 实际设置的 scrollTop
 */
export function scrollPreviewToSourceLine(previewScrollEl, line) {
  const root = previewScrollEl.querySelector(PREVIEW_ROOT_SELECTOR) || previewScrollEl
  const nodes = root.querySelectorAll('[data-md-line]')
  let best = null
  let bestLine = -1
  nodes.forEach((el) => {
    const L = parseInt(el.getAttribute('data-md-line'), 10)
    if (Number.isFinite(L) && L <= line && L >= bestLine) {
      bestLine = L
      best = el
    }
  })
  if (!best) return previewScrollEl.scrollTop
  const cRect = previewScrollEl.getBoundingClientRect()
  const eRect = best.getBoundingClientRect()
  const next = previewScrollEl.scrollTop + (eRect.top - cRect.top) - 10
  const clamped = Math.max(0, Math.min(next, previewScrollEl.scrollHeight - previewScrollEl.clientHeight))
  previewScrollEl.scrollTop = clamped
  return clamped
}

/**
 * 从预览可视区顶部探测当前「主」源码行。
 * @param {HTMLElement} previewScrollEl
 */
export function sourceLineFromPreviewViewport(previewScrollEl) {
  const rect = previewScrollEl.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return 1
  const x = rect.left + Math.min(72, rect.width * 0.22)
  let y = rect.top + Math.min(28, rect.height * 0.1)
  let el = document.elementFromPoint(x, y)
  if (!el || !previewScrollEl.contains(el)) {
    y = rect.top + 6
    el = document.elementFromPoint(x, y)
  }
  const anchor = el?.closest?.('[data-md-line]')
  if (anchor && previewScrollEl.contains(anchor)) {
    const L = parseInt(anchor.getAttribute('data-md-line'), 10)
    return Number.isFinite(L) ? L : 1
  }
  const root = previewScrollEl.querySelector(PREVIEW_ROOT_SELECTOR) || previewScrollEl
  const nodes = [...root.querySelectorAll('[data-md-line]')]
  if (nodes.length === 0) return 1
  const probe = previewScrollEl.scrollTop + 6
  let line = 1
  for (const n of nodes) {
    const t = n.offsetTop
    if (t <= probe + 2) {
      const L = parseInt(n.getAttribute('data-md-line'), 10)
      if (Number.isFinite(L)) line = L
    } else break
  }
  return line
}

/**
 * 将 textarea 滚动到大致展示指定源码行在文档中的相对位置。
 * @param {HTMLTextAreaElement} ta
 * @param {number} line 1-based
 */
export function scrollTextareaToSourceLine(ta, line) {
  const v = ta.value
  if (!v) return
  const parts = v.split('\n')
  const nLines = parts.length
  const target = Math.max(1, Math.min(Math.floor(line), nLines))
  const maxS = ta.scrollHeight - ta.clientHeight
  if (maxS <= 0) {
    ta.scrollTop = 0
    return
  }
  const ratio = nLines <= 1 ? 0 : (target - 1) / (nLines - 1)
  ta.scrollTop = ratio * maxS
}
