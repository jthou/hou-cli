/**
 * MediaWiki wikitext ↔ Markdown 双向转换。
 * 用于：从 Wiki 拉取内容后以 Markdown 编辑、或把 Markdown 内容写入 MediaWiki（如 mediawiki_write 任务）。
 * 与 mdToHtml.js 分工：mdToHtml 负责 MD↔HTML（公众号草稿）；本模块负责 Wiki↔MD。
 * 公式：MediaWiki 使用 <math>（已装 MathJax）；本应用统一用 $ 行内、$$ 行间，转换时互转。
 */

const MATH_PLACEHOLDER_PREFIX = '__WIKIMATH_'
const MATH_PLACEHOLDER_SUFFIX = '__'
const CODE_PLACEHOLDER_PREFIX = '__WIKICODE_'
const CODE_PLACEHOLDER_SUFFIX = '__'

// ---------- Wikitext → Markdown ----------

/**
 * 提取 <math>...</math>，避免后续替换破坏公式内容。
 * display="block" → $$...$$，否则 → $...$
 */
function wikiExtractMathToPlaceholders(wiki) {
  const list = []
  const re = /<math(\s[^>]*)?>([\s\S]*?)<\/math>/gi
  const out = wiki.replace(re, (_, attrs, body) => {
    const isBlock = /display\s*=\s*["']?block["']?/i.test(attrs || '')
    const key = `${MATH_PLACEHOLDER_PREFIX}${list.length}${MATH_PLACEHOLDER_SUFFIX}`
    list.push(isBlock ? `$$${body.trim()}$$` : `$${body.trim()}$`)
    return key
  })
  return { text: out, mathList: list }
}

function wikiRestoreMathPlaceholders(text, mathList) {
  let s = text
  for (let i = 0; i < mathList.length; i++) {
    s = s.replace(`${MATH_PLACEHOLDER_PREFIX}${i}${MATH_PLACEHOLDER_SUFFIX}`, mathList[i])
  }
  return s
}

/**
 * MediaWiki 标题：= H1 =, == H2 ==, === H3 === … → #, ##, ### …
 * 先匹配最长（等号最多）的避免误伤
 */
function wikiHeadersToMd(wiki) {
  return wiki.replace(/^(={2,6})\s*(.+?)\s*\1\s*$/gm, (_, eq, title) => {
    const level = Math.min(eq.length, 6)
    const prefix = '#'.repeat(level)
    return `${prefix} ${title.trim()}`
  })
}

/**
 * '''bold''', ''italic'', '''''bold+italic'''''
 */
function wikiEmphasisToMd(wiki) {
  let s = wiki
  s = s.replace(/'''''(.+?)'''''/g, '***$1***')
  s = s.replace(/'''(.+?)'''/g, '**$1**')
  s = s.replace(/''(.+?)''/g, '*$1*')
  return s
}

/**
 * 内部链接 [[Page]], [[Page|display]] → [display](Page) 或 [Page](Page)
 * 外部链接 [http://... text] → [text](url)
 */
function wikiLinksToMd(wiki) {
  let s = wiki
  s = s.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '[$2]($1)')
  s = s.replace(/\[\[([^\]]+)\]\]/g, '[$1]($1)')
  s = s.replace(/\[(https?:\/\/[^\s\]]+)\s+([^\]]+)\]/g, '[$2]($1)')
  s = s.replace(/\[(https?:\/\/[^\s\]]+)\]/g, '[$1]($1)')
  return s
}

/**
 * 列表：* → -, # → 1. （有序用 1. 占位，渲染时连续）
 */
