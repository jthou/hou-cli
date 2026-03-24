/**
 * 网页阅读 - 通过扩展抓取网页正文（DOM 提取），微信读书已拆至 WereadReader
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { htmlToMd } from '../utils/mdToHtml'
import MarkdownEditorPreview from '../components/MarkdownEditorPreview'
import ExtensionNotReadyHint from '../components/ExtensionNotReadyHint'
import PasteButton from '../components/PasteButton'
import PageHeader from '../components/PageHeader'
import { useToast } from '../components/ToastModal'
import { useExtensionReady } from '../hooks/useExtensionReady'
import { usePasteFromClipboard } from '../hooks/usePasteFromClipboard'
import { saveLastReadForContext, loadLastReadForContext } from '../utils/webReaderIndexedDB'
import { fetchSummarize } from '../utils/summarizeApi'

const REQUEST_ID_PREFIX = 'web-reader-'
const STORAGE_KEY_LAST_LEGACY = 'hou-cli-web-reader-last' // 迁移用
const SAVE_DEBOUNCE_MS = 600

/** 微信等：innerHTML 属性里 & 常序列化为 &amp;，需与扩展传来的 URL 逐字替换都对上 */
function applyInlineImageUrlReplacements(html, mappingEntries, origin) {
  let out = html || ''
  const sorted = [...mappingEntries].sort((a, b) => (b[0] || '').length - (a[0] || '').length)
  for (const [orig, apiPath] of sorted) {
    if (!orig || !apiPath) continue
    const full = `${origin}${apiPath}`
    const variants = []
    const push = (s) => {
      if (s && !variants.includes(s)) variants.push(s)
    }
    push(orig)
    if (orig.includes('&') && !orig.includes('&amp;')) push(orig.replace(/&/g, '&amp;'))
    if (orig.includes('&amp;')) push(orig.replace(/&amp;/g, '&'))
    for (const v of variants) {
      const esc = v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      out = out.replace(new RegExp(esc, 'g'), full)
    }
  }
  return out
}

