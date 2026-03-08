/**
 * 参考块相关工具函数，供 ArticleWriting、WorkAssistant、AddReference 等复用
 */

/** 从用户消息中提取「用户本次提问」部分用于展示，避免参考块长文导致排版混乱 */
export function extractUserQuestionForDisplay(content) {
  if (!content || typeof content !== 'string') return content || ''
  const marker = '【用户本次提问】'
  const idx = content.indexOf(marker)
  if (idx >= 0) {
    const after = content.slice(idx + marker.length).trimStart()
    return after || content
  }
  return content
}

/** 从内容推导参考块标题：取首行或前 80 字，截断至 50 字 */
export function deriveRefTitle(content) {
  const trimmed = (content || '').trim()
  if (!trimmed) return ''
  const firstLine = trimmed.split('\n')[0].trim()
  const candidate = firstLine || trimmed.slice(0, 80)
  return candidate.slice(0, 50)
}

/** 生成参考块唯一 ID */
export function generateReferenceBlockId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

/**
 * 将参考块格式化为模型上下文字符串
 * @param {Array<{id: string, title: string, content: string}>} blocks
 * @returns {string}
 */
export function formatReferenceContext(blocks) {
  const trimmed = (blocks || [])
    .map((b) => ({ ...b, content: (b.content || '').trim() }))
    .filter((b) => b.content)
  if (trimmed.length === 0) return ''
  return `以下是用户提供的参考资料，请在回答时充分利用，并根据用户的最新指令进行综合判断：\n\n${trimmed
    .map((b, idx) => {
      const title = (b.title || '').trim()
      const header = title ? `【参考${idx + 1}：${title}】` : `【参考${idx + 1}】`
      return `${header}\n${b.content}`
    })
    .join('\n\n')}\n\n---\n\n`
}
