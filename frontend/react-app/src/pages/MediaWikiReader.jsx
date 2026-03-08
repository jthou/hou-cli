import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import WikiPreview from '../components/WikiPreview'
import PasteButton from '../components/PasteButton'
import { useToast } from '../components/ToastModal'
import { usePasteFromClipboard } from '../hooks/usePasteFromClipboard'

const STORAGE_KEY_LAST = 'mediawiki_reader_last'

export default function MediaWikiReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [termsInput, setTermsInput] = useState('')
  const [perTermLimit, setPerTermLimit] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [selectedPage, setSelectedPage] = useState(null)

  const handlePasteFromClipboard = usePasteFromClipboard({
    onPaste: (text) => setTermsInput(text),
    toast,
  })

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_LAST)
      if (!raw) return
      const saved = JSON.parse(raw)
      if (saved?.termsInput != null) setTermsInput(String(saved.termsInput))
      if (saved?.perTermLimit != null) setPerTermLimit(Number(saved.perTermLimit) || 5)
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
      toast?.info?.('已恢复上次关键词')
    } catch {
      toast?.warning?.('恢复失败')
    }
  }

  const handleClearLast = () => {
    try {
      if (localStorage.getItem(STORAGE_KEY_LAST)) {
        localStorage.removeItem(STORAGE_KEY_LAST)
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
          JSON.stringify({ termsInput: (termsInput || '').trim(), perTermLimit: perTermLimit || 5 })
        )
      } catch {
        // ignore
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

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Wiki阅读"
        subtitle="按多个关键词从 MediaWiki 中抓取现有页面，适合基于已有知识库做查阅，不会抓取外部网页。"
      />

      <div className="flex-1 overflow-hidden flex min-h-0">
        <div className="w-80 shrink-0 flex flex-col border-r border-border bg-white/[0.02] min-h-0">
          <div className="shrink-0 p-4 border-b border-border">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <label className="block text-sm text-muted">
                    关键词列表
                  </label>
                  <div className="flex items-center gap-1">
                    <PasteButton onClick={handlePasteFromClipboard} title="从剪贴板粘贴" />
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
                  placeholder="每行一个关键词，或逗号分隔。留空随机抓取。"
                />
              </div>

              <div className="flex items-center gap-2">
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
                <button
                  type="submit"
                  disabled={loading}
                  className="mt-4 px-3 py-2 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50"
                >
                  {loading ? '抓取中…' : '抓取'}
                </button>
              </div>

              {error && (
                <div className="text-xs text-red-400">{error}</div>
              )}

              {data && (
                <div className="text-[11px] text-muted">
                  {terms.length === 1 && terms[0] === '随机'
                    ? <>随机 {totalPages} 篇</>
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

        <div className="min-w-0 flex-1 overflow-y-auto bg-white/[0.02] p-6">
          {!selectedPage && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              在左上输入关键词抓取后，点击左下页面列表中的条目，即可在此预览。
            </div>
          )}
          {selectedPage && (
            <div className="max-w-3xl">
              <div className="flex items-baseline justify-between gap-3 mb-4">
                <h2 className="text-lg font-medium text-white truncate">
                  {selectedPage.title || selectedPage.url}
                </h2>
                <a
                  href={selectedPage.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-muted hover:text-accent shrink-0"
                >
                  在新标签页打开
                </a>
              </div>
              <WikiPreview
                wikiText={selectedPage.content || ''}
                theme="dark"
                onAddToReference={(content) =>
                  navigate('/add-reference', { state: { addToReference: content } })
                }
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

