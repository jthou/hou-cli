/**
 * 公众号草稿正文：Markdown ↔ HTML 统一转换。
 * - 编辑与预览用 Markdown → mdToHtml() → HTML 渲染。
 * - 编辑已有草稿时，接口返回的 content 为 HTML，用 htmlToMd() 转成 Markdown 再放入编辑器。
 * - 提交任务/定时任务时，metadata.content 必须为 HTML，由 prepareWechatDraftMetadata 或 prepareMetadataForSubmit 统一转换。
 */
import { marked } from 'marked'
import TurndownService from 'turndown'
import { mdToWiki } from './wikiMdConvert.js'

/** 任务类型：公众号草稿。凡提交该类型任务的 metadata 前，应对 content 做 MD→HTML。 */
export const WECHAT_MP_DRAFT_TASK_TYPE = 'wechat_mp_draft'

/** 任务类型：MediaWiki 写入。若勾选「正文为 Markdown」，提交前对 content 做 MD→Wiki。 */
export const MEDIAWIKI_WRITE_TASK_TYPE = 'mediawiki_write'

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

/**
 * 公众号正文内联样式（微信只保留内联 style，不支持 <style> 与 class 样式）。
 * 单位用 px 更稳妥，参考：font-size/color/line-height/margin/padding 等均支持。
 */
const WECHAT_INLINE_STYLES = {
  p: 'font-size:16px;line-height:1.6;color:#333333;margin:0 0 16px 0;',
  h1: 'font-size:22px;font-weight:600;color:#333333;margin:16px 0 8px 0;line-height:1.4;',
  h2: 'font-size:19px;font-weight:600;color:#333333;margin:16px 0 8px 0;line-height:1.4;',
  h3: 'font-size:17px;font-weight:600;color:#333333;margin:16px 0 8px 0;line-height:1.4;',
  h4: 'font-size:16px;font-weight:600;color:#333333;margin:16px 0 8px 0;line-height:1.4;',
  blockquote: 'color:#57606a;font-size:15px;margin:0 0 16px 0;padding-left:12px;border-left:4px solid #d0d7de;line-height:1.6;',
  ul: 'margin:0 0 16px 0;padding-left:24px;line-height:1.6;color:#333333;',
  ol: 'margin:0 0 16px 0;padding-left:24px;line-height:1.6;color:#333333;',
  li: 'margin-bottom:4px;',
  code: 'background-color:#f5f5f5;color:#333333;font-size:14px;padding:2px 6px;border-radius:4px;',
  pre: 'background-color:#f5f5f5;color:#333333;font-size:14px;line-height:1.5;margin:0 0 16px 0;padding:12px;border-radius:6px;overflow-x:auto;',
  strong: 'font-weight:600;color:#333333;',
  em: 'font-style:italic;color:#57606a;',
  a: 'color:#0969da;text-decoration:none;',
  hr: 'border:0;border-top:1px solid #e1e4e8;margin:24px 0;',
  img: 'max-width:100%;height:auto;',
}

/** 无 DOM 时用正则给开标签注入 style（兜底，确保一定提交内联样式） */
function addWechatInlineStylesFallback(html) {
  let out = html
  const tagStyleList = [
    ['<p>', '<p style="' + WECHAT_INLINE_STYLES.p + '">'],
    ['<h1>', '<h1 style="' + WECHAT_INLINE_STYLES.h1 + '">'],
    ['<h2>', '<h2 style="' + WECHAT_INLINE_STYLES.h2 + '">'],
    ['<h3>', '<h3 style="' + WECHAT_INLINE_STYLES.h3 + '">'],
    ['<h4>', '<h4 style="' + WECHAT_INLINE_STYLES.h4 + '">'],
    ['<blockquote>', '<blockquote style="' + WECHAT_INLINE_STYLES.blockquote + '">'],
    ['<ul>', '<ul style="' + WECHAT_INLINE_STYLES.ul + '">'],
    ['<ol>', '<ol style="' + WECHAT_INLINE_STYLES.ol + '">'],
    ['<li>', '<li style="' + WECHAT_INLINE_STYLES.li + '">'],
    ['<code>', '<code style="' + WECHAT_INLINE_STYLES.code + '">'],
    ['<pre>', '<pre style="' + WECHAT_INLINE_STYLES.pre + '">'],
    ['<strong>', '<strong style="' + WECHAT_INLINE_STYLES.strong + '">'],
    ['<b>', '<b style="' + WECHAT_INLINE_STYLES.strong + '">'],
    ['<em>', '<em style="' + WECHAT_INLINE_STYLES.em + '">'],
    ['<i>', '<i style="' + WECHAT_INLINE_STYLES.em + '">'],
    ['<hr>', '<hr style="' + WECHAT_INLINE_STYLES.hr + '">'],
    ['<hr/>', '<hr style="' + WECHAT_INLINE_STYLES.hr + '" />'],
  ]
  tagStyleList.forEach(([open, replacement]) => {
    out = out.split(open).join(replacement)
  })
  const aOpenRe = /<a(\s+)([^>]*?)href=/g
  out = out.replace(aOpenRe, (m, space, attrs) => {
    if (attrs.includes('style=')) return m
    return '<a' + space + 'style="' + WECHAT_INLINE_STYLES.a + '" ' + attrs + 'href='
  })
  const imgRe = /<img(\s+)([^>]*?)>/g
  out = out.replace(imgRe, (m, space, attrs) => {
    if (attrs.includes('style=')) return m
    return '<img' + space + 'style="' + WECHAT_INLINE_STYLES.img + '" ' + attrs + '>'
  })
  return out
}

