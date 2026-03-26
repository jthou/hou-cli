/**
 * 公众号草稿正文：Markdown ↔ HTML 统一转换。
 * - 编辑与预览用 Markdown → mdToHtml() → HTML 渲染。
 * - 编辑已有草稿时，接口返回的 content 为 HTML，用 htmlToMd() 转成 Markdown 再放入编辑器。
 * - 提交任务/定时任务时，metadata.content 必须为 HTML，由 prepareWechatDraftMetadata 或 prepareMetadataForSubmit 统一转换。
 * - 粘贴到公众号编辑页时，使用 juice 做 CSS 内联化，提升样式保留率。
 */
import TurndownService from 'turndown'
import juice from 'juice'
import { mdToWiki } from './wikiMdConvert.js'
import { mdToHtmlCore } from './mdToHtmlCore.js'
import { MEDIAWIKI_BASE_URL } from '../config/mediawiki.js'

/** 任务类型：公众号草稿。凡提交该类型任务的 metadata 前，应对 content 做 MD→HTML。 */
export const WECHAT_MP_DRAFT_TASK_TYPE = 'wechat_mp_draft'

/** 任务类型：MediaWiki 写入。若勾选「正文为 Markdown」，提交前对 content 做 MD→Wiki。 */
export const MEDIAWIKI_WRITE_TASK_TYPE = 'mediawiki_write'

/** 导出核心转换函数，供测试或直接调用 */
export { mdToHtmlCore } from './mdToHtmlCore.js'

/**
 * 将 [[File:xxx]]、[[File:xxx|200px]]、[[File:xxx|200x300px]] 转为 <img>，使用 Special:FilePath。
 * 时间：2025-03-13；理由：网页阅读上传图片后需在 Markdown 预览中显示；方法：Special:FilePath 重定向到真实图片 URL。
 */
function replaceWikiFileWithImg(md) {
  if (md == null || typeof md !== 'string') return md
  const base = (MEDIAWIKI_BASE_URL || '').replace(/\/$/, '')
  if (!base) return md
  const re = /\[\[(?:File|Image):([^\]|]+)(?:\|([^\]]*))?\]\]/gi
  return md.replace(re, (_, filename, params) => {
    const name = (filename || '').trim()
    if (!name) return ''
    const url = `${base}/index.php/Special:FilePath/${encodeURIComponent(name)}`
    let style = 'max-width:100%;height:auto;border:1px solid #d0d7de;border-radius:6px;'
    if (params) {
      const parts = params.split('|').map((p) => p.trim())
      const pxW = parts.find((p) => /^\d+px$/i.test(p))
      const pxWh = parts.find((p) => /^\d+x\d+px$/i.test(p))
      if (pxWh) {
        const [w, h] = pxWh.split('x').map((s) => parseInt(s, 10))
        if (w && h) style += `width:${w}px;height:${h}px;`
      } else if (pxW) {
        const w = parseInt(pxW, 10)
        if (w) style += `width:${w}px;`
      }
    }
    return `<img src="${url}" alt="${name}" style="${style}" />`
  })
}

/**
 * Markdown 转 HTML（核心转换 + 与 mdToHtmlForWechat 共用同一实现）。
 * @param {string} md - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function mdToHtml(md) {
  const withWikiImg = replaceWikiFileWithImg(md)
  let out = mdToHtmlCore(withWikiImg)
  out = styleNumberedHeadings(out)
  return out
}

/**
 * 公众号正文内联样式。正文 16px，章节标题比正文大两号（h2=22px, h3=20px, h4=18px）。
 * 所有标题下带分割线（border-bottom），API 推送时尽量保留。
 */
