import { useCallback } from 'react'

/**
 * 从剪贴板读取文本并回调
 * @param {Object} options
 * @param {function(string): void} options.onPaste 成功时回调，传入剪贴板文本
 * @param {object} [options.toast] 可选，用于显示警告/错误
 * @returns {function(): Promise<void>} handlePaste 函数
 */
export function usePasteFromClipboard({ onPaste, toast } = {}) {
  return useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text?.trim()) {
        onPaste?.(text.trim())
      } else {
        toast?.warning?.('剪贴板为空')
      }
    } catch (e) {
      toast?.error?.('读取剪贴板失败：' + (e?.message || '请检查权限'))
    }
  }, [onPaste, toast])
}
