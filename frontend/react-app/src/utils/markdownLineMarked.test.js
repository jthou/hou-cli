/**
 * 源码行标注
 */
import { describe, it, expect } from 'vitest'
import { attachBlockSourceLines, getMarkdownLineMarked } from './markdownLineMarked.js'

describe('attachBlockSourceLines', () => {
  it('为顶层 token 写入 sourceLine', () => {
    const md = '# T\n\np\n'
    const tokens = getMarkdownLineMarked().lexer(md)
    attachBlockSourceLines(md, tokens)
    const h = tokens.find((t) => t.type === 'heading')
    const p = tokens.find((t) => t.type === 'paragraph')
    expect(h?.sourceLine).toBe(1)
    expect(p?.sourceLine).toBeGreaterThanOrEqual(2)
  })
})

describe('getMarkdownLineMarked', () => {
  it('输出含 data-md-line', () => {
    const html = getMarkdownLineMarked().parse('# Hi\n\nBody.')
    expect(html).toContain('data-md-line="1"')
    expect(html).toContain('data-md-line="3"')
  })
})
