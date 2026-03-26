/**
 * 从 Markdown 提取图片引用，按出现顺序、按 URL 去重。
 * @param {string} markdown
 * @returns {{ alt: string, url: string }[]}
 */
export function extractMarkdownImages(markdown) {
  const md = markdown || ''
  const re = /!\[([^\]]*)\]\(([^)]+)\)/g
  const seen = new Set()
  const out = []
  let m
  while ((m = re.exec(md)) !== null) {
    const alt = (m[1] || '').trim()
    const url = (m[2] || '').trim().replace(/\s+$/, '')
    if (!url || seen.has(url)) continue
    seen.add(url)
    out.push({ alt, url })
  }
  return out
}

/**
 * 从已替换为站内路径的 HTML 中提取插图（扩展拉图 + materialize 后的 /api/web-reader/inline-static/）
 * 用于 Markdown 转换未带出 ![](url) 时的兜底展示。
 * @param {string} html
 * @param {string} origin - 如 https://app.example.com
 */
export function extractMaterializedImagesFromHtml(html, origin = '') {
  const h = html || ''
  const re = /<img\b[^>]*\bsrc\s*=\s*(["'])([^"']+)\1/gi
  const seen = new Set()
  const out = []
  let m
  while ((m = re.exec(h)) !== null) {
    let url = (m[2] || '').trim().replace(/&amp;/g, '&')
    if (!url || url.startsWith('data:')) continue
    if (url.startsWith('/')) url = `${origin.replace(/\/$/, '')}${url}`
    if (!url.includes('/api/web-reader/inline-static/')) continue
    if (seen.has(url)) continue
    seen.add(url)
    out.push({ alt: '', url })
  }
  return out
}

/**
 * Markdown 与 HTML 两路合并，按 URL 去重，先 Markdown 顺序再补 HTML 独有项。
 * @param {{ alt: string, url: string }[]} fromMd
 * @param {{ alt: string, url: string }[]} fromHtml
 */
export function mergeDownloadedImagesByUrl(fromMd, fromHtml) {
  return mergeImageEntries(fromMd, fromHtml)
}

/**
 * 合并多路 { alt, url }，按 URL 去重，保留先出现的顺序。
 * @param {...{ alt?: string, url: string }[]} lists
 */
export function mergeImageEntries(...lists) {
  const seen = new Set()
  const out = []
  for (const list of lists) {
    for (const item of list || []) {
      const url = (item?.url || '').trim().replace(/&amp;/g, '&')
      if (!url || seen.has(url)) continue
      seen.add(url)
      out.push({ alt: (item.alt || '').trim(), url })
    }
  }
  return out
}

/**
 * materialize-inline-images 返回的 mapping（原 URL → /api/web-reader/inline-static/...）
 * @param {Record<string, string>|null|undefined} mapping
 * @param {string} origin
 */
export function materializedMappingToImageEntries(mapping, origin = '') {
  if (!mapping || typeof mapping !== 'object') return []
  const base = String(origin || '').replace(/\/$/, '')
  const entries = []
  for (const path of Object.values(mapping)) {
    const p = String(path || '').trim()
    if (!p || !p.includes('/api/web-reader/inline-static/')) continue
    const full = /^https?:\/\//i.test(p) ? p : `${base}${p.startsWith('/') ? p : `/${p}`}`
    entries.push({ alt: '插图', url: full })
  }
  return mergeImageEntries(entries)
}

/** 与 extractMaterializedImagesFromHtml / 合并列表里的 url 对齐（去 &amp;、trim） */
function normalizeMaterializedImgUrl(u) {
  return String(u || '').trim().replace(/&amp;/g, '&')
}

/**
 * 根据 materialize 返回的 mapping（原图 URL → /api/web-reader/inline-static/...）反查某张已落盘图的原始地址。
 * @param {string} localFullUrl - 本站完整插图 URL
 * @param {Record<string, string>|null|undefined} mapping
 * @param {string} origin
 * @returns {string|undefined}
 */
export function resolveOriginalUrlForMaterializedUrl(localFullUrl, mapping, origin = '') {
  const want = normalizeMaterializedImgUrl(localFullUrl)
  if (!want || !mapping || typeof mapping !== 'object') return undefined
  const base = String(origin || '').replace(/\/$/, '')
  for (const [orig, path] of Object.entries(mapping)) {
    const p = String(path || '').trim()
    if (!p || !orig) continue
    const full = /^https?:\/\//i.test(p) ? p : `${base}${p.startsWith('/') ? p : `/${p}`}`
    if (normalizeMaterializedImgUrl(full) === want) return orig
  }
  return undefined
}

/**
 * 合并多次 materialize 的 mapping（后写入覆盖同 key）。
 * @param {...Record<string, string>|null|undefined} maps
 * @returns {Record<string, string>}
 */
export function mergeInlineMaterializedMappings(...maps) {
  const out = {}
  for (const m of maps) {
    if (!m || typeof m !== 'object') continue
    Object.assign(out, m)
  }
  return out
}

/**
 * 由 mapping 生成与历史字段 `materializedImageUrls` 一致的绝对 URL 列表（去重保序）。
 */
export function materializedUrlsFromMapping(mapping, origin = '') {
  return materializedMappingToImageEntries(mapping, origin).map((e) => e.url)
}
