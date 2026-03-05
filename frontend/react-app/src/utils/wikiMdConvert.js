/**
 * MediaWiki wikitext ↔ Markdown 双向转换。
 * 用于：从 Wiki 拉取内容后以 Markdown 编辑、或把 Markdown 内容写入 MediaWiki（如 mediawiki_write 任务）。
 * 与 mdToHtml.js 分工：mdToHtml 负责 MD↔HTML（公众号草稿）；本模块负责 Wiki↔MD。
 * 公式：MediaWiki 使用 <math>（已装 MathJax）；本应用统一用 $ 行内、$$ 行间，转换时互转。
 */

// 使用 \x01 避免被 _ 或 __ 的强调正则误匹配
const MATH_PLACEHOLDER_PREFIX = '\x01WIKIMATH'
const MATH_PLACEHOLDER_SUFFIX = '\x01'
const CODE_PLACEHOLDER_PREFIX = '__WIKICODE_'
const CODE_PLACEHOLDER_SUFFIX = '__'
const NOWIKI_PLACEHOLDER_PREFIX = '__WIKINOWIKI_'
const NOWIKI_PLACEHOLDER_SUFFIX = '__'
const PRE_PLACEHOLDER_PREFIX = '__WIKIPRE_'
const PRE_PLACEHOLDER_SUFFIX = '__'

// ---------- Wikitext → Markdown ----------

/**
 * 提取 <nowiki>...</nowiki>，原样保留内容，避免后续替换破坏。
 */
function wikiExtractNowikiToPlaceholders(wiki) {
  const list = []
  const re = /<nowiki>([\s\S]*?)<\/nowiki>/gi
  const out = wiki.replace(re, (_, body) => {
    const key = `${NOWIKI_PLACEHOLDER_PREFIX}${list.length}${NOWIKI_PLACEHOLDER_SUFFIX}`
    list.push(body)
    return key
  })
  return { text: out, list }
}

function wikiRestoreNowikiPlaceholders(text, list) {
  let s = text
  for (let i = 0; i < list.length; i++) {
    s = s.replace(`${NOWIKI_PLACEHOLDER_PREFIX}${i}${NOWIKI_PLACEHOLDER_SUFFIX}`, list[i])
  }
  return s
}

/**
 * 提取 <pre>...</pre>，转为 ``` 代码块占位。
 */
function wikiExtractPreToPlaceholders(wiki) {
  const list = []
  const re = /<pre>([\s\S]*?)<\/pre>/gi
  const out = wiki.replace(re, (_, body) => {
    const key = `${PRE_PLACEHOLDER_PREFIX}${list.length}${PRE_PLACEHOLDER_SUFFIX}`
    list.push('```\n' + body.replace(/\n$/, '') + '\n```')
    return key
  })
  return { text: out, list }
}

function wikiRestorePrePlaceholders(text, list) {
  let s = text
  for (let i = 0; i < list.length; i++) {
    s = s.replace(`${PRE_PLACEHOLDER_PREFIX}${i}${PRE_PLACEHOLDER_SUFFIX}`, list[i])
  }
  return s
}

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
 * ---- (4+ 减号) → --- 水平线
 */
function wikiHrToMd(wiki) {
  return wiki.replace(/^----+\s*$/gm, '---')
}

/**
 * [[File:xxx]]、[[Image:xxx]] → ![](filename) 或 ![caption](filename)
 * 支持 [[File:name.png|thumb|200px|caption]]
 */
function wikiImageToMd(wiki) {
  const re = /\[\[(?:File|Image):([^\]|]+)(?:\|([^\]]*))?\]\]/gi
  return wiki.replace(re, (_, filename, params) => {
    const name = filename.trim()
    if (!params) return `![${name}](${name})`
    const parts = params.split('|').map((p) => p.trim())
    const opts = new Set(['thumb', 'thumbnail', 'frame', 'framed', 'frameless', 'left', 'right', 'center', 'none', 'border', 'upright'])
    let caption = ''
    for (const p of parts) {
      if (!opts.has(p.toLowerCase()) && !/^\d+px$/i.test(p) && !/^upright=/i.test(p) && !/^\d+x\d+px$/i.test(p)) {
        caption = p
      }
    }
    return caption ? `![${caption}](${name})` : `![${name}](${name})`
  })
}

