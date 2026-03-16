/**
 * 写作建议 Hook：调用 API、管理浮层状态。通过按钮触发，无快捷键。
 * @param {Object} options
 * @param {React.RefObject} options.textareaRef - textarea 的 ref
 * @param {string} options.value - 当前文本
 * @param {(newValue: string) => void} options.onInsert - 插入文本时回调（before + insert + after）
 * @param {'markdown'|'wikitext'} [options.format='markdown'] - 格式
 * @param {boolean} [options.enabled=true] - 是否启用
 */
import { useState, useCallback, useEffect } from 'react'

const TEXT_BEFORE_LEN = 400
const TEXT_AFTER_LEN = 100

export function useWritingSuggestions({ textareaRef, value, onInsert, format = 'markdown', enabled = true }) {
  const [visible, setVisible] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const [selectedIndex, setSelectedIndex] = useState(0)

  const fetchSuggestions = useCallback(async () => {
    // #region agent log
    fetch('http://127.0.0.1:7525/ingest/a450801f-395b-4284-ace7-115a496b121c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'0f6f5d'},body:JSON.stringify({sessionId:'0f6f5d',location:'useWritingSuggestions.js:fetchSuggestions:entry',message:'fetchSuggestions 被调用',data:{hasOnInsert:!!onInsert},hypothesisId:'H1',timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (!onInsert) {
      // #region agent log
      fetch('http://127.0.0.1:7525/ingest/a450801f-395b-4284-ace7-115a496b121c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'0f6f5d'},body:JSON.stringify({sessionId:'0f6f5d',location:'useWritingSuggestions.js:earlyReturn',message:'提前返回 !onInsert',data:{},hypothesisId:'H2',timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      return
    }

    const el = textareaRef?.current
    const POPOVER_WIDTH = 306
    const GAP = 16
    let top = 120
    let left = 24
    if (el && typeof window !== 'undefined') {
      const rect = el.getBoundingClientRect()
      // 2025-03-15：浮层初始位置在编辑框左侧
      left = Math.max(GAP, rect.left - POPOVER_WIDTH - GAP)
      top = Math.max(GAP, rect.top + GAP)
    }

    // 立即显示浮层（生成中…），不等待 API。用 fixed 定位 + Portal 避免被裁剪
    setPosition({ top, left, fixed: true })
    setVisible(true)
    // #region agent log
    fetch('http://127.0.0.1:7525/ingest/a450801f-395b-4284-ace7-115a496b121c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'0f6f5d'},body:JSON.stringify({sessionId:'0f6f5d',location:'useWritingSuggestions.js:setVisible',message:'setVisible(true) 已调用',data:{top,left,hasEl:!!el},hypothesisId:'H3',timestamp:Date.now()})}).catch(()=>{});
    // #endregion

    if (!el) {
      setLoading(false)
      return
    }

    const start = el.selectionStart ?? 0
    const end = el.selectionEnd ?? start
    const text = value ?? ''
    const textBefore = text.substring(Math.max(0, start - TEXT_BEFORE_LEN), start)
    const textAfter = text.substring(end, Math.min(text.length, end + TEXT_AFTER_LEN))
    setLoading(true)
    setSuggestions([])
    setSelectedIndex(0)

    if (!textBefore?.trim()) {
      setLoading(false)
      return
    }

    try {
      const res = await fetch('/api/writing-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text_before: textBefore,
          text_after: textAfter,
          format,
          max_suggestions: 5,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && Array.isArray(data?.suggestions)) {
        setSuggestions(data.suggestions)
        setSelectedIndex(0)
      } else {
        setSuggestions([])
      }
    } catch (err) {
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [textareaRef, value, onInsert, format])

  const handleInsert = useCallback(
    (text) => {
      const el = textareaRef?.current
      if (!el || !value || !onInsert) return

      const start = el.selectionStart ?? 0
      const end = el.selectionEnd ?? start
      const before = value.substring(0, start)
      const after = value.substring(end)
      onInsert(before + text + after)
      setVisible(false)
      setTimeout(() => {
        el.focus()
        const newPos = start + text.length
        el.setSelectionRange(newPos, newPos)
      }, 0)
    },
    [textareaRef, value, onInsert]
  )

  const handleKeyDown = useCallback(
    (e) => {
      if (!visible) return

      if (e.key === 'Escape') {
        e.preventDefault()
        setVisible(false)
        return
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((i) => (i < suggestions.length - 1 ? i + 1 : i))
        return
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => (i > 0 ? i - 1 : i))
        return
      }

      if (e.key === 'Enter' && suggestions[selectedIndex]) {
        e.preventDefault()
        handleInsert(suggestions[selectedIndex])
      }
    },
    [visible, suggestions, selectedIndex, handleInsert]
  )

  useEffect(() => {
    if (!enabled) return
    const el = textareaRef?.current
    if (!el) return
    el.addEventListener('keydown', handleKeyDown)
    return () => el.removeEventListener('keydown', handleKeyDown)
  }, [enabled, textareaRef, handleKeyDown])

  return {
    fetchSuggestions,
    visible,
    suggestions,
    loading,
    position,
    selectedIndex,
    onSelect: handleInsert,
    onClose: () => setVisible(false),
  }
}
