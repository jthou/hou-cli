/**
 * 多行聊天输入框：Enter 换行，Ctrl+Enter（或 Cmd+Enter）发送。
 * 供写作助手、对话等场景复用。
 *
 * @param {string} [props.value] - 受控输入值
 * @param {(v: string) => void} [props.onChange] - 输入变化回调
 * @param {() => void} [props.onSubmit] - 提交时回调（父组件在回调中读取当前 value 并清空等）
 * @param {string} [props.placeholder] - 占位文案
 * @param {boolean} [props.disabled] - 是否禁用（如加载中）
 * @param {string} [props.submitLabel] - 发送按钮文案，默认「发送」
 * @param {number} [props.rows] - 初始行数，默认 2
 * @param {string} [props.className] - 表单容器额外类名
 */
export default function ChatInput({
  value = '',
  onChange,
  onSubmit,
  placeholder = '输入消息，Enter 换行，Ctrl+Enter 发送',
  disabled = false,
  submitLabel = '发送',
  rows = 2,
  className = '',
}) {
  const canSubmit = !disabled && (value || '').trim().length > 0

  const handleSubmit = (e) => {
    e?.preventDefault?.()
    if (!canSubmit) return
    onSubmit?.()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`shrink-0 px-4 py-3 border-t border-border bg-surface ${className}`.trim()}
    >
      <div className="flex gap-2 items-end">
        <textarea
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault()
              if (canSubmit) handleSubmit(e)
            }
          }}
          placeholder={placeholder}
          rows={rows}
          className="flex-1 min-h-[40px] max-h-[200px] resize-y rounded-lg bg-white/5 border border-border px-4 py-2.5 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="shrink-0 px-4 py-2.5 rounded-lg bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitLabel}
        </button>
      </div>
    </form>
  )
}