/**
 * 定义列表 ; 术语 : 定义 → **术语**\n> 定义
 */
function wikiDefListToMd(wiki) {
  const lines = wiki.split('\n')
  const out = []
  let lastTerm = null
  const defs = []
  const flushDef = () => {
    if (lastTerm !== null && defs.length) {
      out.push(`**${lastTerm}**`)
      for (const d of defs) out.push('> ' + d)
      defs.length = 0
      lastTerm = null
    } else if (lastTerm !== null) {
      out.push(`**${lastTerm}**`)
      lastTerm = null
    }
  }
  for (const line of lines) {
    const termMatch = line.match(/^;\s*(.*)$/)
    const defMatch = line.match(/^:\s*(.*)$/)
    if (termMatch) {
      flushDef()
      lastTerm = termMatch[1].trim()
    } else if (defMatch && lastTerm !== null) {
      defs.push(defMatch[1])
    } else {
      flushDef()
      out.push(line)
    }
  }
  flushDef()
  return out.join('\n')
}

/**
 * 行首 : 缩进 → > 引用
 */
function wikiIndentToMd(wiki) {
  return wiki.replace(/^(:+)\s*(.*)$/gm, (_, colons, rest) => {
    const depth = colons.length
    return '> '.repeat(depth) + rest
  })
}

/**
 * <sub>、<sup>、<s>、<del> → MD 或保留 HTML
 */
function wikiSubSupStrikeToMd(wiki) {
  let s = wiki
  s = s.replace(/<sub>([\s\S]*?)<\/sub>/gi, '<sub>$1</sub>')
  s = s.replace(/<sup>([\s\S]*?)<\/sup>/gi, '<sup>$1</sup>')
  s = s.replace(/<s>([\s\S]*?)<\/s>/gi, '~~$1~~')
  s = s.replace(/<del>([\s\S]*?)<\/del>/gi, '~~$1~~')
  return s
}

/**
 * 解析 Wiki 单元格：| attr | content 或 | content，返回 { content, colspan, rowspan, align }
 */
