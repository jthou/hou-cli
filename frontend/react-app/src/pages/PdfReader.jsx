import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/ToastModal'
import MarkdownPreview from '../components/MarkdownPreview'
import ExtensionNotReadyHint from '../components/ExtensionNotReadyHint'
import PasteButton from '../components/PasteButton'
import PageHeader from '../components/PageHeader'
import { useExtensionReady } from '../hooks/useExtensionReady'
import { usePasteFromClipboard } from '../hooks/usePasteFromClipboard'
import { mdToWiki } from '../utils/wikiMdConvert'
import { requestPdfFromExtension } from '../utils/extensionCookies'

export default function PdfReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [filePath, setFilePath] = useState('')
  const [pageCount, setPageCount] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageText, setPageText] = useState('')
  const [loadingPage, setLoadingPage] = useState(false)
  const [error, setError] = useState(null)

  const [mergedPages, setMergedPages] = useState([]) // { page, text }[]
  const [useLayout, setUseLayout] = useState(true)
  const [rangeInput, setRangeInput] = useState('1-1') // 支持 1-8、1,3,5、1-3,5,7-9
  const [loadingRange, setLoadingRange] = useState(false)
  const [sourceInput, setSourceInput] = useState('')
  const [sourceOriginal, setSourceOriginal] = useState('')
  const [recentSources, setRecentSources] = useState([])

  const [mwDialogOpen, setMwDialogOpen] = useState(false)
  const [mwTitle, setMwTitle] = useState('')
  const [mwSummary, setMwSummary] = useState('')
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const extensionReady = useExtensionReady()
  const [loadingResolve, setLoadingResolve] = useState(false)
  const saveLastRef = useRef(null)

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

  /** 恢复上次抓取内容 */
  useEffect(() => {
    try {
      if (typeof window === 'undefined') return
      const raw = localStorage.getItem('pdf_reader_last')
      if (!raw) return
      const saved = JSON.parse(raw)
      if (!saved?.filePath) return
      setFilePath(saved.filePath || '')
      setSourceInput(saved.sourceInput || saved.filePath || '')
      setSourceOriginal(saved.sourceOriginal || saved.filePath || '')
      setPageCount(saved.pageCount ?? null)
      setCurrentPage(saved.currentPage ?? 1)
      setPageText(saved.pageText || '')
      setMergedPages(Array.isArray(saved.mergedPages) ? saved.mergedPages : [])
      setRangeInput(
        saved.rangeInput ||
        (saved.rangeFrom != null && saved.rangeTo != null
          ? `${saved.rangeFrom}-${saved.rangeTo}`
          : '1-1')
      )
      setUseLayout(saved.useLayout !== false)
    } catch {
      // ignore
    }
  }, [])

  /** 保存上次抓取内容（防抖） */
  useEffect(() => {
    if (!filePath || (!pageText && mergedPages.length === 0)) return
    if (saveLastRef.current) clearTimeout(saveLastRef.current)
    saveLastRef.current = setTimeout(() => {
      saveLastRef.current = null
      try {
        const toSave = {
          filePath,
          sourceInput,
          sourceOriginal,
          pageCount,
          currentPage,
          pageText,
          mergedPages,
          rangeInput,
          useLayout,
        }
        localStorage.setItem('pdf_reader_last', JSON.stringify(toSave))
      } catch {
        // ignore
      }
    }, 500)
    return () => {
      if (saveLastRef.current) clearTimeout(saveLastRef.current)
    }
  }, [filePath, sourceInput, sourceOriginal, pageCount, currentPage, pageText, mergedPages, rangeInput, useLayout])

  useEffect(() => {
    if (pageCount && pageCount > 1 && rangeInput === '1-1') {
      setRangeInput(`1-${pageCount}`)
    }
  }, [pageCount])

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

  const mergedPagesSorted = [...mergedPages].sort((a, b) => a.page - b.page)

  const mergedPreviewText = mergedPagesSorted
    .map((p) => {
      const body = (p.text || '').trim() || '(该页未提取到文字内容)'
      return `## 第 ${p.page} 页\n\n${body}`
    })
    .join('\n\n---\n\n')

  const handleClearMergedPages = () => {
    setMergedPages([])
  }

  const handlePasteFromClipboard = usePasteFromClipboard({
    onPaste: (text) => setSourceInput(text),
    toast,
  })

  const handleCopyContent = () => {
    const content =
      mergedPagesSorted.length > 0
        ? mergedPreviewText
        : (pageText || '').trim() || '(该页未提取到文字内容)'
    if (!content.trim()) {
      toast?.warning?.('没有可复制的内容')
      return
    }
    navigator.clipboard?.writeText(content).then(
      () => toast?.info?.('已复制到剪贴板'),
      () => toast?.error?.('复制失败')
    )
  }

  const handleAddToReference = () => {
    const content =
      mergedPagesSorted.length > 0
        ? mergedPreviewText
        : (pageText || '').trim() || ''
    if (!content.trim()) {
      toast?.warning?.('没有可添加的内容')
      return
    }
    navigate('/add-reference', { state: { addToReference: content } })
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
      saveRecentSource(json.path, json.path)
      setPageCount(null)
      setCurrentPage(1)
      setPageText('')
      setError(null)
      setMergedPages([])
      setRangeInput('1-1')
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
        layout: String(useLayout),
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

  const fetchPageRange = async () => {
    if (!filePath || !pageCount) return
    const spec = (rangeInput || '').trim()
    setLoadingRange(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        file_path: filePath,
        layout: String(useLayout),
      })
      if (spec) {
        params.set('pages', spec)
      } else {
        params.set('page_from', '1')
        params.set('page_to', String(pageCount))
      }
      const res = await fetch(`/api/pdf/page-range-text?${params.toString()}`)
      const json = await res.json()
      if (!json.success) {
        throw new Error(json.detail || json.error || '读取失败')
      }
      const pages = Array.isArray(json.pages) ? json.pages : []
      if (pages.length === 0 && !(json.text || '').trim()) {
        toast?.warning?.('该范围内未提取到文字')
        return
      }
      setMergedPages((prev) => {
        const byPage = new Map(prev.map((x) => [x.page, x]))
        pages.forEach((p) => byPage.set(p.page, { page: p.page, text: p.text || '' }))
        return Array.from(byPage.values())
      })
      const pgList = (json.pages || []).map((p) => p.page)
      toast?.info?.(
        `已提取 ${pgList.length} 页` +
          (pgList.length <= 5 ? `：${pgList.join(', ')}` : `：${pgList.slice(0, 3).join(', ')}…`) +
          (useLayout ? '（保持排版）' : '')
      )
    } catch (err) {
      const msg = err.message || String(err)
      setError(msg)
      toast?.error?.(msg)
    } finally {
      setLoadingRange(false)
    }
  }

  const handleResolveAndLoad = async (srcOverride) => {
    const raw = srcOverride ?? sourceInput
    const src = (raw || '').trim()
    if (!src) {
      toast.warning('请输入 PDF 路径或 URL')
      return
    }
    const isUrl = src.startsWith('http://') || src.startsWith('https://')
    if (isUrl && !extensionReady) {
      toast.warning('加载在线 PDF 需安装 Hou CLI 扩展，请在 chrome://extensions 加载 extension 目录')
      return
    }
    setLoadingResolve(true)
    setError(null)
    try {
      let resolvedPath
      if (isUrl) {
        const extRes = await requestPdfFromExtension(src, 60000)
        if (!extRes.success || !extRes.base64) {
          throw new Error(extRes.error || '扩展获取失败')
        }
        const uploadRes = await fetch('/api/pdf/upload-from-extension', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ base64: extRes.base64, original_url: src }),
        })
        const uploadJson = await uploadRes.json()
        if (!uploadRes.ok || !uploadJson.success || !uploadJson.file_path) {
          throw new Error(uploadJson.detail || uploadJson.message || '上传失败')
        }
        resolvedPath = uploadJson.file_path
      } else {
        const res = await fetch('/api/pdf/resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: src }),
        })
        const json = await res.json()
        if (!res.ok || !json.success || !json.file_path) {
          throw new Error(json.detail || json.message || '解析失败')
        }
        resolvedPath = json.file_path
      }
      setFilePath(resolvedPath)
      setSourceOriginal(src)
      setPageCount(null)
      setCurrentPage(1)
      setPageText('')
      setMergedPages([])
      setRangeInput('1-1')
      saveRecentSource(src, resolvedPath)
      await fetchPage(resolvedPath, 1)
    } catch (err) {
      const msg = err.message || String(err)
      setError(msg)
      toast.error('加载 PDF 失败: ' + msg)
    } finally {
      setLoadingResolve(false)
    }
  }

  const submitMediaWikiOutput = async () => {
    const title = (mwTitle || '').trim()
    if (!title) {
      toast.warning('请输入页面标题')
      return
    }
    const content =
      mergedPagesSorted.length > 0
        ? mergedPreviewText
        : (pageText || '').trim() || '(该页未提取到文字内容)'
    if (!content.trim()) {
      toast.warning('没有可写入的内容')
      return
    }
    setMwSubmitting(true)
    try {
      const wikitext = mdToWiki(content)
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
            summary: (mwSummary || '').trim() || (filePath ? `从 PDF 导入: ${filePath.split('/').slice(-1)[0]}` : '从 PDF 导入'),
          },
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.task_id) {
        toast.info(`已创建 MediaWiki 写入任务 ${data.task_id.slice(0, 8)}…`)
        setMwDialogOpen(false)
        setMwTitle('')
        setMwSummary('')
      } else {
        throw new Error(data.detail || data.message || '创建任务失败')
      }
    } catch (e) {
      toast.error(e?.message || '创建任务失败')
    } finally {
      setMwSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="PDF阅读"
        subtitle="支持本地 PDF 或在线 URL（在线需安装 Hou CLI 扩展）。可写入 MediaWiki。"
      />
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：PDF 选择 + 浏览器原生 PDF 预览 + 提取控件 */}
        <div className="flex flex-col w-80 shrink-0 border-r border-border min-w-0 min-h-0">
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden p-6 gap-4">
          <section className="shrink-0 space-y-3">
            <h2 className="text-sm font-semibold text-white">选择 PDF</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (sourceInput.trim()) handleResolveAndLoad()
              }}
              className="flex flex-wrap items-center gap-3 text-xs text-muted"
            >
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
                  placeholder="本地路径或在线 URL（在线需安装 Hou CLI 扩展）"
                  className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-xs text-white placeholder-muted focus:border-accent focus:outline-none"
                />
              </div>
              <PasteButton onClick={handlePasteFromClipboard} size="sm" />
              <button
                type="submit"
                disabled={
                  loadingResolve ||
                  (sourceInput.trim() && (sourceInput.startsWith('http://') || sourceInput.startsWith('https://')) && !extensionReady)
                }
                title={
                  sourceInput.trim() && (sourceInput.startsWith('http://') || sourceInput.startsWith('https://')) && !extensionReady
                    ? '加载在线 PDF 需先安装 Hou CLI 扩展'
                    : undefined
                }
                className="px-3 py-2 border border-border rounded-lg text-xs text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingResolve
                  ? '加载中…'
                  : sourceInput.trim() && (sourceInput.startsWith('http://') || sourceInput.startsWith('https://')) && !extensionReady
                    ? '等待扩展…'
                    : '加载'}
              </button>
            </form>
            {!extensionReady && (
              <div className="mt-2">
                <ExtensionNotReadyHint compact />
              </div>
            )}
            {recentSources.length > 0 && (
              <div className="mt-2 text-[11px] text-muted space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span>最近打开的 PDF</span>
                  {!filePath && (
                    <button
                      type="button"
                      onClick={() => {
                        const first = recentSources[0]
                        const src = first?.original || first?.file_path
                        if (src) {
                          setSourceInput(src)
                          handleResolveAndLoad(src)
                        }
                      }}
                      className="text-amber-400/90 hover:text-amber-400"
                    >
                      恢复上次
                    </button>
                  )}
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
            <section className="flex-1 min-h-0 flex flex-col">
              <h2 className="text-sm font-semibold text-white shrink-0">PDF 预览</h2>
              <div className="flex-1 min-h-0 border border-border rounded-lg bg-black overflow-hidden">
                <iframe
                  src={pdfViewUrl}
                  title="PDF 预览"
                  className="w-full h-full bg-black"
                />
              </div>
            </section>
          )}

          {filePath && (
            <section className="shrink-0 space-y-3">
              <div className="flex flex-nowrap items-center gap-3 text-xs text-muted">
                <span className="shrink-0">共 {pageCount ?? '?'} 页</span>
                <label className="inline-flex items-center gap-1 cursor-pointer select-none shrink-0">
                  <input
                    type="checkbox"
                    checked={useLayout}
                    onChange={(e) => setUseLayout(e.target.checked)}
                    className="rounded border-border bg-transparent text-accent focus:ring-accent"
                  />
                  <span>保持原文缩进排版</span>
                </label>
                {pageCount > 1 && (
                  <div className="flex items-center gap-1 shrink-0">
                    <span>提取范围:</span>
                    <input
                      type="text"
                      value={rangeInput}
                      onChange={(e) => setRangeInput(e.target.value)}
                      placeholder={`1-${pageCount} 或 1,3,5`}
                      className="w-24 px-1.5 py-1 bg-white/5 border border-border rounded text-xs text-white placeholder-muted focus:border-accent focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={fetchPageRange}
                      disabled={loadingRange || !filePath}
                      className="px-2 py-1 border border-border rounded text-xs text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
                    >
                      {loadingRange ? '提取中…' : '提取多页'}
                    </button>
                    {mergedPagesSorted.length > 0 && (
                      <button
                        type="button"
                        onClick={handleClearMergedPages}
                        className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-red-400 hover:border-red-400/60"
                      >
                        清空
                      </button>
                    )}
                  </div>
                )}
              </div>
              {loadingPage && <p className="text-xs text-muted">加载中…</p>}
              {error && <p className="text-xs text-red-400">错误: {error}</p>}
            </section>
          )}
          </div>
        </div>

        {/* 右侧：合并预览 + 操作按钮 */}
        <div className="w-1/2 overflow-y-auto p-6 flex flex-col min-h-0">
          {!filePath && (
            <div className="flex-1 flex items-center justify-center text-sm text-muted">
              选择并加载 PDF 后，可在此查看合并预览并进行复制、添加到参考或写入 MediaWiki。
            </div>
          )}
          {mergedPagesSorted.length > 0 && filePath && (
            <section className="flex-1 min-h-0 flex flex-col border border-border rounded-lg bg-white/5 p-3">
              <div className="shrink-0 flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-white">合并预览</h3>
                <span className="text-[11px] text-muted">
                  共 {mergedPagesSorted.length} 页 · 约 {mergedPreviewText.length} 字
                </span>
              </div>
              <div className="flex-1 min-h-0 overflow-auto border border-border/60 rounded bg-black/20 p-2">
                <MarkdownPreview
                  markdown={mergedPreviewText}
                  className="min-h-[120px]"
                  theme="dark"
                />
              </div>
            </section>
          )}

          {filePath && (pageText || mergedPagesSorted.length > 0) && (
            <div className="mt-4 pt-3 border-t border-border flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={handleCopyContent}
                className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
              >
                复制
              </button>
              <button
                type="button"
                onClick={handleAddToReference}
                className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
              >
                添加到参考
              </button>
              <button
                type="button"
                onClick={() => {
                  setMwDialogOpen(true)
                  setMwTitle('')
                  setMwSummary('')
                }}
                className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
              >
                写入 MediaWiki
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

