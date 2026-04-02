/**
 * MediaWiki 前端配置：所有指向本站 Wiki 的链接均使用此 base，页面名做 URL 编码后拼接。
 */
export const MEDIAWIKI_BASE_URL = 'http://www.jthou.com/mediawiki'

/**
 * 根据页面标题生成 MediaWiki 页面实际链接（标题做 HTML/URL 转义）。
 * @param {string} pageTitle - 页面标题
 * @returns {string} 完整 URL，例如 http://www.jthou.com/mediawiki/index.php?title=Page_Name
 */
export function getMediaWikiPageUrl(pageTitle) {
  if (!pageTitle || typeof pageTitle !== 'string') return ''
  const base = MEDIAWIKI_BASE_URL.replace(/\/$/, '')
  // MediaWiki 常用：空格用下划线，再对整体做 encodeURIComponent
  const encoded = encodeURIComponent(pageTitle.trim().replace(/ /g, '_'))
  return `${base}/index.php?title=${encoded}`
}

/**
 * 与本机 gvim-protocol-handler / GvimService 约定一致：hou-gvim://mediawiki?title=...
 * @param {string} pageTitle - 词条标题（原始文本，非 URL 形式）
 * @returns {string}
 */
export function getHouGvimMediawikiUrl(pageTitle) {
  if (!pageTitle || typeof pageTitle !== 'string') return ''
  const t = pageTitle.trim()
  if (!t) return ''
  return `hou-gvim://mediawiki?title=${encodeURIComponent(t)}`
}

/**
 * 判断 URL 是否指向本站 MediaWiki 页面，并解析出页面标题。
 * 支持 /index.php/Page_title、/index.php?title=Page、/wiki/Page_title 等格式。
 * @param {string} href - 链接 href（可相对或绝对）
 * @param {string} [baseUrl] - Wiki 基础 URL，如 http://www.jthou.com/mediawiki
 * @returns {string|null} 页面标题，非本站链接返回 null
 */
export function parseWikiPageTitleFromUrl(href, baseUrl) {
  if (!href || typeof href !== 'string') return null
  const base = (baseUrl || MEDIAWIKI_BASE_URL).replace(/\/$/, '')
  try {
    const url = href.startsWith('http') ? new URL(href) : new URL(href, base)
    const baseParsed = new URL(base)
    if (url.host.toLowerCase() !== baseParsed.host.toLowerCase()) return null
    const pathLower = url.pathname.toLowerCase()
    const basePath = baseParsed.pathname.replace(/\/$/, '').toLowerCase()
    if (!basePath || !pathLower.startsWith(basePath)) return null
    const idxPhp = url.pathname.match(/\/index\.php\/([^?#]+)/i)
    if (idxPhp) return decodeURIComponent(idxPhp[1].replace(/_/g, ' '))
    const titleParam = url.searchParams.get('title')
    if (titleParam) return decodeURIComponent(titleParam.replace(/_/g, ' '))
    const wikiMatch = url.pathname.match(/\/wiki\/([^?#]+)/i)
    if (wikiMatch) return decodeURIComponent(wikiMatch[1].replace(/_/g, ' '))
    return null
  } catch {
    return null
  }
}