export default function WebReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [urlInput, setUrlInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const extensionReady = useExtensionReady()
  const [viewMode, setViewMode] = useState('markdown') // 'text' | 'html' | 'markdown'
  const timeoutRef = useRef(null)
  const saveDebounceRef = useRef(null)
  const [imgUploadModal, setImgUploadModal] = useState(null) // { src, loading, result: { wikitext } }

  /** 恢复上次阅读内容 */
  useEffect(() => {
    if (data || loading) return
    let cancelled = false
    const run = async () => {
      try {
        let saved = await loadLastReadForContext('web')
        if (!saved) {
          const raw = localStorage.getItem(STORAGE_KEY_LAST_LEGACY)
          if (raw) {
            try {
              saved = JSON.parse(raw)
              if (saved?.markdown || saved?.content) {
                await saveLastReadForContext('web', saved)
                localStorage.removeItem(STORAGE_KEY_LAST_LEGACY)
              }
            } catch (_) {}
          }
        }
        if (!saved?.markdown && !saved?.content) return
        if (cancelled) return
        setData({
          url: saved.url,
          title: saved.title || '上次阅读',
          markdown: saved.markdown || saved.content || '',
          content: saved.content || saved.markdown || '',
          html: saved.html || '',
          summary: saved.summary ?? '',
        })
        if (saved.urlInput) setUrlInput(saved.urlInput)
        if (saved.viewMode) setViewMode(saved.viewMode)
      } catch (_) {}
    }
    run()
    return () => { cancelled = true }
  }, [])

  /** 异步保存上次阅读内容 */
  useEffect(() => {
    if (!data?.markdown && !data?.content) return
    if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    saveDebounceRef.current = setTimeout(() => {
      saveDebounceRef.current = null
      saveLastReadForContext('web', {
        url: data.url,
        urlInput,
        title: data.title,
        markdown: data.markdown || '',
        content: data.content || '',
        html: data.html || '',
        viewMode,
        summary: data.summary ?? '',
      }).catch(() => {})
    }, SAVE_DEBOUNCE_MS)
    return () => {
      if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    }
  }, [data?.url, data?.title, data?.markdown, data?.content, data?.html, data?.summary, urlInput, viewMode])

  const buildHtmlForPreviewIframe = (d) => {
    const base = d.fullPageHtml || d.html
    const baseUrl = d.baseUrl || d.url || ''
    let html = base
    if (!html) return ''
    if (baseUrl && !/<\s*base\s+[^>]*href/i.test(html)) {
      html = html.replace(/<head([^>]*)>/i, '<head$1><base href="' + baseUrl.replace(/"/g, '&quot;') + '">')
    }
    const clickScript = `
      <script>
        document.addEventListener('click', function(e) {
          var a = e.target.closest('a');
          if (!a || !a.href) return;
          var raw = a.getAttribute('href') || '';
          if (raw.indexOf('javascript:') === 0 || raw.indexOf('#') === 0) return;
          var href = a.href;
          if (href.indexOf('http://') === 0 || href.indexOf('https://') === 0) {
            e.preventDefault();
            window.parent.postMessage({ type: 'HOU_CLI_IFRAME_LINK_CLICK', href: href }, '*');
          }
        }, true);
      <\/script>
    `
    return html.replace(/<\/body\s*>/i, clickScript + '</body>')
  }

  const handlePasteFromClipboard = usePasteFromClipboard({
    onPaste: (text) => setUrlInput(text),
    toast,
  })

  const doRead = useCallback((url) => {
    const u = (url || '').trim()
    if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) return
    setUrlInput(u)
    setError(null)
    setData(null)
    setLoading(true)
    const requestId = REQUEST_ID_PREFIX + Date.now()
    // 时间：2026-03-14；理由：微信公众号 CDN 防盗链；方法：扩展 SW fetch + 后端落盘，Markdown 引用本站 URL
    const inlineImages = /mp\.weixin\.qq\.com/.test(u)
    window.postMessage(
      { type: 'HOU_CLI_FETCH', url: u, requestId, apiBase: window.location.origin, inlineImages },
      '*'
    )
    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null
      setLoading((prev) => {
        if (prev) setError('扩展无响应（90 秒超时），请刷新页面后重试')
        return false
      })
    }, 90000)
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === 'HOU_CLI_IFRAME_LINK_CLICK' && e.data?.href) {
        doRead(e.data.href)
        return
      }
      if (e.data?.type !== 'HOU_CLI_FETCH_RESULT' || !e.data?.requestId?.startsWith(REQUEST_ID_PREFIX)) return
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      setLoading(false)
      if (e.data.success) {
        const d = e.data.data
        if (d?.screenshots?.length && !d?.html && !d?.fullPageHtml) {
          setData(null)
          navigate('/weread-reader', { state: { prefillUrl: d?.url || urlInput, fetchData: d } })
          return
        }
        ;(async () => {
          let html = d?.html
          const map = d?.inlineImageMap
          if (html && map && typeof map === 'object' && Object.keys(map).length) {
            try {
              const res = await fetch(`${window.location.origin}/api/web-reader/materialize-inline-images`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  images: Object.entries(map).map(([original_url, data_url]) => ({ original_url, data_url })),
                }),
              })
              const jd = await res.json()
              if (jd.success && jd.mapping && Object.keys(jd.mapping).length) {
                html = applyInlineImageUrlReplacements(html, Object.entries(jd.mapping), window.location.origin)
              }
            } catch (_) {}
          }
          const augmented = d
            ? { ...d, html: html || d.html || '', markdown: html ? htmlToMd(html) : (d.html ? htmlToMd(d.html) : (d.content || '')) }
            : null
          setData(augmented)
        })()
        setError(null)
      } else {
        setError(e.data.error || '抓取失败')
        setData(null)
      }
    }
    window.addEventListener('message', handler)
    return () => {
      window.removeEventListener('message', handler)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [doRead])

  const handleRead = (e) => {
    e.preventDefault()
    const url = (urlInput || '').trim()
    if (!url) {
      setError('请输入 URL')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setError('请使用完整的 http:// 或 https:// URL')
      return
    }
    doRead(url)
  }

  const handleImgUploadToWiki = async () => {
    const src = imgUploadModal?.src
    const width = imgUploadModal?.width || 0
    const height = imgUploadModal?.height || 0
    const isWikiFile = imgUploadModal?.isWikiFile
    const oldWikitext = imgUploadModal?.result?.wikitext
    if (!src) return
    setImgUploadModal((prev) => (prev ? { ...prev, loading: true, result: null } : null))
    try {
      const res = await fetch('/api/mediawiki/upload-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_url: src }),
      })
      const apiData = await res.json()
      if (!res.ok) throw new Error(apiData.detail || '上传失败')
      let wikitext = apiData.wikitext || `[[File:${apiData.filename}]]`
      if (width > 0 || height > 0) {
        const sizePart = height > 0 ? `${width}x${height}px` : `${width}px`
        wikitext = wikitext.replace(/\]\]$/, `|${sizePart}]]`)
      }
      setImgUploadModal((prev) => (prev ? { ...prev, loading: false, result: { ...apiData, wikitext } } : null))
      if (apiData.filename) {
        const isWikiFile = imgUploadModal?.isWikiFile
        const oldWikitext = imgUploadModal?.result?.wikitext
        setData((prev) => {
          if (!prev?.markdown) return prev
          let newMd = prev.markdown
          if (isWikiFile && oldWikitext) {
            newMd = newMd.replaceAll(oldWikitext, wikitext)
          } else {
            const srcRaw = imgUploadModal?.srcRaw || src
            const urlsToTry = [src, srcRaw].filter(Boolean)
            const escapeForRe = (u) => u.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            for (const u of urlsToTry) {
              const re = new RegExp(`!\\[([^\\]]*)\\]\\(${escapeForRe(u)}\\)`, 'g')
              newMd = newMd.replace(re, wikitext)
              if (newMd !== prev.markdown) break
            }
          }
          return newMd !== prev.markdown ? { ...prev, markdown: newMd } : prev
        })
        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(wikitext)
            toast?.success?.(`已插入并复制 [[File:${apiData.filename}]] 到剪贴板`)
          } else {
            toast?.success?.(`已插入 [[File:${apiData.filename}]]`)
          }
        } catch (_) {
          toast?.success?.(`已插入 [[File:${apiData.filename}]]`)
        }
      }
    } catch (err) {
      setImgUploadModal((prev) => (prev ? { ...prev, loading: false, result: { error: err?.message || '上传失败' } } : null))
      toast?.error?.(err?.message || '上传失败')
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="网页阅读"
        subtitle="通过浏览器扩展抓取网页正文（DOM）。微信公众号 mp.weixin.qq.com 会经扩展拉取配图并保存到本机数据目录，Markdown 中引用本站 /api/web-reader/inline-static/ 地址。微信读书请用「微信读书」页。"
      />

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col flex-[0.382] min-w-0 border-r border-border min-h-0">
          <div className="shrink-0 p-4 space-y-2">
            <form onSubmit={handleRead} className="flex gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="flex-1 min-w-0 px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-muted focus:border-accent focus:outline-none text-sm"
              />
              <PasteButton onClick={handlePasteFromClipboard} title="从剪贴板获取 URL" />
              <button
                type="submit"
                disabled={loading || !extensionReady}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 text-sm shrink-0"
              >
                {loading ? '抓取中…' : !extensionReady ? '等待扩展…' : '读取'}
              </button>
            </form>
            {!extensionReady && <ExtensionNotReadyHint />}
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>
          <div className="flex-1 min-h-0 border-t border-border overflow-auto w-full">
            {(data?.html || data?.fullPageHtml) ? (
              <iframe
                title="原始网页"
                srcDoc={buildHtmlForPreviewIframe(data)}
                sandbox="allow-same-origin allow-scripts"
                className="w-full h-full border-0 bg-white"
              />
            ) : (
              <div className="h-full flex items-center justify-center p-6 text-sm text-muted text-center">
                {loading ? (
                  '正在抓取…'
                ) : (
                  <>读取网页后，原始页面将在此显示。</>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-[0.618] overflow-y-auto bg-white/[0.02] p-6">
          {!data && !loading && !error && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              输入 URL 并点击「读取网页」，正文将在此展示。
            </div>
          )}
          {loading && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              正在抓取…
            </div>
          )}
          {data && !loading && (
            <div className="flex flex-col h-full">
              <div className="shrink-0 flex items-center justify-between gap-4 mb-4">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-white truncate">{data.title || '无标题'}</h2>
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline break-all"
                  >
                    {data.url}
                  </a>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setViewMode('markdown')}
                    className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'markdown' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                  >
                    Markdown 预览
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('text')}
                    className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'text' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                  >
                    纯文本
                  </button>
                </div>
              </div>
              <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border bg-white flex flex-col">
                {viewMode === 'markdown' ? (
                  <div className="flex-1 min-h-0 p-4 flex flex-col">
                    <MarkdownEditorPreview
                      className="flex-1 min-h-0"
                      content={data.markdown || ''}
                      onContentChange={(v) => setData((prev) => (prev ? { ...prev, markdown: v, summary: '' } : null))}
                      editable
                      theme="dark"
                      showMediaWiki
                      sourceUrl={data.url || ''}
                      showSummary
                      summary={data.summary ?? ''}
                      onSummaryChange={(v) => setData((prev) => (prev ? { ...prev, summary: v } : null))}
                      onGenerateSummary={(content) => fetchSummarize(content)}
                      onSummaryError={(err) => toast?.warning?.(err?.message || '摘要生成失败')}
                      onAddToReference={(c) => navigate('/add-reference', { state: { addToReference: c } })}
                      onImgClick={(_, d) => {
                        let wikitext = null
                        if (d.isWikiFile && d.wikiFileName) {
                          const md = data?.markdown || ''
                          const escaped = d.wikiFileName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                          const m = md.match(new RegExp(`\\[\\[File:${escaped}(?:\\|[^\\]]*)?\\]\\]`))
                          wikitext = m ? m[0] : `[[File:${d.wikiFileName}]]`
                        }
                        setImgUploadModal({ ...d, loading: false, result: wikitext ? { wikitext } : null })
                      }}
                    />
                  </div>
                ) : (
                  <div className="p-4 text-sm text-muted leading-relaxed whitespace-pre-wrap overflow-y-auto h-full">
                    {data.content || '无内容'}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {imgUploadModal && (
        <div className="fixed bottom-4 right-4 z-50 w-72 max-w-[calc(100vw-2rem)]">
          <div className="bg-surface border border-border rounded-xl p-3 shadow-xl">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-white truncate">{imgUploadModal.isWikiFile ? 'MediaWiki 图片' : '上传到 MediaWiki'}</h3>
              <button type="button" onClick={() => setImgUploadModal(null)} className="text-muted hover:text-white text-lg leading-none shrink-0 ml-1">&times;</button>
            </div>
            <div className="mb-2 max-h-24 overflow-hidden rounded bg-white/5">
              <img src={imgUploadModal.src} alt="" className="max-h-24 w-full object-contain" />
            </div>
            {imgUploadModal.result?.wikitext && (
              <div className="mb-2 p-1.5 rounded bg-white/5 text-xs font-mono text-accent break-all max-h-14 overflow-y-auto">{imgUploadModal.result.wikitext}</div>
            )}
            {imgUploadModal.result?.error && (
              <p className="mb-2 text-xs text-red-400 line-clamp-2">{imgUploadModal.result.error}</p>
            )}
            <div className="flex gap-1.5">
              <button
                type="button"
                onClick={handleImgUploadToWiki}
                disabled={imgUploadModal.loading}
                className="flex-1 px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs disabled:opacity-50"
              >
                {imgUploadModal.loading ? '上传中…' : imgUploadModal.isWikiFile ? '再次上传' : imgUploadModal.result?.wikitext ? '重新上传' : '上传'}
              </button>
              <button type="button" onClick={() => setImgUploadModal(null)} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-muted rounded-lg text-xs">
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
