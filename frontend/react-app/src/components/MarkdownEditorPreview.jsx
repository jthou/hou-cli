/**
 * Markdown 编辑 + 预览 + 摘要 + 操作按钮（复制、发送到写作助手、写入 MediaWiki）
 * 默认可编辑时为左右分栏：左侧 Markdown、右侧实时预览；可选「摘要」全宽视图。
 */
import { useState, useEffect, useLayoutEffect, useCallback, useRef } from 'react'
import { flushSync } from 'react-dom'
import { insertSnippetAtTextareaCursor } from '../utils/mediawikiPasteImage'
import MarkdownPreview from './MarkdownPreview'
import MarkdownActionButtons from './MarkdownActionButtons'
import { useWritingSuggestions } from '../hooks/useWritingSuggestions'
import { tabCls, TEXTAREA_CLS_IN_PREVIEW_SHELL } from './editor/EditorConstants'
import WritingSuggestionsButton from './editor/WritingSuggestionsButton'
import EditAreaWithSuggestions from './editor/EditAreaWithSuggestions'
import {
  approxSourceLineFromTextareaScroll,
  scrollPreviewToSourceLine,
  sourceLineFromPreviewViewport,
  scrollTextareaToSourceLine,
} from '../utils/markdownScrollSync.js'

/**
 * @param {Object} props
 * @param {string} [props.content] - Markdown 内容
 * @param {(v: string) => void} [props.onContentChange] - 编辑模式下内容变化回调
 * @param {boolean} [props.editable=true] - 是否支持编辑模式
 * @param {'light'|'dark'} [props.theme='dark'] - 预览主题
 * @param {string} [props.className] - 容器类名
 * @param {(content: string) => void} [props.onCopy] - 复制回调，默认使用剪贴板
 * @param {(content: string) => void} [props.onSendToArticle] - 发送到写作助手回调，不传则隐藏按钮
 * @param {string} [props.sendToArticleLabel='发送到写作助手'] - 发送按钮文案
 * @param {boolean} [props.showMediaWiki=true] - 是否显示写入 MediaWiki 按钮
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考回调，不传则隐藏
 * @param {string} [props.sourceUrl] - 原文链接（如微信读书 URL），写入 MediaWiki 时自动追加到文末
 * @param {React.ReactNode} [props.footerExtra] - 底部额外按钮（如「同步到公众号草稿」）
 * @param {boolean} [props.showSummary=false] - 是否显示摘要区域
 * @param {string} [props.summary] - 摘要内容（受控）
 * @param {(v: string) => void} [props.onSummaryChange] - 摘要变化回调
 * @param {(content: string) => Promise<string>} [props.onGenerateSummary] - 生成摘要回调，返回摘要文本
 * @param {(err: Error) => void} [props.onSummaryError] - 生成失败时回调（如用于 toast 提示）
 * @param {Function} [props.onImgClick] - 点击预览区图片时回调，用于上传到 MediaWiki 等
 * @param {boolean} [props.previewWideFigures=false] - 预览内插图横向拉满预览区内边距（微信读书等示意图阅读）
 * @param {boolean} [props.previewInlineFigureZoom=false] - 预览内插图滚轮缩放、放大后拖拽（仍可点击图片打开 onImgClick 弹层）
 * @param {React.MutableRefObject<{ insertMarkdownAtCursor: (snippet: string) => void } | null>} [props.editorInsertRef] - 父组件 ref，用于在编辑框光标处插入 Markdown
 */
