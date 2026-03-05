/**
 * 页面顶部标题区域，用于各功能页
 * @param {Object} props
 * @param {React.ReactNode} props.title 主标题
 * @param {React.ReactNode} [props.subtitle] 副标题（可选）
 * @param {React.ReactNode} [props.actions] 右侧操作区（可选）
 * @param {string} [props.titleClassName] 标题额外 class，如 text-fg
 * @param {string} [props.className] 额外 class
 */
export default function PageHeader({ title, subtitle, actions, titleClassName = '', className = '' }) {
  return (
    <header className={`shrink-0 px-6 py-4 border-b border-border flex items-center justify-between gap-4 ${className}`}>
      <div className="min-w-0">
        <h1 className={`text-xl font-semibold ${titleClassName || 'text-white'}`}>{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </header>
  )
}
