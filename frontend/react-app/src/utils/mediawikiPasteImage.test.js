import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  insertSnippetAtTextareaCursor,
  snippetForMdWiki,
  snippetForWikitext,
  collectMdImagesByAbsoluteUrl,
  markdownHasUploadableImageUrls,
  batchUploadMarkdownImagesToMediaWiki,
} from './mediawikiPasteImage'

describe('insertSnippetAtTextareaCursor', () => {
  it('inserts at start without leading newline', () => {
    const r = insertSnippetAtTextareaCursor('ab', 0, 0, 'X')
    expect(r.nextValue).toBe('Xab')
    expect(r.caret).toBe(1)
  })
  it('adds newline when pasting after non-newline content', () => {
    const r = insertSnippetAtTextareaCursor('line', 4, 4, '[[F]]')
    expect(r.nextValue).toBe('line\n[[F]]')
    expect(r.caret).toBe(10)
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

describe('collectMdImagesByAbsoluteUrl', () => {
  it('dedupes same https URL', () => {
    const md = 'a ![](https://cdn/x.png) b ![](https://cdn/x.png)'
    const m = collectMdImagesByAbsoluteUrl(md)
    expect(m.size).toBe(1)
    expect([...m.get('https://cdn/x.png').rawUrls]).toEqual(['https://cdn/x.png'])
  })

  it('ignores bare filename markdown image', () => {
    const md = '![](img_hash.png)'
    expect(markdownHasUploadableImageUrls(md)).toBe(false)
  })
})

describe('batchUploadMarkdownImagesToMediaWiki', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('replaces markdown after upload', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, filename: 'up.png', wikitext: '[[File:up.png]]' }),
    })
    const md = '![t](https://ex.com/i.jpg)'
    const r = await batchUploadMarkdownImagesToMediaWiki(md)
    expect(r.ok).toBe(1)
    expect(r.fail).toHaveLength(0)
    expect(r.markdown).toBe('[[File:up.png|t]]')
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/mediawiki/upload-image',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ image_url: 'https://ex.com/i.jpg' }),
      })
    )
  })
})
