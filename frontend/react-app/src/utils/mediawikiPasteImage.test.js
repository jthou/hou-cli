import { describe, it, expect } from 'vitest'
import { insertSnippetAtTextareaCursor, snippetForMdWiki, snippetForWikitext } from './mediawikiPasteImage'

describe('insertSnippetAtTextareaCursor', () => {
  it('inserts at start without leading newline', () => {
    const r = insertSnippetAtTextareaCursor('ab', 0, 0, 'X')
    expect(r.nextValue).toBe('Xab')
    expect(r.caret).toBe(1)
  })
  it('adds newline when pasting after non-newline content', () => {
    const r = insertSnippetAtTextareaCursor('line', 4, 4, '[[F]]')
    expect(r.nextValue).toBe('line\n[[F]]')
    expect(r.caret).toBe(9)
  })
  it('replaces selection', () => {
    const r = insertSnippetAtTextareaCursor('hello world', 0, 5, 'X')
    expect(r.nextValue).toBe('X world')
  })
})

describe('snippets', () => {
  it('md uses image syntax with plain filename', () => {
    expect(snippetForMdWiki('img_abc.png')).toBe('![](img_abc.png)')
  })
  it('wiki uses File', () => {
    expect(snippetForWikitext('img_abc.png')).toBe('[[File:img_abc.png]]')
  })
})
