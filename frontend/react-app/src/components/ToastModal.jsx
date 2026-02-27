import { useState, createContext, useContext, useCallback } from 'react'

const ToastContext = createContext(null)

const ICONS = {
  info: 'ℹ',
  warning: '⚠',
  error: '✕',
  confirm: '?',
}

const STYLES = {
  info: { icon: 'text-cyan-400', border: 'border-cyan-500/30', bg: 'bg-cyan-500/10', defaultTitle: '信息' },
  warning: { icon: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10', defaultTitle: '警告' },
  error: { icon: 'text-red-400', border: 'border-red-500/30', bg: 'bg-red-500/10', defaultTitle: '错误' },
  confirm: { icon: 'text-slate-400', border: 'border-slate-500/30', bg: 'bg-slate-500/10', defaultTitle: '确认' },
}

function ToastModal({ type, title, message, confirmText, cancelText, onConfirm, onCancel }) {
  const style = STYLES[type] || STYLES.info
  const isConfirm = type === 'confirm'
  const displayTitle = title ?? style.defaultTitle

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div
        className={`bg-surface border rounded-xl shadow-xl max-w-sm w-full overflow-hidden ${style.border}`}
        onClick={e => e.stopPropagation()}
      >
        <div className={`flex items-start gap-4 p-5 ${style.bg}`}>
          <span className={`text-2xl shrink-0 ${style.icon}`}>{ICONS[type]}</span>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white mb-1">{displayTitle}</h3>
            <p className="text-sm text-[#94a3b8] whitespace-pre-wrap">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-border">
          {isConfirm ? (
            <>
              <button
                onClick={onCancel}
                className="px-4 py-2 text-sm border border-border rounded-lg text-[#94a3b8] hover:text-white hover:bg-white/5"
              >
                {cancelText || '取消'}
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-2 text-sm bg-accent text-white rounded-lg hover:opacity-90"
              >
                {confirmText || '确定'}
              </button>
            </>
          ) : (
            <button
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

  const show = useCallback((opts) => {
    return new Promise((resolve) => {
      setToast({ ...opts, resolve })
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
