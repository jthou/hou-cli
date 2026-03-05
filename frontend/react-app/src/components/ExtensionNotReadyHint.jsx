/**
 * 扩展未就绪时的详细提示，含安装说明和再次检测按钮
 */
export default function ExtensionNotReadyHint({ onRetry, className = '', compact = false }) {
  const handleRetry = () => {
    if (onRetry) {
      onRetry()
    } else {
      window.postMessage({ type: 'HOU_CLI_PING' }, '*')
    }
  }

  const host = typeof window !== 'undefined' ? window.location.host : ''

  return (
    <div className={`text-xs text-amber-400 space-y-1 ${className}`}>
      <p>未检测到扩展。请确认：</p>
      <ul className={`list-disc list-inside ml-1 ${compact ? 'text-[11px]' : ''}`}>
        <li>
          已安装 Hou CLI 网页阅读助手扩展（chrome://extensions 加载{' '}
          <code className="bg-white/5 px-1 rounded">extension</code> 目录）
        </li>
        <li>
          本页通过 <code className="bg-white/5 px-1 rounded">localhost</code> 或{' '}
          <code className="bg-white/5 px-1 rounded">127.0.0.1</code> 访问（当前：{' '}
          <code className="bg-white/5 px-1 rounded">{host}</code>）
        </li>
        <li>在 Chrome/Edge 中打开，非编辑器内置浏览器</li>
        <li>
          安装后<strong>刷新本页面</strong>
        </li>
      </ul>
      <button
        type="button"
        onClick={handleRetry}
        className={`mt-2 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-amber-300 ${compact ? 'text-[11px]' : ''}`}
      >
        再次检测
      </button>
    </div>
  )
}
