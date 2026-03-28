import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  insertSnippetAtTextareaCursor,
  snippetForMdWiki,
  snippetForWikitext,
  collectMdImagesByAbsoluteUrl,
  markdownHasUploadableImageUrls,
  markdownHasRetryableMwUploadImages,
  batchUploadMarkdownImagesToMediaWiki,
  markBatchUploadFailInMarkdown,
  stripMwBatchUploadFailAltMark,
  MW_BATCH_UPLOAD_FAIL_ALT_MARK,
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

  it('onlyRetryMarked filters to failed-tagged alts', () => {
    const md = `![a](https://x/1.png) ![${MW_BATCH_UPLOAD_FAIL_ALT_MARK}·b](https://x/2.png)`
    expect(collectMdImagesByAbsoluteUrl(md, { onlyRetryMarked: true }).size).toBe(1)
    expect([...collectMdImagesByAbsoluteUrl(md, { onlyRetryMarked: true }).keys()]).toEqual(['https://x/2.png'])
    expect(markdownHasRetryableMwUploadImages(md)).toBe(true)
    expect(markdownHasRetryableMwUploadImages('![ok](https://x/1.png)')).toBe(false)
  })
})

describe('stripMwBatchUploadFailAltMark / markBatchUploadFailInMarkdown', () => {
  it('strips mark and leading middle dot', () => {
    expect(stripMwBatchUploadFailAltMark(`${MW_BATCH_UPLOAD_FAIL_ALT_MARK}·说明`)).toBe('说明')
    expect(stripMwBatchUploadFailAltMark(MW_BATCH_UPLOAD_FAIL_ALT_MARK)).toBe('')
  })

  it('marks failed image alts', () => {
    const out = markBatchUploadFailInMarkdown('![t](https://ex.com/i.jpg)', ['https://ex.com/i.jpg'])
    expect(out).toBe(`![${MW_BATCH_UPLOAD_FAIL_ALT_MARK}·t](https://ex.com/i.jpg)`)
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

  it('on failure writes retry mark into alt', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'boom' }),
    })
    const md = '![cap](https://ex.com/i.jpg)'
    const r = await batchUploadMarkdownImagesToMediaWiki(md)
    expect(r.ok).toBe(0)
    expect(r.fail).toHaveLength(1)
    expect(r.markdown).toContain(MW_BATCH_UPLOAD_FAIL_ALT_MARK)
    expect(r.markdown).toContain('![⚠待重传·cap](https://ex.com/i.jpg)')
  })

  it('onlyRetryMarked batch calls fetch only for marked images', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, filename: 'z.png', wikitext: '[[File:z.png]]' }),
    })
    const md = `![${MW_BATCH_UPLOAD_FAIL_ALT_MARK}](https://a.com/1.png) ![](https://b.com/2.png)`
    await batchUploadMarkdownImagesToMediaWiki(md, { onlyRetryMarked: true })
    expect(global.fetch).toHaveBeenCalledTimes(1)
    expect(JSON.parse(global.fetch.mock.calls[0][1].body).image_url).toBe('https://a.com/1.png')
  })
})
