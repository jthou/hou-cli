import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { htmlToMd } from '../utils/mdToHtml'
import MarkdownPreview from '../components/MarkdownPreview'
import MarkdownEditorPreview from '../components/MarkdownEditorPreview'
import ExtensionNotReadyHint from '../components/ExtensionNotReadyHint'
import PasteButton from '../components/PasteButton'
import PageHeader from '../components/PageHeader'
import { useToast } from '../components/ToastModal'
import { useExtensionReady } from '../hooks/useExtensionReady'
import { usePasteFromClipboard } from '../hooks/usePasteFromClipboard'
import { useSelectableModels } from '../hooks/useSelectableModels'
import VisionModelSelector from '../components/VisionModelSelector'
import { saveScreenshots, clearScreenshots, loadScreenshots, saveLastRead, loadLastRead } from '../utils/webReaderIndexedDB'

const REQUEST_ID_PREFIX = 'web-reader-'
const STORAGE_KEY_LAST_LEGACY = 'hou-cli-web-reader-last' // 迁移用
const STORAGE_KEY_VISION_MODEL = 'hou-cli-web-reader-vision-model'
const SAVE_DEBOUNCE_MS = 600

export default function WebReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [urlInput, setUrlInput] = useState('')
  const [enlargedImageIndex, setEnlargedImageIndex] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [loadingOcr, setLoadingOcr] = useState(false)
  const extensionReady = useExtensionReady()
  const [viewMode, setViewMode] = useState('markdown') // 'text' | 'html' | 'markdown'
  const {
    vision_providers,
    vision_default,
    loading: modelsLoading,
  } = useSelectableModels()
  const [selectedVisionModel, setSelectedVisionModel] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY_VISION_MODEL) || ''
    } catch {
      return ''
    }
  })
  const timeoutRef = useRef(null)
  const ocrRequestedRef = useRef(null)
  const saveDebounceRef = useRef(null)

  /** 持久化视觉模型选择 */
  useEffect(() => {
    if (!selectedVisionModel) return
    try {
      localStorage.setItem(STORAGE_KEY_VISION_MODEL, selectedVisionModel)
    } catch (_) {}
  }, [selectedVisionModel])

  /** 加载后校验：若当前选择不在列表中，重置为默认 */
  useEffect(() => {
    if (modelsLoading || vision_providers.length === 0) return
    const valid = vision_providers.some((p) =>
      p.models?.some((m) => m.value === selectedVisionModel)
    )
    if (!valid && vision_default) {
      setSelectedVisionModel(vision_default)
    } else if (!valid && vision_providers[0]?.models?.[0]?.value) {
      setSelectedVisionModel(vision_providers[0].models[0].value)
    }
  }, [modelsLoading, vision_providers, vision_default, selectedVisionModel])

  /** 恢复上次阅读内容（异步 IndexedDB，避免 localStorage 同步阻塞） */
  useEffect(() => {
    if (data || loading) return
    let cancelled = false
    const run = async () => {
      try {
        let saved = await loadLastRead()
        if (!saved) {
          const raw = localStorage.getItem(STORAGE_KEY_LAST_LEGACY)
          if (raw) {
            try {
              saved = JSON.parse(raw)
              if (saved?.markdown || saved?.content) {
                await saveLastRead(saved)
                localStorage.removeItem(STORAGE_KEY_LAST_LEGACY)
              }
            } catch (_) {}
          }
        }
        if (!saved?.markdown && !saved?.content) return
        let screenshots = null
        if (saved.url) {
          screenshots = await loadScreenshots(saved.url)
        }
        if (cancelled) return
        setData({
          url: saved.url,
          title: saved.title || '上次阅读',
          markdown: saved.markdown || saved.content || '',
          content: saved.content || saved.markdown || '',
          html: saved.html || '',
          screenshots: screenshots || undefined,
          pendingOcr: false,
        })
        if (saved.urlInput) setUrlInput(saved.urlInput)
        if (saved.viewMode) setViewMode(saved.viewMode)
      } catch (_) {}
    }
    run()
    return () => { cancelled = true }
  }, [])

  /** 异步保存上次阅读内容（防抖 + IndexedDB，避免主线程阻塞） */
  useEffect(() => {
    if (!data?.markdown && !data?.content) return
    if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    saveDebounceRef.current = setTimeout(() => {
      saveDebounceRef.current = null
      const toSave = {
        url: data.url,
        urlInput,
        title: data.title,
        markdown: data.markdown || '',
        content: data.content || '',
        html: data.html || '',
        viewMode,
      }
      saveLastRead(toSave).catch(() => {})
    }, SAVE_DEBOUNCE_MS)
    if (data.screenshots?.length) {
      saveScreenshots(data.url, data.screenshots)
    } else {
      clearScreenshots()
    }
    return () => {
      if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    }
  }, [data?.url, data?.title, data?.markdown, data?.content, data?.html, data?.screenshots, urlInput, viewMode])

  useEffect(() => {
    if (enlargedImageIndex == null || !data?.screenshots?.length) return
    const handler = (e) => {
      if (e.key === 'Escape') setEnlargedImageIndex(null)
      if (e.key === 'ArrowLeft' && enlargedImageIndex > 0) setEnlargedImageIndex((i) => i - 1)
      if (e.key === 'ArrowRight' && enlargedImageIndex < data.screenshots.length - 1) setEnlargedImageIndex((i) => i + 1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [enlargedImageIndex, data?.screenshots?.length])

  /** 左侧 iframe 用：完整页面或正文，注入链接点击拦截 */
  const buildHtmlForPreviewIframe = (d) => {
    const base = d.fullPageHtml || d.html
    const baseUrl = d.baseUrl || d.url || ''
    let html = base
    if (!html) return ''
    // 确保有 base 标签，便于相对链接解析
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
    setLoadingOcr(false)
    ocrRequestedRef.current = null
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
        const augmented = d
          ? { ...d, markdown: d.html ? htmlToMd(d.html) : (d.content || '') }
          : null
        setData(augmented)
        setError(null)
        if (augmented?.pendingOcr) ocrRequestedRef.current = null
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

  useEffect(() => {
    const images = data?.screenshots || []
    if (!images.length || !data?.pendingOcr || ocrRequestedRef.current === images[0]) return
    ocrRequestedRef.current = images[0]
    setLoadingOcr(true)
    const apiBase = window.location.origin
    const ocrUrl = `${apiBase}/api/web-reader/ocr`
    const isValidModel = vision_providers.some((p) =>
      p.models?.some((m) => m.value === selectedVisionModel)
    )
    const model =
      (isValidModel ? selectedVisionModel : null) ||
      vision_default ||
      vision_providers[0]?.models?.[0]?.value
    const ocrOne = (img) =>
      fetch(ocrUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: img, ...(model ? { model } : {}) }),
      }).then((r) => r.json())
    Promise.all(images.map(ocrOne))
      .then((results) => {
        const texts = results.map((r) => (r.success ? (r.text || '').trim() : '')).filter(Boolean)
        const text = texts.join('\n\n')
        const html = text ? text.split(/\n\n+/).map((p) => '<p>' + p.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>').join('\n') : ''
        setData((prev) => ({
          ...prev,
          content: text,
          html,
          markdown: text,
          pendingOcr: false,
        }))
      })
      .catch((err) => {
        setError('OCR 识别失败：' + (err?.message || '请确认后端已启动'))
        setData((prev) => ({ ...prev, pendingOcr: false }))
      })
      .finally(() => setLoadingOcr(false))
  }, [
    data?.screenshots,
    data?.pendingOcr,
    selectedVisionModel,
    vision_default,
    vision_providers,
  ])

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
        subtitle="通过浏览器扩展抓取网页正文，可写入 MediaWiki。微信读书使用截图 + Qwen-VL OCR，需配置 BAILIAN_API_KEY。"
      />

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col w-[45%] min-w-[320px] max-w-[600px] border-r border-border shrink-0">
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
                disabled={loading || loadingOcr || !extensionReady}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 text-sm shrink-0"
              >
                {loading ? '抓取中…' : loadingOcr ? '识别中…' : !extensionReady ? '等待扩展…' : '读取'}
              </button>
            </form>
            <VisionModelSelector
              value={selectedVisionModel}
              onChange={setSelectedVisionModel}
              providers={vision_providers}
              defaultModel={vision_default}
              loading={modelsLoading}
              className="mt-2"
            />
            {!extensionReady && <ExtensionNotReadyHint />}
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>
          <div className="flex-1 min-h-0 border-t border-border overflow-auto w-full">
            {data?.screenshots?.length ? (
              <div className="w-full py-2 space-y-2">
                {data.screenshots.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`页面截图 ${i + 1}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => setEnlargedImageIndex(i)}
                    onKeyDown={(e) => e.key === 'Enter' && setEnlargedImageIndex(i)}
                    className="w-full max-w-full h-auto object-contain bg-white rounded block cursor-pointer hover:ring-2 hover:ring-accent/50 transition-shadow"
                  />
                ))}
                {data?.pendingOcr && (
                  <p className="text-xs text-muted text-center">
                    共 {data.screenshots.length} 张截图，正在识别…
                  </p>
                )}
              </div>
            ) : (data?.html || data?.fullPageHtml) ? (
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
                  <>
                    读取网页后，原始页面将在此显示。
                    <br />
                    微信读书会显示截图，普通网页显示 HTML 预览。
                  </>
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
              正在抓取截图…
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
                {!data.screenshots?.length && (
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
                )}
              </div>
              <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border bg-white flex flex-col">
                {loadingOcr ? (
                  <div className="h-full flex items-center justify-center text-sm text-muted">
                    正在识别文字…
                  </div>
                ) : data.screenshots?.length ? (
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
                ) : viewMode === 'markdown' ? (
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

      {enlargedImageIndex != null && data?.screenshots?.[enlargedImageIndex] && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setEnlargedImageIndex(null)}
        >
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setEnlargedImageIndex(null) }}
            className="absolute right-4 top-4 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white text-2xl leading-none"
            title="关闭"
          >
            ×
          </button>
          {enlargedImageIndex > 0 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setEnlargedImageIndex((i) => i - 1) }}
              className="absolute left-4 top-1/2 -translate-y-1/2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm"
            >
              上一张
            </button>
          )}
          <img
            src={data.screenshots[enlargedImageIndex]}
            alt={`截图 ${enlargedImageIndex + 1}`}
            className="max-w-[95vw] max-h-[95vh] object-contain rounded shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
          {enlargedImageIndex < data.screenshots.length - 1 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setEnlargedImageIndex((i) => i + 1) }}
              className="absolute right-4 top-1/2 -translate-y-1/2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm"
            >
              下一张
            </button>
          )}
          <span className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-white/70">
            {enlargedImageIndex + 1} / {data.screenshots.length} · Esc 或点击空白关闭
          </span>
        </div>
      )}
    </div>
  )
}
