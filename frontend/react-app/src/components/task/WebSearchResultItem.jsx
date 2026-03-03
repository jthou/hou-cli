/**
 * 网页搜索结果单项：标题、链接、摘要，可选「网文抓取」或「已抓取」状态
 * scrapedInfo: { taskId, wikiTitle, wroteToWiki, markdown } 表示该 URL 已被 url_to_wiki 抓取过
 */
import { getMediaWikiPageUrl } from '../../config/mediawiki'
import MarkdownDraftActions from './MarkdownDraftActions'

export default function WebSearchResultItem({ item, scrapedInfo, onUrlToWiki, onWriteSuccess }) {
  const wikiPageUrl = scrapedInfo?.wikiTitle ? getMediaWikiPageUrl(scrapedInfo.wikiTitle) : null
  const hasMarkdown = scrapedInfo?.markdown && typeof scrapedInfo.markdown === 'string'

  return (
    <li className="border-b border-border/50 pb-3 last:border-0">
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
        <div className="mt-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            {scrapedInfo ? (
              <>
                <span className="text-[11px] text-green-500/90">已抓取</span>
                {scrapedInfo.wroteToWiki && wikiPageUrl && (
                  <a
                    href={wikiPageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                  >
                    查看 Wiki 页面
                  </a>
                )}
                <button
                  type="button"
                  className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                  onClick={() => onUrlToWiki?.(item.link, item.title || '')}
                >
                  再次抓取
                </button>
              </>
            ) : (
              onUrlToWiki && (
                <button
                  type="button"
                  className="px-2 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                  onClick={() => onUrlToWiki(item.link, item.title || '')}
                >
                  网文抓取（生成草稿）
                </button>
              )
            )}
          </div>
          {scrapedInfo && hasMarkdown && (
            <MarkdownDraftActions
              markdown={scrapedInfo.markdown}
              sourceUrl={item.link}
              suggestTitle={scrapedInfo.wikiTitle}
              sourceType="url_to_wiki"
              summaryText="查看抓取内容"
              onWriteSuccess={(payload) => item.link && onWriteSuccess?.(item.link, payload)}
            />
          )}
        </div>
      )}
    </li>
  )
}
