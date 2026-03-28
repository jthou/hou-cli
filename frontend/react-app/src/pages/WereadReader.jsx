/**
 * 微信读书：左侧为分屏截屏（OCR）+ DOM 插图缩略图；右侧为阅读器 DOM 转 Markdown（无左侧 HTML iframe，与 WebReader 不同）。
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import MarkdownEditorPreview from '../components/MarkdownEditorPreview'
import ZoomPanFigure from '../components/ZoomPanFigure'
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
import { fetchSummarize } from '../utils/summarizeApi'
import { htmlToMd } from '../utils/mdToHtml'
import { materializeInlineImagesFromMap } from '../utils/webReaderInlineImages'
import {
  extractMarkdownImages,
  extractMaterializedImagesFromHtml,
  findOriginalUrlForPreviewImgSrc,
  materializedUrlsFromMapping,
  mergeImageEntries,
  resolveOriginalUrlForMaterializedUrl,
} from '../utils/markdownImages'

const REQUEST_ID_PREFIX = 'weread-reader-'
/** 扩展仅拉图（不截图）；requestId 须仍以 REQUEST_ID_PREFIX 开头以便共用结果通道 */
const IMAGES_ONLY_REQUEST_PREFIX = `${REQUEST_ID_PREFIX}images-`
const STORAGE_KEY_VISION_MODEL = 'hou-cli-weread-reader-vision-model'
const SAVE_DEBOUNCE_MS = 600
const WEREAD_URL_PATTERN = /weread\.qq\.com/

/** 已有足够纯文本，或已有 Markdown 插图链接时，不必再自动 OCR */
function wereadDomEnoughForSkipAutoOcr(markdown, content) {
  const t = ((content || '') + '').trim()
  if (t.length >= 80) return true
  const md = (markdown || '').trim()
  if (md.length > 40 && /!\[[^\]]*\]\([^)]+\)/.test(md)) return true
  return false
}

/**
 * DOM 插图条目：除 materialize 反查外，若 Markdown 里仍是微信 CDN 直链，也视为原图 URL（用于展示链接与重新下载）。
 */
function inferWereadDomOriginalUrl(imUrl, map, origin) {
  const resolved = resolveOriginalUrlForMaterializedUrl(imUrl, map, origin)
  if (resolved) return resolved
  const u = (imUrl || '').trim().replace(/&amp;/g, '&')
  if (!u.startsWith('http://') && !u.startsWith('https://')) return undefined
  if (u.includes('/api/web-reader/inline-static/')) return undefined
  if (
    /weread\.qq\.com/i.test(u) ||
    /res\.weread\.qq\.com/i.test(u) ||
    /i\.weread\.qq\.com/i.test(u) ||
    (/\.myqcloud\.com/i.test(u) && /weread|wrepub|qqread/i.test(u))
  ) {
    return u
  }
  return undefined
}

