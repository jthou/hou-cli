/**
 * textareaCaretPosition 单元测试
 * 测试 getCaretCoordinates 的边界条件及基本 DOM 行为
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { getCaretCoordinates } from './textareaCaretPosition.js'

describe('getCaretCoordinates', () => {
  describe('无效输入返回 { top: 0, left: 0 }', () => {
    it('el 为 null 时', () => {
      expect(getCaretCoordinates(null, 0)).toEqual({ top: 0, left: 0 })
    })

    it('el 为 undefined 时', () => {
      expect(getCaretCoordinates(undefined, 0)).toEqual({ top: 0, left: 0 })
    })

    it('pos 非数字时', () => {
      const el = {}
      expect(getCaretCoordinates(el, undefined)).toEqual({ top: 0, left: 0 })
      expect(getCaretCoordinates(el, null)).toEqual({ top: 0, left: 0 })
      expect(getCaretCoordinates(el, '0')).toEqual({ top: 0, left: 0 })
    })
  })

  describe('DOM 环境下的基本行为', () => {
    /** @type {HTMLTextAreaElement} */
    let textarea

    beforeEach(() => {
      textarea = document.createElement('textarea')
      textarea.value = 'hello world'
      textarea.style.cssText = 'width:200px;height:80px;font-size:14px;'
      document.body.appendChild(textarea)
    })

    afterEach(() => {
      if (textarea?.parentNode) textarea.parentNode.removeChild(textarea)
    })

    it('返回对象包含 top 和 left 且为数字', () => {
      const result = getCaretCoordinates(textarea, 0)
      expect(result).toHaveProperty('top')
      expect(result).toHaveProperty('left')
      expect(typeof result.top).toBe('number')
      expect(typeof result.left).toBe('number')
    })

    it('pos=0 时 top/left 非负', () => {
      const result = getCaretCoordinates(textarea, 0)
      expect(result.top).toBeGreaterThanOrEqual(0)
      expect(result.left).toBeGreaterThanOrEqual(0)
    })

    it('pos 在文本长度内时返回有效坐标', () => {
      const result = getCaretCoordinates(textarea, 5)
      expect(result.top).toBeGreaterThanOrEqual(0)
      expect(result.left).toBeGreaterThanOrEqual(0)
    })

    it('pos 超出文本长度时仍能计算', () => {
      const result = getCaretCoordinates(textarea, 999)
      expect(result.top).toBeGreaterThanOrEqual(0)
      expect(result.left).toBeGreaterThanOrEqual(0)
    })
  })
})
