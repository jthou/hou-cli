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

const REQUEST_ID_PREFIX = 'web-reader-'
const STORAGE_KEY_LAST_LEGACY = 'hou-cli-web-reader-last' // 迁移用
const SAVE_DEBOUNCE_MS = 600

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
      }).catch(() => {})
    }, SAVE_DEBOUNCE_MS)
    return () => {
      if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    }
  }, [data?.url, data?.title, data?.markdown, data?.content, data?.html, urlInput, viewMode])

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
    window.postMessage(
      { type: 'HOU_CLI_FETCH', url: u, requestId, apiBase: window.location.origin },
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
        const augmented = d
          ? { ...d, markdown: d.html ? htmlToMd(d.html) : (d.content || '') }
          : null
        setData(augmented)
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

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="网页阅读"
        subtitle="通过浏览器扩展抓取网页正文（DOM 提取），可写入 MediaWiki。微信读书请使用「微信读书」页面。"
      />

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col w-80 shrink-0 border-r border-border min-h-0">
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

        <div className="min-w-0 flex-1 overflow-y-auto bg-white/[0.02] p-6">
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
                      content={data.markdown || ''}
                      onContentChange={(v) => setData((prev) => (prev ? { ...prev, markdown: v } : null))}
                      editable
                      theme="dark"
                      showMediaWiki
                      onAddToReference={(c) => navigate('/add-reference', { state: { addToReference: c } })}
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
    </div>
  )
}
