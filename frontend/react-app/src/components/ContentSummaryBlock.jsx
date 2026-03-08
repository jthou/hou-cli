/**
 * 可折叠的内容摘要区域，供 MarkdownEditorPreview、ArticleWriting 等复用
 * 摘要支持 Markdown 渲染（结构化分层摘要）
 */
import { useState, useCallback } from 'react'
import MarkdownPreview from './MarkdownPreview'

/**
 * @param {Object} props
 * @param {string} [props.summary] - 摘要内容
 * @param {(v: string) => void} [props.onSummaryChange] - 摘要变化回调
 * @param {(content: string) => Promise<string>} [props.onGenerateSummary] - 生成摘要回调
 * @param {(err: Error) => void} [props.onSummaryError] - 生成失败回调
 * @param {string} [props.content] - 用于生成摘要的正文（空时禁用生成按钮）
 * @param {string} [props.className] - 容器类名
 */
export default function ContentSummaryBlock({
  summary = '',
  onSummaryChange,
  onGenerateSummary,
  onSummaryError,
  content = '',
  className = '',
}) {
  const [expanded, setExpanded] = useState(true)
  const [loading, setLoading] = useState(false)

  const handleGenerate = useCallback(async () => {
    if (!onGenerateSummary || !(content || '').trim()) return
    setLoading(true)
    try {
      const result = await onGenerateSummary(content)
      onSummaryChange?.(result ?? '')
    } catch (err) {
      onSummaryChange?.('')
      onSummaryError?.(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }, [content, onGenerateSummary, onSummaryChange, onSummaryError])

  return (
    <div className={`shrink-0 border-b border-border bg-white/[0.02] ${className}`.trim()}>
      <div
        className="flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-white/5"
        onClick={() => setExpanded((x) => !x)}
      >
        <span className="text-xs text-muted font-medium">内容摘要</span>
        <div className="flex items-center gap-2">
          {onGenerateSummary && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                handleGenerate()
              }}
              disabled={loading || !(content || '').trim()}
              className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 disabled:opacity-50"
            >
              {loading ? '生成中…' : summary ? '重新生成' : '生成摘要'}
            </button>
          )}
          <span className="text-border/60 text-xs">{expanded ? '▼' : '▶'}</span>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-3 pt-0">
          {summary ? (
            <div className="text-sm text-muted [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-1.5 [&_h3]:mb-0.5 [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4">
              <MarkdownPreview markdown={summary} theme="dark" className="p-0 min-h-0 text-sm" />
            </div>
          ) : (
            <p className="text-xs text-muted/70 italic">暂无摘要，点击「生成摘要」由 AI 生成结构化分层摘要。</p>
          )}
        </div>
      )}
    </div>
  )
}
