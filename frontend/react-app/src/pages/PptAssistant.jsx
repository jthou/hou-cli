/**
 * PPT 助手：左输入 / 右输出+预览（与写作助手心智一致，组合 MarkdownPreview）
 * 草稿固化：localStorage，刷新/重进路由不丢（与智能助手页一致思路，键名独立）。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import MarkdownPreview from '../components/MarkdownPreview'
import ModelSelector from '../components/ModelSelector'
import SlideDeckVisualPreview from '../components/SlideDeckVisualPreview'
import { useSelectableModels } from '../hooks/useSelectableModels'

const PPT_ASSISTANT_STORAGE_KEY = 'hou_cli_ppt_assistant_draft_v1'
const DRAFT_VERSION = 1

function loadDraft() {
  try {
    const raw = localStorage.getItem(PPT_ASSISTANT_STORAGE_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (!o || typeof o !== 'object' || o.v !== DRAFT_VERSION) return null
    return o
  } catch {
    return null
  }
}

export default function PptAssistant() {
  const initial = loadDraft()
  const [article, setArticle] = useState(() =>
    typeof initial?.article === 'string' ? initial.article : ''
  )
  const [audience, setAudience] = useState(() =>
    typeof initial?.audience === 'string' ? initial.audience : ''
  )
  const [constraints, setConstraints] = useState(() =>
    typeof initial?.constraints === 'string' ? initial.constraints : ''
  )
  const [userRequirements, setUserRequirements] = useState(() =>
    typeof initial?.userRequirements === 'string' ? initial.userRequirements : ''
  )
  const [pptElementsJson, setPptElementsJson] = useState(() =>
    typeof initial?.pptElementsJson === 'string' ? initial.pptElementsJson : ''
  )
  const [pageInputsJson, setPageInputsJson] = useState(() =>
    typeof initial?.pageInputsJson === 'string' ? initial.pageInputsJson : ''
  )
  const [slideDeckJson, setSlideDeckJson] = useState(() =>
    typeof initial?.slideDeckJson === 'string' ? initial.slideDeckJson : ''
  )
  const [previewMd, setPreviewMd] = useState(() =>
    typeof initial?.previewMd === 'string' ? initial.previewMd : ''
  )
  const [rightTab, setRightTab] = useState(() =>
    ['elements', 'deck', 'preview'].includes(initial?.rightTab)
      ? initial.rightTab
      : 'preview'
  )
  const [loading, setLoading] = useState(false)
  const [streamStatus, setStreamStatus] = useState('')
  const [failedPages, setFailedPages] = useState(() => [])
  const [runId, setRunId] = useState(() =>
    typeof initial?.runId === 'string' ? initial.runId : ''
  )
  /** 生成模式：只在多页分页时生效 */
  const [generationMode, setGenerationMode] = useState(() =>
    typeof initial?.generationMode === 'string' ? initial.generationMode : 'sequential'
  )
  const [parallelism, setParallelism] = useState(() =>
    typeof initial?.parallelism === 'number' ? initial.parallelism : 4
  )
  const [error, setError] = useState('')
  const [pptxBusy, setPptxBusy] = useState(false)
  /** 百炼逐页整图：页 index → 配图 URL（与 banana-slides 心智接近：交付整页画面） */
  const [slideImageUrls, setSlideImageUrls] = useState(() => ({}))
  const [slideImageJobId, setSlideImageJobId] = useState('')
  const [imageGenBusy, setImageGenBusy] = useState(false)
  const [slideImageStyleNote, setSlideImageStyleNote] = useState('')
  const [bailianImageModel, setBailianImageModel] = useState('')
  const [slideImageParallelism, setSlideImageParallelism] = useState(2)
  /** 百炼配图失败的页 index，用于「仅重试失败页」 */
  const [slideImageFailedIndexes, setSlideImageFailedIndexes] = useState(() => [])
  /** 逗号/空格分隔的页码，用于「指定页重跑」（不依赖失败列表） */
  const [slideImageManualPages, setSlideImageManualPages] = useState('')
  /** 每行一个 https 参考图 URL（风格迁移；建议图像模型选 wan2.6-image 等多模态） */
  const [slideImageStyleRefUrls, setSlideImageStyleRefUrls] = useState('')
  const abortRef = useRef(null)
  const imageAbortRef = useRef(null)
  /** 默认 false = 单张幻灯片汇总关键要点；勾选 = 多页分页 */
  const [multiSlide, setMultiSlide] = useState(() => Boolean(initial?.multiSlide))
  const { providers, models: selectableModels, defaultModel, loading: modelsLoading } =
    useSelectableModels({ context: 'ppt_assistant' })
  const [selectedModel, setSelectedModel] = useState(() =>
    typeof initial?.selectedModel === 'string' ? initial.selectedModel : ''
  )

  /** 用于可视化预览；JSON 非法时置空，不阻塞编辑框 */
  const parsedSlideDeck = useMemo(() => {
    if (!slideDeckJson.trim()) return null
    try {
      const o = JSON.parse(slideDeckJson)
      if (!o || typeof o !== 'object' || !Array.isArray(o.slides)) return null
      return o
    } catch {
      return null
    }
  }, [slideDeckJson])

  const clearBailianSlideImages = useCallback(() => {
    setSlideImageUrls({})
    setSlideImageJobId('')
    setSlideImageFailedIndexes([])
  }, [])

  useEffect(() => {
    if (defaultModel && !selectedModel) setSelectedModel(defaultModel)
    else if (!selectedModel && selectableModels?.length) {
      setSelectedModel(selectableModels[0]?.value || '')
    }
  }, [defaultModel, selectedModel, selectableModels])

  useEffect(() => {
    const t = window.setTimeout(() => {
      try {
        localStorage.setItem(
          PPT_ASSISTANT_STORAGE_KEY,
          JSON.stringify({
            v: DRAFT_VERSION,
            article,
            audience,
            constraints,
            userRequirements,
            pptElementsJson,
            pageInputsJson,
            slideDeckJson,
            previewMd,
            multiSlide,
            rightTab,
            selectedModel,
            generationMode,
            parallelism,
            runId,
            savedAt: Date.now(),
          })
        )
      } catch (e) {
        console.warn('[PptAssistant] localStorage 写入失败', e)
      }
    }, 400)
    return () => window.clearTimeout(t)
  }, [
    article,
    audience,
    constraints,
    userRequirements,
    pptElementsJson,
    pageInputsJson,
    slideDeckJson,
    previewMd,
    multiSlide,
    rightTab,
    selectedModel,
    generationMode,
    parallelism,
    runId,
  ])

  const clearLocalDraft = useCallback(() => {
    try {
      localStorage.removeItem(PPT_ASSISTANT_STORAGE_KEY)
    } catch {
      /* ignore */
    }
    setArticle('')
    setAudience('')
    setConstraints('')
    setUserRequirements('')
    setPptElementsJson('')
    setPageInputsJson('')
    setSlideDeckJson('')
    setPreviewMd('')
    setRightTab('preview')
    setMultiSlide(false)
    setGenerationMode('sequential')
    setParallelism(4)
    setRunId('')
    setSelectedModel('')
    setError('')
  }, [])

  const metaPayload = useCallback(() => {
    const m = {}
    if (audience.trim()) m.audience = audience.trim()
    if (constraints.trim()) m.constraints_note = constraints.trim()
    if (userRequirements.trim()) m.user_requirements = userRequirements.trim()
    return m
  }, [audience, constraints, userRequirements])

  const parsePageInputs = useCallback(() => {
    const raw = (pageInputsJson || '').trim()
    if (!raw) return { value: undefined, error: '' }
    try {
      const v = JSON.parse(raw)
      if (!Array.isArray(v)) return { value: undefined, error: 'page_inputs 必须是 JSON 数组' }
      return { value: v, error: '' }
    } catch (e) {
      return {
        value: undefined,
        error: `page_inputs JSON 解析失败：${e.message || String(e)}`,
      }
    }
  }, [pageInputsJson])

  const canStreamParallel = useMemo(
    () => Boolean(multiSlide) && generationMode === 'parallel',
    [multiSlide, generationMode]
  )

  const cancelRunning = useCallback(() => {
    if (abortRef.current) {
      try {
        abortRef.current.abort()
      } catch {
        /* ignore */
      }
      abortRef.current = null
    }
    setLoading(false)
    setStreamStatus('已取消')
  }, [])

  const pollRunStatus = useCallback(async rid => {
    if (!rid) return
    setStreamStatus('连接中断，正在恢复进度…')
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 1000))
      try {
        const res = await fetch(
          `/api/ppt-assistant/run-status?run_id=${encodeURIComponent(rid)}`
        )
        const data = await res.json().catch(() => ({}))
        if (!res.ok) continue
        if (data.status === 'not_found') continue
        if (data.ppt_elements) setPptElementsJson(JSON.stringify(data.ppt_elements, null, 2))
        if (data.slide_deck) {
          setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
          setPreviewMd(data.slide_deck_markdown || '')
          setRightTab('preview')
          setStreamStatus('')
          setLoading(false)
          return
        }
        setStreamStatus(`恢复中… stage=${data.stage || 'running'}`)
      } catch {
        /* ignore */
      }
    }
    setStreamStatus('恢复超时（可稍后点击「恢复进度」或重试生成）')
  }, [])

  const runFull = useCallback(async () => {
    setError('')
    setLoading(true)
    setStreamStatus('')
    setFailedPages([])
    try {
      const { value: pageInputs, error: pageInputsErr } = parsePageInputs()
      if (pageInputsErr) throw new Error(pageInputsErr)

      // 多页并行时走 SSE，能逐页显示生成进度
      if (canStreamParallel) {
        const controller = new AbortController()
        abortRef.current = controller
        const res = await fetch('/api/ppt-assistant/run-stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify({
            article: article.trim(),
            meta: metaPayload(),
            deck_constraints: constraints.trim(),
            single_slide: !multiSlide,
            generation_mode: 'parallel',
            parallelism,
            page_inputs: pageInputs,
            ...(runId ? { run_id: runId } : {}),
            ...(selectedModel ? { model: selectedModel } : {}),
          }),
        })
        if (!res.ok || !res.body) {
          const t = await res.text().catch(() => '')
          throw new Error(t || res.statusText || '请求失败')
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        const slidesSeen = new Set()

        try {
          while (true) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })

            // SSE 以 \n\n 分隔；每段包含 data: ...
            const parts = buffer.split('\n\n')
            buffer = parts.pop() || ''
            for (const part of parts) {
              const line = part
                .split('\n')
                .map(l => l.trim())
                .find(l => l.startsWith('data: '))
              if (!line) continue
              const dataStr = line.slice('data: '.length).trim()
              if (!dataStr) continue

              let outer
              try {
                outer = JSON.parse(dataStr)
              } catch {
                continue
              }

              if (outer.status === 'error') {
                throw new Error(outer.error || '请求失败')
              }

              if (!outer.content) continue
              let payload
              try {
                payload = JSON.parse(outer.content)
              } catch {
                continue
              }

              if (payload.event === 'run_started' && payload.run_id) {
                setRunId(String(payload.run_id))
                setStreamStatus('开始运行…')
              } else if (payload.event === 'extract_done') {
                if (payload.run_id) setRunId(String(payload.run_id))
                setStreamStatus('提取完成，开始生成幻灯片…')
              } else if (payload.event === 'slide_ready') {
                const pi = payload.page_index
                if (!slidesSeen.has(pi)) slidesSeen.add(pi)
                setStreamStatus(`已生成第 ${pi} 页`)
              } else if (payload.event === 'slide_failed') {
                const pi = payload.page_index
                setFailedPages(prev => (prev.includes(pi) ? prev : [...prev, pi]))
                setStreamStatus(`第 ${pi} 页生成失败：${payload.error || ''}`)
              } else if (payload.event === 'done') {
                if (payload.run_id) setRunId(String(payload.run_id))
                clearBailianSlideImages()
                if (payload.ppt_elements) {
                  setPptElementsJson(JSON.stringify(payload.ppt_elements, null, 2))
                }
                if (payload.slide_deck) {
                  setSlideDeckJson(JSON.stringify(payload.slide_deck, null, 2))
                  setPreviewMd(payload.slide_deck_markdown || '')
                }
                setRightTab('preview')
                setStreamStatus('')
              }
            }
          }
        } catch (e) {
          if (controller.signal.aborted || e?.name === 'AbortError') {
            setStreamStatus('已取消')
            throw e
          }
          await pollRunStatus(runId)
          return
        } finally {
          abortRef.current = null
        }
      } else {
        const res = await fetch('/api/ppt-assistant/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            article: article.trim(),
            meta: metaPayload(),
            deck_constraints: constraints.trim(),
            single_slide: !multiSlide,
            generation_mode: generationMode,
            parallelism,
            page_inputs: pageInputs,
            ...(selectedModel ? { model: selectedModel } : {}),
          }),
        })

        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(data.detail || res.statusText || '请求失败')
        }

        clearBailianSlideImages()
        setPptElementsJson(JSON.stringify(data.ppt_elements, null, 2))
        if (data.slide_deck) {
          setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
        } else {
          setSlideDeckJson('')
        }
        setPreviewMd(data.slide_deck_markdown || '')
        setRightTab('preview')
        setStreamStatus('')
      }
    } catch (e) {
      if (e?.name === 'AbortError') setError('')
      else setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [
    article,
    constraints,
    metaPayload,
    multiSlide,
    selectedModel,
    generationMode,
    parallelism,
    canStreamParallel,
    parsePageInputs,
    pollRunStatus,
    runId,
    clearBailianSlideImages,
  ])

  const retryFailedPages = useCallback(async () => {
    setError('')
    if (!failedPages.length) return
    if (!slideDeckJson.trim()) {
      setError('没有 slide_deck 可用于重试，请先生成或提取')
      return
    }
    setLoading(true)
    setStreamStatus('')
    try {
      const deck = JSON.parse(slideDeckJson)
      const elements =
        pptElementsJson && pptElementsJson.trim()
          ? JSON.parse(pptElementsJson)
          : undefined

      const insBase = userRequirements.trim()
        ? `重写以下失败页：${failedPages.join(
            ','
          )}。并严格遵守你的意见与需求。`
        : `重写以下失败页：${failedPages.join(
            ','
          )}。保持与其它页一致的风格与信息粒度。`

      const res = await fetch('/api/ppt-assistant/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slide_deck: deck,
          target_slide_indexes: failedPages,
          instructions: insBase,
          ppt_elements: elements,
          user_requirements: userRequirements.trim(),
          max_repair_attempts: 2,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || '请求失败')
      }
      if (data.slide_deck) {
        clearBailianSlideImages()
        setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
      }
      setPreviewMd(data.slide_deck_markdown || _deckToMdFallback(data.slide_deck))
      setRightTab('preview')
      setFailedPages([])
      setStreamStatus('')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [
    failedPages,
    slideDeckJson,
    pptElementsJson,
    userRequirements,
    selectedModel,
    clearBailianSlideImages,
  ])

  const downloadPptx = useCallback(async () => {
    setError('')
    if (!slideDeckJson.trim()) {
      setError('没有 slide_deck，无法导出 .pptx')
      return
    }
    let deck
    try {
      deck = JSON.parse(slideDeckJson)
    } catch {
      setError('slide_deck JSON 无法解析')
      return
    }
    setPptxBusy(true)
    try {
      const res = await fetch('/api/ppt-assistant/export-pptx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slide_deck: deck,
          ...(slideImageJobId ? { slide_image_job_id: slideImageJobId } : {}),
        }),
      })
      if (!res.ok) {
        const ct = res.headers.get('content-type') || ''
        let msg = res.statusText || '导出失败'
        if (ct.includes('application/json')) {
          const j = await res.json()
          if (typeof j.detail === 'string') msg = j.detail
          else if (Array.isArray(j.detail))
            msg = j.detail.map(x => x.msg || JSON.stringify(x)).join('; ')
        } else {
          const t = await res.text()
          if (t) msg = t.length > 300 ? `${t.slice(0, 300)}…` : t
        }
        throw new Error(msg)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'slide_deck.pptx'
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setPptxBusy(false)
    }
  }, [slideDeckJson, slideImageJobId])

  const runBailianSlideImages = useCallback(
    async (opts = {}) => {
    const retryFailedOnly = Boolean(opts.retryFailedOnly)
    const manualRaw = opts.manualOnlyIndexes
    const manualOnly =
      Array.isArray(manualRaw) && manualRaw.length
        ? [
            ...new Set(
              manualRaw
                .map(n => Number(n))
                .filter(n => Number.isFinite(n) && n >= 1)
            ),
          ].sort((a, b) => a - b)
        : null
    const styleRefList = slideImageStyleRefUrls
      .split(/\r?\n/)
      .map(s => s.trim())
      .filter(
        s =>
          s.startsWith('https://') ||
          s.startsWith('http://') ||
          s.startsWith('data:image/')
      )
      .slice(0, 5)

    setError('')
    if (!parsedSlideDeck) {
      setError('没有可用的 slide_deck，请先生成幻灯片结构')
      return
    }
    if (manualOnly?.length) {
      /* 指定页重跑：可选复用 job_id；不传则新建仅含这些页的配图任务 */
    } else if (retryFailedOnly) {
      if (!slideImageJobId) {
        setError('没有可复用的配图 job，请先「百炼生成整页配图」')
        return
      }
      if (!slideImageFailedIndexes.length) {
        setError('没有记录到失败的配图页')
        return
      }
    }
    if (!retryFailedOnly && !manualOnly?.length) setSlideImageFailedIndexes([])
    setImageGenBusy(true)
    const useOnly = manualOnly?.length
      ? manualOnly
      : retryFailedOnly
        ? [...slideImageFailedIndexes]
        : null
    setStreamStatus(
      manualOnly?.length
        ? `百炼配图：指定页 ${manualOnly.join('、')}…`
        : retryFailedOnly
          ? `百炼配图：补跑失败页（${slideImageFailedIndexes.join(',')}）…`
          : '百炼配图：排队逐页生成…'
    )
    const controller = new AbortController()
    imageAbortRef.current = controller
    try {
      const body = {
        slide_deck: parsedSlideDeck,
        style_note: slideImageStyleNote.trim(),
        parallelism: Math.max(1, Math.min(8, Number(slideImageParallelism) || 2)),
        ...(bailianImageModel.trim() ? { image_model: bailianImageModel.trim() } : {}),
        ...(styleRefList.length ? { style_reference_urls: styleRefList } : {}),
        ...(useOnly?.length
          ? {
              only_indexes: useOnly,
              ...((slideImageJobId || retryFailedOnly)
                ? { job_id: slideImageJobId }
                : {}),
            }
          : {}),
      }
      const res = await fetch('/api/ppt-assistant/slide-images/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify(body),
      })
      if (!res.ok || !res.body) {
        const t = await res.text().catch(() => '')
        throw new Error(t || res.statusText || '配图请求打开失败')
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        for (const part of parts) {
          const line = part
            .split('\n')
            .map(l => l.trim())
            .find(l => l.startsWith('data: '))
          if (!line) continue
          const dataStr = line.slice('data: '.length).trim()
          let outer
          try {
            outer = JSON.parse(dataStr)
          } catch {
            continue
          }
          if (outer.status === 'error') {
            let inner = {}
            try {
              inner = JSON.parse(outer.content || '{}')
            } catch {
              /* */
            }
            throw new Error(inner.error || outer.error || '百炼配图失败')
          }
          if (!outer.content) continue
          let payload
          try {
            payload = JSON.parse(outer.content)
          } catch {
            continue
          }
          if (payload.event === 'slide_images_fatal') {
            throw new Error(payload.error || '百炼配图中断')
          }
          if (payload.event === 'slide_images_job' && payload.job_id) {
            setSlideImageJobId(String(payload.job_id))
            setStreamStatus(`百炼配图 job=${String(payload.job_id).slice(0, 8)}…`)
          } else if (payload.event === 'slide_image_ready' && payload.page_index != null) {
            const pi = Number(payload.page_index)
            const u = payload.url
            if (u)
              setSlideImageUrls(prev => ({
                ...prev,
                [pi]: u,
              }))
            setSlideImageFailedIndexes(prev => prev.filter(x => x !== pi))
            setStreamStatus(`百炼：第 ${payload.page_index} 页配图就绪`)
          } else if (payload.event === 'slide_image_failed') {
            const pi = Number(payload.page_index)
            if (Number.isFinite(pi))
              setSlideImageFailedIndexes(prev =>
                prev.includes(pi) ? prev : [...prev, pi].sort((a, b) => a - b)
              )
            setStreamStatus(
              `百炼：第 ${payload.page_index} 页失败 ${payload.error || ''}`.trim()
            )
          } else if (payload.event === 'slide_images_done') {
            if (payload.job_id) setSlideImageJobId(String(payload.job_id))
            if (payload.images && typeof payload.images === 'object')
              setSlideImageUrls(prev => ({ ...prev, ...payload.images }))
            const errKeys = Object.keys(payload.errors || {})
              .map(Number)
              .filter(n => Number.isFinite(n))
              .sort((a, b) => a - b)
            setSlideImageFailedIndexes(errKeys)
            setStreamStatus(
              errKeys.length
                ? '百炼配图已完成（部分页失败，可点「重试失败配图页」）'
                : '百炼配图已全部完成，可下载带图 pptx'
            )
          }
        }
      }
    } catch (e) {
      if (e?.name === 'AbortError') setStreamStatus('已取消百炼配图')
      else setError(e.message || String(e))
    } finally {
      imageAbortRef.current = null
      setImageGenBusy(false)
    }
  },
  [
    parsedSlideDeck,
    slideImageStyleNote,
    bailianImageModel,
    slideImageParallelism,
    slideImageJobId,
    slideImageFailedIndexes,
    slideImageStyleRefUrls,
  ]
)

  const cancelBailianImages = useCallback(() => {
    imageAbortRef.current?.abort()
  }, [])

  const runExtractOnly = useCallback(async () => {
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/ppt-assistant/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article: article.trim(),
          meta: metaPayload(),
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || '请求失败')
      }
      setPptElementsJson(JSON.stringify(data.ppt_elements, null, 2))
      clearBailianSlideImages()
      setSlideDeckJson('')
      setPreviewMd('')
      setRightTab('elements')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [article, metaPayload, selectedModel, clearBailianSlideImages])

  const runDeck = useCallback(async () => {
    setError('')
    if (!pptElementsJson.trim()) {
      setError('请先提取或粘贴 ppt_elements JSON')
      return
    }
    setLoading(true)
    setStreamStatus('')
    try {
      const elements = JSON.parse(pptElementsJson)
      const { value: pageInputs, error: pageInputsErr } = parsePageInputs()
      if (pageInputsErr) throw new Error(pageInputsErr)
      const res = await fetch('/api/ppt-assistant/deck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ppt_elements: elements,
          constraints: constraints.trim(),
          user_requirements: userRequirements.trim(),
          single_slide: !multiSlide,
          generation_mode: generationMode,
          parallelism,
          page_inputs: pageInputs,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || '请求失败')
      }
      clearBailianSlideImages()
      setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
      setPreviewMd(data.slide_deck_markdown || _deckToMdFallback(data.slide_deck))
      setRightTab('preview')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [
    pptElementsJson,
    parsePageInputs,
    constraints,
    userRequirements,
    multiSlide,
    selectedModel,
    generationMode,
    parallelism,
    clearBailianSlideImages,
  ])

  return (
    <div className="flex flex-col h-full min-h-0 text-fg">
      <header className="shrink-0 px-4 py-3 border-b border-border bg-surface flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-white">📊 PPT 助手</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted hidden sm:inline">
            草稿已保存在本机浏览器；刷新不丢失
          </span>
          <button
            type="button"
            onClick={clearLocalDraft}
            className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-muted hover:text-fg"
            title="清除本地草稿（输入与右侧结果）"
          >
            清除草稿
          </button>
        </div>
      </header>
      <div className="flex-1 flex min-h-0 min-w-0 flex-col md:flex-row gap-0">
        <section className="flex-1 flex flex-col min-w-0 min-h-[40vh] md:min-h-0 border-b md:border-b-0 md:border-r border-border p-3 gap-2">
          <label className="text-sm text-muted">长文章 / 素材</label>
          <textarea
            className="flex-1 min-h-[200px] w-full rounded border border-border bg-black/20 p-2 text-sm font-mono resize-y"
            placeholder="粘贴长文 Markdown 或纯文本…"
            value={article}
            onChange={e => setArticle(e.target.value)}
          />
          <label className="text-sm text-muted">
            用户意见与需求（未填则按默认策略；填写后模型将优先严格按你的要求提取与排版）
          </label>
          <textarea
            className="min-h-[72px] max-h-[160px] w-full rounded border border-border bg-black/20 p-2 text-sm resize-y"
            placeholder="例如：必须突出第三节、只保留与 XX 相关的论点、标题风格要偏技术/偏商务…（提取、合并与生成 deck 时均为最高优先级指令）"
            value={userRequirements}
            onChange={e => setUserRequirements(e.target.value)}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input
              className="rounded border border-border bg-black/20 px-2 py-1 text-sm"
              placeholder="受众（可选）"
              value={audience}
              onChange={e => setAudience(e.target.value)}
            />
            <input
              className="rounded border border-border bg-black/20 px-2 py-1 text-sm"
              placeholder="页数/风格等约束（可选）"
              value={constraints}
              onChange={e => setConstraints(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={multiSlide}
              onChange={e => setMultiSlide(e.target.checked)}
              className="rounded border-border"
            />
            多页分页（默认关 = 一张幻灯片展示关键要点）
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label className="text-sm text-muted flex items-center gap-2">
              生成模式（多页时）：
              <select
                value={generationMode}
                disabled={!multiSlide}
                onChange={e => setGenerationMode(e.target.value)}
                className="rounded border border-border bg-black/20 px-2 py-1 text-sm disabled:opacity-40"
              >
                <option value="sequential">顺序</option>
                <option value="parallel">并行</option>
              </select>
            </label>
            <label className="text-sm text-muted flex items-center gap-2">
              并行上限：
              <input
                type="number"
                min={1}
                max={16}
                value={parallelism}
                disabled={!multiSlide || generationMode !== 'parallel'}
                onChange={e => {
                  const v = Number(e.target.value)
                  setParallelism(Number.isFinite(v) ? Math.max(1, Math.min(16, v)) : 4)
                }}
                className="rounded border border-border bg-black/20 px-2 py-1 text-sm disabled:opacity-40 w-20"
              />
            </label>
          </div>
          <label className="text-sm text-muted">页级输入 page_inputs（可选，JSON 数组）</label>
          <textarea
            className="min-h-[72px] max-h-[200px] w-full rounded border border-border bg-black/20 p-2 text-xs font-mono resize-y"
            placeholder='例如：[{"index":1,"title_hint":"页1","bullets_hint":["A"],"sources":["src1"]}]'
            value={pageInputsJson}
            onChange={e => setPageInputsJson(e.target.value)}
          />
          <div className="rounded border border-border/80 bg-black/15 p-2 space-y-2">
            <p className="text-xs font-medium text-muted">
              百炼 · 整页配图（可选，对齐 Vibe PPT：逐页文生图后预览与导出满幅嵌入）
            </p>
            <textarea
              className="min-h-[56px] w-full rounded border border-border bg-black/20 p-2 text-xs resize-y"
              placeholder="配图额外风格说明（可选）：如深色科技风、参考阿里云大会主视觉、扁平插画…"
              value={slideImageStyleNote}
              onChange={e => setSlideImageStyleNote(e.target.value)}
            />
            <input
              className="w-full rounded border border-border bg-black/20 px-2 py-1 text-xs font-mono"
              placeholder="图像模型 id（可选），如 bailian-wan2.6-t2i；风格迁移建议 bailian-wan2.6-image；空=服务默认"
              value={bailianImageModel}
              onChange={e => setBailianImageModel(e.target.value)}
            />
            <textarea
              className="min-h-[56px] w-full rounded border border-border bg-black/20 p-2 text-xs font-mono resize-y"
              placeholder="风格参考图 URL（可选）：每行一个 https 链接。wan2.6-image 等会以图+文调用百炼；纯 t2i 仅把链接写进文生图说明。"
              value={slideImageStyleRefUrls}
              onChange={e => setSlideImageStyleRefUrls(e.target.value)}
            />
            <label className="flex items-center gap-2 text-[11px] text-muted">
              页级并行数（1–8，过大可能触发百炼限流）
              <input
                type="number"
                min={1}
                max={8}
                value={slideImageParallelism}
                onChange={e => {
                  const v = Number(e.target.value)
                  setSlideImageParallelism(Number.isFinite(v) ? Math.max(1, Math.min(8, v)) : 2)
                }}
                className="w-14 rounded border border-border bg-black/25 px-1 py-0.5 text-xs"
              />
            </label>
            <div className="flex flex-wrap items-end gap-2">
              <label className="flex-1 min-w-[160px] text-[11px] text-muted space-y-0.5">
                <span className="block">指定页重跑（页码与 slide index 一致，逗号/空格分隔）</span>
                <input
                  className="w-full rounded border border-border bg-black/20 px-2 py-1 text-xs font-mono"
                  placeholder="例：2 5 7 或 2,5,7"
                  value={slideImageManualPages}
                  onChange={e => setSlideImageManualPages(e.target.value)}
                />
              </label>
              <button
                type="button"
                disabled={imageGenBusy || !parsedSlideDeck || !slideImageManualPages.trim()}
                onClick={() => {
                  const nums = slideImageManualPages
                    .split(/[,，\s\n]+/)
                    .map(s => parseInt(s.trim(), 10))
                    .filter(n => Number.isFinite(n) && n >= 1)
                  const uniq = [...new Set(nums)].sort((a, b) => a - b)
                  if (!uniq.length) {
                    setError('请输入有效页码（正整数）')
                    return
                  }
                  runBailianSlideImages({ manualOnlyIndexes: uniq })
                }}
                className="shrink-0 px-2.5 py-1.5 rounded bg-sky-600/85 hover:bg-sky-600 text-xs text-white disabled:opacity-40"
                title="仅对填写的页重新出图；若已有 job 则写入同一任务以便导出"
              >
                重跑指定页
              </button>
            </div>
          </div>
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
            providers={providers}
            models={selectableModels}
            loading={modelsLoading}
            className="flex-wrap"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={loading || !article.trim()}
              onClick={runExtractOnly}
              className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm disabled:opacity-40"
            >
              提取 PPT 元素
            </button>
            <button
              type="button"
              disabled={loading || !pptElementsJson.trim()}
              onClick={runDeck}
              className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm disabled:opacity-40"
            >
              生成页面（基于右侧 JSON）
            </button>
            <button
              type="button"
              disabled={loading || !article.trim()}
              onClick={runFull}
              className="px-3 py-1.5 rounded bg-accent/80 hover:bg-accent text-sm text-white disabled:opacity-40"
            >
              一键：提取 + 生成
            </button>
            {loading ? (
              <button
                type="button"
                onClick={cancelRunning}
                className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm"
              >
                取消生成
              </button>
            ) : null}
            {failedPages.length ? (
              <button
                type="button"
                disabled={loading}
                onClick={retryFailedPages}
                className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm disabled:opacity-40"
                title="重写失败页（基于现有 slide_deck 调用 /ppt-assistant/refine）"
              >
                重试失败页（{failedPages.length}）
              </button>
            ) : null}
            {!loading && runId ? (
              <button
                type="button"
                onClick={() => pollRunStatus(runId)}
                className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm"
                title="断线恢复：查询 /ppt-assistant/run-status"
              >
                恢复进度
              </button>
            ) : null}
            <button
              type="button"
              disabled={pptxBusy || !slideDeckJson.trim()}
              onClick={downloadPptx}
              className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm disabled:opacity-40"
              title={
                slideImageJobId
                  ? '导出 pptx：已成功配图的页为整页满幅图，其余页仍为文案版式'
                  : '将当前 slide_deck 导出为 .pptx（要点、讲者备注；无整页配图时为占位）'
              }
            >
              {pptxBusy ? '导出中…' : slideImageJobId ? '下载 .pptx（含百炼图）' : '下载 .pptx'}
            </button>
            <button
              type="button"
              disabled={imageGenBusy || !parsedSlideDeck}
              onClick={() => runBailianSlideImages()}
              className="px-3 py-1.5 rounded bg-teal-600/85 hover:bg-teal-600 text-sm text-white disabled:opacity-40"
              title="调用百炼文生图 API，按 slide_deck 每页生成 16:9 整页画面（需配置百炼 Key）"
            >
              {imageGenBusy ? '百炼配图中…' : '百炼生成整页配图'}
            </button>
            {slideImageFailedIndexes.length ? (
              <button
                type="button"
                disabled={imageGenBusy || !parsedSlideDeck || !slideImageJobId}
                onClick={() => runBailianSlideImages({ retryFailedOnly: true })}
                className="px-3 py-1.5 rounded bg-amber-600/85 hover:bg-amber-600 text-sm text-white disabled:opacity-40"
                title={`仅对失败页重新出图：${slideImageFailedIndexes.join(', ')}`}
              >
                重试失败配图页（{slideImageFailedIndexes.length}）
              </button>
            ) : null}
            {imageGenBusy ? (
              <button
                type="button"
                onClick={cancelBailianImages}
                className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 text-sm"
              >
                取消配图
              </button>
            ) : null}
          </div>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          {loading ? <p className="text-sm text-muted">处理中…</p> : null}
          {streamStatus ? <p className="text-sm text-muted">{streamStatus}</p> : null}
        </section>
        <section className="flex-1 flex flex-col min-w-0 min-h-0 p-3 gap-2">
          <div className="flex gap-1 border-b border-border pb-2">
            {[
              ['elements', 'ppt_elements'],
              ['deck', 'slide_deck JSON'],
              ['preview', '预览 · 幻灯片'],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setRightTab(id)}
                className={`px-2 py-1 text-sm rounded ${
                  rightTab === id ? 'bg-white/15 text-white' : 'text-muted hover:text-fg'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex-1 min-h-0 flex flex-col rounded border border-border bg-black/15 overflow-hidden">
            {rightTab === 'preview' ? (
              <div className="flex flex-col flex-1 min-h-0">
                <div className="shrink-0 px-2 py-1.5 text-xs font-medium text-muted bg-black/25 border-b border-border/80 flex items-center justify-between gap-2">
                  <span>
                    幻灯片预览（16:9 · 顶栏蓝 + 白底正文 + 浅蓝图示区；讲述在片下方）
                  </span>
                  {parsedSlideDeck?.slides?.length ? (
                    <span className="text-[11px] text-muted/90 tabular-nums">
                      共 {parsedSlideDeck.slides.length} 页
                    </span>
                  ) : null}
                </div>
                {slideDeckJson.trim() && !parsedSlideDeck ? (
                  <p className="shrink-0 px-3 py-1.5 text-xs text-amber-400/95 bg-amber-500/10 border-b border-amber-500/20">
                    slide_deck JSON 无法解析，可视化暂不可用；请修正语法或切到「slide_deck JSON」标签检查。
                  </p>
                ) : null}
                <div className="flex-1 min-h-0 overflow-auto p-3 md:p-4 bg-gradient-to-b from-[#5B9BD5]/[0.12] via-slate-500/[0.06] to-transparent dark:from-[#5B9BD5]/[0.14] dark:via-slate-950/30 dark:to-slate-950/50 rounded-none">
                  <SlideDeckVisualPreview deck={parsedSlideDeck} slideImageUrls={slideImageUrls} />
                </div>
                <details className="shrink-0 border-t border-border bg-black/25">
                  <summary className="px-3 py-2 text-xs font-medium text-muted cursor-pointer hover:text-fg list-none flex items-center gap-2 select-none [&::-webkit-details-marker]:hidden">
                    <span className="opacity-60" aria-hidden>
                      ▸
                    </span>
                    Markdown 稿（对照、复制；与「slide_deck JSON」同源）
                  </summary>
                  <div className="border-t border-border/60 flex flex-col max-h-[min(42vh,28rem)]">
                    <pre className="shrink-0 max-h-[min(18vh,12rem)] overflow-auto p-3 text-xs font-mono whitespace-pre-wrap break-words text-fg/85 border-b border-border/40 bg-black/20">
                      {previewMd.trim()
                        ? previewMd
                        : '（尚未生成 Markdown 稿：请「一键」或先提取再生成页面）'}
                    </pre>
                    <div className="flex-1 min-h-[8rem] overflow-auto p-2">
                      <MarkdownPreview
                        markdown={previewMd}
                        theme="dark"
                        className="ppt-deck-preview text-sm"
                      />
                    </div>
                  </div>
                </details>
              </div>
            ) : (
              <pre className="flex-1 min-h-0 overflow-auto p-3 text-xs font-mono whitespace-pre-wrap break-words text-muted">
                {rightTab === 'elements' ? pptElementsJson || '（空）' : slideDeckJson || '（空）'}
              </pre>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function _bulletParts(b) {
  if (b && typeof b === 'object' && ('text' in b || 'point' in b)) {
    const t = String(b.text ?? b.point ?? '').trim()
    const e = String(b.speaker_elaboration ?? b.elaboration ?? '').trim()
    return { t, e }
  }
  return { t: String(b ?? '').trim(), e: '' }
}

function _deckToMdFallback(deck) {
  if (!deck || !deck.slides) return ''
  const title = deck.deck_title || '演示'
  const lines = [`# ${title}`, '']
  for (const s of deck.slides) {
    lines.push(`## 第 ${s.index} 页 (${s.kind || 'content'}) — ${s.title || ''}`, '')
    for (const b of s.bullets || []) {
      const { t, e } = _bulletParts(b)
      if (!t) continue
      lines.push(`- **${t}**`)
      if (e) {
        lines.push('')
        lines.push(`  > ${e}`)
        lines.push('')
      } else {
        lines.push('')
      }
    }
    if (s.speaker_notes) lines.push(`*本页备注：${s.speaker_notes}*`, '')
  }
  return lines.join('\n')
}
