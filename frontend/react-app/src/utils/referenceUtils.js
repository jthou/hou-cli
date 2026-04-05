/**
 * 参考块相关工具函数，供 ArticleWriting、WorkAssistant、AddReference 等复用
 *
 * 契约：发往模型的 user 消息拼装规则须与
 * backend/core/agent/article_writing_message_contract.py 保持一致（改一侧必改另一侧）。
 */

/** 与 Python article_writing_message_contract.USER_QUESTION_MARKER 同步 */
export const ARTICLE_WRITING_USER_QUESTION_MARKER = '【用户本次提问】'

/** 与 Python article_writing_message_contract.REFERENCE_INTRO 同步 */
export const ARTICLE_WRITING_REFERENCE_INTRO =
  '以下是用户提供的参考资料（可能含待改范文、素材或链接稿）。请结合用户本次提问使用。若用户给出修改意见（含提问或资料中的「（修改意见：…）」「(修改意见：…)」等），须**先严格按修改意见逐条落实**，再在**原文事实与论点边界内**做必要梳理（层次、衔接、删冗、统一人称术语）；**禁止**脱离范文与意见编造内容、虚构案例，或擅自扩写用户未要求的段落与章节；括号内修订说明与显式「修改意见」清单同等效力。若括号紧跟在文章标题（如 `# 标题`）之后，仍须完整阅读并落实，不得以「在标题旁」为由跳过。\n\n'

/** 从用户消息中提取「用户本次提问」部分用于展示，避免参考块长文导致排版混乱 */
export function extractUserQuestionForDisplay(content) {
  if (!content || typeof content !== 'string') return content || ''
  const marker = ARTICLE_WRITING_USER_QUESTION_MARKER
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
  return `${ARTICLE_WRITING_REFERENCE_INTRO}${trimmed
    .map((b, idx) => {
      const title = (b.title || '').trim()
      const header = title ? `【参考${idx + 1}：${title}】` : `【参考${idx + 1}】`
      return `${header}\n${b.content}`
    })
    .join('\n\n')}\n\n---\n\n`
}

/**
 * 单次发往模型的完整 user 消息（与 ArticleWriting / WorkAssistant / GeneralChat 原逻辑一致）
 * @param {Array<{id?: string, title?: string, content?: string}>} referenceBlocks
 * @param {string} text
 * @returns {string}
 */
export function buildArticleWritingMessageForModel(referenceBlocks, text) {
  const referenceContext = formatReferenceContext(referenceBlocks)
  const t = (text || '').trim()
  if (!referenceContext) return t
  return `${referenceContext}${ARTICLE_WRITING_USER_QUESTION_MARKER}\n${t}`
}
