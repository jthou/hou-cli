/**
 * 底部固定的扩展安装说明，用于网页阅读、PDF 阅读等依赖扩展的页面
 */
export default function ExtensionInstallFooter({ className = '' }) {
  return (
    <div className={`shrink-0 p-3 text-xs text-muted border-t border-border space-y-1 ${className}`}>
      <p>
        <strong>安装扩展：</strong>chrome://extensions → 开发者模式 → 加载{' '}
        <code className="bg-white/5 px-1 rounded">extension</code> 目录
      </p>
      <p>需在 Chrome/Edge 中打开本页，编辑器内置浏览器无法使用扩展。</p>
    </div>
  )
}
