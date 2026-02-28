/**
 * 公众号草稿正文：Markdown ↔ HTML 统一转换。
 * - 编辑与预览用 Markdown → mdToHtml() → HTML 渲染。
 * - 编辑已有草稿时，接口返回的 content 为 HTML，用 htmlToMd() 转成 Markdown 再放入编辑器。
 * - 提交任务/定时任务时，metadata.content 必须为 HTML，由 prepareWechatDraftMetadata 或 prepareMetadataForSubmit 统一转换。
 */
import { marked } from 'marked'
import TurndownService from 'turndown'

/** 任务类型：公众号草稿。凡提交该类型任务的 metadata 前，应对 content 做 MD→HTML。 */
export const WECHAT_MP_DRAFT_TASK_TYPE = 'wechat_mp_draft'

// 安全起见关闭 raw HTML（用户输入的 MD 中若有 HTML 会转义）
marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * @param {string} md - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function mdToHtml(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''
  const out = marked.parse(trimmed)
  return typeof out === 'string' ? out : String(out)
}

const turndownService = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' })

/**
 * HTML → Markdown，用于编辑已有草稿时把接口返回的正文 HTML 转成 Markdown 再放入编辑器。
 * @param {string} html - HTML 字符串（如公众号草稿 content）
 * @returns {string} Markdown 字符串
 */
export function htmlToMd(html) {
  if (html == null || typeof html !== 'string') return ''
  const trimmed = html.trim()
  if (!trimmed) return ''
  try {
    return turndownService.turndown(trimmed)
  } catch {
    return trimmed
  }
}

/**
 * 公众号草稿提交前：将 metadata 中的 content（Markdown）转为 HTML，其余字段原样返回。
 * 供 WechatDraftPage、TaskManagement 等统一使用，避免两处各自写转换逻辑。
 * @param {Object} metadata - 表单中的 metadata（content 为 Markdown）
 * @returns {Object} 用于提交的 metadata（content 为 HTML）
 */
export function prepareWechatDraftMetadata(metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  const content = metadata.content
  if (content == null || typeof content !== 'string') return { ...metadata }
  const trimmed = String(content).trim()
  if (!trimmed) return { ...metadata }
  return { ...metadata, content: mdToHtml(trimmed) }
}

/**
 * 按任务类型统一处理提交前的 metadata（保证 content 等字段格式一致）。
 * 当前仅 wechat_mp_draft 需将 content 从 Markdown 转为 HTML；其余类型原样返回。
 * 供所有创建/更新任务的入口使用：CreateTaskModal、CreateScheduledTaskModal、EditScheduledTaskModal、TaskFormPage。
 * @param {string} taskType - 任务类型
 * @param {Object} metadata - 表单中的 metadata
 * @returns {Object} 用于提交的 metadata
 */
export function prepareMetadataForSubmit(taskType, metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  if (taskType === WECHAT_MP_DRAFT_TASK_TYPE) return prepareWechatDraftMetadata(metadata)
  return { ...metadata }
}
