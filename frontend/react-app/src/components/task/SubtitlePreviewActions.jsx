/**
 * 字幕预览与操作：复制、发送到写文章、写入 MediaWiki
 * 与 MarkdownDraftActions 保持一致的交互与按钮布局。
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useToast } from '../ToastModal'

export default function SubtitlePreviewActions({
  content,
  suggestTitle,
  summaryText = '查看字幕与后续操作',
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
      const wikitext = `<pre>\n${(content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}\n</pre>`
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
            summary: '从字幕内容写入',
          },
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.task_id) {
        setLastCreatedTaskId(data.task_id)
        toast?.info?.(`已创建 MediaWiki 写入任务 ${data.task_id.slice(0, 8)}…`)
        onWriteSuccess?.({ title, taskId: data.task_id })
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
    if (suggestTitle) params.set('suggest_title', suggestTitle)
    navigate(`/article-writing?${params.toString()}`, {
      state: { initialMarkdown: content || '', sourceType: 'speech_to_text' },
    })
  }

  const handleAddToReference = () => {
    const params = new URLSearchParams()
    if (suggestTitle) params.set('suggest_title', suggestTitle)
    navigate(`/article-writing?${params.toString()}`, {
      state: { addToReference: content || '' },
    })
  }

  const handleCopy = () => {
    navigator.clipboard?.writeText(content || '').then(() => toast?.info?.('已复制到剪贴板')).catch(() => {})
  }

  return (
    <details className="text-xs space-y-1" onToggle={handleToggle}>
      <summary className="cursor-pointer text-muted hover:text-fg">
        {summaryText}
      </summary>
      {hasEverOpened && (
        <>
          <div className="mt-1 border border-border/60 rounded bg-black/20 p-2 max-h-[320px] overflow-y-auto">
            <pre className="text-xs text-fg/90 whitespace-pre-wrap font-mono leading-relaxed">
              {content || ''}
            </pre>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <button
              type="button"
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
              onClick={handleCopy}
            >
              复制字幕
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
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
              onClick={handleAddToReference}
            >
              添加到参考信息
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