function wikiListsToMd(wiki) {
  const lines = wiki.split('\n')
  const out = []
  let inNumList = false
  for (const line of lines) {
    const bulletMatch = line.match(/^(\*+)\s+(.*)$/)
    const numMatch = line.match(/^(#+)\s+(.*)$/)
    if (bulletMatch) {
      const depth = bulletMatch[1].length
      const rest = bulletMatch[2]
      out.push('  '.repeat(depth - 1) + '- ' + rest)
      inNumList = false
    } else if (numMatch) {
      const depth = numMatch[1].length
      const rest = numMatch[2]
      out.push('  '.repeat(depth - 1) + '1. ' + rest)
      inNumList = true
    } else {
      out.push(line)
      inNumList = false
    }
  }
  return out.join('\n')
}

/**
 * <br />, <br> → 换行
 */
function wikiBrToMd(wiki) {
  return wiki.replace(/<br\s*\/?>/gi, '\n')
}

/**
 * Wikitext → Markdown（覆盖常用语法，模板等复杂结构可能保留原样或略化）
 * @param {string} wiki - MediaWiki wikitext
 * @returns {string} Markdown
 */
export function wikiToMd(wiki) {
  if (wiki == null || typeof wiki !== 'string') return ''
  let s = wiki.trim()
  if (!s) return ''
  const { text: afterMath, mathList } = wikiExtractMathToPlaceholders(s)
  s = wikiBrToMd(afterMath)
  s = wikiHeadersToMd(s)
  s = wikiLinksToMd(s)
  s = wikiEmphasisToMd(s)
  s = wikiListsToMd(s)
  return wikiRestoreMathPlaceholders(s, mathList)
}

// ---------- Markdown → Wikitext ----------

/**
 * 提取 ```lang\ncode``` 代码块，避免后续替换破坏内容；转为 <syntaxhighlight lang="..."> 占位。
 */
function mdExtractCodeToPlaceholders(md) {
  const list = []
  const re = /```([\w.+-]*)\s*\n([\s\S]*?)```\s*/g
  const out = md.replace(re, (_, lang, code) => {
    const key = `${CODE_PLACEHOLDER_PREFIX}${list.length}${CODE_PLACEHOLDER_SUFFIX}`
    const langAttr = (lang || '').trim() || 'text'
    list.push({ lang: langAttr, code: code.replace(/\n$/, '') })
    return key
  })
  return { text: out, codeList: list }
}

function mdRestoreCodePlaceholders(text, codeList) {
  let s = text
  for (let i = 0; i < codeList.length; i++) {
    const { lang, code } = codeList[i]
    const tag = `<syntaxhighlight lang="${lang}">\n${code}\n</syntaxhighlight>`
    s = s.replace(`${CODE_PLACEHOLDER_PREFIX}${i}${CODE_PLACEHOLDER_SUFFIX}`, tag)
  }
  return s
}

/**
 * 提取 $$...$$ 与 $...$，避免后续替换破坏公式；先匹配块级再匹配行内。
 */
function mdExtractMathToPlaceholders(md) {
  const list = []
  let out = md
  const blockRe = /\$\$([\s\S]*?)\$\$/g
  out = out.replace(blockRe, (_, body) => {
    const key = `${MATH_PLACEHOLDER_PREFIX}${list.length}${MATH_PLACEHOLDER_SUFFIX}`
    list.push({ block: true, body: body.trim() })
    return key
  })
  const inlineRe = /\$([^$\n]+)\$/g
  out = out.replace(inlineRe, (_, body) => {
    const key = `${MATH_PLACEHOLDER_PREFIX}${list.length}${MATH_PLACEHOLDER_SUFFIX}`
    list.push({ block: false, body: body.trim() })
    return key
  })
  return { text: out, mathList: list }
}

function mdRestoreMathPlaceholders(text, mathList) {
  let s = text
  for (let i = 0; i < mathList.length; i++) {
    const { block, body } = mathList[i]
    const tag = block ? `<math display="block">${body}</math>` : `<math>${body}</math>`
    s = s.replace(`${MATH_PLACEHOLDER_PREFIX}${i}${MATH_PLACEHOLDER_SUFFIX}`, tag)
  }
  return s
}

/**
 * ## H2 → == H2 ==, ### H3 → === H3 === …
 */
function mdHeadersToWiki(md) {
  return md.replace(/^(#{1,6})\s+(.+)$/gm, (_, hash, title) => {
    const level = Math.min(hash.length, 6)
    const eq = '='.repeat(level)
    return `${eq} ${title.trim()} ${eq}`
  })
}

/**
 * **bold** → '''bold''', *italic* → ''italic'', ***both*** → '''''both'''''
 */
function mdEmphasisToWiki(md) {
  let s = md
  s = s.replace(/\*\*\*(.+?)\*\*\*/g, "'''''$1'''''")
  s = s.replace(/\*\*(.+?)\*\*/g, "'''$1'''")
  s = s.replace(/\*(.+?)\*/g, "''$1''")
  s = s.replace(/_(.+?)_/g, "''$1''")
  s = s.replace(/__(.+?)__/g, "'''$1'''")
  return s
}

/**
 * [text](url) → 若 url 像内部链接则 [[url|text]]，否则 [url text]
 * 简单规则：含 :// 视为外部；否则视为内部页面名
 */
function mdLinksToWiki(md) {
  return md.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => {
    const u = url.trim()
    if (/^https?:\/\//i.test(u)) return `[${u} ${text}]`
    return `[[${u}|${text}]]`
  })
}

/**
 * > xxx → <blockquote>xxx</blockquote>
 * 支持多行连续引用，合并为一个 blockquote
 */
function mdBlockquoteToWiki(md) {
  const lines = md.split('\n')
  const out = []
  let blockquoteLines = []
  const flushBlockquote = () => {
    if (blockquoteLines.length) {
      const content = blockquoteLines.map((l) => l.replace(/^>\s*/, '')).join('\n')
      out.push(`<blockquote>${content}</blockquote>`)
      blockquoteLines = []
    }
  }
  for (const line of lines) {
    if (/^>\s*/.test(line)) {
      blockquoteLines.push(line)
    } else {
      flushBlockquote()
      out.push(line)
    }
  }
  flushBlockquote()
  return out.join('\n')
}

/**
 * - item → * item; 1. /2. /3. item → # item
 */
function mdListsToWiki(md) {
  const lines = md.split('\n')
  const out = []
  for (const line of lines) {
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.*)$/)
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)$/)
    if (ulMatch) {
      const indent = ulMatch[1].length
      const depth = Math.floor(indent / 2) + 1
      out.push('*'.repeat(depth) + ' ' + ulMatch[2])
    } else if (olMatch) {
      const indent = olMatch[1].length
      const depth = Math.floor(indent / 2) + 1
      out.push('#'.repeat(depth) + ' ' + olMatch[2])
    } else {
      out.push(line)
    }
  }
  return out.join('\n')
}

/**
 * Markdown → MediaWiki wikitext（覆盖常用语法）
 * @param {string} md - Markdown 文本
 * @returns {string} MediaWiki wikitext
 */
export function mdToWiki(md) {
  if (md == null || typeof md !== 'string') return ''
  let s = md.trim()
  if (!s) return ''
  const { text: afterCode, codeList } = mdExtractCodeToPlaceholders(s)
  const { text: afterMath, mathList } = mdExtractMathToPlaceholders(afterCode)
  s = mdHeadersToWiki(afterMath)
  s = mdLinksToWiki(s)
  s = mdEmphasisToWiki(s)
  s = mdListsToWiki(s)
  s = mdBlockquoteToWiki(s)
  s = mdRestoreMathPlaceholders(s, mathList)
  return mdRestoreCodePlaceholders(s, codeList)
}
