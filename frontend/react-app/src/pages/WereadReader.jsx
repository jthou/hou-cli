/**
 * 微信读书 - 截图 + Qwen-VL OCR，与网页阅读分离，样式保持一致
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import MarkdownEditorPreview from '../components/MarkdownEditorPreview'
import ExtensionNotReadyHint from '../components/ExtensionNotReadyHint'
import PasteButton from '../components/PasteButton'
import PageHeader from '../components/PageHeader'
import { useToast } from '../components/ToastModal'
import { useExtensionReady } from '../hooks/useExtensionReady'
import { usePasteFromClipboard } from '../hooks/usePasteFromClipboard'
import { useSelectableModels } from '../hooks/useSelectableModels'
import VisionModelSelector from '../components/VisionModelSelector'
import {
  saveScreenshots,
  clearScreenshots,
  loadScreenshots,
  saveLastReadForContext,
  loadLastReadForContext,
} from '../utils/webReaderIndexedDB'

const REQUEST_ID_PREFIX = 'weread-reader-'
const STORAGE_KEY_VISION_MODEL = 'hou-cli-weread-reader-vision-model'
const SAVE_DEBOUNCE_MS = 600
const WEREAD_URL_PATTERN = /weread\.qq\.com/

export default function WereadReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [urlInput, setUrlInput] = useState('')
  const [enlargedImageIndex, setEnlargedImageIndex] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [loadingOcr, setLoadingOcr] = useState(false)
  const extensionReady = useExtensionReady()
  const {
    vision_providers,
    vision_default,
    loading: modelsLoading,
  } = useSelectableModels()
  const location = useLocation()
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

  const doRead = useCallback((url) => {
    const u = (url || '').trim()
    if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) return
    if (!WEREAD_URL_PATTERN.test(u)) {
      setError('请输入微信读书链接（weread.qq.com）')
      return
    }
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
    if (!selectedVisionModel) return
    try {
      localStorage.setItem(STORAGE_KEY_VISION_MODEL, selectedVisionModel)
    } catch (_) {}
  }, [selectedVisionModel])

  useEffect(() => {
    const vp = vision_providers || []
    if (modelsLoading || vp.length === 0) return
    const valid = vp.some((p) =>
      p.models?.some((m) => m.value === selectedVisionModel)
    )
    if (!valid && vision_default) {
      setSelectedVisionModel(vision_default)
    } else if (!valid && vp[0]?.models?.[0]?.value) {
      setSelectedVisionModel(vp[0].models[0].value)
    }
  }, [modelsLoading, vision_providers, vision_default, selectedVisionModel])

  /** 从 WebReader 跳转时：若有 fetchData 直接使用，否则预填 URL 并抓取 */
  useEffect(() => {
    const { prefillUrl, fetchData } = location.state || {}
    if (!prefillUrl && !fetchData) return
    navigate(location.pathname, { replace: true, state: {} })
    if (fetchData?.screenshots?.length) {
      setUrlInput((fetchData.url || prefillUrl || '').trim())
      setData({
        ...fetchData,
        markdown: fetchData.markdown || fetchData.content || '',
        content: fetchData.content || fetchData.markdown || '',
      })
      setError(null)
    } else if (prefillUrl && typeof prefillUrl === 'string' && prefillUrl.trim()) {
      setUrlInput(prefillUrl.trim())
      doRead(prefillUrl.trim())
    }
  }, [location.state?.prefillUrl, location.state?.fetchData, navigate, doRead])

  useEffect(() => {
    if (data || loading || location.state?.prefillUrl || location.state?.fetchData) return
    let cancelled = false
    const run = async () => {
      try {
        const saved = await loadLastReadForContext('weread')
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
          screenshots: screenshots || undefined,
          pendingOcr: false,
        })
        if (saved.urlInput) setUrlInput(saved.urlInput)
      } catch (_) {}
    }
    run()
    return () => { cancelled = true }
  }, [location.state?.prefillUrl])

  useEffect(() => {
    if (!data?.markdown && !data?.content) return
    if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    saveDebounceRef.current = setTimeout(() => {
      saveDebounceRef.current = null
      saveLastReadForContext('weread', {
        url: data.url,
        urlInput,
        title: data.title,
        markdown: data.markdown || '',
        content: data.content || '',
      }).catch(() => {})
    }, SAVE_DEBOUNCE_MS)
    if (data.screenshots?.length) {
      saveScreenshots(data.url, data.screenshots)
    } else {
      clearScreenshots()
    }
    return () => {
      if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    }
  }, [data?.url, data?.title, data?.markdown, data?.content, data?.screenshots, urlInput])

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

  const handlePasteFromClipboard = usePasteFromClipboard({
    onPaste: (text) => setUrlInput(text),
    toast,
  })

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type !== 'HOU_CLI_FETCH_RESULT' || !e.data?.requestId?.startsWith(REQUEST_ID_PREFIX)) return
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      setLoading(false)
      if (e.data.success) {
        const d = e.data.data
        setData(d || null)
        setError(null)
        if (d?.pendingOcr) ocrRequestedRef.current = null
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
  }, [])

  useEffect(() => {
    const images = data?.screenshots || []
    if (!images.length || !data?.pendingOcr || ocrRequestedRef.current === images[0]) return
    ocrRequestedRef.current = images[0]
    setLoadingOcr(true)
    const ocrUrl = `${window.location.origin}/api/web-reader/ocr`
    const vp = vision_providers || []
    const isValidModel = vp.some((p) =>
      p.models?.some((m) => m.value === selectedVisionModel)
    )
    const model =
      (isValidModel ? selectedVisionModel : null) ||
      vision_default ||
      vp[0]?.models?.[0]?.value
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
        setData((prev) => ({
          ...prev,
          content: text,
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
      setError('请输入微信读书链接')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setError('请使用完整的 http:// 或 https:// URL')
      return
    }
    if (!WEREAD_URL_PATTERN.test(url)) {
      setError('请输入微信读书链接（weread.qq.com）')
      return
    }
    doRead(url)
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="微信读书"
        subtitle="通过浏览器扩展抓取微信读书页面截图，使用 Qwen-VL OCR 识别文字。需配置 BAILIAN_API_KEY。"
      />

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col w-80 shrink-0 border-r border-border min-h-0">
          <div className="shrink-0 p-4 space-y-2 min-w-0 overflow-hidden">
            <form onSubmit={handleRead} className="flex gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://weread.qq.com/..."
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
            ) : (
              <div className="h-full flex items-center justify-center p-6 text-sm text-muted text-center">
                {loading ? (
                  '正在抓取截图…'
                ) : (
                  <>
                    读取微信读书后，截图将在此显示。
                    <br />
                    支持 OCR 识别文字，可编辑后写入 MediaWiki。
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto bg-white/[0.02] p-6">
          {!data && !loading && !error && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              输入微信读书链接并点击「读取」，正文将在此展示。
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
                  <h2 className="text-lg font-semibold text-white truncate">{data.title || '微信读书'}</h2>
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline break-all"
                  >
                    {data.url}
                  </a>
                </div>
              </div>
              <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border bg-white flex flex-col">
                {loadingOcr ? (
                  <div className="h-full flex items-center justify-center text-sm text-muted">
                    正在识别文字…
                  </div>
                ) : (
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
