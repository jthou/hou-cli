/**
 * MediaWiki：编辑框粘贴图片 → 上传 → 在光标处插入引用。
 * 时间：2026-03-13；理由：与后端 /mediawiki/upload-image-file（内容哈希命名）配合；方法：clipboard image/FormData + 文本区间插入。
 */

/**
 * @param {ClipboardEvent} pasteEvent
 * @returns {File|null}
 */
export function getClipboardImageFile(pasteEvent) {
  const items = pasteEvent.clipboardData?.items
  if (!items?.length) return null
  for (let i = 0; i < items.length; i++) {
    const it = items[i]
    if (it.kind === 'file' && it.type && it.type.startsWith('image/')) {
      const f = it.getAsFile()
      if (f) return f
    }
  }
  return null
}

/**
 * @param {string} value - 全文
 * @param {number} start
 * @param {number} end
 * @param {string} snippet
 * @returns {{ nextValue: string, caret: number }}
 */
export function insertSnippetAtTextareaCursor(value, start, end, snippet) {
  const v = value ?? ''
  const s = Math.max(0, Math.min(start, v.length))
  const e = Math.max(s, Math.min(end, v.length))
  const before = v.slice(0, s)
  const after = v.slice(e)
  const needNl = before.length > 0 && !before.endsWith('\n')
  const pad = needNl ? '\n' : ''
  const nextValue = before + pad + snippet + after
  const caret = (before + pad + snippet).length
  return { nextValue, caret }
}

/**
 * Markdown 侧插入：与 mdToWikiWithImages 首段替换一致，最终变为 [[File:文件名]]
 * @param {string} filename - Wiki 上文件名
 */
export function snippetForMdWiki(filename) {
  const f = (filename || '').trim()
  return `![](${f})`
}

/**
 * @param {string} filename
 */
export function snippetForWikitext(filename) {
  const f = (filename || '').trim()
  return `[[File:${f}]]`
}

/**
 * @param {File|Blob} file
 * @returns {Promise<{ success: boolean, filename: string, wikitext: string }>}
 */
export async function uploadMediaWikiImageFile(file) {
  const form = new FormData()
  const name = file instanceof File && file.name ? file.name : 'paste.png'
  form.append('file', file, name)
  const res = await fetch('/api/mediawiki/upload-image-file', {
    method: 'POST',
    body: form,
  })
  let data = {}
  try {
    data = await res.json()
  } catch {
    data = {}
  }
  if (!res.ok) {
    const msg = typeof data.detail === 'string' ? data.detail : data.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  if (!data.success || !data.filename) {
    throw new Error(data.detail || '上传失败')
  }
  return data
}

function escapeForMdImgRe(u) {
  return String(u).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** 相对路径 /api/... 转为可交给后端的绝对 URL（inline-static 等） */
export function toAbsoluteImageUrlForMwUpload(url) {
  const u = String(url || '')
    .trim()
    .replace(/\s+$/, '')
    .replace(/&amp;/g, '&')
  if (!u) return null
  if (/^https?:\/\//i.test(u)) return u
  if (u.startsWith('/') && typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${u}`
  }
  return null
}

function wikitextForUploadedFile(filename, alt) {
  const f = (filename || '').trim()
  if (!f) return ''
  const a = String(alt || '')
    .trim()
    .replace(/\|/g, '·')
  if (a) return `[[File:${f}|${a}]]`
  return `[[File:${f}]]`
}

/**
 * 扫描 Markdown 中 ![](url)，按绝对 URL 去重后用于批量上传。
 * @returns {Map<string, { rawUrls: Set<string> }>}
 */
export function collectMdImagesByAbsoluteUrl(markdown) {
  const md = markdown == null ? '' : String(markdown)
  const re = /!\[([^\]]*)\]\(([^)]+)\)/g
  const byAbs = new Map()
  let m
  while ((m = re.exec(md)) !== null) {
    const raw = String(m[2] || '')
      .trim()
      .replace(/\s+$/, '')
      .replace(/&amp;/g, '&')
    const abs = toAbsoluteImageUrlForMwUpload(raw)
    if (!abs) continue
    if (!byAbs.has(abs)) byAbs.set(abs, { rawUrls: new Set() })
    byAbs.get(abs).rawUrls.add(raw)
  }
  return byAbs
}

export function markdownHasUploadableImageUrls(markdown) {
  return collectMdImagesByAbsoluteUrl(markdown).size > 0
}

/**
 * 将正文中所有可上传的 ![](http...) / ![]( /api/...) 逐张 POST /api/mediawiki/upload-image，
 * 并替换为 [[File:…]]（与单张预览上传一致，便于再点「写入 MediaWiki」时走 wikitext）。
 * @param {string} markdown
 * @param {{ onProgress?: (index: number, total: number) => void }} [options]
 * @returns {Promise<{ markdown: string, ok: number, fail: { url: string, error: string }[], total: number }>}
 */
export async function batchUploadMarkdownImagesToMediaWiki(markdown, options = {}) {
  const { onProgress } = options
  const byAbs = collectMdImagesByAbsoluteUrl(markdown)
  const list = [...byAbs.entries()]
  let out = markdown == null ? '' : String(markdown)
  let ok = 0
  const fail = []
  const total = list.length
  for (let i = 0; i < list.length; i += 1) {
    const [absUrl, { rawUrls }] = list[i]
    onProgress?.(i + 1, total)
    try {
      const res = await fetch('/api/mediawiki/upload-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_url: absUrl }),
      })
      let data = {}
      try {
        data = await res.json()
      } catch {
        data = {}
      }
      if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : data.message || `HTTP ${res.status}`)
      }
      const filename = data.filename
      if (!filename) throw new Error(data.detail || '上传成功但缺少 filename')
      for (const raw of rawUrls) {
        const esc = escapeForMdImgRe(raw)
        const imgRe = new RegExp(`!\\[([^\\]]*)\\]\\(${esc}\\)`, 'g')
        out = out.replace(imgRe, (_, capAlt) =>
          wikitextForUploadedFile(filename, (capAlt || '').trim())
        )
      }
      ok += 1
    } catch (e) {
      fail.push({ url: absUrl, error: e?.message || '上传失败' })
    }
  }
  return { markdown: out, ok, fail, total }
}
