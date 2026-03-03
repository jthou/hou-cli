/**
 * 任务执行结果展示组件
 * 按 task_type 统一渲染，供任务详情弹窗、任务卡片、执行记录等复用，保持展示一致。
 */
import { useNavigate } from 'react-router-dom'
import WeatherResultDisplay from './WeatherResultDisplay'
import { getMediaWikiPageUrl } from '../config/mediawiki'

export default function TaskResultDisplay({ taskType, result }) {
  const navigate = useNavigate()
  const isSuccess = result?.status === 'success'
  const isError = result?.status === 'error'
  const hasDaily = Array.isArray(result?.daily) || (result?.result && Array.isArray(result?.result?.daily))
  const isRawWeatherForecast = hasDaily && (String(result?.code) === '200' || result?.result?.code == null)

  if (!result) {
    return <pre className="text-muted text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
  }

  // 统一错误结构：status === 'error' 时友好展示
  if (isError) {
    const err = result.error || {}
    return (
      <div className="space-y-2">
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm">
          <p className="text-red-400 font-medium">{result.summary || '执行失败'}</p>
          {err.code && <p className="text-muted mt-1">错误码: {err.code}</p>}
          {err.message && <p className="text-muted mt-1 whitespace-pre-wrap">{err.message}</p>}
        </div>
      </div>
    )
  }

  if (!isSuccess && !isRawWeatherForecast) {
    return <pre className="text-muted text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
  }

  if (taskType === 'video_download' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.title && <p><span className="text-muted">标题 </span>{d.title}</p>}
        {d.output_dir && <p><span className="text-muted">保存位置 </span><code className="text-cyan-300 break-all">{d.output_dir}</code></p>}
      </div>
    )
  }

  if (taskType === 'speech_to_text' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.output_file && <p><span className="text-muted">输出文件 </span><code className="text-cyan-300 break-all">{d.output_file}</code></p>}
        {d.language && <p><span className="text-muted">语言 </span>{d.language}</p>}
        {d.text != null && <p className="mt-2 text-muted text-xs">正文摘要: {String(d.text).slice(0, 200)}{String(d.text).length > 200 ? '…' : ''}</p>}
      </div>
    )
  }

  if (taskType === 'video_extract_audio' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.output_file && <p><span className="text-muted">输出文件 </span><code className="text-cyan-300 break-all">{d.output_file}</code></p>}
        {d.format && <p><span className="text-muted">格式 </span>{d.format}</p>}
      </div>
    )
  }

  if (taskType === 'mediawiki_write' && result.data) {
    const d = result.data
    const pageUrl = d.title ? getMediaWikiPageUrl(d.title) : ''
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.title && (
          <p>
            <span className="text-muted">页面 </span>
            {pageUrl ? (
              <a href={pageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.title}</a>
            ) : (
              d.title
            )}
          </p>
        )}
        {d.message && <p className="text-muted">{d.message}</p>}
      </div>
    )
  }

  if (taskType === 'wechat_mp_draft' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.media_id && <p><span className="text-muted">media_id </span><code className="text-cyan-300 break-all text-xs">{d.media_id}</code></p>}
        {d.message && <p className="text-muted">{d.message}</p>}
      </div>
    )
  }

  if (taskType === 'url_to_wiki' && result.data) {
    const d = result.data
    const wikiPageUrl = d.wiki_title ? getMediaWikiPageUrl(d.wiki_title) : ''
    const wroteToWiki = !!d.wrote_to_wiki
    return (
      <div className="space-y-2 text-muted">
        {result.summary && (
          <p className="text-green-400">
            {result.summary}
          </p>
        )}
        {d.url && (
          <p>
            <span className="text-muted">源 URL </span>
            <a
              href={d.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-300 break-all text-xs"
            >
              {d.url}
            </a>
          </p>
        )}
        {d.wiki_title && (
          <p className="text-xs">
            <span className="text-muted">建议 Wiki 标题 </span>
            {wroteToWiki && wikiPageUrl ? (
              <a
                href={wikiPageUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-300 hover:underline break-all"
              >
                {d.wiki_title}
              </a>
            ) : (
              <span className="text-white">{d.wiki_title}</span>
            )}
            {!wroteToWiki && (
              <span className="text-amber-400/90 ml-2">(尚未写入 MediaWiki)</span>
            )}
          </p>
        )}
        {d.markdown && (
          <details className="text-xs space-y-1">
            <summary className="cursor-pointer text-muted hover:text-fg">
              查看 Markdown 草稿与后续操作
            </summary>
            <pre className="mt-1 p-2 bg-black/40 border border-border/60 rounded whitespace-pre-wrap break-all text-[11px] text-muted">
              {d.markdown}
            </pre>
            <div className="flex flex-wrap gap-2 mt-2">
              <button
                type="button"
                className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                onClick={() => {
                  navigator.clipboard
                    ?.writeText(d.markdown)
                    .catch(() => {})
                }}
              >
                复制 Markdown
              </button>
              <button
                type="button"
                className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                onClick={() => {
                  const params = new URLSearchParams()
                  if (d.url) params.set('source_url', d.url)
                  if (d.wiki_title) params.set('suggest_title', d.wiki_title)
                  navigate(`/article-writing?${params.toString()}`, {
                    state: { initialMarkdown: d.markdown, sourceType: 'url_to_wiki' },
                  })
                }}
              >
                发送到写文章
              </button>
            </div>
          </details>
        )}
      </div>
    )
  }

  if (taskType === 'pdf_to_wiki' && result.data) {
    const d = result.data
    const wikiPageUrl = d.wiki_title ? getMediaWikiPageUrl(d.wiki_title) : ''
    const isPartial = result.status === 'partial'
    return (
      <div className="space-y-2 text-muted">
        {result.summary && (
          <p className={isPartial ? 'text-amber-400' : 'text-green-400'}>{result.summary}</p>
        )}
        {d.pdf_url && <p><span className="text-muted">PDF </span><a href={d.pdf_url} target="_blank" rel="noopener noreferrer" className="text-cyan-300 break-all text-xs">{d.pdf_url}</a></p>}
        {d.file_path && !d.pdf_url && <p><span className="text-muted">本地文件 </span><code className="text-cyan-300 break-all text-xs">{d.file_path}</code></p>}
        {d.wiki_title && (
          <p>
            <span className="text-muted">Wiki 页面 </span>
            {wikiPageUrl ? (
              <a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.wiki_title}</a>
            ) : (
              d.wiki_title
            )}
          </p>
        )}
        {(d.total_pages != null || d.total_chunks != null) && (
          <p className="text-muted text-xs">
            {d.total_pages != null && `共 ${d.total_pages} 页`}
            {d.total_pages != null && d.total_chunks != null && '，'}
            {d.total_chunks != null && `${d.total_chunks} 块`}
            {d.successful_chunks != null && `，成功 ${d.successful_chunks} 块`}
            {Array.isArray(d.failed_chunks) && d.failed_chunks.length > 0 && `，${d.failed_chunks.length} 块失败`}
          </p>
        )}
        {Array.isArray(d.wiki_pages) && d.wiki_pages.length > 1 && (
          <details className="text-xs text-muted">
            <summary>目录与子页（{d.wiki_pages.length} 个）</summary>
            <ul className="mt-1 list-disc pl-4 space-y-0.5">
              {d.wiki_pages.map((page, idx) => {
                const url = getMediaWikiPageUrl(page)
                return (
                  <li key={idx}>
                    {url ? (
                      <a href={url} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{page}</a>
                    ) : (
                      page
                    )}
                  </li>
                )
              })}
            </ul>
          </details>
        )}
        {Array.isArray(d.failed_chunks) && d.failed_chunks.length > 0 && (
          <details className="text-xs text-amber-400/90">
            <summary>失败块明细</summary>
            <ul className="mt-1 list-disc pl-4">
              {d.failed_chunks.map((fc, idx) => (
                <li key={idx}>第 {fc.chunk_index + 1} 块（页 {fc.page_from}-{fc.page_to}）：{fc.reason}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    )
  }

  if (taskType === 'wiki_directory_refresh' && result.data) {
    const d = result.data
    const wikiPageUrl = d.wiki_title ? getMediaWikiPageUrl(d.wiki_title) : ''
    return (
      <div className="space-y-2 text-muted">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.wiki_title && (
          <p>
            <span className="text-muted">目录页 </span>
            {wikiPageUrl ? (
              <a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.wiki_title}</a>
            ) : (
              d.wiki_title
            )}
          </p>
        )}
        {d.entry_count != null && <p className="text-muted text-xs">共 {d.entry_count} 条记录</p>}
      </div>
    )
  }

  if (taskType === 'web_search' && result.result?.results) {
    const res = result.result
    const list = res.results || []
    return (
      <div className="space-y-3 text-sm">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        <ul className="space-y-3">
          {list.map((item, i) => (
            <li key={i} className="border-b border-border/50 pb-3 last:border-0">
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-fg hover:text-accent hover:underline font-medium block"
              >
                {item.title || item.link}
              </a>
              {item.display_link && (
                <p className="text-muted text-xs mt-0.5">{item.display_link}</p>
              )}
              {item.snippet && (
                <p className="text-muted mt-1 text-xs leading-relaxed">{item.snippet}</p>
              )}
              {item.link && (
                <div className="mt-1">
                  <button
                    type="button"
                    className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                    onClick={() => {
                      const params = new URLSearchParams()
                      params.set('url', item.link)
                      if (item.title) params.set('suggest_title', item.title)
                      navigate(`/url-to-wiki?${params.toString()}`)
                    }}
                  >
                    网文抓取（生成草稿）
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  if (taskType === 'weather_query' && (result.result != null || result.summary || (String(result?.code) === '200' && Array.isArray(result.daily)))) {
    return <WeatherResultDisplay result={result} />
  }
  return <pre className="text-muted text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
}
