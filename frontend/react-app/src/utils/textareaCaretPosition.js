/**
 * 获取 textarea 光标位置的像素坐标（相对于 textarea 元素）
 * 使用 mirror div 技术，复制 textarea 的样式与宽度以正确计算换行
 * @param {HTMLTextAreaElement} el - textarea 元素
 * @param {number} pos - 光标字符位置（selectionStart）
 * @returns {{ top: number, left: number }}
 */
export function getCaretCoordinates(el, pos) {
  if (!el || typeof pos !== 'number') return { top: 0, left: 0 }

  const style = getComputedStyle(el)
  const div = document.createElement('div')
  const props = [
    'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
    'fontSizeAdjust', 'lineHeight', 'fontFamily', 'letterSpacing',
    'wordSpacing', 'tabSize', 'whiteSpace',
  ]
  props.forEach((p) => { div.style[p] = style[p] })
  div.style.position = 'absolute'
  div.style.visibility = 'hidden'
  div.style.wordWrap = 'break-word'
  div.style.overflow = 'hidden'
  div.style.whiteSpace = 'pre-wrap'
  div.style.wordBreak = 'break-word'
  div.style.width = `${el.offsetWidth}px`

  const text = el.value.substring(0, pos)
  const span = document.createElement('span')
  span.textContent = text || '\u200b'
  div.appendChild(span)
  document.body.appendChild(div)

  const rect = el.getBoundingClientRect()
  const spanRect = span.getBoundingClientRect()
  const top = spanRect.bottom - rect.top + el.scrollTop
  const left = spanRect.left - rect.left + el.scrollLeft

  document.body.removeChild(div)
  return { top: Math.max(0, top), left: Math.max(0, Math.min(left, rect.width - 50)) }
}
