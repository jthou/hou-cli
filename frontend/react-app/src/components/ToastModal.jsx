import { useState, createContext, useContext, useCallback, useRef, useEffect } from 'react'

const ToastContext = createContext(null)

const ICONS = {
  info: 'ℹ',
  warning: '⚠',
  error: '✕',
  confirm: '?',
}

const TITLES = {
  info: '信息',
  warning: '警告',
  error: '错误',
  confirm: '确认',
}

// 统一样式：仅图标与左侧竖条按类型着色
const TYPE_ACCENT = {
  info: 'text-cyan-400 border-cyan-500',
  warning: 'text-amber-400 border-amber-500',
  error: 'text-red-400 border-red-500',
  confirm: 'text-violet-400 border-violet-500',
}

const OFFSET = 24
const CARD_MAX_W = 380
const CARD_MIN_W = 280

function clampPosition (x, y, cardW, cardH) {
  const vw = typeof window !== 'undefined' ? window.innerWidth : 800
  const vh = typeof window !== 'undefined' ? window.innerHeight : 600
  let left = x + OFFSET
  let top = y + OFFSET
  if (left + cardW > vw - 16) left = Math.max(16, vw - cardW - 16)
  if (left < 16) left = 16
  if (top + cardH > vh - 16) top = Math.max(16, vh - cardH - 16)
  if (top < 16) top = 16
  return { left, top }
}

function ToastModal({ type, title, message, confirmText, cancelText, onConfirm, onCancel, position }) {
  const accent = TYPE_ACCENT[type] || TYPE_ACCENT.info
  const isConfirm = type === 'confirm'
  const displayTitle = title ?? TITLES[type]

  const place = (() => {
    const x = position?.x ?? (typeof window !== 'undefined' ? window.innerWidth / 2 - CARD_MAX_W / 2 : 0)
    const y = position?.y ?? (typeof window !== 'undefined' ? window.innerHeight / 2 - 100 : 0)
    return clampPosition(x, y, CARD_MAX_W, 220)
  })()

  const style = { left: place.left, top: place.top, maxWidth: CARD_MAX_W, minWidth: CARD_MIN_W }

  return (
    <div className="fixed inset-0 z-[100] bg-black/50" onClick={onCancel} aria-hidden="false">
      <div
        role="dialog"
        aria-labelledby="toast-title"
        aria-describedby="toast-message"
        style={style}
        className="fixed z-[101] bg-surface border border-border rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 p-5">
          <span className={`shrink-0 w-10 h-10 flex items-center justify-center rounded-lg border-l-4 ${accent} bg-white/5 text-xl`}>
            {ICONS[type]}
          </span>
          <div className="flex-1 min-w-0">
            <h3 id="toast-title" className="text-base font-semibold text-white mb-1">{displayTitle}</h3>
            <p id="toast-message" className="text-sm text-[#94a3b8] whitespace-pre-wrap">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-border">
          {isConfirm ? (
            <>
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-sm border border-border rounded-lg text-[#94a3b8] hover:text-white hover:bg-white/5"
              >
                {cancelText || '取消'}
              </button>
              <button
                type="button"
                onClick={onConfirm}
                className="px-4 py-2 text-sm bg-accent text-white rounded-lg hover:opacity-90"
              >
                {confirmText || '确定'}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={onConfirm}
              className="px-4 py-2 text-sm bg-accent text-white rounded-lg hover:opacity-90"
            >
              {confirmText || '确定'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const mouseRef = useRef({ x: 0, y: 0 })

  useEffect(() => {
    const onMove = (e) => {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  const show = useCallback((opts) => {
    return new Promise((resolve) => {
      const pos = opts.position ?? mouseRef.current
      setToast({ ...opts, resolve, position: { x: pos.x, y: pos.y } })
    })
  }, [])

  const handleConfirm = useCallback(() => {
    if (toast?.resolve) toast.resolve(true)
    setToast(null)
  }, [toast])

  const handleCancel = useCallback(() => {
    if (toast?.resolve) toast.resolve(toast.type === 'confirm' ? false : true)
    setToast(null)
  }, [toast])

  const api = {
    info: (message, opts = {}) => show({ type: 'info', message, ...opts }),
    success: (message, opts = {}) => show({ type: 'info', message, ...opts, title: opts.title ?? '成功' }),
    warning: (message, opts = {}) => show({ type: 'warning', message, ...opts }),
    error: (message, opts = {}) => show({ type: 'error', message, ...opts }),
    confirm: (message, opts = {}) => show({ type: 'confirm', message, ...opts }),
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      {toast && (
        <ToastModal
          type={toast.type}
          title={toast.title}
          message={toast.message}
          confirmText={toast.confirmText}
          cancelText={toast.cancelText}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          position={toast.position}
        />
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast 必须在 ToastProvider 内使用')
  return ctx
}
