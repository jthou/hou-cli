/**
 * 从剪贴板粘贴按钮，需配合 usePasteFromClipboard 使用
 * @param {Object} props
 * @param {function(): void} props.onClick 粘贴处理函数（来自 usePasteFromClipboard）
 * @param {string} [props.title='从剪贴板粘贴'] 按钮 title
 * @param {string} [props.className] 额外 class
 * @param {'sm'|'md'} [props.size='md'] sm=text-xs, md=text-sm
 */
export default function PasteButton({ onClick, title = '从剪贴板粘贴', className = '', size = 'md' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`px-3 py-2 border border-border rounded-lg text-muted hover:text-fg hover:bg-white/5 shrink-0 ${
        size === 'sm' ? 'text-xs' : 'text-sm'
      } ${className}`}
    >
      粘贴
    </button>
  )
}
