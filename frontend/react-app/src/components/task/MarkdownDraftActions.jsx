/**
 * Markdown 草稿的预览与操作：复制、发送到写文章、写入 MediaWiki
 * 供 url_to_wiki、pdf_to_wiki 等产出 Markdown 草稿的任务结果复用。
 * 内容按需渲染：首次展开时才挂载 MarkdownPreview，避免大量结果时性能问题。
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import MarkdownPreview from '../MarkdownPreview'
import { useToast } from '../ToastModal'
import { mdToWiki } from '../../utils/wikiMdConvert'

export default function MarkdownDraftActions({
  markdown,
  sourceUrl,
  suggestTitle,
  sourceType = 'url_to_wiki',
  summaryText = '查看 Markdown 草稿与后续操作',
  onWriteSuccess,
}) {
  const navigate = useNavigate()
  const toast = useToast()
  const [hasEverOpened, setHasEverOpened] = useState(false)
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const [lastCreatedTaskId, setLastCreatedTaskId] = useState(null)

  const handleToggle = (e) => {
    if (e.target.open && !hasEverOpened) setHasEverOpened(true)
  }

  const handleWriteToWiki = async () => {
    let title = (suggestTitle || '').trim()
    if (!title) {
      const input = window.prompt('请输入 MediaWiki 页面标题')
      title = (input || '').trim()
    }
    if (!title) return
    setMwSubmitting(true)
    try {
      const wikitext = mdToWiki(markdown)
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'mediawiki_write',
          priority: 2,
          max_retries: 3,
          metadata: {
            title,
            content: wikitext,
            summary: sourceUrl ? `从抓取内容写入: ${sourceUrl}` : '从抓取内容写入',
          },
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.task_id) {
        setLastCreatedTaskId(data.task_id)
        toast?.info?.(`已创建 MediaWiki 写入任务 ${data.task_id.slice(0, 8)}…`)
        onWriteSuccess?.({ sourceUrl, title, taskId: data.task_id })
      } else {
        throw new Error(data.detail || data.message || '创建任务失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '创建任务失败')
    }
    setMwSubmitting(false)
  }

  const handleSendToArticle = () => {
    const params = new URLSearchParams()
    if (sourceUrl) params.set('source_url', sourceUrl)
    if (suggestTitle) params.set('suggest_title', suggestTitle)
    navigate(`/article-writing?${params.toString()}`, {
      state: { initialMarkdown: markdown, sourceType },
    })
  }

  const handleCopy = () => {
    navigator.clipboard?.writeText(markdown).catch(() => {})
  }

  return (
    <details className="text-xs space-y-1" onToggle={handleToggle}>
      <summary className="cursor-pointer text-muted hover:text-fg">
        {summaryText}
      </summary>
      {hasEverOpened && (
        <>
          <div className="mt-1 border border-border/60 rounded bg-black/20 p-2">
            <MarkdownPreview
              markdown={markdown}
              className="min-h-[120px]"
              theme="dark"
            />
          </div>
      <div className="flex flex-wrap gap-2 mt-2">
        <button
          type="button"
          className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
          onClick={handleCopy}
        >
          复制 Markdown
        </button>
        <button
          type="button"
          className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
          onClick={handleSendToArticle}
        >
          发送到写文章
        </button>
        <button
          type="button"
          className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
          onClick={handleWriteToWiki}
          disabled={mwSubmitting}
        >
          {mwSubmitting ? '创建中…' : '写入 MediaWiki'}
        </button>
        {lastCreatedTaskId && (
          <Link
            to="/tasks"
            state={{ detailTaskId: lastCreatedTaskId }}
            className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
          >
            查看任务
          </Link>
        )}
      </div>
        </>
      )}
    </details>
  )
}
