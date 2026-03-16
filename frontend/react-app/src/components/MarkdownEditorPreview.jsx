/**
 * Markdown 编辑 + 预览 + 摘要 + 操作按钮（复制、发送到写作助手、写入 MediaWiki）
 * 供 WebReader、ArticleWriting 等页面复用
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import MarkdownPreview from './MarkdownPreview'
import MarkdownActionButtons from './MarkdownActionButtons'
import { useWritingSuggestions } from '../hooks/useWritingSuggestions'
import { tabCls } from './editor/EditorConstants'
import WritingSuggestionsButton from './editor/WritingSuggestionsButton'
import EditAreaWithSuggestions from './editor/EditAreaWithSuggestions'

/**
 * @param {Object} props
 * @param {string} [props.content] - Markdown 内容
 * @param {(v: string) => void} [props.onContentChange] - 编辑模式下内容变化回调
 * @param {boolean} [props.editable=true] - 是否支持编辑模式
 * @param {'light'|'dark'} [props.theme='dark'] - 预览主题
 * @param {string} [props.className] - 容器类名
 * @param {(content: string) => void} [props.onCopy] - 复制回调，默认使用剪贴板
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写作助手回调，不传则隐藏按钮
 * @param {string} [props.sendToArticleLabel='发送到写作助手'] - 按钮文案
 * @param {boolean} [props.showMediaWiki=true] - 是否显示写入 MediaWiki 按钮
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考回调，不传则隐藏
 * @param {string} [props.sourceUrl] - 原文链接（如微信读书 URL），写入 MediaWiki 时自动追加到文末
 * @param {React.ReactNode} [props.footerExtra] - 底部额外按钮（如「同步到公众号草稿」）
 * @param {boolean} [props.showSummary=false] - 是否显示摘要区域
 * @param {string} [props.summary] - 摘要内容（受控）
 * @param {(v: string) => void} [props.onSummaryChange] - 摘要变化回调
 * @param {(content: string) => Promise<string>} [props.onGenerateSummary] - 生成摘要回调，返回摘要文本
 * @param {(err: Error) => void} [props.onSummaryError] - 生成失败时回调（如用于 toast 提示）
 * @param {Function} [props.onImgClick] - 点击预览区图片时回调，用于上传到 MediaWiki 等
 */
export default function MarkdownEditorPreview({
  content = '',
  onContentChange,
  editable = true,
  theme = 'dark',
  className = '',
  onCopy,
  onSendToArticle,
  sendToArticleLabel = '发送到写作助手',
  showMediaWiki = true,
  onAddToReference,
  sourceUrl = '',
  footerExtra,
  showSummary = false,
  summary = '',
  onSummaryChange,
  onGenerateSummary,
  onSummaryError,
  onImgClick,
}) {
  const [viewMode, setViewMode] = useState('preview')
  const [editDraft, setEditDraft] = useState(content)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const textareaRef = useRef(null)

  const handleInsertSuggestion = useCallback(
    (newValue) => {
      setEditDraft(newValue)
      onContentChange?.(newValue)
    },
    [onContentChange]
  )

  const writingSuggestions = useWritingSuggestions({
    textareaRef,
    value: editDraft,
    onInsert: handleInsertSuggestion,
    format: 'markdown',
    enabled: viewMode === 'edit' && editable,
  })

  useEffect(() => {
    if (viewMode === 'preview') setEditDraft(content)
  }, [content, viewMode])

  const effectiveContent = viewMode === 'edit' ? editDraft : content

  const enterEdit = () => {
    setEditDraft(content)
    setViewMode('edit')
  }

  const handleGenerateSummary = useCallback(async () => {
    if (!onGenerateSummary || !effectiveContent?.trim()) return
    setSummaryLoading(true)
    try {
      const result = await onGenerateSummary(effectiveContent)
      onSummaryChange?.(result ?? '')
    } catch (err) {
      onSummaryChange?.('')
      onSummaryError?.(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setSummaryLoading(false)
    }
  }, [effectiveContent, onGenerateSummary, onSummaryChange, onSummaryError])

  /** 点击摘要且无摘要时，自动生成 */
  useEffect(() => {
    if (
      viewMode === 'summary' &&
      !summary?.trim() &&
      effectiveContent?.trim() &&
      onGenerateSummary &&
      !summaryLoading
    ) {
      handleGenerateSummary()
    }
  }, [viewMode, summary, effectiveContent, onGenerateSummary, summaryLoading, handleGenerateSummary])

  const tabCls = (active) =>
    `px-2 py-1 rounded text-xs ${active ? 'bg-accent text-white' : 'border border-border text-muted hover:bg-white/10'}`

  return (
    <div className={`flex flex-col min-h-0 ${className}`.trim()}>
      <div className="shrink-0 px-4 py-3 border-b border-border bg-white/[0.02] flex flex-wrap items-center gap-2">
        {editable && (
          <>
            <button type="button" onClick={() => setViewMode('preview')} className={tabCls(viewMode === 'preview')}>
              预览
            </button>
            <button type="button" onClick={enterEdit} className={tabCls(viewMode === 'edit')}>
              编辑
            </button>
            {showSummary && (
              <button type="button" onClick={() => setViewMode('summary')} className={tabCls(viewMode === 'summary')}>
                摘要
              </button>
            )}
            {viewMode === 'edit' && (
              <WritingSuggestionsButton
                onClick={() => writingSuggestions.fetchSuggestions?.()}
                loading={writingSuggestions.loading}
              />
            )}
          </>
        )}
      </div>
      <div className="flex-1 min-h-[320px] overflow-y-auto flex flex-col">
        {viewMode === 'edit' ? (
          <EditAreaWithSuggestions
            textareaRef={textareaRef}
            value={editDraft}
            onChange={(v) => { setEditDraft(v); onContentChange?.(v) }}
            placeholder="在此编辑 Markdown 内容…"
            writingSuggestions={writingSuggestions}
          />
        ) : viewMode === 'summary' ? (
          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto flex flex-col p-4">
            <div className="shrink-0 flex items-center justify-between gap-2 mb-3">
              {onGenerateSummary && (
                <button
                  type="button"
                  onClick={handleGenerateSummary}
                  disabled={summaryLoading || !effectiveContent?.trim()}
                  className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 disabled:opacity-50"
                >
                  {summaryLoading ? '生成中…' : summary ? '重新生成' : '生成摘要'}
                </button>
              )}
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto text-sm text-muted [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-1.5 [&_h3]:mb-0.5 [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4">
              {summary ? (
                <MarkdownPreview markdown={summary} theme="dark" className="p-0 min-h-0 text-sm" />
              ) : (
                <p className="text-xs text-muted/70 italic">点击「生成摘要」由 AI 生成结构化分层摘要。</p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto">
            <MarkdownPreview markdown={effectiveContent || ''} className="min-h-full p-4" theme={theme} onImgClick={onImgClick} />
          </div>
        )}
      </div>
      <div className="shrink-0 px-4 py-3 border-t border-border flex items-center justify-center gap-3 bg-black/20">
        <MarkdownActionButtons
          content={effectiveContent}
          onCopy={onCopy}
          onSendToArticle={onSendToArticle}
          sendToArticleLabel={sendToArticleLabel}
          showMediaWiki={showMediaWiki}
          onAddToReference={onAddToReference}
          sourceUrl={sourceUrl}
          extra={footerExtra}
        />
      </div>
    </div>
  )
}
