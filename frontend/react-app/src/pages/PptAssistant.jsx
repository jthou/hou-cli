/**
 * PPT 助手：左输入 / 右输出+预览（与写作助手心智一致，组合 MarkdownPreview）
 * 草稿固化：localStorage，刷新/重进路由不丢（与智能助手页一致思路，键名独立）。
 */
import { useCallback, useEffect, useState } from 'react'
import MarkdownPreview from '../components/MarkdownPreview'
import ModelSelector from '../components/ModelSelector'
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
  const [error, setError] = useState('')
  /** 默认 false = 单张幻灯片汇总关键要点；勾选 = 多页分页 */
  const [multiSlide, setMultiSlide] = useState(() => Boolean(initial?.multiSlide))
  const { providers, models: selectableModels, defaultModel, loading: modelsLoading } =
    useSelectableModels({ context: 'ppt_assistant' })
  const [selectedModel, setSelectedModel] = useState(() =>
    typeof initial?.selectedModel === 'string' ? initial.selectedModel : ''
  )

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
            slideDeckJson,
            previewMd,
            multiSlide,
            rightTab,
            selectedModel,
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
    slideDeckJson,
    previewMd,
    multiSlide,
    rightTab,
    selectedModel,
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
    setSlideDeckJson('')
    setPreviewMd('')
    setRightTab('preview')
    setMultiSlide(false)
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

  const runFull = useCallback(async () => {
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/ppt-assistant/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article: article.trim(),
          meta: metaPayload(),
          deck_constraints: constraints.trim(),
          single_slide: !multiSlide,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || '请求失败')
      }
      setPptElementsJson(JSON.stringify(data.ppt_elements, null, 2))
      if (data.slide_deck) {
        setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
      } else {
        setSlideDeckJson('')
      }
      setPreviewMd(data.slide_deck_markdown || '')
      setRightTab('preview')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [article, constraints, metaPayload, multiSlide, selectedModel])

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
      setSlideDeckJson('')
      setPreviewMd('')
      setRightTab('elements')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [article, metaPayload, selectedModel])

  const runDeck = useCallback(async () => {
    setError('')
    if (!pptElementsJson.trim()) {
      setError('请先提取或粘贴 ppt_elements JSON')
      return
    }
    setLoading(true)
    try {
      const elements = JSON.parse(pptElementsJson)
      const res = await fetch('/api/ppt-assistant/deck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ppt_elements: elements,
          constraints: constraints.trim(),
          user_requirements: userRequirements.trim(),
          single_slide: !multiSlide,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || '请求失败')
      }
      setSlideDeckJson(JSON.stringify(data.slide_deck, null, 2))
      setPreviewMd(data.slide_deck_markdown || _deckToMdFallback(data.slide_deck))
      setRightTab('preview')
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [pptElementsJson, constraints, userRequirements, multiSlide, selectedModel])

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
          </div>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          {loading ? <p className="text-sm text-muted">处理中…</p> : null}
        </section>
        <section className="flex-1 flex flex-col min-w-0 min-h-0 p-3 gap-2">
          <div className="flex gap-1 border-b border-border pb-2">
            {[
              ['elements', 'ppt_elements'],
              ['deck', 'slide_deck JSON'],
              ['preview', '预览 · 上文下渲染'],
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
                <div className="flex flex-[2] flex-col min-h-0 min-h-[8rem] border-b border-border">
                  <div className="shrink-0 px-2 py-1.5 text-xs font-medium text-muted bg-black/25 border-b border-border/80">
                    文本内容（slide_deck → Markdown 稿，可对照修改源文后重写）
                  </div>
                  <pre className="flex-1 min-h-0 overflow-auto p-3 text-xs font-mono whitespace-pre-wrap break-words text-fg/90">
                    {previewMd.trim() ? previewMd : '（尚未生成：请「一键」或先提取再生成页面）'}
                  </pre>
                </div>
                <div className="flex flex-[3] flex-col min-h-0 min-h-[10rem]">
                  <div className="shrink-0 px-2 py-1.5 text-xs font-medium text-muted bg-black/25 border-b border-border/80">
                    PPT 预览（上图下文版式：渲染效果）
                  </div>
                  <div className="flex-1 min-h-0 overflow-auto p-2">
                    <MarkdownPreview
                      markdown={previewMd}
                      theme="dark"
                      className="ppt-deck-preview"
                    />
                  </div>
                </div>
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
