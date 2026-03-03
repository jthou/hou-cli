import { useState, useEffect } from 'react'
import { useToast } from '../components/ToastModal'
import MarkdownPreview from '../components/MarkdownPreview'

export default function PdfReader() {
  const toast = useToast()
  const [filePath, setFilePath] = useState('')
  const [pageCount, setPageCount] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageText, setPageText] = useState('')
  const [loadingPage, setLoadingPage] = useState(false)
  const [error, setError] = useState(null)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const [mergedPages, setMergedPages] = useState([]) // { page, text }[]
  const [useCurrentPageContext, setUseCurrentPageContext] = useState(true)
  const [useMergedContext, setUseMergedContext] = useState(false)
  const [sourceInput, setSourceInput] = useState('')
  const [downloadStatus, setDownloadStatus] = useState('')
  const [sourceOriginal, setSourceOriginal] = useState('')
  const [recentSources, setRecentSources] = useState([])

  const pdfViewUrl =
    filePath && filePath.trim()
      ? `/api/pdf/view?file_path=${encodeURIComponent(filePath)}`
      : ''

  useEffect(() => {
    try {
      if (typeof window === 'undefined') return
      const raw = window.localStorage.getItem('pdf_reader_recent_sources')
      if (!raw) return
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) {
        setRecentSources(arr)
      }
    } catch {
      // ignore
    }
  }, [])

  const saveRecentSource = (original, path) => {
    if (!original && !path) return
    if (typeof window === 'undefined') return
    const orig = (original || path || '').trim()
    const fp = (path || '').trim()
    if (!orig && !fp) return
    const now = Date.now()
    setRecentSources((prev) => {
      const filtered = prev.filter(
        (item) => item.original !== orig && item.file_path !== fp
      )
      const next = [{ original: orig, file_path: fp, opened_at: now }, ...filtered].slice(0, 8)
      try {
        window.localStorage.setItem('pdf_reader_recent_sources', JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
  }

  const isCurrentPageSelected = mergedPages.some((p) => p.page === currentPage)

  const mergedPagesSorted = [...mergedPages].sort((a, b) => a.page - b.page)

  const mergedPreviewText = mergedPagesSorted
    .map((p) => {
      const body = (p.text || '').trim() || '(该页未提取到文字内容)'
      return `## 第 ${p.page} 页\n\n${body}`
    })
    .join('\n\n---\n\n')

  const handleToggleCurrentPageInMerge = () => {
    const text = (pageText || '').trim()
    if (isCurrentPageSelected) {
      setMergedPages((prev) => prev.filter((p) => p.page !== currentPage))
      return
    }
    if (!text) {
      toast?.warning?.('当前页没有可加入合并的文字内容')
      return
    }
    setMergedPages((prev) => {
      const others = prev.filter((p) => p.page !== currentPage)
      return [...others, { page: currentPage, text }]
    })
  }

  const handleClearMergedPages = () => {
    setMergedPages([])
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/task-queue/upload-input-file', {
        method: 'POST',
        body: form,
      })
      const json = await res.json()
      if (!json.success || !json.path) {
        throw new Error(json.detail || json.message || '上传失败')
      }
      setFilePath(json.path)
      setSourceInput(json.path)
      setSourceOriginal(json.path)
      setDownloadStatus(`已保存到服务器: ${json.path}`)
      saveRecentSource(json.path, json.path)
      setPageCount(null)
      setCurrentPage(1)
      setPageText('')
      setError(null)
      setMergedPages([])
      setUseCurrentPageContext(true)
      setUseMergedContext(false)
      await fetchPage(json.path, 1)
    } catch (err) {
      const msg = err.message || String(err)
      setError(msg)
      toast.error('上传 PDF 失败: ' + msg)
    } finally {
      // 清空 input，否则无法再次选择同一个文件
      e.target.value = ''
    }
  }

  const fetchPage = async (path, page) => {
    if (!path) return
    setLoadingPage(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        file_path: path,
        page: String(page),
      })
      const res = await fetch(`/api/pdf/page-text?${params.toString()}`)
      const json = await res.json()
      if (!json.success) {
        throw new Error(json.detail || json.error || '读取失败')
      }
      setFilePath(json.file_path || path)
      setPageCount(json.page_count || null)
      setCurrentPage(json.page || page)
      setPageText(json.text || '')
    } catch (err) {
      const msg = err.message || String(err)
      setError(msg)
    } finally {
      setLoadingPage(false)
    }
  }

  const handleResolveAndLoad = async (srcOverride) => {
    const raw = srcOverride ?? sourceInput
    const src = (raw || '').trim()
    if (!src) {
      toast.warning('请输入 PDF 路径或 URL')
      return
    }
    setDownloadStatus('下载/解析中…')
    setError(null)
    try {
      const res = await fetch('/api/pdf/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: src }),
      })
      const json = await res.json()
      if (!res.ok || !json.success || !json.file_path) {
        throw new Error(json.detail || json.message || '下载或解析失败')
      }
      const resolvedPath = json.file_path
      setFilePath(resolvedPath)
      setSourceOriginal(json.original || src)
      setDownloadStatus(
        json.downloaded
          ? `已从网络下载到本地: ${resolvedPath}`
          : `已解析本地路径: ${resolvedPath}`
      )
      setPageCount(null)
      setCurrentPage(1)
      setPageText('')
      setMergedPages([])
      setUseCurrentPageContext(true)
      setUseMergedContext(false)
      saveRecentSource(json.original || src, resolvedPath)
      await fetchPage(resolvedPath, 1)
    } catch (err) {
      const msg = err.message || String(err)
      setDownloadStatus(`下载/解析失败: ${msg}`)
      setError(msg)
      toast.error('加载 PDF 失败: ' + msg)
    }
  }

  const handleChangePage = async (delta) => {
    if (!filePath || !pageCount) return
    const target = currentPage + delta
    if (target < 1 || target > pageCount) return
    await fetchPage(filePath, target)
  }

  const handleGotoPage = async (page) => {
    if (!filePath || !pageCount) return
    if (!page || page < 1 || page > pageCount) return
    await fetchPage(filePath, page)
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim()) return
    const question = input.trim()
    setInput('')

    const nextMessages = [...messages, { role: 'user', content: question }]
    setMessages(nextMessages)
    setSending(true)
    try {
      const historyText = nextMessages
        .map((m) => `${m.role === 'user' ? '用户' : '助手'}: ${m.content}`)
        .join('\n')

      const MAX_CONTEXT = 4000
      let pdfContextParts = []

      if (useCurrentPageContext) {
        const text = (pageText || '').trim()
        if (text) {
          const truncated =
            text.length > MAX_CONTEXT
              ? text.slice(0, MAX_CONTEXT) + '\n...[内容过长，已截断]'
              : text
          const pageInfo = filePath
            ? `（文件: ${filePath.split('/').slice(-1)[0] || filePath} 第 ${currentPage} 页）`
            : ''
          pdfContextParts.push(`下面是 PDF 第 ${currentPage} 页${pageInfo} 的文字内容：\n\n${truncated}\n`)
        }
      }

      if (useMergedContext && mergedPagesSorted.length > 0) {
        const mergedText = mergedPreviewText.trim()
        if (mergedText) {
          const truncated =
            mergedText.length > MAX_CONTEXT * 2
              ? mergedText.slice(0, MAX_CONTEXT * 2) + '\n...[合并内容过长，已截断]'
              : mergedText
          pdfContextParts.push(
            `下面是用户从多个 PDF 页中选择并合并的重点内容（按页码排序）：\n\n${truncated}\n`
          )
        }
      }

      const pdfContext = pdfContextParts.length > 0 ? pdfContextParts.join('\n') + '\n' : ''

      const prompt = `${pdfContext}${historyText}\n\n请基于以上 PDF 内容（如有）和对话历史，回答用户的最新问题。`

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: prompt,
          context_type: 'pdf_reader',
        }),
      })
      const json = await res.json()
      if (json.status !== 'success' || !json.response) {
        throw new Error(json.error || '回答失败')
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: json.response }])
    } catch (err) {
      const msg = err.message || String(err)
      toast.error('提问失败: ' + msg)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">PDF 阅读</h1>
      </header>
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：PDF 选择 + 浏览器原生 PDF 预览 + 页文字 */}
        <div className="w-1/2 border-r border-border overflow-y-auto p-6 space-y-4">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-white">选择 PDF</h2>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
              <div className="flex items-center gap-2">
                <label className="px-3 py-2 rounded-lg border border-border text-sm text-muted hover:text-fg hover:bg-white/5 cursor-pointer">
                  选择本地 PDF
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </label>
              </div>
              <div className="flex-1 min-w-[200px]">
                <input
                  type="text"
                  value={sourceInput}
                  onChange={(e) => setSourceInput(e.target.value)}
                  placeholder="或输入服务器上的 PDF 路径 / 在线 URL，点击右侧加载"
                  className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-xs text-white placeholder-muted focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={handleResolveAndLoad}
                className="px-3 py-2 border border-border rounded-lg text-xs text-muted hover:text-fg hover:bg-white/5"
              >
                加载
              </button>
            </div>
            {downloadStatus && (
              <p className="mt-1 text-[11px] text-muted break-all">
                {downloadStatus}
              </p>
            )}
            {recentSources.length > 0 && (
              <div className="mt-2 text-[11px] text-muted space-y-1">
                <div className="flex items-center justify-between">
                  <span>最近打开的 PDF</span>
                  <button
                    type="button"
                    className="text-[11px] text-muted hover:text-fg"
                    onClick={() => {
                      setRecentSources([])
                      try {
                        if (typeof window !== 'undefined') {
                          window.localStorage.removeItem('pdf_reader_recent_sources')
                        }
                      } catch {
                        // ignore
                      }
                    }}
                  >
                    清空
                  </button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {recentSources.map((item) => (
                    <button
                      key={`${item.original}-${item.file_path}`}
                      type="button"
                      onClick={() => {
                        const src = item.original || item.file_path
                        setSourceInput(src)
                        handleResolveAndLoad(src)
                      }}
                      className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 max-w-full truncate"
                      title={item.original || item.file_path}
                    >
                      {(item.original || item.file_path || '').split('/').slice(-1)[0] ||
                        item.original ||
                        item.file_path}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>

          {filePath && pdfViewUrl && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-white">PDF 预览</h2>
              <div className="border border-border rounded-lg bg-black overflow-hidden">
                <iframe
                  src={pdfViewUrl}
                  title="PDF 预览"
                  className="w-full h-[420px] bg-black"
                />
              </div>
              <p className="text-[11px] text-muted">
                使用浏览器自带的 PDF 工具栏进行缩放、翻页、下载等操作。
              </p>
            </section>
          )}

          {filePath && (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs text-muted">
                  当前来源:{' '}
                  <span className="break-all">
                    {sourceOriginal || filePath}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted">
                <span>
                  页码:
                  {' '}
                  {pageCount ? `${currentPage} / ${pageCount}` : '未知'}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleChangePage(-1)}
                    disabled={!filePath || currentPage <= 1 || loadingPage}
                    className="px-2 py-1 border border-border rounded text-xs text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
                  >
                    上一页
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChangePage(1)}
                    disabled={!filePath || (pageCount && currentPage >= pageCount) || loadingPage}
                    className="px-2 py-1 border border-border rounded text-xs text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
                  >
                    下一页
                  </button>
                  <input
                    type="number"
                    min={1}
                    max={pageCount || undefined}
                    value={currentPage}
                    onChange={(e) => {
                      const v = Number(e.target.value) || 1
                      setCurrentPage(v)
                    }}
                    onBlur={(e) => {
                      const v = Number(e.target.value) || 1
                      handleGotoPage(v)
                    }}
                    className="w-16 px-2 py-1 bg-white/5 border border-border rounded text-xs text-white focus:border-accent focus:outline-none"
                  />
                </div>
              </div>
              {loadingPage ? (
                <p className="text-xs text-muted">加载第 {currentPage} 页内容中…</p>
              ) : error ? (
                <p className="text-xs text-red-400">错误: {error}</p>
              ) : (
                <>
                  <div className="mt-2 border border-border rounded-lg bg-black/30 max-h-[260px] overflow-auto p-3 text-xs text-muted whitespace-pre-wrap leading-relaxed">
                    {pageText || '该页未提取到文字内容。'}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-muted">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleToggleCurrentPageInMerge}
                        className={`px-2.5 py-1 rounded border text-[11px] ${
                          isCurrentPageSelected
                            ? 'border-accent/60 text-accent bg-accent/10'
                            : 'border-border text-muted hover:text-fg hover:bg-white/5'
                        }`}
                      >
                        {isCurrentPageSelected ? '已加入合并' : '将本页加入合并'}
                      </button>
                      {mergedPagesSorted.length > 0 && (
                        <button
                          type="button"
                          onClick={handleClearMergedPages}
                          className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-red-400 hover:border-red-400/60"
                        >
                          清空已选页
                        </button>
                      )}
                    </div>
                    {mergedPagesSorted.length > 0 && (
                      <div className="text-right">
                        <span>
                          已选 {mergedPagesSorted.length} 页：{' '}
                          {mergedPagesSorted
                            .map((p) => p.page)
                            .sort((a, b) => a - b)
                            .slice(0, 6)
                            .join(', ')}
                          {mergedPagesSorted.length > 6 ? '…' : ''}
                        </span>
                      </div>
                    )}
                  </div>
                </>
              )}
            </section>
          )}
        </div>

        {/* 右侧：合并预览 + 对话窗口 */}
        <div className="w-1/2 overflow-y-auto p-6 flex flex-col">
          <h2 className="text-sm font-semibold text-white mb-3">基于 PDF 的问答</h2>

          {mergedPagesSorted.length > 0 && (
            <section className="mb-4 border border-border rounded-lg bg-white/5 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-white">合并预览（发送到写文章的草稿）</h3>
                <span className="text-[11px] text-muted">
                  共 {mergedPagesSorted.length} 页 · 约 {mergedPreviewText.length} 字
                </span>
              </div>
              <div className="max-h-40 overflow-auto border border-border/60 rounded bg-black/20 p-2">
                <MarkdownPreview
                  markdown={mergedPreviewText}
                  className="min-h-[120px]"
                  theme="dark"
                />
              </div>
            </section>
          )}

          <div className="flex-1 border border-border rounded-lg bg-white/5 p-3 overflow-y-auto space-y-2 text-xs">
            {messages.length === 0 && (
              <p className="text-muted">
                先在左侧选择 PDF 并加载某一页，然后在下面输入问题，模型会结合该页文字和上下文对话回答。
              </p>
            )}
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`rounded-lg px-3 py-2 ${
                  m.role === 'user'
                    ? 'bg-accent/20 text-accent'
                    : 'bg-black/30 text-muted'
                }`}
              >
                <div className="text-[11px] font-semibold mb-1">
                  {m.role === 'user' ? '你' : '助手'}
                </div>
                <div className="whitespace-pre-wrap break-words text-xs">
                  {m.content}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted">
              <span className="font-semibold">本次提问上下文：</span>
              <label className="inline-flex items-center gap-1 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useCurrentPageContext}
                  onChange={(e) => setUseCurrentPageContext(e.target.checked)}
                  className="rounded border-border bg-transparent text-accent focus:ring-accent"
                />
                <span>包含当前页文字</span>
              </label>
              <label className="inline-flex items-center gap-1 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useMergedContext}
                  onChange={(e) => setUseMergedContext(e.target.checked)}
                  disabled={mergedPagesSorted.length === 0}
                  className="rounded border-border bg-transparent text-accent focus:ring-accent disabled:opacity-40"
                />
                <span>
                  包含合并文本
                  {mergedPagesSorted.length > 0 && `（已选 ${mergedPagesSorted.length} 页）`}
                </span>
              </label>
            </div>
            <form onSubmit={handleSend} className="flex items-center gap-2">
              <textarea
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入你想根据 PDF 内容提问的问题…"
                className="flex-1 px-3 py-2 bg-white/5 border border-border rounded-lg text-xs text-white placeholder-muted focus:border-accent focus:outline-none resize-none"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {sending ? '发送中…' : '发送'}
              </button>
            </form>
          </div>

          {mergedPagesSorted.length > 0 && (
            <section className="mt-4 border border-border rounded-lg bg-white/5 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-white">合并预览（将写入 MediaWiki 的全文）</h3>
                <span className="text-[11px] text-muted">
                  共 {mergedPagesSorted.length} 页 · 约 {mergedPreviewText.length} 字
                </span>
              </div>
              <div className="max-h-64 overflow-auto border border-border/60 rounded bg-black/20 p-2 text-[11px] text-muted whitespace-pre-wrap leading-relaxed">
                {mergedPreviewText}
              </div>
            </section>
          )}

          {filePath && (pageText || mergedPagesSorted.length > 0) && (
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setMwDialogOpen(true)
                  setMwTitle('')
                  setMwSummary('')
                }}
                className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
              >
                当前页写入 MediaWiki
              </button>
            </div>
          )}
        </div>
      </div>

      {mwDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setMwDialogOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">当前 PDF 页写入 MediaWiki</h3>
              {/* 标题在正文说明里区分「单页」与「多页合并」 */}
              <button
                type="button"
                onClick={() => setMwDialogOpen(false)}
                className="text-muted hover:text-fg text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted">
                {mergedPagesSorted.length > 0
                  ? '将已选择的多页 PDF 文本合并后，以 Wikitext 形式写入指定页面，不存在则创建。'
                  : '将当前 PDF 页提取到的文字内容以 Wikitext 形式写入指定页面，不存在则创建。'}
              </p>
              <div>
                <label className="block text-sm text-muted mb-1">页面标题 *</label>
                <input
                  type="text"
                  value={mwTitle}
                  onChange={(e) => setMwTitle(e.target.value)}
                  placeholder="MediaWiki 页面标题"
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">编辑摘要（选填）</label>
                <input
                  type="text"
                  value={mwSummary}
                  onChange={(e) => setMwSummary(e.target.value)}
                  placeholder="本次写入说明，例如：从某 PDF 第 N 页导入"
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>
            <div className="shrink-0 flex gap-3 px-5 py-4 border-t border-border bg-surface">
              <button
                type="button"
                onClick={() => setMwDialogOpen(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg"
              >
                取消
              </button>
              <button
                type="button"
                onClick={submitMediaWikiOutput}
                disabled={mwSubmitting || !mwTitle.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50"
              >
                {mwSubmitting ? '写入中…' : '写入'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

