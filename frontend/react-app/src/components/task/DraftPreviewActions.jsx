/**
 * 草稿预览与操作：复制、发送到写作助手、添加到参考、写入 MediaWiki
 * 统一 SubtitlePreviewActions 与 MarkdownDraftActions 的交互与布局。
 * @param {Object} props
 * @param {string} props.content - 内容（纯文本或 Markdown）
 * @param {'text'|'markdown'} props.format - 内容格式，决定预览与 MediaWiki 转换方式
 * @param {string} [props.copyLabel] - 复制按钮文案
 * @param {string} [props.suggestTitle] - 建议的 MediaWiki 页面标题
 * @param {string} [props.sourceUrl] - 来源 URL（可选）
 * @param {string} [props.sourceType] - 发送到写作助手时的来源类型
 * @param {string} [props.summaryText] - 展开区域摘要文案
 * @param {Function} [props.onWriteSuccess] - 写入 MediaWiki 成功回调
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import MarkdownPreview from '../MarkdownPreview'
import { useToast } from '../ToastModal'
import { mdToWiki } from '../../utils/wikiMdConvert'

const BTN_CLS = 'px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5'

export default function DraftPreviewActions({
  content = '',
  format = 'markdown',
  copyLabel,
  suggestTitle,
  sourceUrl,
  sourceType,
  summaryText = '查看草稿与后续操作',
  onWriteSuccess,
}) {
  const navigate = useNavigate()
  const toast = useToast()
  const [hasEverOpened, setHasEverOpened] = useState(false)
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const [lastCreatedTaskId, setLastCreatedTaskId] = useState(null)

  const effectiveCopyLabel = copyLabel ?? (format === 'text' ? '复制字幕' : '复制 Markdown')
  const effectiveSourceType = sourceType ?? (format === 'text' ? 'speech_to_text' : 'url_to_wiki')

  const handleToggle = (e) => {
    if (e.target.open && !hasEverOpened) setHasEverOpened(true)
  }

  const getWikitext = () => {
    if (format === 'text') {
      return `<pre>\n${(content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}\n</pre>`
    }
    return mdToWiki(content || '')
  }

  const getWriteSummary = () => {
    if (format === 'text') return '从字幕内容写入'
    return sourceUrl ? `从抓取内容写入: ${sourceUrl}` : '从抓取内容写入'
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
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'mediawiki_write',
          priority: 2,
          max_retries: 3,
          metadata: {
            title,
            content: getWikitext(),
            summary: getWriteSummary(),
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
      state: { initialMarkdown: content || '', sourceType: effectiveSourceType },
    })
  }

  const handleAddToReference = () => {
    const params = new URLSearchParams()
    if (sourceUrl) params.set('source_url', sourceUrl)
    if (suggestTitle) params.set('suggest_title', suggestTitle)
    navigate(`/add-reference?${params.toString()}`, {
      state: { addToReference: content || '' },
    })
  }

  const handleCopy = () => {
    const toCopy = content || ''
    if (format === 'markdown') {
      navigator.clipboard?.writeText(toCopy).catch(() => {})
    } else {
      navigator.clipboard?.writeText(toCopy).then(() => toast?.info?.('已复制到剪贴板')).catch(() => {})
    }
  }

  return (
    <details className="text-xs space-y-1" onToggle={handleToggle}>
      <summary className="cursor-pointer text-muted hover:text-fg">
        {summaryText}
      </summary>
      {hasEverOpened && (
        <>
          <div className={`mt-1 border border-border/60 rounded bg-black/20 p-2 ${format === 'text' ? 'max-h-[320px] overflow-y-auto' : ''}`}>
            {format === 'text' ? (
              <pre className="text-xs text-fg/90 whitespace-pre-wrap font-mono leading-relaxed">
                {content || ''}
              </pre>
            ) : (
              <MarkdownPreview markdown={content || ''} className="min-h-[120px]" theme="dark" />
            )}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <button type="button" className={BTN_CLS} onClick={handleCopy}>
              {effectiveCopyLabel}
            </button>
            <button type="button" className={BTN_CLS} onClick={handleSendToArticle}>
              发送到写作助手
            </button>
            <button type="button" className={BTN_CLS} onClick={handleAddToReference}>
              添加到参考
            </button>
            <button
              type="button"
              className={`${BTN_CLS} disabled:opacity-50`}
              onClick={handleWriteToWiki}
              disabled={mwSubmitting}
            >
              {mwSubmitting ? '创建中…' : '写入 MediaWiki'}
            </button>
            {lastCreatedTaskId && (
              <Link to="/tasks" state={{ detailTaskId: lastCreatedTaskId }} className={BTN_CLS}>
                查看任务
              </Link>
            )}
          </div>
        </>
      )}
    </details>
  )
}
