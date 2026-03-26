/**
 * Markdown → HTML 核心转换（纯函数，无 DOM/网络依赖，便于单元测试）。
 * 流程：围栏代码块 / 行内反引号占位 → 提取 $$ 与 $ 内 TeX（避免 marked breaks 把公式换行变成 &lt;br&gt;，导致仅依赖 DOM 的 KaTeX auto-render 无法识别整块矩阵）
 * → marked 解析（块级节点带 data-md-line 源码行，供编辑/预览滚动对齐）→ 还原代码 → katex.renderToString 注入 → 空列表项过滤。
 * 公众号样式注入、公式转图等由 mdToHtml.js 上层处理。
 */
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { getMarkdownLineMarked } from './markdownLineMarked.js'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/** 占位符：HTML 注释，marked 会原样保留，便于在 HTML 阶段替换 */
const fenceComment = (i) => `\n\n<!--hou_fence_${i}-->\n\n`
const inlineCodeComment = (i) => `<!--hou_inline_code_${i}-->`
const katexDisplayComment = (i) => `\n\n<!--hou_katex_d_${i}-->\n\n`
const katexInlineComment = (i) => `<!--hou_katex_i_${i}-->`

/**
 * 将 ``` 围栏代码块替换为 HTML 注释占位，避免块内 `$` 被当作公式；保留完整围栏字符串供后续 marked 解析。
 * @param {string} md
 * @returns {{ md: string, fences: string[] }}
 */
function protectFencedCode(md) {
  const fences = []
  const out = md.replace(/```[\s\S]*?```/g, (full) => {
    const i = fences.length
    fences.push(full)
    return fenceComment(i)
  })
  return { md: out, fences }
}

/**
 * 行内反引号代码 `...`（不含换行）占位，避免其中 `$x$` 被当作公式。
 * @param {string} md
 * @returns {{ md: string, inlineCodes: string[] }}
 */
function protectInlineCode(md) {
  const inlineCodes = []
  const out = md.replace(/`[^`\n]+`/g, (full) => {
    const i = inlineCodes.length
    inlineCodes.push(full)
    return inlineCodeComment(i)
  })
  return { md: out, inlineCodes }
}

/**
 * 在 HTML 中还原围栏为 marked 解析结果（pre/code）。
 * @param {string} html
 * @param {string[]} fences
 */
function restoreFencedCodeInHtml(html, fences) {
  let out = html
  fences.forEach((fence, i) => {
    const rendered = marked.parse(fence)
    const chunk = typeof rendered === 'string' ? rendered : String(rendered)
    const re = new RegExp(`<!--hou_fence_${i}-->`, 'g')
    out = out.replace(re, chunk)
  })
  return out
}

/**
 * 在 HTML 中还原行内代码占位为 <code>（去掉 marked 可能包的外层 <p>）。
 * @param {string} html
 * @param {string[]} inlineCodes
 */
function restoreInlineCodeInHtml(html, inlineCodes) {
  let out = html
  inlineCodes.forEach((raw, i) => {
    const rendered = marked.parse(raw)
    let chunk = typeof rendered === 'string' ? rendered : String(rendered)
    chunk = chunk.replace(/^<p>\s*|\s*<\/p>\s*$/gi, '').trim()
    const re = new RegExp(`<!--hou_inline_code_${i}-->`, 'g')
    out = out.replace(re, chunk)
  })
  return out
}

/**
 * 提取 $$...$$ 为占位注释（先于行内 $ 处理）。
 * @param {string} md
 * @returns {{ md: string, display: string[] }}
 */
function extractDisplayMath(md) {
  const display = []
  const out = md.replace(/\$\$([\s\S]*?)\$\$/g, (full, body) => {
    const t = (body || '').trim()
    if (!t) return full
    const i = display.length
    display.push(t)
    return katexDisplayComment(i)
  })
  return { md: out, display }
}

/**
 * 提取单行 $...$（不含换行），避免与 $$ 冲突。
 * @param {string} md
 * @returns {{ md: string, inline: string[] }}
 */
function extractInlineMath(md) {
  const inline = []
  const out = md.replace(/\$([^$\n]+?)\$/g, (full, body) => {
    const t = (body || '').trim()
    if (!t) return full
    const i = inline.length
    inline.push(t)
    return katexInlineComment(i)
  })
  return { md: out, inline }
}

function renderKatexDisplay(tex) {
  try {
    return katex.renderToString(tex, {
      displayMode: true,
      throwOnError: false,
      strict: false,
    })
  } catch {
    return `<span class="hou-katex-error" title="display math">[公式渲染失败]</span>`
  }
}

function renderKatexInline(tex) {
  try {
    return katex.renderToString(tex, {
      displayMode: false,
      throwOnError: false,
      strict: false,
    })
  } catch {
    return `<span class="hou-katex-error" title="inline math">[公式]</span>`
  }
}

function applyKatexPlaceholders(html, display, inline) {
  let out = html
  display.forEach((tex, i) => {
    const re = new RegExp(`<!--hou_katex_d_${i}-->`, 'g')
    out = out.replace(re, renderKatexDisplay(tex))
  })
  inline.forEach((tex, i) => {
    const re = new RegExp(`<!--hou_katex_i_${i}-->`, 'g')
    out = out.replace(re, renderKatexInline(tex))
  })
  return out
}

/**
 * 移除 HTML 中的空列表项（如 <li></li>、<li> </li>、<li><br></li>、<li><p></p></li>），避免公众号显示空 bullet。
 * @param {string} html - HTML 字符串
 * @returns {string} 移除空 li 后的 HTML
 */
export function removeEmptyListItems(html) {
  if (typeof html !== 'string') return html
  return html.replace(/<li(?:\s[^>]*)?>(\s|&nbsp;|<br\s*\/?>|<p>\s*<\/p>)*<\/li>/gi, '')
}

/**
 * Markdown 转 HTML 核心逻辑（数学公式 KaTeX 预渲染 + marked 解析 + 空列表项过滤）。
 * @param {string} md - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function mdToHtmlCore(md) {
  if (md == null || typeof md !== 'string') return ''
  const trimmed = md.trim()
  if (!trimmed) return ''

  let s = trimmed
  const { md: w1, fences } = protectFencedCode(s)
  const { md: w2, inlineCodes } = protectInlineCode(w1)
  const { md: w3, display } = extractDisplayMath(w2)
  const { md: w4, inline } = extractInlineMath(w3)

  let out = getMarkdownLineMarked().parse(w4)
  out = typeof out === 'string' ? out : String(out)
  out = restoreFencedCodeInHtml(out, fences)
  out = applyKatexPlaceholders(out, display, inline)
  out = restoreInlineCodeInHtml(out, inlineCodes)
  return removeEmptyListItems(out)
}
