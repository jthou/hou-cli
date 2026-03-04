/**
 * 注入到微信读书页面主世界，patch fetch 以捕获 API 响应
 * 需通过 script.src 加载（CSP 允许 chrome-extension://），不能用 inline script
 */
(function () {
  if (window.__HOU_WEREAD_PATCHED) return
  window.__HOU_WEREAD_PATCHED = true
  window.__HOU_WEREAD_CAPTURED = { reviews: [], infos: [], chapters: [], raw: [] }

  const _fetch = window.fetch
  window.fetch = function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '')
    return _fetch.apply(this, args).then(async (res) => {
      const clone = res.clone()
      try {
        if (url.includes('i.weread.qq.com') || url.includes('weread.qq.com')) {
          const ct = res.headers.get('content-type') || ''
          if (ct.includes('json')) {
            const data = await clone.json()
            window.__HOU_WEREAD_CAPTURED.raw.push({ url, data })
          }
        }
      } catch (_) {}
      return res
    })
  }
})()
