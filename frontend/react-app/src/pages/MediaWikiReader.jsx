import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import WikitextEditorPreview from '../components/WikitextEditorPreview'
import { fetchSummarize } from '../utils/summarizeApi'
import { useToast } from '../components/ToastModal'
import { getHouGvimMediawikiUrl } from '../config/mediawiki'

const STORAGE_KEY_LAST = 'mediawiki_reader_last'
const STORAGE_KEY_SUMMARIES = 'mediawiki_reader_summaries'

export default function MediaWikiReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [termsInput, setTermsInput] = useState('')
  const [perTermLimit, setPerTermLimit] = useState(5)
  const [emptyMode, setEmptyMode] = useState('recent') // 'recent' | 'random'，关键词留空时的抓取方式
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [selectedPage, setSelectedPage] = useState(null)
  const [editedWikitext, setEditedWikitext] = useState(null)
  const [linkNavigateLoading, setLinkNavigateLoading] = useState(false)
  /** 时间：2026-03-13；理由：在 Wiki 阅读页直接起稿；方法：本地占位 selectedPage.isNewDraft，不调用 API 直至用户写入 MediaWiki。 */
  const [wikiBaseUrl, setWikiBaseUrl] = useState('')
  const [summaryPerPage, setSummaryPerPage] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_SUMMARIES)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  })

  useEffect(() => {
    fetch('/api/mediawiki/base-url')
      .then((r) => r.json())
      .then((d) => setWikiBaseUrl((d && d.base_url) || ''))
      .catch(() => {})
  }, [])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_LAST)
      if (!raw) return
      const saved = JSON.parse(raw)
      if (saved?.termsInput != null) setTermsInput(String(saved.termsInput))
      if (saved?.perTermLimit != null) setPerTermLimit(Number(saved.perTermLimit) || 5)
      if (saved?.emptyMode === 'random' || saved?.emptyMode === 'recent') setEmptyMode(saved.emptyMode)
      if (saved?.data && Array.isArray(saved.data?.results)) setData(saved.data)
    } catch {
      // ignore
    }
  }, [])

  const handleRestoreLast = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_LAST)
      if (!raw) {
        toast?.warning?.('暂无上次记录')
        return
      }
      const saved = JSON.parse(raw)
      if (saved?.termsInput != null) setTermsInput(String(saved.termsInput))
      if (saved?.perTermLimit != null) setPerTermLimit(Number(saved.perTermLimit) || 5)
      if (saved?.emptyMode === 'random' || saved?.emptyMode === 'recent') setEmptyMode(saved.emptyMode)
      if (saved?.data && Array.isArray(saved.data?.results)) setData(saved.data)
      toast?.info?.('已恢复上次记录')
    } catch {
      toast?.warning?.('恢复失败')
    }
  }

  const handleClearLast = () => {
    try {
      if (localStorage.getItem(STORAGE_KEY_LAST)) {
        localStorage.removeItem(STORAGE_KEY_LAST)
        setData(null)
        toast?.info?.('已清空上次记录')
      } else {
        toast?.warning?.('暂无上次记录')
      }
    } catch {
      toast?.warning?.('清空失败')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setData(null)
    try {
      const raw = (termsInput || '').trim()
      let res
      if (raw) {
        const params = new URLSearchParams()
        params.set('terms', raw)
        params.set('per_term_limit', String(perTermLimit || 5))
        res = await fetch(`/api/mediawiki/search-read?${params.toString()}`)
      } else if (emptyMode === 'recent') {
        const params = new URLSearchParams()
        params.set('count', String(perTermLimit || 5))
        res = await fetch(`/api/mediawiki/recent-read?${params.toString()}`)
      } else {
        const params = new URLSearchParams()
        params.set('count', String(perTermLimit || 5))
        res = await fetch(`/api/mediawiki/random-read?${params.toString()}`)
      }
      const json = await res.json()
      if (!json.success) {
        throw new Error(json.detail || json.message || '抓取失败')
      }
      setData(json)
      try {
        localStorage.setItem(
          STORAGE_KEY_LAST,
          JSON.stringify({
            termsInput: (termsInput || '').trim(),
            perTermLimit: perTermLimit || 5,
            emptyMode,
            data: json,
          })
        )
      } catch {
        // ignore (可能因内容过大超出 quota)
      }
    } catch (err) {
      setError(err.message || String(err))
    }
    setLoading(false)
  }

  const totalPages = data?.total_pages ?? 0
  const terms = data?.terms ?? []
  const results = data?.results ?? []
  const allPages = results.flatMap((g) => (g.pages || []).map((p) => ({ ...p, term: g.term })))

  useEffect(() => {
    if (!data) setSelectedPage(null)
  }, [data])
  useEffect(() => {
    setEditedWikitext(null)
  }, [selectedPage])

  useEffect(() => {
    try {
      if (Object.keys(summaryPerPage).length > 0) {
        localStorage.setItem(STORAGE_KEY_SUMMARIES, JSON.stringify(summaryPerPage))
      }
    } catch {
      // ignore
    }
  }, [summaryPerPage])

  const handleNewPage = useCallback(() => {
    const base = (wikiBaseUrl || '').replace(/\/$/, '')
    setSelectedPage({
      title: '新页面（未保存）',
      content: '',
      url: base || undefined,
      categories: [],
      isNewDraft: true,
    })
    setEditedWikitext(null)
    toast?.info?.('已打开空白页，编辑后点击「写入 MediaWiki」，在弹窗中填写正式标题并选择新建')
  }, [toast, wikiBaseUrl])

  const handleWikiLinkClick = useCallback(
    async (pageTitle) => {
      if (!pageTitle?.trim()) return
      setLinkNavigateLoading(true)
      try {
        const res = await fetch(`/api/mediawiki/pages/${encodeURIComponent(pageTitle)}`)
        const json = await res.json()
        if (!json.success || !json.page) {
          toast?.warning?.(json.detail || '页面加载失败')
          return
        }
        const p = json.page
        setSelectedPage({
          title: p.title,
          content: p.content,
          url: p.url,
          categories: p.categories || [],
        })
        setEditedWikitext(null)
      } catch (err) {
        toast?.warning?.(err?.message || '页面加载失败')
      } finally {
        setLinkNavigateLoading(false)
      }
    },
    [toast]
  )

  const pageKey = selectedPage?.title || selectedPage?.url || ''
  const gvimOpenHref =
    selectedPage && !selectedPage.isNewDraft
      ? getHouGvimMediawikiUrl(selectedPage.title || '')
      : ''
  const currentSummary = pageKey ? (summaryPerPage[pageKey] ?? '') : ''
  const setCurrentSummary = useCallback(
    (v) => {
      if (!pageKey) return
      setSummaryPerPage((prev) => ({ ...prev, [pageKey]: v ?? '' }))
    },
    [pageKey]
  )

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Wiki阅读" />

      <div className="flex-1 overflow-hidden flex min-h-0">
        <div className="flex-[0.382] min-w-0 flex flex-col border-r border-border bg-white/[0.02] min-h-0">
          <div className="shrink-0 p-4 border-b border-border">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <label className="block text-sm text-muted">
                    关键词列表
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={handleRestoreLast}
                      className="px-2 py-1 text-[11px] rounded border border-border text-muted hover:text-fg hover:bg-white/5"
                    >
                      恢复
                    </button>
                    <button
                      type="button"
                      onClick={handleClearLast}
                      className="px-2 py-1 text-[11px] rounded border border-border text-muted hover:text-fg hover:bg-white/5"
                    >
                      清空
                    </button>
                  </div>
                </div>
                <textarea
                  value={termsInput}
                  onChange={(e) => setTermsInput(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-muted focus:border-accent focus:outline-none resize-y text-sm"
                  placeholder="每行一个关键词，或逗号分隔。留空可抓取最新更改或随机文章。"
                />
              </div>

              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="block text-[11px] text-muted mb-0.5">每词篇数</label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={perTermLimit}
                    onChange={(e) => setPerTermLimit(Number(e.target.value) || 5)}
                    className="w-16 px-2 py-1.5 text-sm bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
                  />
                </div>
                {!termsInput.trim() && (
                  <div>
                    <label className="block text-[11px] text-muted mb-1">关键词留空时</label>
                    <div className="flex gap-2">
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          name="emptyMode"
                          checked={emptyMode === 'recent'}
                          onChange={() => setEmptyMode('recent')}
                          className="text-accent"
                        />
                        <span className="text-sm">最新更改</span>
                      </label>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          name="emptyMode"
                          checked={emptyMode === 'random'}
                          onChange={() => setEmptyMode('random')}
                          className="text-accent"
                        />
                        <span className="text-sm">随机</span>
                      </label>
                    </div>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="mt-4 px-3 py-2 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50"
                >
                  {loading ? '抓取中…' : '抓取'}
                </button>
                <button
                  type="button"
                  onClick={handleNewPage}
                  className="mt-4 px-3 py-2 text-sm rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
                >
                  新建页面
                </button>
              </div>

              {error && (
                <div className="text-xs text-red-400">{error}</div>
              )}

              {data && (
                <div className="text-[11px] text-muted">
                  {terms.length === 1 && terms[0] === '随机'
                    ? <>随机 {totalPages} 篇</>
                    : terms.length === 1 && terms[0] === '最新更改'
                      ? <>最新更改 {totalPages} 篇</>
                      : <>{terms.length} 词 · {totalPages} 篇</>}
                </div>
              )}
            </form>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-3">
            {loading && (
              <div className="py-4 text-center text-sm text-muted">抓取中…</div>
            )}
            {!loading && data && allPages.length === 0 && (
              <div className="py-4 text-center text-sm text-muted">未找到匹配的页面</div>
            )}
            {!loading && allPages.length > 0 && (
              <ul className="space-y-1.5">
                {allPages.map((page, idx) => (
                  <li key={`${page.title}-${idx}`}>
                    <button
                      type="button"
                      onClick={() => setSelectedPage(page)}
                      className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
                        selectedPage === page
                          ? 'border-accent bg-accent/20 text-accent'
                          : 'border-border/60 bg-black/20 text-fg hover:border-accent/60 hover:bg-white/5'
                      }`}
                    >
                      <span className="font-medium block truncate">{page.title || page.url}</span>
                      {page.term && (
                        <span className="text-[11px] text-muted truncate block">
                          {page.term}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-[0.618] overflow-y-auto bg-white/[0.02] p-6 flex flex-col min-h-0">
          {!selectedPage && (
            <div className="h-full flex flex-col items-center justify-center gap-3 text-sm text-muted px-4 text-center">
              <p>在左上抓取后点击列表条目即可预览；或点击左侧「新建页面」在此起稿。</p>
              <button
                type="button"
                onClick={handleNewPage}
                className="px-4 py-2 rounded-lg border border-border text-accent hover:bg-white/5"
              >
                新建页面
              </button>
            </div>
          )}
          {selectedPage && (
            <div className="flex flex-col h-full min-w-0">
              <div className="shrink-0 flex items-baseline justify-between gap-3 mb-4">
                <h2 className="text-lg font-medium text-white truncate">
                  {selectedPage.title || selectedPage.url}
                </h2>
                <div className="flex items-center gap-2 shrink-0">
                  {gvimOpenHref ? (
                    <a
                      href={gvimOpenHref}
                      className="text-xs text-muted hover:text-accent"
                      title="本机已注册 hou-gvim:// 时打开 gvim（gvim-protocol-handler）"
                    >
                      用 gvim 打开
                    </a>
                  ) : null}
                  {selectedPage.url && (
                    <a
                      href={selectedPage.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-muted hover:text-accent"
                    >
                      {selectedPage.isNewDraft ? '打开 Wiki 站点' : '在新标签页打开'}
                    </a>
                  )}
                </div>
              </div>
              <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border bg-white flex flex-col relative">
                {linkNavigateLoading && (
                  <div className="absolute inset-0 bg-black/30 z-10 flex items-center justify-center">
                    <span className="text-sm text-muted">加载中…</span>
                  </div>
                )}
                <div className="flex-1 min-h-0 p-4 flex flex-col">
                  <WikitextEditorPreview
                    className="flex-1 min-h-0"
                    wikiText={editedWikitext ?? (selectedPage.content || '')}
                    onContentChange={(v) => {
                      setEditedWikitext(v)
                      setCurrentSummary('')
                    }}
                    editable
                    theme="dark"
                    showSummary
                    summary={currentSummary}
                    onSummaryChange={setCurrentSummary}
                    onGenerateSummary={(content) => fetchSummarize(content)}
                    onSummaryError={(err) => toast?.warning?.(err?.message || '摘要生成失败')}
                    onAddToReference={(content) =>
                      navigate('/add-reference', { state: { addToReference: content } })
                    }
                    onWikiLinkClick={handleWikiLinkClick}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