function parseWikiCell(raw) {
  const s = raw.trim().replace(/&#124;/g, '|')
  const pipeIdx = s.indexOf('|')
  if (pipeIdx < 0) return { content: s, colspan: 1, rowspan: 1, align: 'left' }
  const left = s.slice(0, pipeIdx).trim()
  const content = s.slice(pipeIdx + 1).trim()
  if (!left || !/=/.test(left)) return { content: s, colspan: 1, rowspan: 1, align: 'left' }
  const colspan = parseInt(left.match(/colspan\s*=\s*["']?(\d+)["']?/i)?.[1], 10) || 1
  const rowspan = parseInt(left.match(/rowspan\s*=\s*["']?(\d+)["']?/i)?.[1], 10) || 1
  const alignMatch = left.match(/text-align\s*:\s*(left|center|right)/i)
  const align = alignMatch ? alignMatch[1].toLowerCase() : 'left'
  return { content, colspan, rowspan, align }
}

/**
 * MediaWiki 表格 {| ... |} → Markdown 或 HTML 表格
 * 支持 |+ caption、| A || B（同行多格）、每行一格的 | A \n| B、! 表头、colspan、rowspan
 */
function wikiTableToMd(wiki) {
  const re = /\{\|([^]*?)\|\}/g
  return wiki.replace(re, (block) => {
    const inner = block.slice(2, -2).trim()
    const lines = inner.split('\n')
    let caption = ''
    const rows = []
    let currentRow = []
    const flushRow = () => {
      if (currentRow.length) {
        rows.push(currentRow)
        currentRow = []
      }
    }
    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('|+')) {
        const cap = trimmed.slice(2).trim()
        const pipeIdx = cap.indexOf('|')
        caption = pipeIdx >= 0 ? cap.slice(pipeIdx + 1).trim() : cap
        continue
      }
      if (trimmed === '|-') {
        flushRow()
        continue
      }
      if (/^\|/.test(trimmed)) {
        const parts = trimmed.replace(/^\|\s*/, '').split(/\|\|/)
        for (const p of parts) {
          currentRow.push({ ...parseWikiCell(p), header: false })
        }
      } else if (/^!/.test(trimmed)) {
        const parts = trimmed.replace(/^!\s*/, '').split(/!!/)
        for (const p of parts) {
          currentRow.push({ ...parseWikiCell(p), header: true })
        }
      }
    }
    flushRow()
    if (rows.length === 0) return block
    const hasSpan = rows.some((r) => r.some((c) => c.colspan > 1 || c.rowspan > 1))
    if (hasSpan) {
      const escape = (t) => (t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      const grid = []
      for (let ri = 0; ri < rows.length; ri++) {
        const r = rows[ri]
        if (!grid[ri]) grid[ri] = []
        let col = 0
        for (const cell of r) {
          while (col < grid[ri].length && grid[ri][col] === null) col++
          const attrs = []
          if (cell.colspan > 1) attrs.push(`colspan="${cell.colspan}"`)
          if (cell.rowspan > 1) attrs.push(`rowspan="${cell.rowspan}"`)
          const tag = cell.header ? 'th' : 'td'
          const attrStr = attrs.length ? ' ' + attrs.join(' ') : ''
          const html = `<${tag}${attrStr}>${escape(cell.content)}</${tag}>`
          grid[ri][col] = html
          for (let rr = 0; rr < cell.rowspan; rr++) {
            for (let cc = 0; cc < cell.colspan; cc++) {
              if (rr === 0 && cc === 0) continue
              const rri = ri + rr
              const cci = col + cc
              if (!grid[rri]) grid[rri] = []
              grid[rri][cci] = null
            }
          }
          col += cell.colspan
        }
      }
      const htmlRows = grid.map((row) => {
        const cells = (row || []).filter((c) => c !== null)
        return `<tr>${cells.join('')}</tr>`
      })
      const table = `<table class="wikitable">${caption ? `<caption>${escape(caption)}</caption>` : ''}<tbody>${htmlRows.join('')}</tbody></table>`
      return table
    }
    const colCount = Math.max(...rows.map((r) => r.reduce((s, c) => s + c.colspan, 0)))
    const pad = (arr) => {
      const a = arr.flatMap((c) => Array(c.colspan).fill(c.content))
      while (a.length < colCount) a.push('')
      return a.slice(0, colCount)
    }
    const alignToSep = (a) => {
      if (a === 'center') return ':---:'
      if (a === 'right') return '---:'
      return ':---'
    }
    const firstAligns = rows[0].flatMap((c) => Array(c.colspan).fill(c.align)).slice(0, colCount)
    const sep = firstAligns
      .map((a) => alignToSep(a || 'left'))
      .concat(Array(Math.max(0, colCount - firstAligns.length)).fill(':---'))
      .slice(0, colCount)
      .join(' | ')
    const mdRows = rows.map((r) => pad(r).map((c) => (c || ' ').replace(/\|/g, '&#124;')).join(' | '))
    const header = mdRows[0]
    const body = mdRows.slice(1)
    let out = `| ${header} |\n| ${sep} |\n` + body.map((r) => `| ${r} |`).join('\n')
    if (caption) out = `**${caption}**\n\n` + out
    return out
  })
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
  const { text: afterNowiki, list: nowikiList } = wikiExtractNowikiToPlaceholders(s)
  const { text: afterPre, list: preList } = wikiExtractPreToPlaceholders(afterNowiki)
  const { text: afterMath, mathList } = wikiExtractMathToPlaceholders(afterPre)
  s = wikiBrToMd(afterMath)
  s = wikiHrToMd(s)
  s = wikiTableToMd(s)
  s = wikiListsToMd(s)
  s = wikiHeadersToMd(s)
  s = wikiImageToMd(s)
  s = wikiLinksToMd(s)
  s = wikiEmphasisToMd(s)
  s = wikiDefListToMd(s)
  s = wikiIndentToMd(s)
  s = wikiSubSupStrikeToMd(s)
  s = wikiRestoreMathPlaceholders(s, mathList)
  s = wikiRestorePrePlaceholders(s, preList)
  return wikiRestoreNowikiPlaceholders(s, nowikiList)
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
    const tag = block ? `$$${body}$$` : `$${body}$`
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
 * 解析 MD 分隔行对齐：:--- 左，:---: 中，---: 右
 */
function parseMdAlign(cell) {
  const s = (cell || '').trim()
  const hasLeft = s.startsWith(':')
  const hasRight = s.endsWith(':')
  if (hasLeft && hasRight) return 'center'
  if (hasRight) return 'right'
  return 'left'
}

/**
 * Markdown 表格 → MediaWiki 表格
 * | H1 | H2 | + | :---: | --- | + 数据行
 * 若上一行是 **xxx** 或 '''xxx'''，作为 |+ caption
 */
function mdTableToWiki(md) {
  const lines = md.split('\n')
  const out = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!/^\|[\s\S]*\|?\s*$/.test(line.trim())) {
      out.push(line)
      i++
      continue
    }
    let prevLine = ''
    for (let k = out.length - 1; k >= 0; k--) {
      if (out[k].trim()) {
        prevLine = out[k]
        break
      }
    }
    const captionMatch = prevLine.match(/^['*]{2,3}(.+?)['*]{2,3}\s*$/)
    let tableCaption = ''
    if (captionMatch) {
      tableCaption = captionMatch[1].trim()
      for (let k = out.length - 1; k >= 0; k--) {
        if (out[k].trim()) {
          out.splice(k, 1)
          break
        }
      }
    }
    const tableRows = []
    let alignments = []
    while (i < lines.length && /^\|[\s\S]*\|?\s*$/.test(lines[i].trim())) {
      const parts = lines[i]
        .trim()
        .split('|')
        .map((c) => c.trim())
      if (parts[0] === '') parts.shift()
      if (parts[parts.length - 1] === '') parts.pop()
      if (parts.every((c) => /^[-:\s]+$/.test(c))) {
        alignments = parts.map(parseMdAlign)
        i++
        continue
      }
      tableRows.push(parts)
      i++
    }
    if (tableRows.length === 0) {
      out.push(line)
      i++
      continue
    }
    const colCount = Math.max(...tableRows.map((r) => r.length))
    if (alignments.length === 0) alignments = Array(colCount).fill('left')
    const pad = (arr) => {
      const a = [...arr]
      while (a.length < colCount) a.push('')
      return a
    }
    const escapePipe = (s) => (s || '').replace(/\|/g, '&#124;')
    const formatCell = (text, colIdx) => {
      const align = alignments[colIdx] || 'left'
      if (align === 'left') return escapePipe(text)
      return `style="text-align:${align}" | ${escapePipe(text)}`
    }
    const wikiRows = tableRows.map((r) => {
      const padded = pad(r)
      return padded
        .map((c, ci) => formatCell(c, ci))
        .join(' || ')
    })
    const captionLine = tableCaption ? `|+ ${tableCaption}\n` : ''
    const wiki = `{| class="wikitable"\n${captionLine}|-\n| ${wikiRows.join('\n|-\n| ')}\n|}`
    out.push(wiki)
  }
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
  s = mdTableToWiki(s)
  s = mdRestoreMathPlaceholders(s, mathList)
  return mdRestoreCodePlaceholders(s, codeList)
}
