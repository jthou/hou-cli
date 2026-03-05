/**
 * MediaWiki wikitext 预览组件。
 * 内部通过 wikiToMd 将 wikitext 转为 Markdown，再复用通用 MarkdownPreview 进行渲染，
 * 这样可与其它 Markdown 源的预览风格保持一致。
 */
import { useMemo } from 'react'
import MarkdownPreview from './MarkdownPreview'
import { wikiToMd } from '../utils/wikiMdConvert'

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - MediaWiki wikitext
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - 预览主题
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考信息回调，不传则隐藏按钮
 */
export default function WikiPreview({ wikiText = '', className = '', theme = 'light', onAddToReference }) {
  const markdown = useMemo(
    () => (wikiText ? wikiToMd(wikiText) : ''),
    [wikiText],
  )

  return (
    <div className="flex flex-col min-h-0">
      <MarkdownPreview markdown={markdown} className={className} theme={theme} />
      {onAddToReference && (
        <div className="shrink-0 flex flex-wrap gap-2 mt-2">
          <button
            type="button"
            onClick={() => {
              const toAdd = (wikiText || '').trim()
              if (toAdd) onAddToReference(toAdd)
            }}
            className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
          >
            添加到参考信息
          </button>
        </div>
      )}
    </div>
  )
}

