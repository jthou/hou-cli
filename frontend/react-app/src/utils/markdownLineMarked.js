/**
 * 为 Markdown 块级节点写入 data-md-line（1-based 源码行），供编辑区与预览区按「结构」对齐滚动。
 * 使用独立 Marked 实例，不污染全局 marked。
 */
import { Marked } from 'marked'

/** @param {string} md @param {number} idx */
function lineFromCharIndex(md, idx) {
  if (idx <= 0) return 1
  let line = 1
  const end = Math.min(idx, md.length)
  for (let i = 0; i < end; i++) {
    if (md.charCodeAt(i) === 10) line++
  }
  return line
}

/**
 * 为 lexer 产出的顶层 block token 标注 sourceLine（与 md 字符串一致，含占位符阶段）。
 * @param {string} md
 * @param {import('marked').Token[]} tokens
 */
export function attachBlockSourceLines(md, tokens) {
  if (!md || !Array.isArray(tokens)) return
  let pos = 0
  for (const token of tokens) {
    if (!token || token.type === 'space') continue
    const raw = token.raw
    if (!raw) continue
    let idx = md.indexOf(raw, pos)
    if (idx === -1) idx = md.indexOf(raw)
    if (idx === -1) continue
    token.sourceLine = lineFromCharIndex(md, idx)
    pos = idx + raw.length
  }
}

function escAttr(n) {
  const x = Number(n)
  if (!Number.isFinite(x) || x < 0) return '0'
  return String(Math.floor(x))
}

/** @param {string} html @param {string} tag @param {number} line */
function injectLineOnOpenTag(html, tag, line) {
  const re = new RegExp(`<${tag}(\\s|>)`, 'i')
  return html.replace(re, `<${tag} data-md-line="${escAttr(line)}"$1`)
}

const srcRef = { md: '' }

const blockExtensions = [
  {
    name: 'heading',
    renderer(token) {
      const line = token.sourceLine
      if (line == null || line < 1) return false
      const text = this.parser.parseInline(token.tokens)
      return `<h${token.depth} data-md-line="${escAttr(line)}">${text}</h${token.depth}>\n`
    },
  },
  {
    name: 'paragraph',
    renderer(token) {
      const line = token.sourceLine
      if (line == null || line < 1) return false
      const body = this.parser.parseInline(token.tokens)
      return `<p data-md-line="${escAttr(line)}">${body}</p>\n`
    },
  },
  {
    name: 'code',
    renderer(token) {
      const inner = this.parser.options.renderer.code(token.text, token.lang, !!token.escaped)
      const line = token.sourceLine ?? 0
      return injectLineOnOpenTag(inner, 'pre', line)
    },
  },
  {
    name: 'blockquote',
    renderer(token) {
      const body = this.parser.parse(token.tokens)
      const line = token.sourceLine ?? 0
      return `<blockquote data-md-line="${escAttr(line)}">\n${body}</blockquote>\n`
    },
  },
  {
    name: 'list',
    renderer(token) {
      const listToken = token
      const ordered = listToken.ordered
      const start = listToken.start
      const loose = listToken.loose
      let body = ''
      const { renderer } = this.parser
      for (let j = 0; j < listToken.items.length; j++) {
        const item = listToken.items[j]
        const checked = item.checked
        const task = item.task
        let itemBody = ''
        if (item.task) {
          const checkbox = renderer.checkbox(!!checked)
          if (loose) {
            if (item.tokens.length > 0 && item.tokens[0].type === 'paragraph') {
              item.tokens[0].text = checkbox + ' ' + item.tokens[0].text
              if (
                item.tokens[0].tokens &&
                item.tokens[0].tokens.length > 0 &&
                item.tokens[0].tokens[0].type === 'text'
              ) {
                item.tokens[0].tokens[0].text = checkbox + ' ' + item.tokens[0].tokens[0].text
              }
            } else {
              item.tokens.unshift({ type: 'text', text: checkbox + ' ' })
            }
          } else {
            itemBody += checkbox + ' '
          }
        }
        itemBody += this.parser.parse(item.tokens, loose)
        body += renderer.listitem(itemBody, task, !!checked)
      }
      const inner = renderer.list(body, ordered, start)
      const line = token.sourceLine ?? 0
      const tag = ordered ? 'ol' : 'ul'
      return inner.replace(new RegExp(`<${tag}(\\s|>)`, 'i'), `<${tag} data-md-line="${escAttr(line)}"$1`)
    },
  },
  {
    name: 'table',
    renderer(token) {
      const tableToken = token
      let header = ''
      let cell = ''
      const { renderer } = this.parser
      for (let j = 0; j < tableToken.header.length; j++) {
        cell += renderer.tablecell(this.parser.parseInline(tableToken.header[j].tokens), {
          header: true,
          align: tableToken.align[j],
        })
      }
      header += renderer.tablerow(cell)
      let tbody = ''
      for (let j = 0; j < tableToken.rows.length; j++) {
        const row = tableToken.rows[j]
        cell = ''
        for (let k = 0; k < row.length; k++) {
          cell += renderer.tablecell(this.parser.parseInline(row[k].tokens), {
            header: false,
            align: tableToken.align[k],
          })
        }
        tbody += renderer.tablerow(cell)
      }
      const inner = renderer.table(header, tbody)
      const line = token.sourceLine ?? 0
      return injectLineOnOpenTag(inner, 'table', line)
    },
  },
  {
    name: 'hr',
    renderer(token) {
      const line = token.sourceLine ?? 0
      return `<hr data-md-line="${escAttr(line)}" />\n`
    },
  },
]

let _lineMarked = null

/** 带 data-md-line 的 Marked 单例（gfm + breaks） */
export function getMarkdownLineMarked() {
  if (_lineMarked) return _lineMarked
  _lineMarked = new Marked()
  _lineMarked.setOptions({ gfm: true, breaks: true })
  _lineMarked.use({
    hooks: {
      preprocess(md) {
        srcRef.md = md
        return md
      },
      processAllTokens(tokens) {
        attachBlockSourceLines(srcRef.md, tokens)
        return tokens
      },
    },
  })
  _lineMarked.use({ extensions: blockExtensions })
  return _lineMarked
}
