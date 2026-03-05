/**
 * Markdown 编辑 + 预览 + 操作按钮（复制、发送到写文章、写入 MediaWiki）
 * 供 WebReader、ArticleWriting 等页面复用
 */
import { useState, useEffect } from 'react'
import MarkdownPreview from './MarkdownPreview'
import MarkdownActionButtons from './MarkdownActionButtons'

const textareaCls =
  'flex-1 min-h-[200px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed'

/**
 * @param {Object} props
 * @param {string} [props.content] - Markdown 内容
 * @param {(v: string) => void} [props.onContentChange] - 编辑模式下内容变化回调
 * @param {boolean} [props.editable=true] - 是否支持编辑模式
 * @param {'light'|'dark'} [props.theme='dark'] - 预览主题
 * @param {string} [props.className] - 容器类名
 * @param {(content: string) => void} [props.onCopy] - 复制回调，默认使用剪贴板
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写文章回调，不传则隐藏按钮
 * @param {string} [props.sendToArticleLabel='发送到写文章'] - 按钮文案
 * @param {boolean} [props.showMediaWiki=true] - 是否显示写入 MediaWiki 按钮
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考信息回调，不传则隐藏
 * @param {React.ReactNode} [props.footerExtra] - 底部额外按钮（如「同步到公众号草稿」）
 */
export default function MarkdownEditorPreview({
  content = '',
  onContentChange,
  editable = true,
  theme = 'dark',
  className = '',
  onCopy,
  onSendToArticle,
  sendToArticleLabel = '发送到写文章',
  showMediaWiki = true,
  onAddToReference,
  footerExtra,
}) {
  const [viewMode, setViewMode] = useState('preview')
  const [editDraft, setEditDraft] = useState(content)

  useEffect(() => {
    if (viewMode === 'preview') setEditDraft(content)
  }, [content, viewMode])

  const effectiveContent = viewMode === 'edit' ? editDraft : content

  const enterEdit = () => {
    setEditDraft(content)
    setViewMode('edit')
  }

  return (
    <div className={`flex flex-col min-h-0 ${className}`.trim()}>
      {editable && (
        <div className="shrink-0 flex items-center gap-2 mb-2">
          <button
            type="button"
            onClick={() => setViewMode('preview')}
            className={`px-2 py-1 rounded text-xs ${viewMode === 'preview' ? 'bg-accent text-white' : 'border border-border text-muted hover:bg-white/10'}`}
          >
            预览
          </button>
          <button
            type="button"
            onClick={enterEdit}
            className={`px-2 py-1 rounded text-xs ${viewMode === 'edit' ? 'bg-accent text-white' : 'border border-border text-muted hover:bg-white/10'}`}
          >
            编辑
          </button>
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
        {viewMode === 'edit' ? (
          <textarea
            value={editDraft}
            onChange={(e) => {
              setEditDraft(e.target.value)
              onContentChange?.(e.target.value)
            }}
            placeholder="在此编辑 Markdown 内容…"
            className={textareaCls}
            spellCheck={false}
          />
        ) : (
          <MarkdownPreview markdown={effectiveContent || ''} className="min-h-[200px]" theme={theme} />
        )}
      </div>
      <div className="shrink-0 px-4 py-3 border-t border-border bg-white/[0.02]">
        <MarkdownActionButtons
          content={effectiveContent}
          onCopy={onCopy}
          onSendToArticle={onSendToArticle}
          sendToArticleLabel={sendToArticleLabel}
          showMediaWiki={showMediaWiki}
          onAddToReference={onAddToReference}
          extra={footerExtra}
        />
      </div>
    </div>
  )
}
