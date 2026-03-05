import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import WikiPreview from '../components/WikiPreview'

export default function MediaWikiReader() {
  const navigate = useNavigate()
  const [termsInput, setTermsInput] = useState('')
  const [perTermLimit, setPerTermLimit] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

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
    } catch (err) {
      setError(err.message || String(err))
    }
    setLoading(false)
  }

  const totalPages = data?.total_pages ?? 0
  const terms = data?.terms ?? []
  const results = data?.results ?? []

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">MediaWiki 阅读</h1>
          <p className="mt-1 text-sm text-muted">
            按多个关键词从 MediaWiki 中抓取现有页面，用于阅读和修改。
            适合基于已有知识库做查阅，不会抓取外部网页。
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-hidden flex">
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-muted mb-1">
                关键词列表（每词抓取若干篇文章）
              </label>
              <textarea
                value={termsInput}
                onChange={(e) => setTermsInput(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-muted focus:border-accent focus:outline-none resize-y"
                placeholder={
                  '每行一个关键词，或用逗号分隔多个关键词。\n' +
                  '例如：产品名、标签、日期、周次等。'
                }
              />
              <p className="mt-1 text-xs text-muted">
                支持换行或逗号分隔，工具会去重。
              </p>
            </div>

            <div className="flex items-center gap-4">
              <div>
                <label className="block text-sm text-muted mb-1">
                每个关键词抓取篇数 / 随机抓取篇数
                </label>
                <input
                  type="number"
                  min={1}
                max={50}
                  value={perTermLimit}
                  onChange={(e) => setPerTermLimit(Number(e.target.value) || 5)}
                  className="w-24 px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="mt-5 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50"
              >
                {loading ? '抓取中...' : '抓取 MediaWiki 文章'}
              </button>
            </div>

            {error && (
              <div className="mt-2 text-sm text-red-400">
                {error}
              </div>
            )}

            {data && (
              <div className="mt-4 text-xs text-muted">
                {terms.length === 1 && terms[0] === '随机'
                  ? <>随机抓取到 {totalPages} 篇文章。</>
                  : <>共 {terms.length} 个关键词，抓取到 {totalPages} 篇文章。</>}
              </div>
            )}
            <p className="mt-1 text-xs text-muted">
              不填关键词时，将从主命名空间的所有页面中随机抓取上述篇数。
            </p>
          </form>
        </div>

        <div className="min-w-0 flex-1 border-l border-border overflow-y-auto bg-white/[0.02] p-6">
          {!data && !loading && !error && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              在左侧输入关键词或留空直接抓取，即可在此看到可点击打开的 MediaWiki 页面列表。
            </div>
          )}

          {loading && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              抓取中，请稍候...
            </div>
          )}

          {data && results.length > 0 && (
            <div className="space-y-6">
              {results.map((group) => (
                <div
                  key={group.term}
                  className="border border-border rounded-xl bg-white/5 p-4"
                >
                  <div className="flex items-baseline justify-between gap-3 mb-3">
                    <div className="flex items-baseline gap-2">
                      <span className="text-sm font-medium text-white">
                        关键词：
                      </span>
                      <span className="text-sm text-accent">
                        {group.term}
                      </span>
                    </div>
                    <span className="text-xs text-muted">
                      抓取 {group.count} / {group.requested_limit} 篇
                    </span>
                  </div>
                  {group.pages.length === 0 ? (
                    <p className="text-sm text-muted">
                      未找到匹配的页面。
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {group.pages.map((page, idx) => (
                        <li
                          key={`${page.title}-${idx}`}
                          className="border border-border/60 rounded-lg bg-black/20 px-3 py-2"
                        >
                          <div className="flex flex-col min-w-0">
                            <a
                              href={page.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-medium text-accent hover:underline break-all"
                            >
                              {page.title || page.url}
                            </a>
                            <span className="text-xs text-muted mt-0.5 break-words">
                              {Array.isArray(page.categories) && page.categories.length
                                ? `分类：${page.categories.join(' / ')}`
                                : '无分类'}
                            </span>
                            <a
                              href={page.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-muted hover:text-accent mt-1 break-all"
                            >
                              {page.url}
                            </a>
                          </div>
                          {page.content && (
                            <details className="mt-2 text-xs">
                              <summary className="cursor-pointer text-muted hover:text-fg">
                                预览页面内容
                              </summary>
                              <div className="mt-1 border border-border/60 rounded bg-white/5 p-2">
                                <WikiPreview
                                  wikiText={page.content}
                                  className="min-h-[120px]"
                                  theme="dark"
                                  onAddToReference={(content) =>
                                    navigate('/article-writing', { state: { addToReference: content } })
                                  }
                                />
                              </div>
                            </details>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

