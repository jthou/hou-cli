import { describe, it, expect } from 'vitest'
import { extractFirstMarkdownAtxTitle } from './markdownTitle'

describe('extractFirstMarkdownAtxTitle', () => {
  it('returns first ATX heading text', () => {
    expect(extractFirstMarkdownAtxTitle('# 你好\n\n正文')).toBe('你好')
    expect(extractFirstMarkdownAtxTitle('intro\n\n## 二级\n')).toBe('二级')
  })
  it('respects maxLen', () => {
    const long = 'x'.repeat(40)
    expect(extractFirstMarkdownAtxTitle(`# ${long}`, 10).length).toBe(10)
  })
  it('empty when no heading', () => {
    expect(extractFirstMarkdownAtxTitle('plain')).toBe('')
  })
})
