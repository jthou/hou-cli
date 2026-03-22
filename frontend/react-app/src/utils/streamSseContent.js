/**
 * 统一处理 SSE streaming 帧：工具、上下文 meta、其它控制帧不进入用户可见正文。
 *
 * 时间：2026-03-13；理由：ArticleWriting 曾仅用 isOrchestratorControlChunk，__CTX_META__ 会误入正文；方法：与 GeneralChat 分支对齐并抽成单处实现。
 */

import { isOrchestratorControlChunk } from './streamChunkFilters'
import { parseContextMetaChunk } from './streamContextMeta'

/**
 * @param {string} raw
 * @param {{ onToolCall?: (toolData: object) => void, onContextMeta?: (meta: object) => void }} handlers
 * @returns {boolean} true = 应将 raw 追加到 fullContent / streaming 正文
 */
export function shouldAppendStreamingPlainText(raw, handlers = {}) {
  const r = String(raw)
  if (r.startsWith('__TOOL__:')) {
    try {
      const toolData = JSON.parse(r.slice(9).trim())
      if (toolData?.name) handlers.onToolCall?.(toolData)
    } catch (_) {
      /* ignore */
    }
    return false
  }
  const ctxMeta = parseContextMetaChunk(r)
  if (ctxMeta) {
    handlers.onContextMeta?.(ctxMeta)
    return false
  }
  if (isOrchestratorControlChunk(r)) return false
  return true
}
