import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/ToastModal'
import MarkdownEditorPreview from '../components/MarkdownEditorPreview'
import ExtensionNotReadyHint from '../components/ExtensionNotReadyHint'
import PageHeader from '../components/PageHeader'
import { useExtensionReady } from '../hooks/useExtensionReady'
import { requestPdfFromExtension } from '../utils/extensionCookies'
import { fetchSummarize } from '../utils/summarizeApi'

/** 最近列表里展示用：路径取文件名，URL 取路径段或截断，避免预签名链接撑爆布局 */
function shortPdfLabel(originalOrPath) {
  const t = (originalOrPath || '').trim()
  if (!t) return ''
  if (t.startsWith('http://') || t.startsWith('https://')) {
    try {
      const u = new URL(t)
      const segs = u.pathname.split('/').filter(Boolean)
      const last = segs.length ? segs[segs.length - 1] : ''
      const decoded = last ? decodeURIComponent(last.split('?')[0] || last) : ''
      if (decoded && decoded.length <= 36) return decoded
      const head = `${u.hostname.replace(/^www\./, '')}${u.pathname}`.slice(0, 30)
      return head + (t.length > 30 ? '…' : '')
    } catch {
      return t.length > 32 ? `${t.slice(0, 29)}…` : t
    }
  }
  const base = t.split(/[/\\]/).pop() || t
  return base.length > 36 ? `${base.slice(0, 33)}…` : base
}

