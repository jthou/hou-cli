import { describe, it, expect } from 'vitest'
import { mdToWiki, wikiToMd } from './wikiMdConvert.js'

describe('wikiMdConvert math $$', () => {
  it('mdToWiki keeps block $$ on own lines', () => {
    const md = `$$\n` +
      `x_i = \\\\left( x_i^{(1)}, x_i^{(2)}, \\\\cdots, x_i^{(n)} \\\\right)^{\\\\mathrm{T}}\n` +
      `$$\n`
    const out = mdToWiki(md)
    expect(out).toContain('$$\n')
    expect(out).toContain('\n$$')
    expect(out).toContain('x_i')
  })

  it('wikiToMd does not collapse $$ to single $ in replacement', () => {
    const wiki = `before\n<math display="block">x_i=1</math>\nafter\n`
    const md = wikiToMd(wiki)
    expect(md).toContain('$$')
    expect(md).toContain('x_i=1')
  })
})