export default function MarkdownEditorPreview({
  content = '',
  onContentChange,
  editable = true,
  theme = 'dark',
  className = '',
  onCopy,
  onSendToArticle,
  sendToArticleLabel = '发送到写作助手',
  showMediaWiki = true,
  onAddToReference,
  sourceUrl = '',
  footerExtra,
  showSummary = false,
  summary = '',
  onSummaryChange,
  onGenerateSummary,
  onSummaryError,
  onImgClick,
  previewWideFigures = false,
  previewInlineFigureZoom = false,
  editorInsertRef,
}) {
  /** split：左编辑右预览；summary：全宽摘要 */
  const [paneMode, setPaneMode] = useState('split')
  const [editDraft, setEditDraft] = useState(content)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const textareaRef = useRef(null)
  /** 失焦前选区：点侧栏「插入图片」等时 textarea 失焦，浏览器常把 selection 挪到文末，插入须用此处保存的位置 */
  const savedTextareaSelectionRef = useRef({ start: 0, end: 0 })
  /** 插入后待应用：光标行 + 与预览对齐（须在 DOM 已写入 value 后的 layout 阶段执行） */
  const pendingInsertScrollRef = useRef(null)
  /** 右侧预览可滚动容器 */
  const previewScrollRef = useRef(null)
  /**
   * 正在程序化设置「预览区」scrollTop 时 >0，仅供预览 onScroll 忽略回传编辑区，避免死循环。
   * 注意：编辑区滚动触发的预览同步会连续多次进入此状态，若用单个 bool 且在同步期间丢弃后续编辑 scroll，预览会「跟丢」。
   */
  const scrollProgrammaticDepthRef = useRef(0)
  const scrollProgrammaticRef = useRef(false)
  /** 程序化滚动预览后，浏览器仍可能晚到触发 onScroll；此窗口内禁止预览→编辑，避免编辑区滚动条被拽动 */
  const suppressPreviewToEditorUntilRef = useRef(0)
  const rafEditorScrollRef = useRef(0)
  const rafPreviewScrollRef = useRef(0)
  /** 用户正在操作预览滚动条时，防抖内容更新不要抢预览位置 */
  const userScrollingPreviewRef = useRef(false)
  const previewScrollIdleTimerRef = useRef(null)
  /** 由预览同步或插入逻辑程序设置 textarea.scrollTop 时置 true，避免触发 handleEditorScroll 又把预览拽回 */
  const textareaScrollProgrammaticRef = useRef(false)
  /** 与 props.content 对齐，供 useLayoutEffect 读取「上一帧」本地草稿（避免闭包陈旧） */
  const editDraftRef = useRef(editDraft)
  editDraftRef.current = editDraft

  /**
   * 父级 content 变化时同步到 editDraft。若编辑区聚焦且为「在文末追加」类更新（如微信读书 OCR），须恢复选区，否则光标会跳到文末。
   */
  useLayoutEffect(() => {
    const prevLocal = editDraftRef.current
    if (content === prevLocal) return

    const ta = textareaRef.current
    if (!ta || document.activeElement !== ta) {
      setEditDraft(content)
      return
    }

    const selStart = ta.selectionStart
    const selEnd = ta.selectionEnd

    if (content.startsWith(prevLocal)) {
      flushSync(() => {
        setEditDraft(content)
      })
      ta.setSelectionRange(selStart, selEnd)
      return
    }

    if (prevLocal.startsWith(content)) {
      flushSync(() => {
        setEditDraft(content)
      })
      ta.setSelectionRange(
        Math.min(selStart, content.length),
        Math.min(selEnd, content.length),
      )
      return
    }

    flushSync(() => {
      setEditDraft(content)
    })
    ta.setSelectionRange(
      Math.min(selStart, content.length),
      Math.min(selEnd, content.length),
    )
  }, [content])

  const runTextareaScrollProgrammatic = useCallback((fn) => {
    textareaScrollProgrammaticRef.current = true
    try {
      fn()
    } finally {
      requestAnimationFrame(() => {
        textareaScrollProgrammaticRef.current = false
      })
    }
  }, [])

  const withScrollProgrammatic = useCallback((fn) => {
    scrollProgrammaticDepthRef.current += 1
    scrollProgrammaticRef.current = true
    suppressPreviewToEditorUntilRef.current = performance.now() + 140
    try {
      fn()
    } finally {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          scrollProgrammaticDepthRef.current = Math.max(0, scrollProgrammaticDepthRef.current - 1)
          scrollProgrammaticRef.current = scrollProgrammaticDepthRef.current > 0
        })
      })
    }
  }, [])

  /** 仅由编辑区滚动/布局同步驱动：始终允许排队更新预览，不得在 scrollProgrammatic 期间 return（否则快速滚编辑时预览卡住） */
  const flushEditorScrollToPreview = useCallback(() => {
    const ta = textareaRef.current
    const pv = previewScrollRef.current
    if (!ta || !pv) return
    const line = approxSourceLineFromTextareaScroll(ta)
    withScrollProgrammatic(() => {
      scrollPreviewToSourceLine(pv, line)
    })
  }, [withScrollProgrammatic])

  const flushPreviewScrollToEditor = useCallback(() => {
    if (scrollProgrammaticRef.current) return
    if (performance.now() < suppressPreviewToEditorUntilRef.current) return
    const ta = textareaRef.current
    const pv = previewScrollRef.current
    if (!ta || !pv) return
    /** 正在编辑源码时只应由编辑区驱动预览，禁止预览侧把 textarea.scrollTop 改掉（否则会感觉「打一两个字滚动条乱跳」） */
    if (document.activeElement === ta) return
    const line = sourceLineFromPreviewViewport(pv)
    runTextareaScrollProgrammatic(() => {
      scrollTextareaToSourceLine(ta, line)
    })
  }, [runTextareaScrollProgrammatic])

  const handleEditorScroll = useCallback(() => {
    if (textareaScrollProgrammaticRef.current) return
    if (rafEditorScrollRef.current) cancelAnimationFrame(rafEditorScrollRef.current)
    rafEditorScrollRef.current = requestAnimationFrame(() => {
      rafEditorScrollRef.current = 0
      flushEditorScrollToPreview()
    })
  }, [flushEditorScrollToPreview])

  const handlePreviewScroll = useCallback(() => {
    if (scrollProgrammaticRef.current) return
    if (performance.now() < suppressPreviewToEditorUntilRef.current) return
    const ta = textareaRef.current
    if (ta && document.activeElement === ta) return
    userScrollingPreviewRef.current = true
    if (previewScrollIdleTimerRef.current) clearTimeout(previewScrollIdleTimerRef.current)
    previewScrollIdleTimerRef.current = window.setTimeout(() => {
      previewScrollIdleTimerRef.current = null
      userScrollingPreviewRef.current = false
    }, 500)
    if (rafPreviewScrollRef.current) cancelAnimationFrame(rafPreviewScrollRef.current)
    rafPreviewScrollRef.current = requestAnimationFrame(() => {
      rafPreviewScrollRef.current = 0
      flushPreviewScrollToEditor()
    })
  }, [flushPreviewScrollToEditor])

  /** 进入分栏：按源码行对齐预览；多次延迟以覆盖 KaTeX 等异步增高 */
  useLayoutEffect(() => {
    if (!editable || paneMode !== 'split') return
    const ta = textareaRef.current
    const pv = previewScrollRef.current
    if (!ta || !pv) return
    const sync = () => {
      if (scrollProgrammaticRef.current) return
      const line = approxSourceLineFromTextareaScroll(ta)
      withScrollProgrammatic(() => {
        scrollPreviewToSourceLine(pv, line)
      })
    }
    sync()
    const raf = requestAnimationFrame(sync)
    const t1 = window.setTimeout(sync, 180)
    const t2 = window.setTimeout(sync, 360)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [editable, paneMode, withScrollProgrammatic])

  const captureTextareaSelection = useCallback((ta) => {
    if (!ta) return
    savedTextareaSelectionRef.current = {
      start: ta.selectionStart,
      end: ta.selectionEnd,
    }
  }, [])

  const handleTextareaSelectOrBlur = useCallback(
    (e) => {
      captureTextareaSelection(e.currentTarget)
    },
    [captureTextareaSelection]
  )

  /** 外部插入等：value 已提交 DOM 后再设光标并滚动，避免受控 textarea 未更新就 setSelectionRange 导致错位 */
  useLayoutEffect(() => {
    const pending = pendingInsertScrollRef.current
    if (!pending) return
    pendingInsertScrollRef.current = null
    const ta = textareaRef.current
    const pv = previewScrollRef.current
    if (!ta) return
    ta.focus()
    ta.setSelectionRange(pending.caret, pending.caret)
    runTextareaScrollProgrammatic(() => {
      scrollTextareaToSourceLine(ta, pending.caretLine)
    })
    if (pv) {
      withScrollProgrammatic(() => {
        scrollPreviewToSourceLine(pv, pending.caretLine)
      })
    }
  }, [editDraft, withScrollProgrammatic, runTextareaScrollProgrammatic])

  /** 正文变化防抖：在编辑框聚焦且未操作预览滚动时，按当前源码行重新对齐预览（公式渲染后高度变化） */
  useEffect(() => {
    if (!editable || paneMode !== 'split') return
    const ta = textareaRef.current
    const pv = previewScrollRef.current
    if (!ta || !pv) return
    const t = window.setTimeout(() => {
      if (userScrollingPreviewRef.current) return
      if (document.activeElement !== ta) return
      if (scrollProgrammaticRef.current) return
      const line = approxSourceLineFromTextareaScroll(ta)
      withScrollProgrammatic(() => {
        scrollPreviewToSourceLine(pv, line)
      })
    }, 260)
    return () => clearTimeout(t)
  }, [editDraft, editable, paneMode, withScrollProgrammatic])

  const handleInsertSuggestion = useCallback(
    (newValue) => {
      setEditDraft(newValue)
      onContentChange?.(newValue)
    },
    [onContentChange]
  )

  const writingSuggestions = useWritingSuggestions({
    textareaRef,
    value: editDraft,
    onInsert: handleInsertSuggestion,
    format: 'markdown',
    enabled: editable && paneMode === 'split',
  })

  const effectiveContent = editable ? editDraft : content

  const insertMarkdownAtCursor = useCallback(
    (snippet) => {
      const text = String(snippet || '')
      if (!text || !editable) return
      const tryOnce = () => {
        const ta = textareaRef.current
        if (!ta) return false
        const v = ta.value
        const focused = document.activeElement === ta
        const saved = savedTextareaSelectionRef.current
        const rawStart = focused ? ta.selectionStart : saved.start
        const rawEnd = focused ? ta.selectionEnd : saved.end
        const s = Math.max(0, Math.min(rawStart, v.length))
        const e = Math.max(s, Math.min(rawEnd, v.length))
        const { nextValue, caret } = insertSnippetAtTextareaCursor(v, s, e, text)
        const caretLine = nextValue.slice(0, caret).split('\n').length
        savedTextareaSelectionRef.current = { start: caret, end: caret }
        pendingInsertScrollRef.current = { caret, caretLine }
        setEditDraft(nextValue)
        onContentChange?.(nextValue)
        return true
      }
      requestAnimationFrame(() => {
        if (!tryOnce()) requestAnimationFrame(() => tryOnce())
      })
    },
    [editable, onContentChange]
  )

  useEffect(() => {
    if (!editorInsertRef) return
    editorInsertRef.current = { insertMarkdownAtCursor }
    return () => {
      editorInsertRef.current = null
    }
  }, [editorInsertRef, insertMarkdownAtCursor])

  const handleGenerateSummary = useCallback(async () => {
    if (!onGenerateSummary || !effectiveContent?.trim()) return
    setSummaryLoading(true)
    try {
      const result = await onGenerateSummary(effectiveContent)
      onSummaryChange?.(result ?? '')
    } catch (err) {
      onSummaryChange?.('')
      onSummaryError?.(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setSummaryLoading(false)
    }
  }, [effectiveContent, onGenerateSummary, onSummaryChange, onSummaryError])

  /** 进入摘要且无内容时触发生成 */
  useEffect(() => {
    if (
      paneMode === 'summary' &&
      !summary?.trim() &&
      effectiveContent?.trim() &&
      onGenerateSummary &&
      !summaryLoading
    ) {
      handleGenerateSummary()
    }
  }, [paneMode, summary, effectiveContent, onGenerateSummary, summaryLoading, handleGenerateSummary])

  return (
    <div className={`flex flex-col min-h-0 ${className}`.trim()}>
      <div className="shrink-0 px-4 py-3 border-b border-border bg-white/[0.02] flex flex-wrap items-center gap-2">
        {editable && (
          <>
            {showSummary && (
              <>
                <button type="button" onClick={() => setPaneMode('split')} className={tabCls(paneMode === 'split')}>
                  编辑与预览
                </button>
                <button type="button" onClick={() => setPaneMode('summary')} className={tabCls(paneMode === 'summary')}>
                  摘要
                </button>
              </>
            )}
            {paneMode === 'split' && (
              <WritingSuggestionsButton
                onClick={() => writingSuggestions.fetchSuggestions?.()}
                loading={writingSuggestions.loading}
              />
            )}
          </>
        )}
      </div>
      <div className="flex-1 min-h-[320px] flex flex-col overflow-hidden">
        {paneMode === 'summary' && showSummary ? (
          <div className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col">
            <div className="shrink-0 flex items-center justify-between gap-2 mb-3">
              {onGenerateSummary && (
                <button
                  type="button"
                  onClick={handleGenerateSummary}
                  disabled={summaryLoading || !effectiveContent?.trim()}
                  className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 disabled:opacity-50"
                >
                  {summaryLoading ? '生成中…' : summary ? '重新生成' : '生成摘要'}
                </button>
              )}
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto text-sm text-muted [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-1.5 [&_h3]:mb-0.5 [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4">
              {summary ? (
                <MarkdownPreview markdown={summary} theme="dark" className="p-0 min-h-0 text-sm" />
              ) : (
                <p className="text-xs text-muted/70 italic">点击「生成摘要」由 AI 生成结构化分层摘要。</p>
              )}
            </div>
          </div>
        ) : !editable ? (
          <div className="flex-1 min-h-0 overflow-y-auto p-4">
            <MarkdownPreview
              markdown={content || ''}
              className="min-h-full"
              theme={theme}
              onImgClick={onImgClick}
              wideFigures={previewWideFigures}
              inlineFigureZoom={previewInlineFigureZoom}
            />
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">
            <section className="flex min-h-0 min-w-0 flex-1 flex-col border-border max-lg:min-h-[200px] max-lg:shrink-0 max-lg:border-b lg:basis-0 lg:min-h-0 lg:border-r">
              <div className="shrink-0 px-3 py-1.5 text-[11px] text-muted border-b border-border/50 lg:hidden">
                编辑（Markdown）
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto p-3 flex flex-col">
                <EditAreaWithSuggestions
                  textareaRef={textareaRef}
                  value={editDraft}
                  onChange={(v) => {
                    setEditDraft(v)
                    onContentChange?.(v)
                  }}
                  placeholder="在此编辑 Markdown 内容…"
                  writingSuggestions={writingSuggestions}
                  rootClassName="flex-1 min-h-0 min-h-[200px] flex flex-col gap-2 relative"
                  textareaClassName={TEXTAREA_CLS_IN_PREVIEW_SHELL}
                  onTextareaScroll={handleEditorScroll}
                  onTextareaBlur={handleTextareaSelectOrBlur}
                  onTextareaSelect={handleTextareaSelectOrBlur}
                />
              </div>
            </section>
            <section className="flex min-h-0 min-w-0 flex-1 flex-col max-lg:min-h-[240px] max-lg:shrink-0 lg:basis-0 lg:min-h-0">
              <div className="shrink-0 px-3 py-1.5 text-[11px] text-muted border-b border-border/50 lg:hidden">
                预览（同步）
              </div>
              <div
                ref={previewScrollRef}
                className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3"
                onScroll={handlePreviewScroll}
              >
                <MarkdownPreview
                  markdown={editDraft || ''}
                  className="min-h-full"
                  theme={theme}
                  onImgClick={onImgClick}
                  wideFigures={previewWideFigures}
                  inlineFigureZoom={previewInlineFigureZoom}
                />
              </div>
            </section>
          </div>
        )}
      </div>
      <div className="shrink-0 px-4 py-3 border-t border-border flex items-center justify-center gap-3 bg-black/20">
        <MarkdownActionButtons
          content={effectiveContent}
          onCopy={onCopy}
          onSendToArticle={onSendToArticle}
          sendToArticleLabel={sendToArticleLabel}
          showMediaWiki={showMediaWiki}
          onAddToReference={onAddToReference}
          sourceUrl={sourceUrl}
          extra={footerExtra}
          onContentReplace={
            editable && typeof onContentChange === 'function'
              ? (next) => {
                  setEditDraft(next)
                  onContentChange(next)
                }
              : undefined
          }
        />
      </div>
    </div>
  )
}
