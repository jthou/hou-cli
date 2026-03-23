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
