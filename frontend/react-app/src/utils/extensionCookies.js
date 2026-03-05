/**
 * 从 Hou CLI 扩展获取指定域名的 cookies（Netscape 格式）
 * 用于视频下载等需要登录态的场景
 * @param {string} domain - 域名，如 'youtube.com'
 * @param {number} timeoutMs - 超时毫秒
 * @returns {Promise<{ success: boolean, content?: string, error?: string }>}
 */
export function requestCookiesFromExtension(domain = 'youtube.com', timeoutMs = 10000) {
  return new Promise((resolve) => {
    const requestId = 'ext-cookies-' + Date.now()
    const timer = setTimeout(() => {
      window.removeEventListener('message', handler)
      resolve({ success: false, error: '扩展无响应，请确保已安装并启用 Hou CLI 扩展' })
    }, timeoutMs)

    const handler = (e) => {
      if (e.data?.type !== 'HOU_CLI_EXPORT_COOKIES_RESULT' || e.data?.requestId !== requestId) return
      clearTimeout(timer)
      window.removeEventListener('message', handler)
      resolve({
        success: !!e.data.success,
        content: e.data.content,
        error: e.data.error,
      })
    }
    window.addEventListener('message', handler)
    window.postMessage({ type: 'HOU_CLI_EXPORT_COOKIES', domain, requestId }, '*')
  })
}
