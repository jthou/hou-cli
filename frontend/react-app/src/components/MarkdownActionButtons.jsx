/**
 * Markdown 操作按钮：复制、发送到写作助手、写入 MediaWiki
 * 供 MarkdownEditorPreview、ArticleWriting 等复用
 * 写入 MediaWiki 与同步到公众号草稿均通过任务队列，可在任务管理中审计。
 */
import { useRef, useState } from 'react'
import { mdToWikiWithImages, wikiToMd } from '../utils/wikiMdConvert'
import {
  getClipboardImageFile,
  insertSnippetAtTextareaCursor,
  snippetForMdWiki,
  snippetForWikitext,
  uploadMediaWikiImageFile,
  batchUploadMarkdownImagesToMediaWiki,
  markdownHasUploadableImageUrls,
  markdownHasRetryableMwUploadImages,
  MW_BATCH_UPLOAD_FAIL_ALT_MARK,
} from '../utils/mediawikiPasteImage'
import { operationFromMwDialogMode } from '../utils/mediawikiWriteOperation'
import { useToast } from './ToastModal'

/**
 * @param {Object} props
 * @param {string} [props.content] - 当前 Markdown 内容
 * @param {(content: string) => void} [props.onCopy] - 复制回调，默认使用剪贴板
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写作助手回调，不传则隐藏
 * @param {string} [props.sendToArticleLabel='发送到写作助手'] - 按钮文案
 * @param {boolean} [props.showMediaWiki=true] - 是否显示写入 MediaWiki
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考回调，不传则隐藏
 * @param {React.ReactNode} [props.extra] - 额外按钮（如「同步到公众号草稿」）
 * @param {string} [props.className] - 容器类名
 * @param {string} [props.sourceUrl] - 原文链接（如微信读书 URL），写入 MediaWiki 时自动追加到文末
 * @param {(nextMarkdown: string) => void} [props.onContentReplace] - 若提供，显示「一键上传全部插图」：上传后写回正文（将 ![](url) 转为 [[File:…]]，与单张预览上传一致）
 */