const BODY_FONT_SIZE = '16px'
const WECHAT_INLINE_STYLES = {
  p: `font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;font-size:${BODY_FONT_SIZE};line-height:1.6;line-break:anywhere;color:#24292f;margin:0 0 16px 0;`,
  h1: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;font-size:24px;font-weight:600;color:#24292f;margin:16px 0 8px 0;line-height:1.4;border-bottom:1px solid #d0d7de;padding-bottom:0.3em;',
  h2: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;font-size:22px;font-weight:600;color:#24292f;margin:16px 0 8px 0;line-height:1.4;border-bottom:1px solid #d0d7de;padding-bottom:0.3em;',
  h3: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;font-size:20px;font-weight:600;color:#24292f;margin:16px 0 8px 0;line-height:1.4;border-bottom:1px solid #d0d7de;padding-bottom:0.3em;',
  h4: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;font-size:18px;font-weight:600;color:#24292f;margin:16px 0 8px 0;line-height:1.4;border-bottom:1px solid #d0d7de;padding-bottom:0.3em;',
  blockquote: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;color:#57606a;font-size:15px;margin:0 0 16px 0;padding-left:12px;border-left:4px solid #d0d7de;line-height:1.6;',
  ul: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;margin:0 0 16px 0;padding-left:24px;line-height:1.6;color:#24292f;',
  ol: 'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",Helvetica,Arial,sans-serif;margin:0 0 16px 0;padding-left:24px;line-height:1.6;color:#24292f;',
  li: 'font-size:16px;line-height:1.6;line-break:anywhere;color:#24292f;margin-bottom:12px;',
  code: 'font-family:ui-monospace,monospace;background-color:#f6f8fa;color:#24292f;font-size:14px;padding:2px 6px;border:1px solid #d0d7de;border-radius:4px;',
  pre: 'font-family:ui-monospace,monospace;background-color:#f6f8fa;color:#24292f;font-size:14px;line-height:1.5;margin:0 0 16px 0;padding:12px;border:1px solid #d0d7de;border-radius:6px;overflow-x:auto;',
  strong: 'font-weight:bold;color:#24292f;',
  em: 'font-style:italic;color:#57606a;',
  a: 'color:#0969da;text-decoration:none;',
  hr: 'border:0;border-top:1px solid #d0d7de;margin:8px 0 16px 0;',
  img: 'max-width:100%;height:auto;border:1px solid #d0d7de;border-radius:6px;',
  table: 'border-collapse:collapse;margin:0 auto 16px;max-width:100%;width:max-content;',
  th: 'border:1px solid #d0d7de;padding:8px 12px;color:#24292f;vertical-align:top;font-weight:600;background-color:#f6f8fa;',
  td: 'border:1px solid #d0d7de;padding:8px 12px;color:#24292f;vertical-align:top;',
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
    ['<table>', '<table style="' + WECHAT_INLINE_STYLES.table + '">'],
    ['<th>', '<th style="' + WECHAT_INLINE_STYLES.th + '">'],
    ['<td>', '<td style="' + WECHAT_INLINE_STYLES.td + '">'],
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
      const selectors = ['p', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol', 'li', 'code', 'pre', 'strong', 'b', 'em', 'i', 'a', 'hr', 'img', 'table', 'th', 'td']
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

/** 公众号主题 CSS（供 juice 内联化）。正文 16px，章节标题大两号，标题下分割线。 */
const WECHAT_THEME_CSS = `
  #wechat-content { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.6; line-break: anywhere; color: #24292f; }
  #wechat-content p { font-size: 16px; line-height: 1.6; line-break: anywhere; color: #24292f; margin: 0 0 16px 0; }
  #wechat-content h1 { font-size: 24px; font-weight: 600; color: #24292f; margin: 16px 0 8px 0; line-height: 1.4; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
  #wechat-content h2 { font-size: 22px; font-weight: 600; color: #24292f; margin: 16px 0 8px 0; line-height: 1.4; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
  #wechat-content h3 { font-size: 20px; font-weight: 600; color: #24292f; margin: 16px 0 8px 0; line-height: 1.4; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
  #wechat-content h4 { font-size: 18px; font-weight: 600; color: #24292f; margin: 16px 0 8px 0; line-height: 1.4; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }
  #wechat-content blockquote { color: #57606a; font-size: 15px; margin: 0 0 16px 0; padding-left: 12px; border-left: 4px solid #d0d7de; line-height: 1.6; }
  #wechat-content ul { margin: 0 0 16px 0; padding-left: 24px; line-height: 1.6; color: #24292f; }
  #wechat-content ol { margin: 0 0 16px 0; padding-left: 24px; line-height: 1.6; color: #24292f; }
  #wechat-content li { font-size: 16px; line-height: 1.6; line-break: anywhere; color: #24292f; margin-bottom: 12px; }
  #wechat-content code { font-family: ui-monospace, monospace; background-color: #f6f8fa; color: #24292f; font-size: 14px; padding: 2px 6px; border: 1px solid #d0d7de; border-radius: 4px; }
  #wechat-content pre { font-family: ui-monospace, monospace; background-color: #f6f8fa; color: #24292f; font-size: 14px; line-height: 1.5; margin: 0 0 16px 0; padding: 12px; border: 1px solid #d0d7de; border-radius: 6px; overflow-x: auto; }
  #wechat-content strong, #wechat-content b { font-weight: bold; color: #24292f; }
  #wechat-content em, #wechat-content i { font-style: italic; color: #57606a; }
  #wechat-content a { color: #0969da; text-decoration: none; }
  #wechat-content hr { border: 0; border-top: 1px solid #d0d7de; margin: 24px 0; }
  #wechat-content table { border-collapse: collapse; margin: 0 auto 16px; max-width: 100%; width: max-content; }
  #wechat-content th, #wechat-content td { border: 1px solid #d0d7de; padding: 8px 12px; color: #24292f; vertical-align: top; }
  #wechat-content th { font-weight: 600; background-color: #f6f8fa; }
  #wechat-content img { max-width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 6px; }
`

/** 微信粘贴：代码块空格用 \\u00A0 防被合并，换行用 <br>（参考 bm.md） */
function wechatCodeBlockFixes(html) {
  return html.replace(/<pre[^>]*>([\s\S]*?)<\/pre>/gi, (_, content) => {
    const fixed = content
      .replace(/^( +)/gm, (spaces) => '\u00A0'.repeat(spaces.length))
      .replace(/\n/g, '<br>')
    return `<pre>${fixed}</pre>`
  })
}

/** 带数字的章节标题：数字比标题大 1–2 号，如 ## 01 电力基建 */
const CH_NUM_COLOR = '#24292f'
const CH_NUM_STYLES = { h1: '28px', h2: '26px', h3: '20px', h4: '18px' }
function styleNumberedHeadings(html) {
  return html.replace(/<h([1-4])>(\d{1,2})(\s)/g, (_, level, num, space) => {
    const size = CH_NUM_STYLES[`h${level}`] || '24px'
    return `<h${level}><span class="ch-num" style="font-size:${size};color:${CH_NUM_COLOR};font-weight:600">${num}</span>${space}`
  })
}

/** 防止微信在标签边界插入 section 导致换行。采用相对安全的格式：1) 冒号移入加粗 2) 句号移入加粗 3) li 内容用 span 包裹，减少块级边界 */
function preventCjkLineBreaks(html) {
  return html
    .replace(/(<(?:strong|b)>[\s\S]*?)(<\/(?:strong|b)>)(：)/g, '$1$3$2')
    .replace(/(<(?:strong|b)>[\s\S]*?)(\d+)(倍|个|元|%)(<\/(?:strong|b)>)(。)/g, '$1$2$3$5$4')
    .replace(/<li([^>]*)>([\s\S]*?)<\/li>/gi, (_, attrs, content) => `<li${attrs}><span style="display:inline">${content}</span></li>`)
}

/**
 * 转为带内联样式的 HTML，专供提交公众号草稿及粘贴到公众号编辑页使用。
 * 使用 juice 做 CSS 内联化，提升粘贴时样式保留率（参考 bm.md、Markdown Nice）。
 * @param {string} md - Markdown 文本
 * @returns {string} 带 style 属性的 HTML
 */
export function mdToHtmlForWechat(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''
  let raw = mdToHtml(trimmed)
  raw = wechatCodeBlockFixes(raw)
  const wrapped = `<section id="wechat-content">${raw}</section>`
  try {
    let inlined = juice(wrapped, { extraCss: WECHAT_THEME_CSS, removeStyleTags: true })
    const match = inlined.match(/<section id="wechat-content">([\s\S]*?)<\/section>/)
    let out = match ? match[1].trim() : inlined.replace(/^<section[^>]*>|<\/section>$/g, '').trim()
    return preventCjkLineBreaks(out)
  } catch (_) {
    return preventCjkLineBreaks(addWechatInlineStyles(raw))
  }
}

const turndownService = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' })

turndownService.addRule('style', { filter: 'style', replacement: () => '' })
turndownService.addRule('script', { filter: 'script', replacement: () => '' })

turndownService.addRule('table', {
  filter: 'table',
  replacement: (_content, node) => {
    const rows = Array.from(node.querySelectorAll('tr'))
    if (rows.length === 0) return ''
    const getCells = (tr) => {
      const cells = []
      for (const cell of tr.querySelectorAll('th, td')) {
        const raw = (cell.textContent || '').trim().replace(/\n/g, ' ')
        const text = raw.replace(/\|/g, '\\|') || ' '
        cells.push(text)
      }
      return cells
    }
    const mdRows = rows.map((tr) => getCells(tr))
    const colCount = Math.max(...mdRows.map((r) => r.length))
    const pad = (arr) => {
      const a = [...arr]
      while (a.length < colCount) a.push(' ')
      return a.slice(0, colCount)
    }
    const sep = Array(colCount)
      .fill('---')
      .join(' | ')
    const lines = mdRows.map((r) => '| ' + pad(r).join(' | ') + ' |')
    return '\n' + lines[0] + '\n| ' + sep + ' |\n' + lines.slice(1).join('\n') + '\n'
  },
})

/**
 * 从完整页面 HTML 中提取维基百科正文（#mw-content-text），并清理 CSS/导航等噪音。
 * 2026-03-13：维基百科全页转 Markdown 时混入大量 UI、style 块、navbox，需提取并清理。
 * @param {string} html - 可能含维基全页的 HTML
 * @returns {string} 提取并清理后的 HTML，无匹配则返回原串
 */
function extractWikipediaContent(html) {
  if (typeof document === 'undefined' || typeof DOMParser === 'undefined') return html
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    const mwContent = doc.getElementById('mw-content-text')
    if (!mwContent || (mwContent.innerText || mwContent.textContent || '').trim().length < 50) {
      return html
    }
    const frag = doc.createElement('div')
    frag.innerHTML = mwContent.innerHTML
    frag.querySelectorAll('style, script').forEach((el) => el.remove())
    frag.querySelectorAll('.mw-editsection, .navbox, .metadata, .mw-collapsible-toggle').forEach((el) => el.remove())
    return frag.innerHTML
  } catch (_) {}
  return html
}

/**
 * HTML → Markdown，用于编辑已有草稿时把接口返回的正文 HTML 转成 Markdown 再放入编辑器。
 * 若 HTML 含维基百科正文容器（#mw-content-text），先提取再转换，避免导航/侧栏混入。
 * @param {string} html - HTML 字符串（如公众号草稿 content、扩展抓取的网页）
 * @returns {string} Markdown 字符串
 */
export function htmlToMd(html) {
  if (html == null || typeof html !== 'string') return ''
  const trimmed = html.trim()
  if (!trimmed) return ''
  const toConvert = extractWikipediaContent(trimmed)
  try {
    return turndownService.turndown(toConvert)
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
