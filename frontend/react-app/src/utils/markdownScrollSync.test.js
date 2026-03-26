/**
 * markdownScrollSync 纯函数测试（不依赖真实 DOM 布局）
 */
import { describe, it, expect } from 'vitest'
import { approxSourceLineFromTextareaScroll } from './markdownScrollSync.js'

describe('approxSourceLineFromTextareaScroll', () => {
  it('空内容返回 1', () => {
    const ta = { value: '', scrollHeight: 100, clientHeight: 100, scrollTop: 0 }
    expect(approxSourceLineFromTextareaScroll(/** @type {HTMLTextAreaElement} */ (ta))).toBe(1)
  })

  it('不可滚动时返回 1', () => {
    const ta = { value: 'a\nb\nc', scrollHeight: 50, clientHeight: 50, scrollTop: 0 }
    expect(approxSourceLineFromTextareaScroll(/** @type {HTMLTextAreaElement} */ (ta))).toBe(1)
  })

  it('滚到底接近末行', () => {
    const v = 'L1\nL2\nL3\nL4'
    const ta = { value: v, scrollHeight: 200, clientHeight: 50, scrollTop: 150 }
    const line = approxSourceLineFromTextareaScroll(/** @type {HTMLTextAreaElement} */ (ta))
    expect(line).toBeGreaterThanOrEqual(3)
    expect(line).toBeLessThanOrEqual(5)
  })
})
