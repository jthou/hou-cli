/**
 * 解析编排下发的 __CTX_META__ 单行，供「本次上下文」面板与 SSE 去污染共用。
 *
 * 时间：2026-03-13；理由：避免 ContextSelectionPanel 与多页流式逻辑重复、防止 __CTX_META__ 误入 Markdown；方法：从组件抽离纯函数，单测可回归。
 */

const PREFIX = '__CTX_META__:'

/** @param {string} raw */
export function parseContextMetaChunk(raw) {
  if (raw == null || typeof raw !== 'string' || !raw.startsWith(PREFIX)) return null
  try {
    const data = JSON.parse(raw.slice(PREFIX.length).trim())
    return data?.type === 'context_selection' ? data : null
  } catch {
    return null
  }
}