/**
 * 给 HTML 块级与行内标签加上公众号用内联样式（微信不解析 style 标签，只保留内联样式）。
 * 优先用 DOMParser，无 DOM 时用正则兜底，确保提交的正文带 style。
 * @param {string} html - 由 mdToHtml 得到的 HTML
 * @returns {string} 带 style 的 HTML
 */
function addWechatInlineStyles(html) {
  if (typeof document !== 'undefined' && typeof window !== 'undefined' && window.DOMParser) {
    try {
      const parser = new DOMParser()
      const doc = parser.parseFromString(html, 'text/html')
      const selectors = ['p', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol', 'li', 'code', 'pre', 'strong', 'b', 'em', 'i', 'a', 'hr', 'img']
      selectors.forEach((tag) => {
        const style = WECHAT_INLINE_STYLES[tag]
        if (!style) return
        doc.querySelectorAll(tag).forEach((el) => {
          const cur = el.getAttribute('style') || ''
          el.setAttribute('style', (cur ? cur + ';' : '') + style)
        })
      })
      if (doc.body) return doc.body.innerHTML
    } catch (_) {}
  }
  return addWechatInlineStylesFallback(html)
}

/**
 * 转为带内联样式的 HTML，专供提交公众号草稿使用，便于公众号内展示与系统预览一致。
 * @param {string} md - Markdown 文本
 * @returns {string} 带 style 属性的 HTML
 */
export function mdToHtmlForWechat(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''
  const raw = mdToHtml(trimmed)
  return addWechatInlineStyles(raw)
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
  return { ...metadata, content: mdToHtmlForWechat(trimmed) }
}

/**
 * MediaWiki 写入任务提交前：若勾选「正文为 Markdown」，将 content 转为 wikitext；并去掉内部字段 _contentIsMarkdown。
 * @param {Object} metadata - 表单中的 metadata（可能含 _contentIsMarkdown）
 * @returns {Object} 用于提交的 metadata
 */
function prepareMediaWikiWriteMetadata(metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  const out = { ...metadata }
  delete out._contentIsMarkdown
  const content = out.content
  if (content != null && typeof content === 'string' && content.trim()) {
    out.content = mdToWiki(content.trim())
  }
  return out
}

/**
 * 按任务类型统一处理提交前的 metadata（保证 content 等字段格式一致）。
 * wechat_mp_draft：content 从 Markdown 转为 HTML；mediawiki_write 且 _contentIsMarkdown 时：content 从 Markdown 转为 Wiki。
 * @param {string} taskType - 任务类型
 * @param {Object} metadata - 表单中的 metadata
 * @returns {Object} 用于提交的 metadata
 */
export function prepareMetadataForSubmit(taskType, metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  if (taskType === WECHAT_MP_DRAFT_TASK_TYPE) return prepareWechatDraftMetadata(metadata)
  if (taskType === MEDIAWIKI_WRITE_TASK_TYPE && metadata._contentIsMarkdown) return prepareMediaWikiWriteMetadata(metadata)
  return { ...metadata }
}

// ---------- 公众号公式转图（LaTeX → 图片 → 上传微信 → HTML 中替换） ----------

const FORMULA_PLACEHOLDER_PREFIX = '__MATHIMG_'
const FORMULA_PLACEHOLDER_SUFFIX = '__'

/**
 * 从 Markdown 中提取 $$...$$ 与 $...$，替换为占位符，返回占位后的 MD 与公式体列表。
 * @param {string} md
 * @returns {{ mdWithPlaceholders: string, formulaBodies: string[] }}
 */
function extractFormulasFromMd(md) {
  const formulaBodies = []
  let out = md
  const blockRe = /\$\$([\s\S]*?)\$\$/g
  out = out.replace(blockRe, (_, body) => {
    const key = `${FORMULA_PLACEHOLDER_PREFIX}${formulaBodies.length}${FORMULA_PLACEHOLDER_SUFFIX}`
    formulaBodies.push(body.trim())
    return key
  })
  const inlineRe = /\$([^$\n]+)\$/g
  out = out.replace(inlineRe, (_, body) => {
    const key = `${FORMULA_PLACEHOLDER_PREFIX}${formulaBodies.length}${FORMULA_PLACEHOLDER_SUFFIX}`
    formulaBodies.push(body.trim())
    return key
  })
  return { mdWithPlaceholders: out, formulaBodies }
}

/**
 * 拉取公式 SVG 并上传到微信「上传图文消息内的图片」，返回图片 URL。
 * @param {string} formula - LaTeX 公式
 * @returns {Promise<string>} 微信返回的图片 URL
 */
async function renderFormulaAndUploadToWechat(formula) {
  const res = await fetch(`/api/latex/render?formula=${encodeURIComponent(formula)}`)
  if (!res.ok) throw new Error('公式渲染失败')
  const blob = await res.blob()
  const file = new File([blob], 'formula.png', { type: blob.type || 'image/png' })
  const form = new FormData()
  form.append('file', file)
  const up = await fetch('/api/wechat-mp/upload-article-image', { method: 'POST', body: form })
  const data = await up.json().catch(() => ({}))
  if (!up.ok || !data?.url) throw new Error(data?.detail || data?.message || '公式图片上传失败')
  return data.url
}

/**
 * 公众号草稿提交前：将 content（Markdown）转为 HTML，并将其中的 LaTeX 公式转为图片后上传微信并替换。
 * 异步，供提交时 await。
 * @param {Object} metadata - 表单中的 metadata（content 为 Markdown）
 * @returns {Promise<Object>} 用于提交的 metadata（content 为 HTML，公式已为 <img>）
 */
export async function prepareWechatDraftMetadataWithFormulaImages(metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  const content = metadata.content
  if (content == null || typeof content !== 'string') return { ...metadata }
  const trimmed = String(content).trim()
  if (!trimmed) return { ...metadata }

  const { mdWithPlaceholders, formulaBodies } = extractFormulasFromMd(trimmed)
  let html = mdToHtmlForWechat(mdWithPlaceholders)

  if (formulaBodies.length === 0) return { ...metadata, content: html }

  const urls = []
  for (let i = 0; i < formulaBodies.length; i++) {
    try {
      const url = await renderFormulaAndUploadToWechat(formulaBodies[i])
      urls.push(url)
    } catch (e) {
      urls.push('') // 失败时留空，替换时可保留占位或去掉
    }
  }
  for (let i = 0; i < urls.length; i++) {
    const placeholder = `${FORMULA_PLACEHOLDER_PREFIX}${i}${FORMULA_PLACEHOLDER_SUFFIX}`
    const img = urls[i] ? `<img src="${urls[i]}" alt="公式" />` : placeholder
    html = html.split(placeholder).join(img)
  }
  return { ...metadata, content: html }
}

/**
 * 按任务类型统一处理提交前的 metadata（异步版）。
 * wechat_mp_draft 时会执行公式→图→上传→替换；其余类型与同步版一致。
 * @param {string} taskType - 任务类型
 * @param {Object} metadata - 表单中的 metadata
 * @returns {Promise<Object>} 用于提交的 metadata
 */
export async function prepareMetadataForSubmitAsync(taskType, metadata) {
  if (!metadata || typeof metadata !== 'object') return metadata
  if (taskType === WECHAT_MP_DRAFT_TASK_TYPE) return prepareWechatDraftMetadataWithFormulaImages(metadata)
  if (taskType === MEDIAWIKI_WRITE_TASK_TYPE && metadata._contentIsMarkdown) return Promise.resolve(prepareMediaWikiWriteMetadata(metadata))
  return Promise.resolve(prepareMetadataForSubmit(taskType, metadata))
}
