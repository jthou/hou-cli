/**
 * Markdown 操作按钮：复制、发送到写文章、写入 MediaWiki
 * 供 MarkdownEditorPreview、ArticleWriting 等复用
 */
import { useState } from 'react'
import { mdToWiki } from '../utils/wikiMdConvert'
import { useToast } from './ToastModal'

/**
 * @param {Object} props
 * @param {string} [props.content] - 当前 Markdown 内容
 * @param {(content: string) => void} [props.onCopy] - 复制回调，默认使用剪贴板
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写文章回调，不传则隐藏
 * @param {string} [props.sendToArticleLabel='发送到写文章'] - 按钮文案
 * @param {boolean} [props.showMediaWiki=true] - 是否显示写入 MediaWiki
 * @param {React.ReactNode} [props.extra] - 额外按钮（如「同步到公众号草稿」）
 * @param {string} [props.className] - 容器类名
 */
export default function MarkdownActionButtons({
  content = '',
  onCopy,
  onSendToArticle,
  sendToArticleLabel = '发送到写文章',
  showMediaWiki = true,
  extra,
  className = '',
}) {
  const toast = useToast()
  const [mwDialogOpen, setMwDialogOpen] = useState(false)
  const [mwTitle, setMwTitle] = useState('')
  const [mwSummary, setMwSummary] = useState('')
  const [mwMode, setMwMode] = useState('create') // 'create' | 'append'
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const [mwMdState, setMwMdState] = useState('')
  const [mwWikitextState, setMwWikitextState] = useState('')

  const handleCopy = () => {
    const toCopy = (content || '').trim()
    if (!toCopy) {
      toast?.warning?.('当前无内容可复制')
      return
    }
    if (onCopy) {
      onCopy(toCopy)
      return
    }
    navigator.clipboard.writeText(toCopy).then(
      () => toast?.info?.('已复制到剪贴板'),
      () => toast?.error?.('复制失败')
    )
  }

  const handleSendToArticle = () => {
    const toSend = (content || '').trim()
    if (!toSend) {
      toast?.warning?.('当前无内容可发送')
      return
    }
    onSendToArticle?.(toSend)
  }

  const handleMwDialogOpen = () => {
    const trimmed = (content || '').trim()
    setMwMdState(trimmed)
    setMwWikitextState(mdToWiki(trimmed))
    setMwTitle('')
    setMwSummary('')
    setMwMode('create')
    setMwDialogOpen(true)
  }

  const handleMdChange = (val) => {
    setMwMdState(val)
    setMwWikitextState(mdToWiki(val))
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
      let finalWikitext = toPublish
      if (mwMode === 'append') {
        const getRes = await fetch(`/api/mediawiki/pages/${encodeURIComponent(title)}`)
        const getData = await getRes.json().catch(() => ({}))
        if (!getRes.ok || !getData.success) {
          toast?.warning?.('页面不存在，请使用新建')
          setMwSubmitting(false)
          return
        }
        const existing = (getData.page?.content || '').trim()
        finalWikitext = existing ? existing + '\n\n' + toPublish : toPublish
      }
      const res = await fetch(`/api/mediawiki/pages/${encodeURIComponent(title)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: finalWikitext, summary: (mwSummary || '').trim() || undefined }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.success) {
        toast?.info?.(mwMode === 'append' ? '已追加到 MediaWiki' : '已发布到 MediaWiki')
        setMwDialogOpen(false)
        setMwTitle('')
        setMwSummary('')
        setMwMode('create')
      } else {
        toast?.error?.(data.detail || data.message || '发布失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '发布失败')
    }
    setMwSubmitting(false)
  }

  return (
    <>
      <div className={`flex flex-wrap gap-3 ${className}`.trim()}>
        <button
          type="button"
          onClick={handleCopy}
          className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
        >
          复制 Markdown
        </button>
        {onSendToArticle && (
          <button
            type="button"
            onClick={handleSendToArticle}
            className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
          >
            {sendToArticleLabel}
          </button>
        )}
        {showMediaWiki && (
          <button
            type="button"
            onClick={handleMwDialogOpen}
            className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 text-sm"
          >
            写入 MediaWiki
          </button>
        )}
        {extra}
      </div>

      {mwDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setMwDialogOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full mx-4 max-w-5xl h-[95vh] max-h-[95vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">写入 MediaWiki</h3>
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
              <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-5 min-h-[360px]">
                <div className="flex flex-col min-h-[320px] overflow-hidden">
                  <span className="text-xs text-muted mb-1 block shrink-0">Markdown（可编辑，修改后右侧会同步）</span>
                  <textarea
                    value={mwMdState}
                    onChange={(e) => handleMdChange(e.target.value)}
                    className="flex-1 min-h-[320px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] font-mono resize-y"
                    placeholder="Markdown 内容"
                  />
                </div>
                <div className="flex flex-col min-h-[320px] overflow-hidden">
                  <span className="text-xs text-muted mb-1 block shrink-0">MediaWiki 格式（Wikitext，可编辑）</span>
                  <textarea
                    value={mwWikitextState}
                    onChange={(e) => setMwWikitextState(e.target.value)}
                    className="flex-1 min-h-[320px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] font-mono resize-y"
                    placeholder="Wikitext 内容"
                  />
                </div>
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
                {mwSubmitting ? '提交中…' : mwMode === 'append' ? '追加' : '新建'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
