/**
 * Wikitext 编辑 + 预览 + 摘要 + 操作按钮
 * 供 MediaWikiReader 使用，直接编辑 Wikitext，不做 Markdown 转换
 */
import { useState, useEffect, useCallback } from 'react'
import WikiPreview from './WikiPreview'
import WikitextActionButtons from './WikitextActionButtons'

const textareaCls =
  'flex-1 min-h-[200px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed'

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - Wikitext 内容
 * @param {(v: string) => void} [props.onContentChange] - 编辑模式下内容变化回调
 * @param {boolean} [props.editable=true] - 是否支持编辑模式
 * @param {'light'|'dark'} [props.theme='dark'] - 预览主题
 * @param {string} [props.className] - 容器类名
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考（会转为 Markdown）
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写作助手（会转为 Markdown）
 * @param {(pageTitle: string) => void} [props.onWikiLinkClick] - 点击本站 Wiki 链接时回调，用于在应用内打开
 * @param {boolean} [props.showSummary=false] - 是否显示摘要区域
 * @param {string} [props.summary] - 摘要内容（受控）
 * @param {(v: string) => void} [props.onSummaryChange] - 摘要变化回调
 * @param {(content: string) => Promise<string>} [props.onGenerateSummary] - 生成摘要回调
 * @param {(err: Error) => void} [props.onSummaryError] - 生成失败时回调
 */
export default function WikitextEditorPreview({
  wikiText = '',
  onContentChange,
  editable = true,
  theme = 'dark',
  className = '',
  onAddToReference,
  onSendToArticle,
  onWikiLinkClick,
  showSummary = false,
  summary = '',
  onSummaryChange,
  onGenerateSummary,
  onSummaryError,
}) {
  const [viewMode, setViewMode] = useState('preview')
  const [editDraft, setEditDraft] = useState(wikiText)
  const [summaryLoading, setSummaryLoading] = useState(false)

  useEffect(() => {
    if (viewMode === 'preview') setEditDraft(wikiText)
  }, [wikiText, viewMode])

  const effectiveContent = viewMode === 'edit' ? editDraft : wikiText

  const enterEdit = () => {
    setEditDraft(wikiText)
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
          </>
        )}
      </div>
      <div className="flex-1 min-h-[320px] overflow-y-auto flex flex-col">
        {viewMode === 'edit' ? (
          <div className="flex-1 min-h-[280px] flex flex-col gap-2">
            <textarea
              value={editDraft}
              onChange={(e) => {
                setEditDraft(e.target.value)
                onContentChange?.(e.target.value)
              }}
              placeholder="在此编辑 Wikitext 内容…"
              className={textareaCls}
              spellCheck={false}
            />
          </div>
        ) : viewMode === 'summary' ? (
          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto flex flex-col p-4">
            <div className="shrink-0 flex justify-between gap-2 mb-3">
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
                <div className="whitespace-pre-wrap">{summary}</div>
              ) : (
                <p className="text-xs text-muted/70 italic">点击「生成摘要」由 AI 生成结构化分层摘要。</p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto">
            <WikiPreview wikiText={effectiveContent || ''} className="min-h-full p-4" theme={theme} hideActions onWikiLinkClick={onWikiLinkClick} />
          </div>
        )}
      </div>
      <div className="shrink-0 px-4 py-3 border-t border-border flex items-center justify-center gap-3 bg-black/20">
        <WikitextActionButtons
          wikiText={effectiveContent}
          onAddToReference={onAddToReference}
          onSendToArticle={onSendToArticle}
        />
      </div>
    </div>
  )
}
