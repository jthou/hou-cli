/**
 * 写作建议浮层：在左侧区域浮动展示 1–5 条建议，支持拖拽调整位置、点击插入、键盘选择
 * 使用 Portal 挂载到 body，避免被父级 overflow 裁剪
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'

const DEFAULT_LEFT = 24
const DEFAULT_TOP = 120

/**
 * @param {Object} props
 * @param {boolean} props.visible - 是否显示
 * @param {string[]} props.suggestions - 建议列表
 * @param {boolean} props.loading - 加载中
 * @param {{ top: number, left: number, fixed?: boolean }} props.position - 初始坐标（fixed 时为视口坐标）
 * @param {(text: string) => void} props.onSelect - 选择某条建议时回调
 * @param {() => void} props.onClose - 关闭时回调
 * @param {() => void} props.onRefresh - 刷新建议时回调
 * @param {number} props.selectedIndex - 当前键盘选中的索引
 */
export default function WritingSuggestionsPopover({
  visible,
  suggestions,
  loading,
  position,
  onSelect,
  onClose,
  onRefresh,
  selectedIndex = 0,
}) {
  const listRef = useRef(null)
  const [coords, setCoords] = useState({ top: DEFAULT_TOP, left: DEFAULT_LEFT })
  const dragRef = useRef(null)

  // 可见时用 props 的 position 初始化（仅首次或坐标变化时）
  useEffect(() => {
    if (visible && position?.fixed) {
      const top = position.top ?? DEFAULT_TOP
      const left = position.left ?? DEFAULT_LEFT
      setCoords((prev) => (prev.top === DEFAULT_TOP && prev.left === DEFAULT_LEFT ? { top, left } : prev))
    }
  }, [visible, position?.top, position?.left])

  useEffect(() => {
    if (selectedIndex >= 0 && listRef.current) {
      const item = listRef.current.children[selectedIndex]
      item?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedIndex])

  const handleDragStart = useCallback((e) => {
    if (e.button !== 0) return
    e.preventDefault()
    dragRef.current = { x: e.clientX, y: e.clientY, top: coords.top, left: coords.left }
  }, [coords])

  useEffect(() => {
    const onMove = (e) => {
      const d = dragRef.current
      if (!d) return
      const pad = 16
      const maxTop = Math.max(0, (typeof window !== 'undefined' ? window.innerHeight : 600) - 350)
      const maxLeft = Math.max(0, (typeof window !== 'undefined' ? window.innerWidth : 800) - 300)
      setCoords({
        top: Math.max(pad, Math.min(d.top + e.clientY - d.y, maxTop)),
        left: Math.max(pad, Math.min(d.left + e.clientX - d.x, maxLeft)),
      })
    }
    const onUp = () => { dragRef.current = null }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [])

  if (!visible) return null

  // #region agent log
  if (typeof fetch !== 'undefined') fetch('http://127.0.0.1:7525/ingest/a450801f-395b-4284-ace7-115a496b121c',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'0f6f5d'},body:JSON.stringify({sessionId:'0f6f5d',location:'WritingSuggestionsPopover.jsx:render',message:'Popover 正在渲染',data:{visible,coords},hypothesisId:'H4',timestamp:Date.now()})}).catch(()=>{});
  // #endregion

  const content = (
    <div
      className="z-[9999] min-w-[280px] max-w-[560px] rounded-lg border border-slate-200 bg-white shadow-lg text-slate-800"
      style={{ position: 'fixed', top: coords.top, left: coords.left }}
      role="listbox"
    >
      <div
        className="flex items-center justify-between gap-2 px-2 py-1.5 text-xs text-slate-500 border-b border-slate-200 cursor-move select-none"
        onMouseDown={handleDragStart}
      >
        <span>写作建议</span>
        <div className="flex items-center gap-1 shrink-0" onMouseDown={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRefresh?.() }}
            disabled={loading}
            className="w-6 h-6 flex items-center justify-center rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-50 cursor-pointer"
            aria-label="刷新"
            title="重新获取建议"
          >
            ↻
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onClose?.() }}
            className="w-5 h-5 flex items-center justify-center rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
            aria-label="关闭"
          >
            ×
          </button>
        </div>
      </div>
      <ul ref={listRef} className="max-h-[320px] overflow-y-auto py-1">
        {loading ? (
          <li className="px-3 py-2 text-sm text-slate-600">生成中…</li>
        ) : suggestions.length === 0 ? (
          <li className="px-3 py-2 text-sm text-slate-600">暂无建议</li>
        ) : (
          suggestions.map((s, i) => (
            <li
              key={i}
              role="option"
              aria-selected={i === selectedIndex}
              className={`px-3 py-2 text-sm cursor-pointer whitespace-pre-wrap break-words ${
                i === selectedIndex ? 'bg-cyan-50 text-cyan-800' : 'hover:bg-slate-50 text-slate-800'
              }`}
              onClick={() => onSelect?.(s)}
            >
              {s}
            </li>
          ))
        )}
      </ul>
    </div>
  )

  return typeof document !== 'undefined'
    ? createPortal(content, document.body)
    : content
}
