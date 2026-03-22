/**
 * 流式/持久助手气泡：剥离编排前言「执行 xxx 代理…」，避免进入 Markdown 与复制区。
 *
 * 时间：2026-03-13；理由：写作与通用对话应一致展示；方法：与 STREAM_AGENT_PREAMBLE 输出格式对齐（单行前缀正则）。
 */

/** @param {string} text */
export function stripAgentStatusPrefix(text) {
  if (!text || typeof text !== 'string') return { status: null, content: text || '' }
  const m = text.match(/^执行\s+\S+\s+代理\.\.\.\s*/)
  if (m) {
    return { status: m[0].trim(), content: text.slice(m[0].length).trimStart() }
  }
  return { status: null, content: text }
}
