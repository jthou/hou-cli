/**
 * 网页阅读 / 微信读书：扩展传来的 inlineImageMap 落盘并替换 HTML 中的原图 URL
 */

/** innerHTML 属性里 & 常序列化为 &amp; */
export function applyInlineImageUrlReplacements(html, mappingEntries, origin) {
  let out = html || ''
  const sorted = [...mappingEntries].sort((a, b) => (b[0] || '').length - (a[0] || '').length)
  for (const [orig, apiPath] of sorted) {
    if (!orig || !apiPath) continue
    const full = `${origin}${apiPath}`
    const variants = []
    const push = (s) => {
      if (s && !variants.includes(s)) variants.push(s)
    }
    push(orig)
    if (orig.includes('&') && !orig.includes('&amp;')) push(orig.replace(/&/g, '&amp;'))
    if (orig.includes('&amp;')) push(orig.replace(/&amp;/g, '&'))
    for (const v of variants) {
      const esc = v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      out = out.replace(new RegExp(esc, 'g'), full)
    }
  }
  return out
}

/**
 * POST materialize-inline-images 并按 mapping 替换 html
 * @returns {{ html: string, mapping: object|null }}
 */
export async function materializeInlineImagesFromMap(html, inlineImageMap, apiOrigin) {
  const h = html || ''
  if (!h || !inlineImageMap || typeof inlineImageMap !== 'object') {
    return { html: h, mapping: null }
  }
  const entries = Object.entries(inlineImageMap)
  if (!entries.length) return { html: h, mapping: null }
  try {
    const res = await fetch(`${apiOrigin}/api/web-reader/materialize-inline-images`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        images: entries.map(([original_url, data_url]) => ({ original_url, data_url })),
      }),
    })
    const jd = await res.json()
    if (!jd.success || !jd.mapping || !Object.keys(jd.mapping).length) {
      return { html: h, mapping: null }
    }
    return {
      html: applyInlineImageUrlReplacements(h, Object.entries(jd.mapping), apiOrigin),
      mapping: jd.mapping,
    }
  } catch (_) {
    return { html: h, mapping: null }
  }
}