/** 与后端 pdf_routes._parse_pages_spec 一致，返回升序、去重后的 1-based 页码 */
function parsePagesSpecToOneBased(spec, pageCount) {
  const s = (spec || '').trim().replace(/，/g, ',')
  if (!s) return []
  const seen = new Set()
  for (const part of s.split(',')) {
    const p = part.trim()
    if (!p) continue
    const dash = p.indexOf('-')
    if (dash !== -1) {
      const a = p.slice(0, dash).trim()
      const b = p.slice(dash + 1).trim()
      const lo = parseInt(a, 10)
      const hi = parseInt(b, 10)
      if (Number.isNaN(lo) || Number.isNaN(hi)) continue
      const lo2 = Math.max(1, lo)
      const hi2 = Math.min(pageCount, hi)
      if (lo2 <= hi2) {
        for (let n = lo2; n <= hi2; n++) seen.add(n)
      }
    } else {
      const n = parseInt(p, 10)
      if (!Number.isNaN(n) && n >= 1 && n <= pageCount) seen.add(n)
    }
  }
  return Array.from(seen).sort((a, b) => a - b)
}

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
  /** text：PDF 文本层；vision：逐页渲染 + VL OCR（与 pdf_to_wiki vision 同源） */
  const [extractMethod, setExtractMethod] = useState('text')
  const [useLayout, setUseLayout] = useState(true)
  const [useColumns, setUseColumns] = useState(false) // 按分栏提取（多栏 PDF）
  const [rangeInput, setRangeInput] = useState('1-1') // 支持 1-8、1,3,5、1-3,5,7-9
  const [loadingRange, setLoadingRange] = useState(false)
  /** VL 多页：逐页进度（微信读书式，完成一页追加到底部预览） */
  const [visionRangeProgress, setVisionRangeProgress] = useState(null) // { current, total } | null
  const visionRangeAbortRef = useRef(null)
  const previewScrollRef = useRef(null)
  const [sourceInput, setSourceInput] = useState('')
  const [sourceOriginal, setSourceOriginal] = useState('')
  const [recentSources, setRecentSources] = useState([])

  const extensionReady = useExtensionReady()
  const [loadingResolve, setLoadingResolve] = useState(false)
  const [mergedEditedContent, setMergedEditedContent] = useState(null)
  const [contentSummary, setContentSummary] = useState('')
  const saveLastRef = useRef(null)
  const restoredRef = useRef(false)

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
      setUseColumns(saved.useColumns === true)
      setExtractMethod(saved.extractMethod === 'vision' ? 'vision' : 'text')
      setContentSummary(saved.contentSummary ?? '')
      restoredRef.current = true
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
          useColumns,
          extractMethod,
          contentSummary,
        }
        localStorage.setItem('pdf_reader_last', JSON.stringify(toSave))
      } catch {
        // ignore
      }
    }, 500)
    return () => {
      if (saveLastRef.current) clearTimeout(saveLastRef.current)
    }
  }, [filePath, sourceInput, sourceOriginal, pageCount, currentPage, pageText, mergedPages, rangeInput, useLayout, useColumns, extractMethod, contentSummary])

  useEffect(() => {
    if (pageCount && pageCount > 1 && rangeInput === '1-1') {
      setRangeInput(`1-${pageCount}`)
    }
  }, [pageCount])

  useEffect(() => {
    return () => {
      visionRangeAbortRef.current?.abort()
    }
  }, [])

  /** VL 逐页追加时把右侧预览滚到底部（对齐微信读书式阅读） */
  useEffect(() => {
    if (extractMethod !== 'vision' || !loadingRange) return
    const el = previewScrollRef.current
    if (!el) return
    const id = requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight
    })
    return () => cancelAnimationFrame(id)
  }, [mergedPages, loadingRange, extractMethod])

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

  useEffect(() => {
    setMergedEditedContent(null)
    if (!restoredRef.current) setContentSummary('')
    restoredRef.current = false
  }, [mergedPages])

  const mergedPreviewText = mergedPagesSorted
    .map((p) => {
      const body = (p.text || '').trim() || '(该页未提取到文字内容)'
      return `## 第 ${p.page} 页\n\n${body}`
    })
    .join('\n\n---\n\n')

  const handleClearMergedPages = () => {
    setMergedPages([])
    setMergedEditedContent(null)
  }

  const changeExtractMethod = (m) => {
    if (m !== 'text' && m !== 'vision') return
    if (m === extractMethod) return
    visionRangeAbortRef.current?.abort()
    visionRangeAbortRef.current = null
    setVisionRangeProgress(null)
    setExtractMethod(m)
    setPageText('')
    setMergedPages([])
    setMergedEditedContent(null)
    setContentSummary('')
    toast?.info?.(
      m === 'vision'
        ? '已切换页图识别。若 PDF 已打开，请再点「打开」刷新第 1 页；多页较慢、占额度。'
        : '已切换文本层。若 PDF 已打开，请再点「打开」刷新第 1 页。'
    )
  }

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
      const params = new URLSearchParams({ file_path: path, page: String(page) })
      const endpoint =
        extractMethod === 'vision' ? '/api/pdf/page-vision' : '/api/pdf/page-text'
      if (extractMethod === 'text') {
        params.set('layout', String(useLayout))
        params.set('columns', String(useColumns))
      }
      const res = await fetch(`${endpoint}?${params.toString()}`)
      const json = await res.json()
      if (!res.ok || !json.success) {
        const detail = json.detail
        throw new Error(typeof detail === 'string' ? detail : json.error || '读取失败')
      }
      setFilePath(json.file_path || path)
      setPageCount(json.page_count || null)
      setCurrentPage(json.page || page)
      setPageText(json.text || '')
      setContentSummary('')
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

    if (extractMethod === 'vision') {
      visionRangeAbortRef.current?.abort()
      const ac = new AbortController()
      visionRangeAbortRef.current = ac
      const { signal } = ac

      let pageList
      if (spec) {
        pageList = parsePagesSpecToOneBased(spec, pageCount)
        if (pageList.length === 0) {
          setError('页码范围格式无效，示例：1-8、1,3,5')
          toast?.warning?.('页码范围无效')
          setLoadingRange(false)
          visionRangeAbortRef.current = null
          return
        }
      } else {
        pageList = Array.from({ length: pageCount }, (_, i) => i + 1)
      }

      setVisionRangeProgress({ current: 0, total: pageList.length })
      try {
        for (let i = 0; i < pageList.length; i++) {
          if (signal.aborted) break
          const pageNum = pageList[i]
          setVisionRangeProgress({ current: i + 1, total: pageList.length })
          const params = new URLSearchParams({
            file_path: filePath,
            page: String(pageNum),
          })
          const res = await fetch(`/api/pdf/page-vision?${params.toString()}`, { signal })
          const json = await res.json()
          if (signal.aborted) break
          if (!res.ok || !json.success) {
            const detail = json.detail
            throw new Error(
              typeof detail === 'string' ? detail : json.error || `第 ${pageNum} 页识别失败`
            )
          }
          setMergedPages((prev) => {
            const byPage = new Map(prev.map((x) => [x.page, x]))
            byPage.set(pageNum, { page: pageNum, text: json.text || '' })
            return Array.from(byPage.values()).sort((a, b) => a.page - b.page)
          })
        }
        if (!signal.aborted) {
          toast?.info?.(`页图识别完成，共 ${pageList.length} 页（已陆续追加到下方预览）`)
        }
      } catch (err) {
        if (err?.name === 'AbortError') {
          toast?.info?.('已停止页图识别')
        } else {
          const msg = err.message || String(err)
          setError(msg)
          toast?.error?.(msg)
        }
      } finally {
        setVisionRangeProgress(null)
        setLoadingRange(false)
        if (visionRangeAbortRef.current === ac) visionRangeAbortRef.current = null
      }
      return
    }

    try {
      const params = new URLSearchParams({ file_path: filePath })
      params.set('layout', String(useLayout))
      params.set('columns', String(useColumns))
      if (spec) {
        params.set('pages', spec)
      } else {
        params.set('page_from', '1')
        params.set('page_to', String(pageCount))
      }
      const res = await fetch(`/api/pdf/page-range-text?${params.toString()}`)
      const json = await res.json()
      if (!res.ok || !json.success) {
        const detail = json.detail
        throw new Error(typeof detail === 'string' ? detail : json.error || '读取失败')
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
      const pgList = pages.map((p) => p.page)
      toast?.info?.(
        `已提取 ${pgList.length} 页` +
          (pgList.length <= 5 ? `：${pgList.join(', ')}` : `：${pgList.slice(0, 3).join(', ')}…`) +
          `${useLayout ? '（保持排版）' : ''}${useColumns ? '（分栏）' : ''}`
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

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="PDF阅读" />
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：PDF 选择 + 浏览器原生 PDF 预览 + 提取控件 */}
        <div className="flex flex-col flex-[0.382] min-w-0 border-r border-border min-h-0">
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden p-6 gap-4">
          <section className="shrink-0 space-y-3">
            <div className="flex flex-nowrap items-center gap-x-4 min-w-0 overflow-x-auto pb-0.5">
              <h2 className="text-sm font-semibold text-white shrink-0">1 · 提取方式</h2>
              <div className="flex flex-nowrap items-center gap-x-4 text-xs text-muted shrink-0">
                <label className="inline-flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap">
                  <input
                    type="radio"
                    name="pdf_extract_method"
                    checked={extractMethod === 'text'}
                    onChange={() => changeExtractMethod('text')}
                    className="border-border bg-transparent text-accent focus:ring-accent shrink-0"
                  />
                  <span>文本层（快）</span>
                </label>
                <label
                  className="inline-flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap"
                  title="渲染页图后调用视觉模型，适合扫描件、公式；慢且消耗额度"
                >
                  <input
                    type="radio"
                    name="pdf_extract_method"
                    checked={extractMethod === 'vision'}
                    onChange={() => changeExtractMethod('vision')}
                    className="border-border bg-transparent text-accent focus:ring-accent shrink-0"
                  />
                  <span>页图识别 VL（慢）</span>
                </label>
              </div>
            </div>
            {extractMethod === 'text' && (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted pt-1 border-t border-border/50">
                <span className="shrink-0 text-[11px] text-muted">文本层选项</span>
                <label className="inline-flex items-center gap-1 cursor-pointer select-none shrink-0">
                  <input
                    type="checkbox"
                    checked={useLayout}
                    onChange={(e) => setUseLayout(e.target.checked)}
                    className="rounded border-border bg-transparent text-accent focus:ring-accent"
                  />
                  <span>保持原文缩进排版</span>
                </label>
                <label
                  className="inline-flex items-center gap-1 cursor-pointer select-none shrink-0"
                  title="多栏 PDF 时勾选，可改善左右栏阅读顺序"
                >
                  <input
                    type="checkbox"
                    checked={useColumns}
                    onChange={(e) => setUseColumns(e.target.checked)}
                    disabled={!useLayout}
                    className="rounded border-border bg-transparent text-accent focus:ring-accent disabled:opacity-50"
                  />
                  <span>按分栏提取</span>
                </label>
              </div>
            )}
          </section>

          <section className="shrink-0 space-y-3">
            <h2 className="text-sm font-semibold text-white">2 · 打开 PDF</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (sourceInput.trim()) handleResolveAndLoad()
              }}
              className="flex flex-wrap items-center gap-3 text-xs text-muted"
            >
              <div className="flex items-center gap-2">
                <label className="px-3 py-2 rounded-lg border border-border text-sm text-muted hover:text-fg hover:bg-white/5 cursor-pointer">
                  选择...
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
                  ? '打开中…'
                  : sourceInput.trim() && (sourceInput.startsWith('http://') || sourceInput.startsWith('https://')) && !extensionReady
                    ? '等待扩展…'
                    : '打开'}
              </button>
            </form>
            {!extensionReady && (
              <div className="mt-2">
                <ExtensionNotReadyHint compact />
              </div>
            )}
            {recentSources.length > 0 && (
              <div className="mt-2 flex items-center gap-2 min-w-0 h-7 text-[11px] text-muted">
                <span className="shrink-0 whitespace-nowrap">最近</span>
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
                    className="shrink-0 whitespace-nowrap text-amber-400/90 hover:text-amber-400"
                  >
                    恢复
                  </button>
                )}
                <div className="flex-1 min-w-0 flex items-center gap-1 overflow-x-auto overflow-y-hidden whitespace-nowrap py-0.5">
                  {recentSources.map((item) => {
                    const full = item.original || item.file_path || ''
                    return (
                      <button
                        key={`${item.original}-${item.file_path}`}
                        type="button"
                        onClick={() => {
                          setSourceInput(full)
                          handleResolveAndLoad(full)
                        }}
                        className="shrink-0 max-w-[10rem] truncate inline-block px-2 py-0.5 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 align-middle"
                        title={full}
                      >
                        {shortPdfLabel(full)}
                      </button>
                    )
                  })}
                </div>
                <button
                  type="button"
                  className="shrink-0 whitespace-nowrap text-[11px] text-muted hover:text-fg"
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
            )}
          </section>

          {filePath && (
            <section className="shrink-0 space-y-2">
              <div className="flex flex-nowrap items-center gap-x-2 sm:gap-x-3 min-w-0 overflow-x-auto pb-0.5 text-xs text-muted">
                <h2 className="text-sm font-semibold text-white shrink-0">
                  3 ·{pageCount > 1 ? ' 多页与范围' : ' 状态'}
                </h2>
                <span className="shrink-0 whitespace-nowrap">共 {pageCount ?? '?'} 页</span>
                {pageCount > 1 && (
                  <>
                    <span className="shrink-0 whitespace-nowrap">范围</span>
                    <input
                      type="text"
                      value={rangeInput}
                      onChange={(e) => setRangeInput(e.target.value)}
                      placeholder={`1-${pageCount}`}
                      title={`如 1-${pageCount} 或 1,3,5`}
                      className="w-[5.5rem] shrink-0 px-1.5 py-1 bg-white/5 border border-border rounded text-xs text-white placeholder-muted focus:border-accent focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={fetchPageRange}
                      disabled={loadingRange || !filePath}
                      className="shrink-0 whitespace-nowrap px-2 py-1 border border-border rounded text-xs text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
                    >
                      {loadingRange
                        ? extractMethod === 'vision' && visionRangeProgress
                          ? `VL ${visionRangeProgress.current}/${visionRangeProgress.total}…`
                          : extractMethod === 'vision'
                            ? 'VL…'
                            : '提取中…'
                        : '提取多页'}
                    </button>
                    {loadingRange && extractMethod === 'vision' && (
                      <button
                        type="button"
                        onClick={() => visionRangeAbortRef.current?.abort()}
                        className="shrink-0 whitespace-nowrap px-2 py-1 rounded border border-red-500/50 text-[11px] text-red-300/95 hover:bg-red-500/10"
                      >
                        停止
                      </button>
                    )}
                    {mergedPagesSorted.length > 0 && (
                      <button
                        type="button"
                        onClick={handleClearMergedPages}
                        className="shrink-0 whitespace-nowrap px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-red-400 hover:border-red-400/60"
                      >
                        清空合并
                      </button>
                    )}
                  </>
                )}
              </div>
              {loadingPage && (
                <p className="text-xs text-muted">
                  {extractMethod === 'vision' ? 'VL 识别中，请稍候…' : '加载中…'}
                </p>
              )}
              {error && <p className="text-xs text-red-400">错误: {error}</p>}
            </section>
          )}

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
          </div>
        </div>

        {/* 右侧：合并预览 + 操作按钮，占满剩余宽度 */}
        <div
          ref={previewScrollRef}
          className="flex-[0.618] min-w-0 overflow-y-auto p-6 flex flex-col min-h-0"
        >
          {!filePath && (
            <div className="flex-1 flex items-center justify-center text-sm text-muted">
              选择并加载 PDF 后，可在此查看合并预览并进行复制、添加到参考或写入 MediaWiki。
            </div>
          )}
          {filePath && (pageText || mergedPagesSorted.length > 0) && (
            <div className="flex-1 min-h-0 flex flex-col rounded-lg border border-border bg-white overflow-hidden">
              {mergedPagesSorted.length > 0 && (
                <div className="shrink-0 px-4 py-2 border-b border-border text-xs text-muted">
                  共 {mergedPagesSorted.length} 页 · 约 {mergedPreviewText.length} 字
                </div>
              )}
              <div className="flex-1 min-h-0 p-4 flex flex-col">
                <MarkdownEditorPreview
                  className="flex-1 min-h-0"
                  content={
                    mergedPagesSorted.length > 0
                      ? (mergedEditedContent ?? mergedPreviewText)
                      : (pageText || '').trim()
                  }
                  onContentChange={(v) => {
                    if (mergedPagesSorted.length > 0) {
                      setMergedEditedContent(v)
                    } else {
                      setPageText(v)
                    }
                    setContentSummary('')
                  }}
                  editable
                  theme="dark"
                  showMediaWiki
                  showSummary
                  summary={contentSummary}
                  onSummaryChange={setContentSummary}
                  onGenerateSummary={(content) => fetchSummarize(content)}
                  onSummaryError={(err) => toast?.warning?.(err?.message || '摘要生成失败')}
                  onAddToReference={(content) =>
                    navigate('/add-reference', { state: { addToReference: content } })
                  }
                />
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  )
}

