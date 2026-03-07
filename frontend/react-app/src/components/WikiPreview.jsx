/**
 * MediaWiki wikitext 预览组件。
 * 内部通过 wikiToMd 将 wikitext 转为 Markdown，再复用通用 MarkdownPreview 进行渲染，
 * 这样可与其它 Markdown 源的预览风格保持一致。
 */
import { useMemo } from 'react'
import MarkdownPreview from './MarkdownPreview'
import { useToast } from './ToastModal'
import { wikiToMd } from '../utils/wikiMdConvert'

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - MediaWiki wikitext
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - 预览主题
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考回调，不传则隐藏
 * @param {(content: string) => void} [props.onSendToArticle] - 加入写文章回调，不传则隐藏
 */
export default function WikiPreview({
  wikiText = '',
  className = '',
  theme = 'light',
  onAddToReference,
  onSendToArticle,
}) {
  const toast = useToast()
  const markdown = useMemo(
    () => (wikiText ? wikiToMd(wikiText) : ''),
    [wikiText],
  )
  const mdContent = (markdown || '').trim()
  const hasActions = onAddToReference || onSendToArticle || mdContent

  return (
    <div className="flex flex-col min-h-0">
      <MarkdownPreview markdown={markdown} className={className} theme={theme} />
      {hasActions && (
        <div className="shrink-0 flex flex-wrap gap-2 mt-2">
          {mdContent && (
            <button
              type="button"
              onClick={() => {
                navigator.clipboard?.writeText(mdContent).then(
                  () => toast?.info?.('已复制到剪贴板'),
                  () => toast?.error?.('复制失败')
                )
              }}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
            >
              复制 Markdown
            </button>
          )}
          {onSendToArticle && (
            <button
              type="button"
              onClick={() => mdContent && onSendToArticle(mdContent)}
              disabled={!mdContent}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              加入写文章
            </button>
          )}
          {onAddToReference && (
            <button
              type="button"
              onClick={() => mdContent && onAddToReference(mdContent)}
              disabled={!mdContent}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              添加到参考
            </button>
          )}
        </div>
      )}
    </div>
  )
}

