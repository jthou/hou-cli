import { deriveWikiTitlePreview } from './taskFormUtils'

/**
 * 当用户未填 Wiki 页面标题时，根据 url/file_path 预览将使用的标题；
 * 若疑似哈希则提示用户填写可读标题（避免目录出现 58284b19... 这类名称）。
 */
export default function WikiTitlePreviewHint({ taskType, metadata }) {
  const wikiTitle = (metadata?.wiki_title || '').trim()
  if (wikiTitle) return null
  const { derived, looksLikeHash } = deriveWikiTitlePreview(metadata, taskType)
  if (!derived) return null
  return (
    <div className="rounded-lg p-3 text-sm border border-amber-500/30 bg-amber-500/10">
      {looksLikeHash ? (
        <p className="text-amber-400">
          当前将使用标题：<strong className="font-mono break-all">{derived}</strong>
          <br />
          <span className="text-amber-300/90">疑似哈希或随机串，建议在上方「Wiki 页面标题」填写可读名称，避免目录中出现难以识别的标题。</span>
        </p>
      ) : (
        <p className="text-[#94a3b8]">
          留空时将使用标题：<strong className="break-all">{derived}</strong>
        </p>
      )}
    </div>
  )
}