export default function WereadReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [urlInput, setUrlInput] = useState('')
  /** 左侧大图预览：分屏截图或 DOM 已下载插图，共用 ZoomPanFigure 弹层 */
  const [figureLightbox, setFigureLightbox] = useState(null)
  const [loading, setLoading] = useState(false)
  /** 扩展「仅拉图」进行中（与整章读取 loading 独立） */
  const [imagesOnlyBusy, setImagesOnlyBusy] = useState(false)
  /** DOM 缩略图「重新下载」：当前正在拉取的原图 URL（用于按钮文案与禁用） */
  const [domRedownloadOriginalUrl, setDomRedownloadOriginalUrl] = useState(null)
  const domRefetchBusyRef = useRef(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [loadingOcr, setLoadingOcr] = useState(false)
  /** { cur, total } 顺序 OCR 进度 */
  const [ocrProgress, setOcrProgress] = useState(null)
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
  const imagesOnlyTimeoutRef = useRef(null)
  const ocrRequestedRef = useRef(null)
  const ocrBusyRef = useRef(false)
  /** 用户点「停止」或「重新开始」时置 true；当前张 fetch 用 AbortController 中断 */
  const ocrStopRef = useRef(false)
  const fetchAbortRef = useRef(null)
  /** 本轮 OCR 开始前的正文，用于「重新开始」还原 */
  const ocrBaselineRef = useRef('')
  const ocrNextIndexRef = useRef(0)
  const screenshotsRef = useRef([])
  /** 供 fetchData / 恢复等早于 runOcrSequential 声明的 effect 调用 */
  const runOcrSeqRef = useRef(null)
  const saveDebounceRef = useRef(null)
  /** null | running | paused */
  const [ocrPhase, setOcrPhase] = useState(null)
  const [ocrNextIndex, setOcrNextIndex] = useState(0)
  /** 是否已跑过 OCR（用于显示「重新开始」） */
  const [ocrTouched, setOcrTouched] = useState(false)
  /** 勾选多张后「按序识别并追加到文末」进行中 */
  const [ocrMultiBatchBusy, setOcrMultiBatchBusy] = useState(false)
  const [ocrMultiProgress, setOcrMultiProgress] = useState(null)
  /** 分屏截图多选（按勾选顺序排序后依次 OCR，结果逐段追加到右侧正文末尾） */
  const [selectedShotIndices, setSelectedShotIndices] = useState(() => new Set())
  const [imgUploadModal, setImgUploadModal] = useState(null)
  const dataRef = useRef(null)

  useEffect(() => {
    dataRef.current = data
  }, [data])

  /**
   * 微信读书：章节插图来自扩展对阅读器 DOM 的拉图（inline-static），与左侧「分屏截图」是两路数据。
   * 列表从右侧 Markdown 与 materialize 后的 HTML 合并解析（WereadReader 不做网页阅读那种左侧 HTML iframe）。
   */
  const downloadedArticleImages = useMemo(() => {
    const md = data?.markdown || data?.content || ''
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    const fromMd = extractMarkdownImages(md)
    const fromHtml = extractMaterializedImagesFromHtml(data?.html || '', origin)
    const fromMaterialize = (data?.materializedImageUrls || [])
      .map((u) => ({ alt: '插图', url: String(u || '').trim() }))
      .filter((x) => x.url)
    const merged = mergeImageEntries(fromMd, fromHtml, fromMaterialize)
    const map = data?.inlineMaterializedByOriginal
    return merged.map((im) => ({
      ...im,
      originalUrl: inferWereadDomOriginalUrl(im.url, map, origin),
    }))
  }, [data?.markdown, data?.content, data?.html, data?.materializedImageUrls, data?.inlineMaterializedByOriginal])

  const doRead = useCallback((url) => {
    const u = (url || '').trim()
    if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) return
    if (!WEREAD_URL_PATTERN.test(u)) {
      setError('请输入微信读书链接（weread.qq.com）')
      return
    }
    setUrlInput(u)
    setError(null)
    ocrStopRef.current = true
    try {
      fetchAbortRef.current?.()
    } catch (_) {}
    ocrBusyRef.current = false
    setOcrPhase(null)
    ocrNextIndexRef.current = 0
    setOcrNextIndex(0)
    setOcrTouched(false)
    setSelectedShotIndices(new Set())
    ocrBaselineRef.current = ''
    const keepEditor = ((dataRef.current?.markdown || dataRef.current?.content || '').trim().length > 0)
    if (!keepEditor) {
      setData(null)
    }
    setLoadingOcr(false)
    setOcrProgress(null)
    ocrRequestedRef.current = null
    setLoading(true)
    const requestId = REQUEST_ID_PREFIX + Date.now()
    window.postMessage(
      {
        type: 'HOU_CLI_FETCH',
        url: u,
        requestId,
        apiBase: window.location.origin,
        inlineImages: true,
      },
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

  const handleWereadImagesOnly = useCallback(() => {
    const u = (urlInput || data?.url || '').trim()
    if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) {
      toast?.warning?.('请输入完整微信读书链接')
      return
    }
    if (!WEREAD_URL_PATTERN.test(u)) {
      toast?.warning?.('请输入微信读书链接（weread.qq.com）')
      return
    }
    if (!extensionReady || loading || imagesOnlyBusy) return
    setUrlInput((prev) => (prev.trim() ? prev : u))
    setError(null)
    setImagesOnlyBusy(true)
    const requestId = IMAGES_ONLY_REQUEST_PREFIX + Date.now()
    window.postMessage(
      {
        type: 'HOU_CLI_FETCH',
        url: u,
        requestId,
        apiBase: window.location.origin,
        inlineImages: true,
        wereadImagesOnly: true,
      },
      '*'
    )
    if (imagesOnlyTimeoutRef.current) clearTimeout(imagesOnlyTimeoutRef.current)
    imagesOnlyTimeoutRef.current = setTimeout(() => {
      imagesOnlyTimeoutRef.current = null
      setImagesOnlyBusy(false)
      toast?.warning?.('扩展无响应（120 秒超时），请重试')
    }, 120000)
  }, [urlInput, data, extensionReady, loading, imagesOnlyBusy, toast])

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
    if (fetchData?.screenshots?.length || fetchData?.html || fetchData?.inlineImageMap) {
      setUrlInput((fetchData.url || prefillUrl || '').trim())
      ;(async () => {
        let html = fetchData.html
        const map = fetchData.inlineImageMap
        let materializedMapping = null
        let inlineImageMapAttemptCount = 0
        if (html && map && typeof map === 'object') {
          inlineImageMapAttemptCount = Object.keys(map).length
        }
        if (html && map && typeof map === 'object' && Object.keys(map).length) {
          const { html: nh, mapping } = await materializeInlineImagesFromMap(
            html,
            map,
            window.location.origin
          )
          html = nh
          materializedMapping = mapping
        }
        const origin = window.location.origin
        const materializedImageUrls = materializedMapping
          ? materializedUrlsFromMapping(materializedMapping, origin)
          : []
        let markdown = html ? htmlToMd(html) : ''
        markdown = markdown || fetchData.markdown || fetchData.content || ''
        const textForDomEnough = markdown || fetchData.content || ''
        const domEnough = wereadDomEnoughForSkipAutoOcr(markdown, textForDomEnough)
        const contentOut = markdown || fetchData.content || ''
        const shots = fetchData.screenshots || []
        screenshotsRef.current = shots
        setData({
          ...fetchData,
          html: html || fetchData.html || '',
          markdown,
          content: contentOut,
          pendingOcr: !!(shots.length && !domEnough),
          materializedImageUrls,
          inlineMaterializedByOriginal: materializedMapping ? { ...materializedMapping } : {},
          inlineImageMapAttemptCount,
        })
        setSelectedShotIndices(new Set())
        ocrStopRef.current = false
        setOcrPhase(null)
        setOcrTouched(false)
        ocrNextIndexRef.current = 0
        setOcrNextIndex(0)
      })()
      setError(null)
    } else if (prefillUrl && typeof prefillUrl === 'string' && prefillUrl.trim()) {
      setUrlInput(prefillUrl.trim())
      doRead(prefillUrl.trim())
    }
  }, [location.state?.prefillUrl, location.state?.fetchData, navigate, doRead])

  const handleRestoreLast = useCallback(async () => {
    try {
      const saved = await loadLastReadForContext('weread')
      const hasSavedDomImages = Array.isArray(saved?.materializedImageUrls) && saved.materializedImageUrls.length > 0
      if (!saved?.url && !saved?.markdown && !saved?.content && !hasSavedDomImages) {
        toast?.info?.('暂无上次阅读记录')
        return
      }
      let screenshots = null
      if (saved.url) {
        screenshots = await loadScreenshots(saved.url)
      }
      const hasContent = saved.markdown || saved.content
      screenshotsRef.current = screenshots || []
      setData({
        url: saved.url,
        title: saved.title || '上次阅读',
        markdown: saved.markdown || saved.content || '',
        content: saved.content || saved.markdown || '',
        html: saved.html || '',
        screenshots: screenshots || undefined,
        pendingOcr: !hasContent && screenshots?.length ? true : false,
        summary: saved.summary ?? '',
        materializedImageUrls: saved.materializedImageUrls || [],
        inlineMaterializedByOriginal: saved.inlineMaterializedByOriginal || {},
        inlineImageMapAttemptCount: saved.inlineImageMapAttemptCount ?? 0,
        imageUrls: saved.imageUrls,
      })
      setSelectedShotIndices(new Set())
      if (saved.urlInput) setUrlInput(saved.urlInput)
      setError(null)
      toast?.info?.('已恢复上次阅读')
    } catch (_) {
      toast?.warning?.('恢复失败')
    }
  }, [toast])

  /** 恢复上次阅读（正文或仅截图均可恢复） */
  useEffect(() => {
    if (data || loading || location.state?.prefillUrl || location.state?.fetchData) return
    let cancelled = false
    const run = async () => {
      try {
        const saved = await loadLastReadForContext('weread')
        const hasSavedDomImages = Array.isArray(saved?.materializedImageUrls) && saved.materializedImageUrls.length > 0
        if (!saved?.url && !saved?.markdown && !saved?.content && !hasSavedDomImages) return
        let screenshots = null
        if (saved.url) {
          screenshots = await loadScreenshots(saved.url)
        }
        if (cancelled) return
        const hasContent = saved.markdown || saved.content
        screenshotsRef.current = screenshots || []
        setData({
          url: saved.url,
          title: saved.title || '上次阅读',
          markdown: saved.markdown || saved.content || '',
          content: saved.content || saved.markdown || '',
          html: saved.html || '',
          screenshots: screenshots || undefined,
          pendingOcr: !hasContent && screenshots?.length ? true : false,
          summary: saved.summary ?? '',
          materializedImageUrls: saved.materializedImageUrls || [],
          inlineMaterializedByOriginal: saved.inlineMaterializedByOriginal || {},
          inlineImageMapAttemptCount: saved.inlineImageMapAttemptCount ?? 0,
          imageUrls: saved.imageUrls,
        })
        setSelectedShotIndices(new Set())
        if (saved.urlInput) setUrlInput(saved.urlInput)
      } catch (_) {}
    }
    run()
    return () => { cancelled = true }
  }, [location.state?.prefillUrl])

  /** 保存上次阅读：有正文、截图或已下载插图 URL 时均存储，便于恢复 */
  useEffect(() => {
    const hasContent = data?.markdown || data?.content
    const hasScreenshots = data?.screenshots?.length && data?.url
    const hasDomImageUrls =
      data?.url && Array.isArray(data.materializedImageUrls) && data.materializedImageUrls.length > 0
    if (!hasContent && !hasScreenshots && !hasDomImageUrls) return
    if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current)
    saveDebounceRef.current = setTimeout(() => {
      saveDebounceRef.current = null
      saveLastReadForContext('weread', {
        url: data.url,
        urlInput,
        title: data.title,
        markdown: data.markdown || '',
        content: data.content || '',
        summary: data.summary ?? '',
        html: data.html || '',
        materializedImageUrls: data.materializedImageUrls || [],
        inlineMaterializedByOriginal: data.inlineMaterializedByOriginal || {},
        inlineImageMapAttemptCount: data.inlineImageMapAttemptCount ?? 0,
        imageUrls: data.imageUrls,
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
  }, [
    data?.url,
    data?.title,
    data?.markdown,
    data?.content,
    data?.summary,
    data?.screenshots,
    data?.html,
    data?.materializedImageUrls,
    data?.inlineMaterializedByOriginal,
    data?.inlineImageMapAttemptCount,
    data?.imageUrls,
    urlInput,
  ])

  useEffect(() => {
    if (figureLightbox == null) return
    const handler = (e) => {
      if (e.key === 'Escape') {
        setFigureLightbox(null)
        return
      }
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      setFigureLightbox((prev) => {
        if (!prev) return prev
        const dir = e.key === 'ArrowLeft' ? -1 : 1
        if (prev.kind === 'screenshot') {
          const n = data?.screenshots?.length ?? 0
          if (n <= 0) return prev
          const next = prev.index + dir
          if (next < 0 || next >= n) return prev
          return { kind: 'screenshot', index: next }
        }
        if (prev.kind === 'dom') {
          const n = downloadedArticleImages.length
          if (n <= 0) return prev
          const next = prev.index + dir
          if (next < 0 || next >= n) return prev
          return { kind: 'dom', index: next }
        }
        return prev
      })
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [figureLightbox, data?.screenshots?.length, downloadedArticleImages.length])

  useEffect(() => {
    if (!imgUploadModal) return
    const handler = (e) => {
      if (e.key !== 'Escape') return
      setImgUploadModal((prev) => (prev && !prev.loading ? null : prev))
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [imgUploadModal])

  const handlePasteFromClipboard = usePasteFromClipboard({
    onPaste: (text) => setUrlInput(text),
    toast,
  })

  useEffect(() => {
    screenshotsRef.current = data?.screenshots || []
  }, [data?.screenshots])

  useEffect(() => {
    if (loading) setSelectedShotIndices(new Set())
  }, [loading])

  const runOcrSequential = useCallback(
    async (startIndex, opts = {}) => {
      const { isResume = false, baselineLocked = false, baselineMarkdown } = opts
      const images = screenshotsRef.current?.length ? screenshotsRef.current : []
      if (!images.length) return
      if (ocrBusyRef.current) return
      ocrBusyRef.current = true
      ocrStopRef.current = false
      setOcrPhase('running')
      setLoadingOcr(true)
      setOcrTouched(true)
      if (!isResume && startIndex === 0 && baselineMarkdown !== undefined) {
        ocrBaselineRef.current = String(baselineMarkdown || '').trimEnd()
      } else if (!isResume && startIndex === 0 && !baselineLocked) {
        ocrBaselineRef.current = ((data?.markdown ?? data?.content) || '').trimEnd()
      }
      const n = images.length
      const ocrUrl = `${window.location.origin}/api/web-reader/ocr`
      const vp = vision_providers || []
      const isValidModel = vp.some((p) =>
        p.models?.some((m) => m.value === selectedVisionModel)
      )
      const model =
        (isValidModel ? selectedVisionModel : null) ||
        vision_default ||
        vp[0]?.models?.[0]?.value

      const finishPaused = (nextIdx) => {
        ocrNextIndexRef.current = nextIdx
        setOcrNextIndex(nextIdx)
        setOcrPhase('paused')
        setLoadingOcr(false)
        ocrBusyRef.current = false
        setOcrProgress(null)
        setData((prev) => (prev ? { ...prev, pendingOcr: true } : null))
      }

      const finishAllDone = () => {
        ocrNextIndexRef.current = n
        setOcrNextIndex(n)
        setOcrPhase(null)
        setLoadingOcr(false)
        ocrBusyRef.current = false
        setOcrProgress(null)
        ocrRequestedRef.current = null
        setData((prev) => (prev ? { ...prev, pendingOcr: false } : null))
      }

      try {
        for (let i = startIndex; i < n; i++) {
          if (ocrStopRef.current) {
            finishPaused(i)
            return
          }
          setOcrProgress({ cur: i + 1, total: n })
          const ac = new AbortController()
          fetchAbortRef.current = () => {
            try {
              ac.abort()
            } catch (_) {}
          }
          let block = ''
          try {
            const r = await fetch(ocrUrl, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image: images[i], source: 'weread', ...(model ? { model } : {}) }),
              signal: ac.signal,
            })
            let jd
            try {
              jd = await r.json()
            } catch (_) {
              jd = { success: false, error: `HTTP ${r.status}` }
            }
            if (jd.success && (jd.text || '').trim()) block = (jd.text || '').trim()
            else block = `[第${i + 1}张识别失败: ${jd.error || '未知'}]`
          } catch (err) {
            if (err?.name === 'AbortError' && ocrStopRef.current) {
              fetchAbortRef.current = null
              finishPaused(i)
              return
            }
            block = `[第${i + 1}张: ${err?.message || '请求失败'}]`
          } finally {
            fetchAbortRef.current = null
          }
          const isLast = i >= n - 1
          setData((prev) => {
            // 勿 trimEnd：与右侧编辑器正文逐字一致，避免 OCR 追加时父串变短导致 MarkdownEditorPreview 重置草稿、光标乱跳
            const raw = (prev?.markdown ?? prev?.content ?? '')
            const sep = raw.trim() ? '\n\n---\n\n' : ''
            const next = raw + sep + block
            return {
              ...prev,
              markdown: next,
              content: next,
              summary: '',
              pendingOcr: !isLast,
            }
          })
          if (ocrStopRef.current) {
            finishPaused(i + 1)
            return
          }
        }
        finishAllDone()
      } catch (err) {
        setOcrProgress(null)
        setLoadingOcr(false)
        ocrBusyRef.current = false
        ocrRequestedRef.current = null
        setOcrPhase(null)
        setError('OCR 识别失败：' + (err?.message || '请确认后端已启动'))
        setData((prev) => ({ ...prev, pendingOcr: false }))
      }
    },
    [data?.content, data?.markdown, selectedVisionModel, vision_default, vision_providers]
  )

  runOcrSeqRef.current = runOcrSequential

  const handleOcrStop = useCallback(() => {
    ocrStopRef.current = true
    try {
      fetchAbortRef.current?.()
    } catch (_) {}
  }, [])

  const handleOcrContinue = useCallback(() => {
    if (ocrBusyRef.current) return
    const next = ocrNextIndexRef.current
    const n = screenshotsRef.current?.length || 0
    if (next >= n) {
      toast?.info?.('已全部识别完毕')
      setOcrPhase(null)
      setData((prev) => (prev ? { ...prev, pendingOcr: false } : null))
      return
    }
    ocrStopRef.current = false
    queueMicrotask(() => runOcrSequential(next, { isResume: true }))
  }, [runOcrSequential, toast])

  const handleOcrRestart = useCallback(() => {
    const imgs = screenshotsRef.current || []
    if (!imgs.length) return
    ocrStopRef.current = true
    try {
      fetchAbortRef.current?.()
    } catch (_) {}
    const base = ocrBaselineRef.current
    queueMicrotask(() => {
      ocrStopRef.current = false
      ocrBusyRef.current = false
      setLoadingOcr(false)
      setOcrProgress(null)
      ocrNextIndexRef.current = 0
      setOcrNextIndex(0)
      setOcrPhase(null)
      setData((prev) => ({
        ...prev,
        markdown: base,
        content: base,
        summary: '',
        pendingOcr: true,
      }))
      setTimeout(() => {
        runOcrSequential(0, { isResume: false, baselineMarkdown: base })
      }, 0)
    })
  }, [runOcrSequential])

  const runOcr = useCallback(() => {
    const images = data?.screenshots || []
    if (!images.length) return
    if (ocrPhase === 'running' || (ocrBusyRef.current && !ocrStopRef.current)) {
      toast?.info?.('正在识别中，可先停止')
      return
    }
    if (ocrPhase === 'paused') {
      handleOcrContinue()
      return
    }
    const n = images.length
    if (ocrNextIndex >= n && ocrTouched) {
      toast?.info?.('当前截图已全部识别过，请用「重新开始」')
      return
    }
    ocrRequestedRef.current = null
    ocrBaselineRef.current = ((data?.markdown ?? data?.content) || '').trimEnd()
    ocrNextIndexRef.current = 0
    setOcrNextIndex(0)
    setData((prev) => (prev ? { ...prev, pendingOcr: true } : null))
    screenshotsRef.current = images
    queueMicrotask(() =>
      runOcrSequential(0, { isResume: false, baselineLocked: true })
    )
  }, [
    data?.content,
    data?.markdown,
    data?.screenshots,
    handleOcrContinue,
    ocrNextIndex,
    ocrPhase,
    ocrTouched,
    runOcrSequential,
    toast,
  ])

  const markdownEditorInsertRef = useRef(null)

  const insertMarkdownImageAtCursor = useCallback((url, alt) => {
    if (!url) return
    const label = (alt || '插图').replace(/\]/g, '')
    const line = `![${label}](${url})`
    const api = markdownEditorInsertRef.current
    if (!api?.insertMarkdownAtCursor) {
      toast?.warning?.('Markdown 编辑区尚未就绪，请先打开本章正文编辑区')
      return
    }
    api.insertMarkdownAtCursor(line)
    toast?.success?.('已插入到 Markdown 编辑框光标处')
  }, [toast])

  const redownloadDomImageByOriginalUrl = useCallback(
    async (originalUrl) => {
      const ou = (originalUrl || '').trim()
      if (!ou.startsWith('http://') && !ou.startsWith('https://')) {
        toast?.warning?.('缺少可用的原图链接，请先「读取」或「仅拉图」')
        return
      }
      const chapterUrl = (dataRef.current?.url || urlInput || '').trim()
      if (!chapterUrl.startsWith('http')) {
        toast?.warning?.('缺少章节页链接（请在上方输入框填写本章 weread 链接）')
        return
      }
      if (domRefetchBusyRef.current) return
      domRefetchBusyRef.current = true
      setDomRedownloadOriginalUrl(ou)

      const origin = window.location.origin
      const mergeMaterializedMapping = (materializedMapping) => {
        setData((prev) => {
          if (!prev) return prev
          const prevMap = prev.inlineMaterializedByOriginal || {}
          const mergedMap = { ...prevMap, ...materializedMapping }
          const materializedImageUrls = materializedUrlsFromMapping(mergedMap, origin)
          return {
            ...prev,
            inlineMaterializedByOriginal: mergedMap,
            materializedImageUrls,
          }
        })
        toast?.success?.('已重新下载并更新本站插图')
      }

      try {
        let backendErr = ''
        try {
          const br = await fetch(`${origin}/api/web-reader/fetch-weread-inline-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_url: ou, page_url: chapterUrl }),
          })
          const bj = await br.json().catch(() => ({}))
          if (bj.success && bj.mapping && typeof bj.mapping === 'object' && Object.keys(bj.mapping).length) {
            mergeMaterializedMapping(bj.mapping)
            return
          }
          backendErr = (bj.error && String(bj.error)) || (br.ok ? '' : `HTTP ${br.status}`)
        } catch (e) {
          backendErr = e?.message || '后端请求失败'
        }

        if (!extensionReady) {
          toast?.error?.(
            backendErr
              ? `重新下载失败：${backendErr}（可安装扩展后重试，以带上微信登录 Cookie）`
              : '重新下载失败'
          )
          return
        }

        const requestId = `weread-refetch-${Date.now()}`
        const res = await new Promise((resolve) => {
          const handler = (e) => {
            if (e.data?.type !== 'HOU_CLI_REFETCH_IMAGES_RESULT' || e.data.requestId !== requestId) return
            window.removeEventListener('message', handler)
            resolve(e.data)
          }
          window.addEventListener('message', handler)
          window.postMessage(
            {
              type: 'HOU_CLI_REFETCH_IMAGES',
              requestId,
              imageUrls: [ou],
              pageUrl: chapterUrl,
            },
            '*'
          )
          setTimeout(() => {
            window.removeEventListener('message', handler)
            resolve({ success: false, error: '扩展无响应，请重试或刷新页面' })
          }, 90000)
        })

        if (!res.success) {
          toast?.error?.(
            [backendErr && `本机后端：${backendErr}`, res.error && `扩展：${res.error}`]
              .filter(Boolean)
              .join('；') || '重新下载失败'
          )
          return
        }
        const map = res.data?.inlineImageMap
        if (!map || typeof map !== 'object' || !Object.keys(map).length) {
          toast?.error?.(backendErr ? `未拉到图片数据（本机后端：${backendErr}）` : '未拉到图片数据')
          return
        }

        const { mapping: materializedMapping } = await materializeInlineImagesFromMap('', map, origin)
        if (!materializedMapping || !Object.keys(materializedMapping).length) {
          toast?.error?.('落盘失败，请确认本机后端 /api/web-reader/materialize-inline-images 可用')
          return
        }
        mergeMaterializedMapping(materializedMapping)
      } catch (err) {
        toast?.error?.(err?.message || '落盘失败')
      } finally {
        domRefetchBusyRef.current = false
        setDomRedownloadOriginalUrl(null)
      }
    },
    [extensionReady, toast, urlInput]
  )

  const toggleShotSelected = useCallback((index) => {
    setSelectedShotIndices((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }, [])

  const runOcrSelectedAppendToEnd = useCallback(async () => {
    const images = screenshotsRef.current?.length ? screenshotsRef.current : data?.screenshots || []
    const indices = [...selectedShotIndices]
      .filter((i) => Number.isInteger(i) && i >= 0 && i < images.length)
      .sort((a, b) => a - b)
    if (!indices.length) {
      toast?.info?.('请先勾选要识别的截图')
      return
    }
    if (loadingOcr && ocrPhase === 'running') {
      toast?.info?.('整块识别进行中，请先点「停止」')
      return
    }
    if (ocrMultiBatchBusy) return

    const ocrUrl = `${window.location.origin}/api/web-reader/ocr`
    const vp = vision_providers || []
    const isValidModel = vp.some((p) =>
      p.models?.some((m) => m.value === selectedVisionModel)
    )
    const model =
      (isValidModel ? selectedVisionModel : null) ||
      vision_default ||
      vp[0]?.models?.[0]?.value

    setOcrMultiBatchBusy(true)
    setOcrMultiProgress(null)
    try {
      for (let k = 0; k < indices.length; k++) {
        const index = indices[k]
        const img = images[index]
        if (!img) continue
        setOcrMultiProgress({ cur: k + 1, total: indices.length })
        let jd
        try {
          const r = await fetch(ocrUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: img, source: 'weread', ...(model ? { model } : {}) }),
          })
          try {
            jd = await r.json()
          } catch (_) {
            jd = { success: false, error: `HTTP ${r.status}` }
          }
        } catch (err) {
          jd = { success: false, error: err?.message || '请求失败' }
        }
        let block = ''
        if (jd.success && (jd.text || '').trim()) block = (jd.text || '').trim()
        else block = `[第${index + 1}张截图识别失败: ${jd.error || '未知'}]`
        setData((prev) => {
          const raw = (prev?.markdown ?? prev?.content ?? '')
          const sep = raw.trim() ? '\n\n---\n\n' : ''
          const next = raw + sep + block
          return {
            ...prev,
            markdown: next,
            content: next,
            summary: '',
          }
        })
        setOcrTouched(true)
      }
      toast?.success?.(`已识别 ${indices.length} 张，内容已按顺序追加到正文末尾`)
      setSelectedShotIndices(new Set())
    } catch (err) {
      toast?.error?.(err?.message || '批量识别失败')
    } finally {
      setOcrMultiBatchBusy(false)
      setOcrMultiProgress(null)
    }
  }, [
    data?.screenshots,
    loadingOcr,
    ocrMultiBatchBusy,
    ocrPhase,
    selectedShotIndices,
    selectedVisionModel,
    toast,
    vision_default,
    vision_providers,
  ])

  const handleImgUploadToWiki = async () => {
    const modal = imgUploadModal
    const src = modal?.src
    const srcRaw = modal?.srcRaw || src
    const width = modal?.width || 0
    const height = modal?.height || 0
    const isWikiFile = modal?.isWikiFile
    const oldWikitext = modal?.result?.wikitext
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
        setData((prev) => {
          if (!prev?.markdown) return prev
          let newMd = prev.markdown
          if (isWikiFile && oldWikitext) {
            newMd = newMd.replaceAll(oldWikitext, wikitext)
          } else {
            const urlsToTry = [src, srcRaw].filter(Boolean)
            const escapeForRe = (u) => u.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            for (const u of urlsToTry) {
              const re = new RegExp(`!\\[([^\\]]*)\\]\\(${escapeForRe(u)}\\)`, 'g')
              newMd = newMd.replace(re, wikitext)
              if (newMd !== prev.markdown) break
            }
          }
          return newMd !== prev.markdown ? { ...prev, markdown: newMd, content: newMd } : prev
        })
        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(wikitext)
            toast?.success?.(`已替换链接并复制 [[File:${apiData.filename}]]`)
          } else {
            toast?.success?.(`已替换为 [[File:${apiData.filename}]]`)
          }
        } catch (_) {
          toast?.success?.(`已替换为 [[File:${apiData.filename}]]`)
        }
      }
    } catch (err) {
      setImgUploadModal((prev) => (prev ? { ...prev, loading: false, result: { error: err?.message || '上传失败' } } : null))
      toast?.error?.(err?.message || '上传失败')
    }
  }

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type !== 'HOU_CLI_FETCH_RESULT' || !e.data?.requestId?.startsWith(REQUEST_ID_PREFIX)) return
      const rid = e.data.requestId || ''
      const isImagesOnly = rid.startsWith(IMAGES_ONLY_REQUEST_PREFIX)

      if (isImagesOnly) {
        if (imagesOnlyTimeoutRef.current) {
          clearTimeout(imagesOnlyTimeoutRef.current)
          imagesOnlyTimeoutRef.current = null
        }
        setImagesOnlyBusy(false)
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }
        setLoading(false)
      }

      if (e.data.success) {
        const d = e.data.data
        if (isImagesOnly) {
          ;(async () => {
            const origin = window.location.origin
            const cur = dataRef.current
            const hadEditorText = ((cur?.markdown || cur?.content || '').trim().length > 0)
            const map = d?.inlineImageMap
            let materializedMapping = null
            if (map && typeof map === 'object' && Object.keys(map).length) {
              const { mapping } = await materializeInlineImagesFromMap('', map, origin)
              materializedMapping = mapping
            }
            const mapAttempt = map && typeof map === 'object' ? Object.keys(map).length : 0
            setData((prev) => {
              const shots = prev?.screenshots?.length ? prev.screenshots : []
              screenshotsRef.current = shots
              const prevMap = prev?.inlineMaterializedByOriginal || {}
              const mergedMap =
                materializedMapping && Object.keys(materializedMapping).length
                  ? { ...prevMap, ...materializedMapping }
                  : { ...prevMap }
              const materializedImageUrls = materializedUrlsFromMapping(mergedMap, origin)
              const base = prev || {}
              const baseMd = (base.markdown || base.content || '').trim()
              const domEnough = wereadDomEnoughForSkipAutoOcr(base.markdown, base.content)
              const pendingOcr = !!(shots.length && !domEnough)
              const hasExistingText = baseMd.length > 0
              let markdown = base.markdown ?? ''
              let contentOut = base.content ?? ''
              let html = base.html ?? ''
              if (!hasExistingText) {
                const nh = d?.html || ''
                markdown = nh ? htmlToMd(nh) : ''
                markdown = markdown || d?.content || ''
                contentOut = markdown || d?.content || ''
                html = nh
              }
              return {
                ...base,
                title:
                  d?.title && String(d.title).trim()
                    ? d.title
                    : base.title || '微信读书',
                html,
                markdown,
                content: contentOut,
                url: d?.url || base.url || '',
                imageUrls: Array.isArray(d?.imageUrls) ? d.imageUrls : base.imageUrls,
                screenshots: shots,
                materializedImageUrls,
                inlineMaterializedByOriginal: mergedMap,
                inlineImageMapAttemptCount: mapAttempt > 0 ? mapAttempt : base.inlineImageMapAttemptCount ?? 0,
                pendingOcr,
                summary: base.summary ?? '',
                baseUrl: d?.baseUrl || base.baseUrl,
                fullPageHtml: base.fullPageHtml ?? '',
                stylesheets: base.stylesheets ?? [],
                inlineStyles: base.inlineStyles ?? [],
              }
            })
            toast?.success?.(
              hadEditorText
                ? '已拉图：正文未改写，预览用站内地址显示插图（左侧截图未变）'
                : '已拉图并写入正文（此前无正文时由 DOM 生成；左侧截图未变）'
            )
          })()
          setError(null)
          return
        }

        ;(async () => {
          const origin = window.location.origin
          const prevSnap = dataRef.current
          const hadEditorText = ((prevSnap?.markdown || prevSnap?.content || '').trim().length > 0)
          let html = d?.html
          const map = d?.inlineImageMap
          let materializedMapping = null
          const mapAttempt = map && typeof map === 'object' ? Object.keys(map).length : 0

          if (hadEditorText) {
            if (map && Object.keys(map).length) {
              const { mapping } = await materializeInlineImagesFromMap('', map, origin)
              materializedMapping = mapping
            }
          } else if (html && map && typeof map === 'object' && Object.keys(map).length) {
            const { html: nh, mapping } = await materializeInlineImagesFromMap(html, map, origin)
            html = nh
            materializedMapping = mapping
          }

          const shots = d?.screenshots || []
          screenshotsRef.current = shots

          setData((prev) => {
            const base = hadEditorText ? prev || prevSnap || {} : prev || {}
            const prevMap = base.inlineMaterializedByOriginal || {}
            const mergedMap =
              materializedMapping && Object.keys(materializedMapping).length
                ? hadEditorText
                  ? { ...prevMap, ...materializedMapping }
                  : { ...materializedMapping }
                : hadEditorText
                  ? { ...prevMap }
                  : {}

            const materializedImageUrls = Object.keys(mergedMap).length
              ? materializedUrlsFromMapping(mergedMap, origin)
              : []

            let markdown
            let contentOut
            let htmlOut
            let domEnough
            if (hadEditorText) {
              markdown = base.markdown ?? ''
              contentOut = base.content ?? ''
              htmlOut = base.html ?? ''
              domEnough = wereadDomEnoughForSkipAutoOcr(markdown, contentOut)
            } else {
              htmlOut = html || d?.html || ''
              markdown = htmlOut ? htmlToMd(htmlOut) : ''
              markdown = markdown || d?.content || ''
              contentOut = markdown || d?.content || ''
              const textForDomEnough = markdown || d?.content || ''
              domEnough = wereadDomEnoughForSkipAutoOcr(markdown, textForDomEnough)
            }

            const pendingOcr = !!(shots.length && !domEnough)
            const inlineImageMapAttemptCount =
              mapAttempt > 0 ? mapAttempt : hadEditorText ? base.inlineImageMapAttemptCount ?? 0 : 0

            return {
              ...(d || {}),
              html: htmlOut,
              markdown,
              content: contentOut,
              pendingOcr,
              materializedImageUrls,
              inlineMaterializedByOriginal: mergedMap,
              inlineImageMapAttemptCount,
              summary: hadEditorText ? base.summary ?? '' : base.summary ?? d?.summary ?? '',
            }
          })
          setSelectedShotIndices(new Set())
          ocrStopRef.current = false
          setOcrPhase(null)
          setOcrTouched(false)
          ocrNextIndexRef.current = 0
          setOcrNextIndex(0)
        })()
        setError(null)
        ocrRequestedRef.current = null
      } else {
        if (isImagesOnly) {
          setError(e.data.error || '拉图失败')
          toast?.error?.(e.data.error || '拉图失败')
          return
        }
        setError(e.data.error || '抓取失败')
        const stillHasEditor = ((dataRef.current?.markdown || dataRef.current?.content || '').trim().length > 0)
        if (!stillHasEditor) setData(null)
      }
    }
    window.addEventListener('message', handler)
    return () => {
      window.removeEventListener('message', handler)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (imagesOnlyTimeoutRef.current) clearTimeout(imagesOnlyTimeoutRef.current)
    }
  }, [runOcrSequential, toast])

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

  const downloadedImagesPanel =
    downloadedArticleImages.length > 0 ? (
      <div className="shrink-0 border-t border-border bg-black/20 px-2 py-2 max-h-[min(40vh,240px)] overflow-y-auto">
        <div className="text-[11px] text-muted mb-1.5 px-0.5 flex flex-wrap gap-x-2 gap-y-0.5 items-baseline">
          <span className="font-medium text-fg/90">已下载插图（DOM）</span>
          <span>
            共 {downloadedArticleImages.length} 张 · 来自阅读器内插图拉图，非上方截屏
          </span>
          {Array.isArray(data?.imageUrls) && data.imageUrls.length > 0 && (
            <span className="text-[10px] opacity-75">DOM 原地址 {data.imageUrls.length} 个</span>
          )}
          {Object.keys(data?.inlineMaterializedByOriginal || {}).length > 0 && (
            <span className="text-[10px] opacity-75">已记原链→本站映射 {Object.keys(data.inlineMaterializedByOriginal).length} 条</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {downloadedArticleImages.map((im, domIdx) => (
            <div
              key={`dom-img-${domIdx}-${im.url}`}
              className="flex flex-col items-stretch gap-1 w-[76px] shrink-0 rounded border border-border/50 bg-white/[0.06] p-1"
            >
              <img
                src={im.url}
                alt=""
                role="button"
                tabIndex={0}
                title={
                  im.originalUrl
                    ? `原图地址：${im.originalUrl}\n点击打开大图（内可重新下载）`
                    : '点击打开大图预览'
                }
                onClick={() => setFigureLightbox({ kind: 'dom', index: domIdx })}
                onKeyDown={(e) => e.key === 'Enter' && setFigureLightbox({ kind: 'dom', index: domIdx })}
                className="h-11 w-full object-cover rounded bg-white/5 cursor-pointer hover:ring-2 hover:ring-accent/50 transition-shadow"
              />
              <button
                type="button"
                title="在右侧 Markdown 编辑框光标处插入本站图片"
                disabled={!data}
                onClick={(e) => {
                  e.stopPropagation()
                  insertMarkdownImageAtCursor(im.url, im.alt)
                }}
                className="text-[10px] px-1 py-0.5 rounded bg-accent/25 hover:bg-accent/35 text-fg/90 w-full disabled:opacity-40"
              >
                插入图片
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-fg/85 mt-1.5 px-0.5 leading-snug">
          缩略图下可快速「插入图片」；点图打开大图可「重新下载」等。映射写入 IndexedDB；缺图请「仅拉图」或「读取」。
        </p>
      </div>
    ) : null

  const showImageDiagnostic =
    data &&
    downloadedArticleImages.length === 0 &&
    ((Array.isArray(data.imageUrls) && data.imageUrls.length > 0) ||
      (typeof data.inlineImageMapAttemptCount === 'number' && data.inlineImageMapAttemptCount > 0))

  const domImageUrlHint = showImageDiagnostic ? (
    <div className="shrink-0 px-2 py-2 text-xs text-amber-50 border-t border-amber-500/35 bg-amber-950/45 leading-relaxed space-y-1.5">
      {Array.isArray(data.imageUrls) && data.imageUrls.length > 0 && (
        <p className="text-amber-50/95">
          DOM 内标记了 {data.imageUrls.length} 个原图地址，但未在正文/HTML 中解析到可展示的插图。可点「仅拉图」或重新「读取」；并确认本机后端
          /api/web-reader/materialize-inline-images 可用。
        </p>
      )}
      {typeof data.inlineImageMapAttemptCount === 'number' && data.inlineImageMapAttemptCount > 0 && (
        <p className="text-amber-50/95">
          扩展传回了 {data.inlineImageMapAttemptCount} 张图的 data URL，但落盘后未得到本站 inline-static 地址。请确认本机后端已启动、磁盘可写，再点「仅拉图」或重新「读取」。
        </p>
      )}
    </div>
  ) : null

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="微信读书" />

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col flex-[0.382] min-w-0 border-r border-border min-h-0">
          <div className="shrink-0 p-4 space-y-2 min-w-0 overflow-hidden">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <button
                type="button"
                onClick={handleRestoreLast}
                className="shrink-0 px-2.5 py-2 text-xs rounded-lg border border-border text-fg/90 hover:bg-white/10"
                title="从本机恢复上次会话：链接、正文、分屏截图、DOM 插图映射（IndexedDB）"
              >
                恢复上次
              </button>
              <form onSubmit={handleRead} className="flex flex-1 min-w-0 gap-2 items-center">
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
                  disabled={loading || imagesOnlyBusy || !extensionReady}
                  className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 text-sm shrink-0"
                  title={
                    loadingOcr
                      ? '将中止当前识别并重新抓取'
                      : 'DOM、拉图与分屏截图；右侧已有正文时不改写 Markdown（预览仍可用站内映射显示插图）'
                  }
                >
                  {loading ? '抓取中…' : !extensionReady ? '等待扩展…' : '读取'}
                </button>
                <button
                  type="button"
                  onClick={handleWereadImagesOnly}
                  disabled={
                    loading ||
                    imagesOnlyBusy ||
                    !extensionReady ||
                    !WEREAD_URL_PATTERN.test((urlInput || data?.url || '').trim())
                  }
                  className="shrink-0 px-3 py-2 text-xs rounded-lg border border-border text-fg/90 hover:bg-white/10 disabled:opacity-50"
                  title="扩展预扫并拉图落盘；不改右侧 Markdown 原文（预览仍会显示站内插图）、不重新分屏截图、不自动 OCR"
                >
                  {imagesOnlyBusy ? '拉图中…' : '仅拉图'}
                </button>
              </form>
            </div>
            {!extensionReady && <ExtensionNotReadyHint />}
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>
          <div className="flex-1 min-h-0 border-t border-border overflow-auto w-full flex flex-col">
            {data?.screenshots?.length ? (
              <>
                <div className="shrink-0 px-2 py-1 border-b border-border/40 flex flex-wrap items-center gap-x-2 gap-y-1 justify-between">
                  <VisionModelSelector
                    compact
                    value={selectedVisionModel}
                    onChange={setSelectedVisionModel}
                    providers={vision_providers}
                    defaultModel={vision_default}
                    loading={modelsLoading}
                    className="shrink-0 min-w-0"
                  />
                  <div className="flex flex-wrap items-center gap-1 shrink-0">
                    <button
                      type="button"
                      title="全选截图"
                      onClick={() =>
                        setSelectedShotIndices(new Set(data.screenshots.map((_, idx) => idx)))
                      }
                      disabled={ocrMultiBatchBusy || (loadingOcr && ocrPhase === 'running')}
                      className="px-1.5 py-0.5 rounded border border-border/60 text-[10px] text-fg hover:bg-white/10 disabled:opacity-40"
                    >
                      全选
                    </button>
                    <button
                      type="button"
                      title="清空勾选"
                      onClick={() => setSelectedShotIndices(new Set())}
                      disabled={ocrMultiBatchBusy || selectedShotIndices.size === 0}
                      className="px-1.5 py-0.5 rounded border border-border/60 text-[10px] text-fg hover:bg-white/10 disabled:opacity-40"
                    >
                      清空
                    </button>
                    <button
                      type="button"
                      title="识别已选截图，按序追加到文末"
                      onClick={() => void runOcrSelectedAppendToEnd()}
                      disabled={
                        ocrMultiBatchBusy ||
                        selectedShotIndices.size === 0 ||
                        (loadingOcr && ocrPhase === 'running')
                      }
                      className="px-1.5 py-0.5 rounded bg-accent/80 hover:bg-accent text-white text-[10px] font-medium disabled:opacity-40"
                    >
                      {ocrMultiBatchBusy && ocrMultiProgress
                        ? `识别 ${ocrMultiProgress.cur}/${ocrMultiProgress.total}…`
                        : '识别已选'}
                    </button>
                    {selectedShotIndices.size > 0 && !ocrMultiBatchBusy && (
                      <span className="text-[10px] text-fg/70 tabular-nums">已选{selectedShotIndices.size}</span>
                    )}
                  </div>
                </div>
                <p className="shrink-0 px-2 py-1 text-[10px] text-muted/90 leading-snug border-b border-border/25">
                  扩展会对截图做居中窄幅裁切；若仍为整页宽图，请在 chrome://extensions 重载扩展后重新点「读取」。
                </p>
                <div className="flex-1 min-h-0 overflow-y-auto py-2 space-y-3 px-1">
                  {data.screenshots.map((src, i) => {
                    const multiBusy = ocrMultiBatchBusy
                    return (
                      <div
                        key={i}
                        className="rounded-lg border border-border/60 overflow-hidden bg-black/20"
                      >
                        <div className="flex items-start gap-2 px-2 pt-2 pb-1 border-b border-border/30">
                          <label className="flex items-center gap-1.5 shrink-0 text-[10px] text-muted cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={selectedShotIndices.has(i)}
                              onChange={() => toggleShotSelected(i)}
                              disabled={multiBusy}
                              className="rounded border-border"
                            />
                            选中
                          </label>
                          <span className="text-[10px] text-muted/90 pt-0.5">第 {i + 1} 张</span>
                        </div>
                        <img
                          src={src}
                          alt={`页面截图 ${i + 1}`}
                          role="button"
                          tabIndex={0}
                          onClick={() => setFigureLightbox({ kind: 'screenshot', index: i })}
                          onKeyDown={(e) => e.key === 'Enter' && setFigureLightbox({ kind: 'screenshot', index: i })}
                          className="block w-full min-w-0 h-auto max-h-none bg-white cursor-pointer hover:ring-2 hover:ring-accent/50 transition-shadow"
                        />
                      </div>
                    )
                  })}
                </div>
                {downloadedImagesPanel}
                {domImageUrlHint}
                {data?.pendingOcr ? (
                  <div className="shrink-0 px-3 py-2 space-y-2 border-t border-border">
                    <div className="text-xs text-muted text-center">
                      共 {data.screenshots.length} 张截图
                      {ocrPhase === 'running' && ocrProgress
                        ? `，第 ${ocrProgress.cur}/${ocrProgress.total} 张`
                        : ocrPhase === 'paused'
                          ? ocrNextIndex >= data.screenshots.length
                            ? '，本轮队列已结束（点「继续」收尾）'
                            : `，已暂停（下次从第 ${ocrNextIndex + 1} 张继续）`
                          : '，准备识别…'}
                    </div>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {ocrPhase === 'running' && (
                        <button
                          type="button"
                          onClick={handleOcrStop}
                          className="px-3 py-1.5 rounded-lg border border-border text-xs text-fg hover:bg-white/5"
                        >
                          停止
                        </button>
                      )}
                      {ocrPhase === 'paused' && (
                        <>
                          <button
                            type="button"
                            onClick={handleOcrContinue}
                            className="px-3 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium"
                          >
                            继续
                          </button>
                          {ocrTouched && (
                            <button
                              type="button"
                              onClick={handleOcrRestart}
                              className="px-3 py-1.5 rounded-lg border border-border text-xs text-fg hover:bg-white/5"
                            >
                              重新开始
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ) : !(data?.markdown || data?.content) ? (
                  <div className="shrink-0 p-3 border-t border-border">
                    <button
                      type="button"
                      onClick={runOcr}
                      disabled={loadingOcr}
                      className="w-full px-3 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium disabled:opacity-50"
                    >
                      识别文字
                    </button>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="h-full flex flex-col min-h-0 text-sm text-muted">
                <div className="shrink-0 px-2 py-1.5 border-b border-border/40">
                  <VisionModelSelector
                    compact
                    value={selectedVisionModel}
                    onChange={setSelectedVisionModel}
                    providers={vision_providers}
                    defaultModel={vision_default}
                    loading={modelsLoading}
                    className="justify-center sm:justify-start"
                  />
                </div>
                <div className="shrink-0 p-4 text-center">
                  {loading ? (
                    '正在抓取页面（插图与正文 + 截图）…'
                  ) : data?.markdown || data?.content ? (
                    <>
                      未生成分屏截图或本页无可截区域；正文已在右侧（含已落盘的插图 Markdown）。
                      <br />
                      需要整页 OCR 时请重新打开书籍页再试。
                    </>
                  ) : (
                    <>
                      读取后左侧上方为分屏截图；下方为已下载的章节插图。
                      <br />
                      DOM 正文不足时请手动点「识别文字」做整页 OCR（读取后不会自动开始）。
                    </>
                  )}
                </div>
                {downloadedImagesPanel}
                {domImageUrlHint}
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-[0.618] overflow-y-auto bg-white/[0.02] p-6">
          {!data && !loading && !error && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              输入微信读书链接并点击「读取」，正文将在此展示。
            </div>
          )}
          {loading && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              正在抓取页面…
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
                {(loadingOcr || ocrPhase === 'paused') && (
                  <div className="shrink-0 px-4 py-2 border-b border-border bg-black/20 text-sm text-muted flex flex-wrap items-center gap-2">
                    {ocrPhase === 'paused' ? (
                      <span>
                        {ocrNextIndex >= (data.screenshots?.length || 0)
                          ? '识别已暂停，可在左侧点「继续」结束本轮。'
                          : `识别已暂停，可在左侧「继续」从第 ${ocrNextIndex + 1} / ${data.screenshots?.length || 0} 张接着识别。`}
                      </span>
                    ) : ocrProgress ? (
                      <span>
                        正在识别：第 {ocrProgress.cur} / {ocrProgress.total} 张（结果逐段写入下方正文）
                      </span>
                    ) : (
                      <span>正在识别文字…</span>
                    )}
                  </div>
                )}
                <div className="flex-1 min-h-0 p-4 flex flex-col">
                  {data.screenshots?.length && !(data.markdown || data.content) && !data.pendingOcr && (
                    <div className="shrink-0 text-center text-sm text-muted mb-3">
                      左侧勾选截图后点「识别已选（按序追加到文末）」（只认一张时勾一张即可），或使用「识别文字」按顺序整批识别；右侧为编辑与预览分栏，内容同步。
                    </div>
                  )}
                  <MarkdownEditorPreview
                    className="flex-1 min-h-0"
                    editorInsertRef={markdownEditorInsertRef}
                    content={data.markdown || ''}
                    onContentChange={(v) => setData((prev) => (prev ? { ...prev, markdown: v, summary: '' } : null))}
                    editable
                    theme="dark"
                    previewWideFigures
                    previewInlineFigureZoom
                    previewImageMaterializedMapping={data.inlineMaterializedByOriginal}
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
                      const origin = typeof window !== 'undefined' ? window.location.origin : ''
                      const map = data?.inlineMaterializedByOriginal
                      const originalImageUrl =
                        findOriginalUrlForPreviewImgSrc(d.srcRaw || '', map, origin) ||
                        findOriginalUrlForPreviewImgSrc(d.src || '', map, origin) ||
                        undefined
                      setImgUploadModal({
                        ...d,
                        originalImageUrl,
                        loading: false,
                        result: wikitext ? { wikitext } : null,
                      })
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {figureLightbox &&
        (figureLightbox.kind === 'screenshot'
          ? data?.screenshots?.[figureLightbox.index]
          : downloadedArticleImages[figureLightbox.index]?.url) && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-stretch justify-center bg-black/88 backdrop-blur-[2px] p-3 pt-10 pb-12 sm:p-4 sm:pt-12 sm:pb-14"
          role="dialog"
          aria-modal="true"
          aria-label="图片预览"
          onClick={() => setFigureLightbox(null)}
        >
          {figureLightbox.index > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setFigureLightbox((prev) =>
                  prev ? { ...prev, index: prev.index - 1 } : prev
                )
              }}
              className="absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 z-20 px-3 py-2 rounded-lg border border-white/20 bg-zinc-950/80 text-white text-sm shadow-lg hover:bg-zinc-900/90"
            >
              上一张
            </button>
          )}
          <div
            className="mx-auto flex h-[min(100dvh-7rem,100%)] w-full max-w-[min(96rem,calc(100vw-1.5rem))] min-h-0 flex-col overflow-hidden rounded-2xl border border-zinc-500/60 bg-zinc-800 shadow-2xl shadow-black/40"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex shrink-0 flex-wrap items-center gap-x-2 gap-y-2 border-b border-zinc-600/80 bg-zinc-700 px-3 py-2.5 sm:px-4">
              <span className="min-w-0 flex-1 basis-[min(100%,10rem)] text-sm font-medium text-zinc-50">
                {figureLightbox.kind === 'screenshot' ? '分屏截图' : 'DOM 插图'} ·{' '}
                {figureLightbox.index + 1} /{' '}
                {figureLightbox.kind === 'screenshot'
                  ? (data?.screenshots?.length ?? 0)
                  : downloadedArticleImages.length}
              </span>
              <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                {figureLightbox.kind === 'dom' &&
                  downloadedArticleImages[figureLightbox.index] &&
                  (() => {
                    const domLb = downloadedArticleImages[figureLightbox.index]
                    const chapterRef = (data?.url || urlInput || '').trim()
                    const canRedownload =
                      !!domLb.originalUrl &&
                      !domRedownloadOriginalUrl &&
                      /^https?:\/\//i.test(chapterRef)
                    return (
                      <>
                        <button
                          type="button"
                          title={
                            canRedownload
                              ? extensionReady
                                ? '优先本机后端代拉；失败则扩展带 Cookie 重试'
                                : '本机后端代拉（无需扩展）；若失败请安装扩展后重试'
                              : [
                                  !domLb.originalUrl && '需要可用的原图链接',
                                  !/^https?:\/\//i.test(chapterRef) && '需要在上方填写本章页面链接',
                                  !!domRedownloadOriginalUrl && '正在下载中',
                                ]
                                  .filter(Boolean)
                                  .join('；') || '暂不可重新下载'
                          }
                          disabled={!canRedownload}
                          onClick={(e) => {
                            e.stopPropagation()
                            redownloadDomImageByOriginalUrl(domLb.originalUrl)
                          }}
                          className="rounded-lg border border-zinc-500 bg-zinc-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-zinc-500 sm:px-3 sm:text-sm disabled:opacity-45 disabled:cursor-not-allowed"
                        >
                          {domRedownloadOriginalUrl === domLb.originalUrl ? '下载中…' : '重新下载'}
                        </button>
                        <button
                          type="button"
                          title="插入到右侧 Markdown 编辑框光标处，并关闭本弹层"
                          disabled={!data}
                          onClick={(e) => {
                            e.stopPropagation()
                            insertMarkdownImageAtCursor(domLb.url, domLb.alt)
                            setFigureLightbox(null)
                          }}
                          className="rounded-lg border border-sky-500 bg-sky-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-sky-500 sm:px-3 sm:text-sm disabled:opacity-45"
                        >
                          插入图片
                        </button>
                      </>
                    )
                  })()}
                <button
                  type="button"
                  onClick={() => setFigureLightbox(null)}
                  className="shrink-0 rounded-lg border border-zinc-500 bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900 shadow-sm hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
                >
                  关闭
                </button>
              </div>
            </div>
            {figureLightbox.kind === 'dom' &&
              downloadedArticleImages[figureLightbox.index] &&
              (() => {
                const domLb = downloadedArticleImages[figureLightbox.index]
                return (
                  <div className="grid shrink-0 grid-cols-2 gap-x-3 gap-y-1 border-b border-zinc-600/70 bg-zinc-800/95 px-3 py-2.5 sm:gap-4 sm:px-4">
                    <div className="min-w-0 border-r border-zinc-600/50 pr-2 sm:pr-3">
                      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-zinc-400 sm:text-[11px]">
                        原图链接（新标签打开 · 扩展「重新下载」用此地址）
                      </p>
                      {domLb.originalUrl ? (
                        <a
                          href={domLb.originalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs leading-snug text-blue-400 hover:text-blue-300 hover:underline break-all sm:text-sm"
                        >
                          {domLb.originalUrl}
                        </a>
                      ) : (
                        <p className="text-xs leading-snug text-amber-200/95 sm:text-sm">
                          当前条目不包含可识别的微信读书原链。请先对本章点「仅拉图」或「读取」。
                        </p>
                      )}
                    </div>
                    <div className="min-w-0 pl-2 sm:pl-3">
                      <p className="mb-1 text-[10px] font-medium text-zinc-400 sm:text-[11px]">
                        当前预览 / 插入用的地址
                      </p>
                      <p className="break-all font-mono text-xs leading-snug text-zinc-200 sm:text-sm">{domLb.url}</p>
                    </div>
                  </div>
                )
              })()}
            <div className="flex min-h-0 flex-1 flex-col bg-zinc-900/35 px-4 py-3 sm:px-8 sm:py-4 md:px-12">
              <ZoomPanFigure
                key={
                  figureLightbox.kind === 'screenshot'
                    ? `${figureLightbox.kind}-${figureLightbox.index}`
                    : `${figureLightbox.kind}-${figureLightbox.index}-${downloadedArticleImages[figureLightbox.index]?.url || ''}`
                }
                src={
                  figureLightbox.kind === 'screenshot'
                    ? data.screenshots[figureLightbox.index]
                    : downloadedArticleImages[figureLightbox.index].url
                }
                className="min-h-0 w-full flex-1"
                imgClassName="rounded-lg ring-1 ring-white/10"
              />
            </div>
          </div>
          {figureLightbox.index <
            (figureLightbox.kind === 'screenshot'
              ? (data?.screenshots?.length ?? 0)
              : downloadedArticleImages.length) -
              1 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setFigureLightbox((prev) =>
                  prev ? { ...prev, index: prev.index + 1 } : prev
                )
              }}
              className="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 z-20 px-3 py-2 rounded-lg border border-white/20 bg-zinc-950/80 text-white text-sm shadow-lg hover:bg-zinc-900/90"
            >
              下一张
            </button>
          )}
          <span className="pointer-events-none absolute bottom-3 left-1/2 z-10 max-w-[95vw] -translate-x-1/2 px-2 text-center text-xs text-white/65 sm:text-sm sm:text-white/70">
            捏合/Ctrl+滚轮缩放，放大后双指滑动或拖拽 · 双击重置 · Esc 或点空白关闭
          </span>
        </div>
      )}

      {imgUploadModal && (
        <div
          className="fixed inset-0 z-[55] flex flex-col bg-black/90"
          role="dialog"
          aria-modal="true"
          aria-label="插图大图"
          onClick={() => {
            setImgUploadModal((prev) => (prev && !prev.loading ? null : prev))
          }}
        >
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setImgUploadModal((prev) => (prev && !prev.loading ? null : prev))
            }}
            className="absolute right-4 top-4 z-10 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white text-2xl leading-none"
            title="关闭"
          >
            ×
          </button>
          <div
            className="flex-1 min-h-0 min-w-0 flex flex-col p-4 pt-16 gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <ZoomPanFigure
              src={imgUploadModal.src}
              className="min-h-[200px]"
              fitContainer
              imgClassName="max-h-[min(72vh,calc(100vh-12rem))] max-w-[min(92vw,900px)] rounded-lg border border-white/10"
            />
            {imgUploadModal.originalImageUrl && (
              <div className="shrink-0 rounded-lg border border-white/15 bg-black/50 px-3 py-2 max-w-[min(92vw,900px)] mx-auto w-full">
                <p className="text-[10px] uppercase tracking-wide text-white/45 mb-1">原图链接</p>
                <a
                  href={imgUploadModal.originalImageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-sky-300 hover:text-sky-200 break-all leading-snug block"
                >
                  {imgUploadModal.originalImageUrl}
                </a>
              </div>
            )}
          </div>
          <div
            className="shrink-0 border-t border-white/10 bg-black/70 px-4 py-3 space-y-2"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-[11px] text-white/55 text-center leading-snug">
              {imgUploadModal.isWikiFile
                ? '已是 Wiki 文件语法，可再次上传替换。捏合或滚轮缩放；放大后双指滑动/拖拽平移；双击恢复 100%。'
                : '捏合或滚轮缩放；放大后双指滑动/拖拽；双击恢复 100%。落 Wiki 点「上传」；Esc 或空白处关闭。'}
            </p>
            {imgUploadModal.result?.wikitext && (
              <div className="p-2 rounded bg-white/5 text-xs font-mono text-accent break-all max-h-20 overflow-y-auto">
                {imgUploadModal.result.wikitext}
              </div>
            )}
            {imgUploadModal.result?.error && (
              <p className="text-xs text-red-400 text-center line-clamp-3">{imgUploadModal.result.error}</p>
            )}
            <div className="flex flex-wrap gap-2 justify-center">
              <button
                type="button"
                onClick={handleImgUploadToWiki}
                disabled={imgUploadModal.loading}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {imgUploadModal.loading
                  ? '上传中…'
                  : imgUploadModal.isWikiFile
                    ? '再次上传'
                    : imgUploadModal.result?.wikitext
                      ? '重新上传'
                      : '上传 Wiki'}
              </button>
              <button
                type="button"
                onClick={() => setImgUploadModal(null)}
                disabled={imgUploadModal.loading}
                className="px-4 py-2 bg-white/10 hover:bg-white/15 text-white rounded-lg text-sm disabled:opacity-40"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
