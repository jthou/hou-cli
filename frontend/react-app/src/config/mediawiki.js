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