export default function MarkdownActionButtons({
  content = '',
  onCopy,
  onSendToArticle,
  sendToArticleLabel = '发送到写作助手',
  showMediaWiki = true,
  onAddToReference,
  extra,
  className = '',
  sourceUrl = '',
  onContentReplace,
}) {
  const toast = useToast()
  const [mwDialogOpen, setMwDialogOpen] = useState(false)
  const [mwTitle, setMwTitle] = useState('')
  const [mwSummary, setMwSummary] = useState('')
  /** 新建 | 更新(覆盖) | 追加 —— 对应 metadata.operation：create | edit | append */
  const [mwMode, setMwMode] = useState('edit')
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const [mwMdState, setMwMdState] = useState('')
  const [mwWikitextState, setMwWikitextState] = useState('')
  const mwMdTextareaRef = useRef(null)
  const mwWikiTextareaRef = useRef(null)
  const [mwPasteUploading, setMwPasteUploading] = useState(false)
  const [bulkWikiImgBusy, setBulkWikiImgBusy] = useState(false)
  const [bulkWikiImgProgress, setBulkWikiImgProgress] = useState(null)

  const runBulkWikiUpload = async (onlyRetryMarked) => {
    if (!onContentReplace || bulkWikiImgBusy) return
    const md = content || ''
    if (onlyRetryMarked) {
      if (!markdownHasRetryableMwUploadImages(md)) {
        toast?.warning?.(`正文中没有带「${MW_BATCH_UPLOAD_FAIL_ALT_MARK}」的插图可重试`)
        return
      }
    } else if (!markdownHasUploadableImageUrls(md)) {
      toast?.warning?.('正文中没有可上传的网络/本站图片链接（![](https://…）或 ![]( /api/…））')
      return
    }
    setBulkWikiImgBusy(true)
    setBulkWikiImgProgress(null)
    try {
      const { markdown: next, ok, fail, total } = await batchUploadMarkdownImagesToMediaWiki(md, {
        onProgress: (cur, tot) => setBulkWikiImgProgress({ cur, tot }),
        onlyRetryMarked,
      })
      onContentReplace(next)
      if (fail.length === 0) {
        toast?.success?.(
          onlyRetryMarked
            ? `待重试插图已全部处理（共 ${ok} 张）`
            : `已全部上传并替换为 Wiki 插图（共 ${ok} 张）`
        )
      } else {
        toast?.warning?.(
          `已上传 ${ok}/${total} 张；${fail.length} 张失败。失败项已在 alt 标为「${MW_BATCH_UPLOAD_FAIL_ALT_MARK}」，可搜索正文或点「仅重试待传插图」。详情见控制台。`
        )
        console.warn('[batchUploadMarkdownImagesToMediaWiki]', fail)
      }
    } catch (e) {
      toast?.error?.(e?.message || '批量上传失败')
    } finally {
      setBulkWikiImgBusy(false)
      setBulkWikiImgProgress(null)
    }
  }

  const handleBulkUploadPreviewImages = () => runBulkWikiUpload(false)
  const handleBulkRetryFailedWikiImages = () => runBulkWikiUpload(true)

  const handleMwPasteImage = async (e, mode) => {
    const file = getClipboardImageFile(e)
    if (!file || mwPasteUploading) return
    e.preventDefault()
    const ta = e.target
    const start = ta.selectionStart ?? 0
    const end = ta.selectionEnd ?? start
    setMwPasteUploading(true)
    try {
      const { filename } = await uploadMediaWikiImageFile(file)
      const snippet = mode === 'wikitext' ? snippetForWikitext(filename) : snippetForMdWiki(filename)
      if (mode === 'markdown') {
        let nextMd = ''
        let caret = 0
        setMwMdState((prev) => {
          const r = insertSnippetAtTextareaCursor(prev, start, end, snippet)
          nextMd = r.nextValue
          caret = r.caret
          return r.nextValue
        })
        setMwWikitextState(mdToWikiWithImages(nextMd).wikitext)
        setTimeout(() => {
          const el = mwMdTextareaRef.current
          if (el) {
            el.focus()
            el.setSelectionRange(caret, caret)
          }
        }, 0)
        toast?.info?.(`已上传 ${filename} 并插入 Markdown 引用`)
      } else {
        let nextWiki = ''
        let caret = 0
        setMwWikitextState((prev) => {
          const r = insertSnippetAtTextareaCursor(prev, start, end, snippet)
          nextWiki = r.nextValue
          caret = r.caret
          return r.nextValue
        })
        setMwMdState(wikiToMd(nextWiki))
        setTimeout(() => {
          const el = mwWikiTextareaRef.current
          if (el) {
            el.focus()
            el.setSelectionRange(caret, caret)
          }
        }, 0)
        toast?.info?.(`已上传 ${filename} 并插入 Wikitext 引用`)
      }
    } catch (err) {
      toast?.error?.(err?.message || '图片上传失败')
    } finally {
      setMwPasteUploading(false)
    }
  }

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

  const handleSendToArticle = () => {
    const toSend = (content || '').trim()
    if (!toSend) {
      toast?.warning?.('当前无内容可发送')
      return
    }
    onSendToArticle?.(toSend)
  }

  const handleMwDialogOpen = () => {
    let trimmed = (content || '').trim()
    if (sourceUrl?.trim()) {
      trimmed = trimmed + '\n\n---\n\n原文链接：[' + sourceUrl.trim() + '](' + sourceUrl.trim() + ')'
    }
    setMwMdState(trimmed)
    const { wikitext } = mdToWikiWithImages(trimmed)
    setMwWikitextState(wikitext)
    setMwTitle('')
    setMwSummary('')
    setMwMode('edit')
    setMwDialogOpen(true)
  }

  const handleMdChange = (val) => {
    setMwMdState(val)
    const { wikitext } = mdToWikiWithImages(val)
    setMwWikitextState(wikitext)
  }

  const handleMwSubmit = async () => {
    const title = (mwTitle || '').trim()
    if (!title) {
      toast?.warning?.('请输入页面标题')
      return
    }
    const { wikitext, images } = mdToWikiWithImages(mwMdState || '')
    const toPublish = (wikitext || '').trim()
    if (!toPublish) {
      toast?.warning?.('当前无内容可发布')
      return
    }
    setMwSubmitting(true)
    try {
      const metadata = {
        title,
        content: toPublish,
        summary: (mwSummary || '').trim() || undefined,
        operation: operationFromMwDialogMode(mwMode),
      }
      if (images?.length) metadata.images = images
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'mediawiki_write',
          priority: 2,
          max_retries: 3,
          metadata,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.success) {
        toast?.info?.('任务已创建，可在任务管理中查看执行状态')
        setMwDialogOpen(false)
        setMwTitle('')
        setMwSummary('')
        setMwMode('edit')
      } else {
        toast?.error?.(data.detail || data.message || '创建任务失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '创建任务失败')
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
        {showMediaWiki && onContentReplace && (
          <button
            type="button"
            onClick={handleBulkUploadPreviewImages}
            disabled={bulkWikiImgBusy || !markdownHasUploadableImageUrls(content)}
            title="将正文中所有网络/本站图片链接上传至 MediaWiki，并把 ![](url) 替换为 [[File:…]]（与预览里逐张上传一致）；再打开「写入 MediaWiki」时 wikitext 会随正文更新"
            className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm disabled:opacity-50 disabled:pointer-events-none"
          >
            {bulkWikiImgBusy && bulkWikiImgProgress
              ? `上传插图中 ${bulkWikiImgProgress.cur}/${bulkWikiImgProgress.tot}…`
              : bulkWikiImgBusy
                ? '上传插图中…'
                : '一键上传全部插图到 Wiki'}
          </button>
        )}
        {showMediaWiki && onContentReplace && (
          <button
            type="button"
            onClick={handleBulkRetryFailedWikiImages}
            disabled={bulkWikiImgBusy || !markdownHasRetryableMwUploadImages(content)}
            title={`只上传 alt 中含「${MW_BATCH_UPLOAD_FAIL_ALT_MARK}」的 Markdown 图（批量失败或网络恢复后使用）`}
            className="px-4 py-2 rounded-lg border border-amber-500/50 text-amber-100/90 hover:bg-amber-500/15 text-sm disabled:opacity-40 disabled:pointer-events-none"
          >
            {bulkWikiImgBusy && bulkWikiImgProgress
              ? `重试中 ${bulkWikiImgProgress.cur}/${bulkWikiImgProgress.tot}…`
              : '仅重试待传插图'}
          </button>
        )}
        {onAddToReference && (
          <button
            type="button"
            onClick={() => {
              const toAdd = (content || '').trim()
              if (toAdd) onAddToReference(toAdd)
            }}
            className="px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5 text-sm"
          >
            添加到参考
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
              <div>
                <h3 className="text-lg font-semibold text-white">写入 MediaWiki</h3>
                <p className="text-xs text-muted mt-0.5">
                  创建任务后由任务队列执行，可在任务管理中审计。可在编辑框内直接粘贴截图：自动哈希命名上传并在光标处插入引用
                  {mwPasteUploading ? '（上传中…）' : ''}。
                </p>
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
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="mwModeMd" checked={mwMode === 'create'} onChange={() => setMwMode('create')} className="text-accent" />
                    <span className="text-sm text-white">新建</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="mwModeMd" checked={mwMode === 'edit'} onChange={() => setMwMode('edit')} className="text-accent" />
                    <span className="text-sm text-white">更新</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="mwModeMd" checked={mwMode === 'append'} onChange={() => setMwMode('append')} className="text-accent" />
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
                    ref={mwMdTextareaRef}
                    value={mwMdState}
                    onChange={(e) => handleMdChange(e.target.value)}
                    onPaste={(e) => handleMwPasteImage(e, 'markdown')}
                    disabled={mwPasteUploading}
                    className="flex-1 min-h-[320px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] font-mono resize-y disabled:opacity-60"
                    placeholder="Markdown 内容（可粘贴截图）"
                  />
                </div>
                <div className="flex flex-col min-h-[320px] overflow-hidden">
                  <span className="text-xs text-muted mb-1 block shrink-0">MediaWiki 格式（Wikitext，可编辑）</span>
                  <textarea
                    ref={mwWikiTextareaRef}
                    value={mwWikitextState}
                    onChange={(e) => setMwWikitextState(e.target.value)}
                    onPaste={(e) => handleMwPasteImage(e, 'wikitext')}
                    disabled={mwPasteUploading}
                    className="flex-1 min-h-[320px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-4 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed disabled:opacity-60"
                    placeholder="Wikitext 内容（可粘贴截图）"
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
                {mwSubmitting
                  ? '提交中…'
                  : mwMode === 'append'
                    ? '创建追加任务'
                    : mwMode === 'create'
                      ? '创建新建任务'
                      : '创建更新任务'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
