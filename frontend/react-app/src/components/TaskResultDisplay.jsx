/**
 * 任务执行结果展示组件
 * 按 task_type 统一渲染，供任务详情弹窗、任务卡片、执行记录等复用，保持展示一致。
 */
import WeatherResultDisplay from './WeatherResultDisplay'
import { getMediaWikiPageUrl } from '../config/mediawiki'

export default function TaskResultDisplay({ taskType, result }) {
  const isSuccess = result?.status === 'success'
  const isError = result?.status === 'error'
  const hasDaily = Array.isArray(result?.daily) || (result?.result && Array.isArray(result?.result?.daily))
  const isRawWeatherForecast = hasDaily && (String(result?.code) === '200' || result?.result?.code == null)

  if (!result) {
    return <pre className="text-[#94a3b8] text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
  }

  // 统一错误结构：status === 'error' 时友好展示
  if (isError) {
    const err = result.error || {}
    return (
      <div className="space-y-2">
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm">
          <p className="text-red-400 font-medium">{result.summary || '执行失败'}</p>
          {err.code && <p className="text-[#94a3b8] mt-1">错误码: {err.code}</p>}
          {err.message && <p className="text-[#94a3b8] mt-1 whitespace-pre-wrap">{err.message}</p>}
        </div>
      </div>
    )
  }

  if (!isSuccess && !isRawWeatherForecast) {
    return <pre className="text-[#94a3b8] text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
  }

  if (taskType === 'video_download' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.title && <p><span className="text-[#64748b]">标题 </span>{d.title}</p>}
        {d.output_dir && <p><span className="text-[#64748b]">保存位置 </span><code className="text-cyan-300 break-all">{d.output_dir}</code></p>}
      </div>
    )
  }

  if (taskType === 'speech_to_text' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.output_file && <p><span className="text-[#64748b]">输出文件 </span><code className="text-cyan-300 break-all">{d.output_file}</code></p>}
        {d.language && <p><span className="text-[#64748b]">语言 </span>{d.language}</p>}
        {d.text != null && <p className="mt-2 text-[#64748b] text-xs">正文摘要: {String(d.text).slice(0, 200)}{String(d.text).length > 200 ? '…' : ''}</p>}
      </div>
    )
  }

  if (taskType === 'video_extract_audio' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.output_file && <p><span className="text-[#64748b]">输出文件 </span><code className="text-cyan-300 break-all">{d.output_file}</code></p>}
        {d.format && <p><span className="text-[#64748b]">格式 </span>{d.format}</p>}
      </div>
    )
  }

  if (taskType === 'mediawiki_write' && result.data) {
    const d = result.data
    const pageUrl = d.title ? getMediaWikiPageUrl(d.title) : ''
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.title && (
          <p>
            <span className="text-[#64748b]">页面 </span>
            {pageUrl ? (
              <a href={pageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.title}</a>
            ) : (
              d.title
            )}
          </p>
        )}
        {d.message && <p className="text-[#94a3b8]">{d.message}</p>}
      </div>
    )
  }

  if (taskType === 'wechat_mp_draft' && result.data) {
    const d = result.data
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.media_id && <p><span className="text-[#64748b]">media_id </span><code className="text-cyan-300 break-all text-xs">{d.media_id}</code></p>}
        {d.message && <p className="text-[#94a3b8]">{d.message}</p>}
      </div>
    )
  }

  if (taskType === 'url_to_wiki' && result.data) {
    const d = result.data
    const wikiPageUrl = d.wiki_title ? getMediaWikiPageUrl(d.wiki_title) : ''
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && (
          <p className="text-green-400">
            {d.wiki_title && wikiPageUrl ? (
              <>已抓取并翻译写入页面「<a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline">{d.wiki_title}</a>」</>
            ) : (
              result.summary
            )}
          </p>
        )}
        {d.url && <p><span className="text-[#64748b]">源 URL </span><a href={d.url} target="_blank" rel="noopener noreferrer" className="text-cyan-300 break-all text-xs">{d.url}</a></p>}
        {d.wiki_title && (
          <p>
            <span className="text-[#64748b]">Wiki 页面 </span>
            {wikiPageUrl ? (
              <a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.wiki_title}</a>
            ) : (
              d.wiki_title
            )}
          </p>
        )}
      </div>
    )
  }

  if (taskType === 'pdf_to_wiki' && result.data) {
    const d = result.data
    const wikiPageUrl = d.wiki_title ? getMediaWikiPageUrl(d.wiki_title) : ''
    const isPartial = result.status === 'partial'
    return (
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && (
          <p className={isPartial ? 'text-amber-400' : 'text-green-400'}>{result.summary}</p>
        )}
        {d.pdf_url && <p><span className="text-[#64748b]">PDF </span><a href={d.pdf_url} target="_blank" rel="noopener noreferrer" className="text-cyan-300 break-all text-xs">{d.pdf_url}</a></p>}
        {d.file_path && !d.pdf_url && <p><span className="text-[#64748b]">本地文件 </span><code className="text-cyan-300 break-all text-xs">{d.file_path}</code></p>}
        {d.wiki_title && (
          <p>
            <span className="text-[#64748b]">Wiki 页面 </span>
            {wikiPageUrl ? (
              <a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.wiki_title}</a>
            ) : (
              d.wiki_title
            )}
          </p>
        )}
        {(d.total_pages != null || d.total_chunks != null) && (
          <p className="text-[#64748b] text-xs">
            {d.total_pages != null && `共 ${d.total_pages} 页`}
            {d.total_pages != null && d.total_chunks != null && '，'}
            {d.total_chunks != null && `${d.total_chunks} 块`}
            {d.successful_chunks != null && `，成功 ${d.successful_chunks} 块`}
            {Array.isArray(d.failed_chunks) && d.failed_chunks.length > 0 && `，${d.failed_chunks.length} 块失败`}
          </p>
        )}
        {Array.isArray(d.wiki_pages) && d.wiki_pages.length > 1 && (
          <details className="text-xs text-[#94a3b8]">
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
      <div className="space-y-2 text-[#94a3b8]">
        {result.summary && <p className="text-green-400">{result.summary}</p>}
        {d.wiki_title && (
          <p>
            <span className="text-[#64748b]">目录页 </span>
            {wikiPageUrl ? (
              <a href={wikiPageUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-300 hover:underline break-all">{d.wiki_title}</a>
            ) : (
              d.wiki_title
            )}
          </p>
        )}
        {d.entry_count != null && <p className="text-[#64748b] text-xs">共 {d.entry_count} 条记录</p>}
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
                className="text-cyan-300 hover:underline font-medium block"
              >
                {item.title || item.link}
              </a>
              {item.display_link && (
                <p className="text-[#64748b] text-xs mt-0.5">{item.display_link}</p>
              )}
              {item.snippet && (
                <p className="text-[#94a3b8] mt-1 text-xs leading-relaxed">{item.snippet}</p>
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
  return <pre className="text-[#94a3b8] text-xs whitespace-pre-wrap break-all">{JSON.stringify(result, null, 2)}</pre>
}
