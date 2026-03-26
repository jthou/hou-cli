import { describe, it, expect } from 'vitest'
import {
  extractMarkdownImages,
  extractMaterializedImagesFromHtml,
  mergeDownloadedImagesByUrl,
  materializedMappingToImageEntries,
  mergeImageEntries,
  resolveOriginalUrlForMaterializedUrl,
  materializedUrlsFromMapping,
} from './markdownImages'

describe('extractMarkdownImages', () => {
  it('dedupes by url and keeps order', () => {
    const md = '![a](https://x/1.png) x ![b](https://x/2.png) ![a2](https://x/1.png)'
    expect(extractMarkdownImages(md)).toEqual([
      { alt: 'a', url: 'https://x/1.png' },
      { alt: 'b', url: 'https://x/2.png' },
    ])
  })

  it('returns empty for no images', () => {
    expect(extractMarkdownImages('# hi')).toEqual([])
  })
})

describe('extractMaterializedImagesFromHtml', () => {
  it('collects inline-static src and resolves relative', () => {
    const html =
      '<p><img src="/api/web-reader/inline-static/abc.png" /></p>'
    const r = extractMaterializedImagesFromHtml(html, 'https://x.com')
    expect(r).toEqual([{ alt: '', url: 'https://x.com/api/web-reader/inline-static/abc.png' }])
  })

  it('ignores data urls and external src', () => {
    const html = '<img src="data:image/png;base64,xx"/><img src="https://cdn/x.jpg"/>'
    expect(extractMaterializedImagesFromHtml(html, 'https://x.com')).toEqual([])
  })
})

describe('mergeDownloadedImagesByUrl', () => {
  it('dedupes by url with md first', () => {
    const a = [{ alt: 'm', url: 'https://a/1.png' }]
    const b = [{ alt: '', url: 'https://a/1.png' }, { alt: '', url: 'https://a/2.png' }]
    expect(mergeDownloadedImagesByUrl(a, b)).toEqual([
      { alt: 'm', url: 'https://a/1.png' },
      { alt: '', url: 'https://a/2.png' },
    ])
  })
})

describe('materializedMappingToImageEntries', () => {
  it('builds absolute urls from api paths', () => {
    const m = { 'https://cdn/x': '/api/web-reader/inline-static/a.png' }
    expect(materializedMappingToImageEntries(m, 'https://app.com')).toEqual([
      { alt: '插图', url: 'https://app.com/api/web-reader/inline-static/a.png' },
    ])
  })
})

describe('resolveOriginalUrlForMaterializedUrl', () => {
  it('finds original key for local inline-static url', () => {
    const m = { 'https://cdn/x?a=1': '/api/web-reader/inline-static/a.png' }
    const local = 'https://app.com/api/web-reader/inline-static/a.png'
    expect(resolveOriginalUrlForMaterializedUrl(local, m, 'https://app.com')).toBe('https://cdn/x?a=1')
  })

  it('returns undefined when no match', () => {
    expect(resolveOriginalUrlForMaterializedUrl('https://app.com/api/web-reader/inline-static/nope.png', {}, 'https://app.com')).toBeUndefined()
  })
})

describe('materializedUrlsFromMapping', () => {
  it('lists absolute urls', () => {
    const m = { 'https://a/x': '/api/web-reader/inline-static/u.webp' }
    expect(materializedUrlsFromMapping(m, 'https://h.com')).toEqual(['https://h.com/api/web-reader/inline-static/u.webp'])
  })
})

describe('mergeImageEntries', () => {
  it('merges three lists with dedupe', () => {
    expect(
      mergeImageEntries([{ alt: 'a', url: 'https://x/1' }], [{ url: 'https://x/1' }], [{ url: 'https://x/2' }])
    ).toEqual([
      { alt: 'a', url: 'https://x/1' },
      { alt: '', url: 'https://x/2' },
    ])
  })
})
