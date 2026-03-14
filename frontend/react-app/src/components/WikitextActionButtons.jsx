/**
 * Wikitext 操作按钮：复制 Wikitext、写入 MediaWiki、添加到参考、发送到写作助手
 * 供 WikitextEditorPreview 使用，直接操作 Wikitext，写入 MediaWiki 时无需转换
 */
import { useState } from 'react'
import { wikiToMd } from '../utils/wikiMdConvert'
import { useToast } from './ToastModal'

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - 当前 Wikitext 内容
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考（传入 Markdown）
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写作助手（传入 Markdown）
 */
export default function WikitextActionButtons({
  wikiText = '',
  onAddToReference,
  onSendToArticle,
}) {
  const toast = useToast()
  const [mwDialogOpen, setMwDialogOpen] = useState(false)
  const [mwTitle, setMwTitle] = useState('')
  const [mwSummary, setMwSummary] = useState('')
  const [mwMode, setMwMode] = useState('create')
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const [mwWikitextState, setMwWikitextState] = useState('')

  const handleCopy = () => {
    const toCopy = (wikiText || '').trim()
    if (!toCopy) {
      toast?.warning?.('当前无内容可复制')
      return
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(toCopy).then(
        () => toast?.info?.('已复制到剪贴板'),
        () => fallbackCopy(toCopy)
      )
      return
    }
    fallbackCopy(toCopy)
  }

  const fallbackCopy = (text) => {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (ok) toast?.info?.('已复制到剪贴板')
      else toast?.error?.('复制失败')
    } catch {
      toast?.error?.('复制失败')
    }
  }

  const handleMwDialogOpen = () => {
    setMwWikitextState((wikiText || '').trim())
    setMwTitle('')
    setMwSummary('')
    setMwMode('create')
    setMwDialogOpen(true)
  }

  const handleMwSubmit = async () => {
    const title = (mwTitle || '').trim()
    if (!title) {
      toast?.warning?.('请输入页面标题')
      return
    }
    const toPublish = (mwWikitextState || '').trim()
    if (!toPublish) {
      toast?.warning?.('当前无内容可发布')
      return
    }
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
            content: toPublish,
            summary: (mwSummary || '').trim() || undefined,
            operation: mwMode === 'append' ? 'append' : 'edit',
          },
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.success) {
        toast?.info?.('任务已创建，可在任务管理中查看执行状态')
        setMwDialogOpen(false)
        setMwTitle('')
        setMwSummary('')
        setMwMode('create')
      } else {
        toast?.error?.(data.detail || data.message || '创建任务失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '创建任务失败')
    }
    setMwSubmitting(false)
  }

  const handleAddToReference = () => {
    const trimmed = (wikiText || '').trim()
    if (!trimmed) {
      toast?.warning?.('当前无内容可添加')
      return
    }
    const md = wikiToMd(trimmed)
    onAddToReference?.(md)
  }

  const handleSendToArticle = () => {
    const trimmed = (wikiText || '').trim()
    if (!trimmed) {
      toast?.warning?.('当前无内容可发送')
      return
    }
    const md = wikiToMd(trimmed)
    onSendToArticle?.(md)
  }

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleCopy}
          className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
        >
          复制 Wikitext
        </button>
        <button
          type="button"
          onClick={handleMwDialogOpen}
          className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 text-sm"
        >
          写入 MediaWiki
        </button>
        {onAddToReference && (
          <button
            type="button"
            onClick={handleAddToReference}
            className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
          >
            添加到参考
          </button>
        )}
        {onSendToArticle && (
          <button
            type="button"
            onClick={handleSendToArticle}
            className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
          >
            发送到写作助手
          </button>
        )}
      </div>

      {mwDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setMwDialogOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full mx-4 max-w-4xl h-[95vh] max-h-[95vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-6 py-4 border-b border-border">
              <div>
                <h3 className="text-lg font-semibold text-white">写入 MediaWiki</h3>
                <p className="text-xs text-muted mt-0.5">直接使用 Wikitext，无需转换。创建任务后由任务队列执行。</p>
              </div>
              <button type="button" onClick={() => setMwDialogOpen(false)} className="text-muted hover:text-fg text-2xl leading-none">×</button>
            </div>
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden p-6">
              <div className="shrink-0 flex flex-wrap gap-4 items-end mb-4">
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-sm text-muted mb-1">页面标题 *</label>
                  <input
                    type="text"
                    value={mwTitle}
                    onChange={(e) => setMwTitle(e.target.value)}
                    placeholder="MediaWiki 页面标题"
                    className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="mwMode" checked={mwMode === 'create'} onChange={() => setMwMode('create')} className="text-accent" />
                    <span className="text-sm text-white">新建</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="mwMode" checked={mwMode === 'append'} onChange={() => setMwMode('append')} className="text-accent" />
                    <span className="text-sm text-white">追加</span>
                  </label>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-sm text-muted mb-1">编辑摘要（选填）</label>
                  <input
                    type="text"
                    value={mwSummary}
                    onChange={(e) => setMwSummary(e.target.value)}
                    placeholder="本次修改说明"
                    className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              </div>
              <div className="flex-1 min-h-0 flex flex-col min-h-[360px]">
                <span className="text-xs text-muted mb-1 block shrink-0">Wikitext（直接写入，无需转换）</span>
                <textarea
                  value={mwWikitextState}
                  onChange={(e) => setMwWikitextState(e.target.value)}
                  className="flex-1 min-h-[320px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-4 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed"
                  placeholder="Wikitext 内容"
                />
              </div>
            </div>
            <div className="shrink-0 flex gap-3 px-6 py-4 border-t border-border bg-surface">
              <button type="button" onClick={() => setMwDialogOpen(false)} className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg">取消</button>
              <button
                type="button"
                onClick={handleMwSubmit}
                disabled={mwSubmitting || !mwTitle.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50"
              >
                {mwSubmitting ? '创建中…' : mwMode === 'append' ? '创建追加任务' : '创建任务'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
