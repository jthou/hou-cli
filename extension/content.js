/**
 * Hou CLI 网页阅读助手 - Content Script
 * 使用 Port 长连接与 background 通信，避免 sendResponse 因 SW 被 kill 而丢失
 */

window.__HOU_CLI_EXTENSION_LOADED = true

let port = null

// 扩展重新加载后，Chrome 调用 Port 回调时可能抛出，需全局捕获避免控制台报错
window.addEventListener('error', (e) => {
  if (e.message && String(e.message).includes('Extension context invalidated')) {
    e.stopImmediatePropagation()
    e.preventDefault()
    return true
  }
})
window.addEventListener('unhandledrejection', (e) => {
  const m = e.reason && (e.reason.message || String(e.reason))
  if (m && String(m).includes('Extension context invalidated')) {
    e.preventDefault()
  }
})

function extensionContextAlive() {
  try {
    return !!(chrome.runtime && chrome.runtime.id)
  } catch (_) {
    return false
  }
}

/** 将 runtime.lastError / 抛错英文信息换成对用户可读的中文（避免页面直接展示 Extension context invalidated） */
function humanizeExtensionError(raw) {
  const s = String(raw || '')
  if (
    s.includes('Extension context invalidated') ||
    s.includes('message port closed') ||
    /Receiving end does not exist/i.test(s)
  ) {
    return '扩展已重新加载或更新，请刷新本页后重试'
  }
  return s.trim() || '扩展通信失败，请刷新本页后重试'
}

function ensurePort() {
  if (!extensionContextAlive()) {
    try {
      port = null
    } catch (_) {}
    return null
  }
  if (port) return port
  for (let i = 0; i < 3; i++) {
    try {
      port = chrome.runtime.connect({ name: 'hou-cli-web-reader' })
      port.onDisconnect.addListener(() => {
        try {
          port = null
        } catch (_) {}
      })
      return port
    } catch (_) {
      port = null
    }
  }
  return null
}

// 页面加载时预连接，确保 Port 就绪
try {
  ensurePort()
} catch (_) {
  port = null
}

window.addEventListener('message', (event) => {
  if (event.data?.type === 'HOU_CLI_PING') {
    window.postMessage({ type: 'HOU_CLI_PONG' }, '*')
    return
  }
  if (event.data?.type === 'HOU_CLI_EXPORT_COOKIES') {
    const { domain, requestId } = event.data
    const rid = requestId || 'cookies-' + Date.now()
    const forward = (res) => {
      window.postMessage(
        { type: 'HOU_CLI_EXPORT_COOKIES_RESULT', requestId: rid, success: res.success, content: res.content, error: res.error },
        '*'
      )
    }
    const p = ensurePort()
    if (p) {
      const onResult = (msg) => {
        if (msg.type !== 'HOU_CLI_EXPORT_COOKIES_RESULT' || msg.requestId !== rid) return
        try { p.onMessage.removeListener(onResult) } catch (_) {}
        forward(msg)
      }
      p.onMessage.addListener(onResult)
      try {
        p.postMessage({ type: 'HOU_CLI_EXPORT_COOKIES', domain: domain || 'youtube.com', requestId: rid })
      } catch (e) {
        try { p.onMessage.removeListener(onResult) } catch (_) {}
        port = null
        forward({ success: false, error: humanizeExtensionError(e?.message || e), content: undefined })
      }
    } else {
      try {
        chrome.runtime.sendMessage(
          { action: 'export_cookies', domain: domain || 'youtube.com', requestId: rid },
          (r) => {
            try {
              if (chrome.runtime?.lastError) {
                forward({
                  success: false,
                  error: humanizeExtensionError(chrome.runtime.lastError.message),
                  content: undefined,
                })
                return
              }
              forward(r || { success: false, error: '扩展无响应' })
            } catch (_) {
              forward({ success: false, error: humanizeExtensionError(''), content: undefined })
            }
          }
        )
      } catch (_) {
        forward({ success: false, error: humanizeExtensionError(''), content: undefined })
      }
    }
    return
  }
  if (event.data?.type === 'HOU_CLI_FETCH_PDF' && event.data?.url) {
    const { url, requestId } = event.data
    const rid = requestId || 'pdf-' + Date.now()
    const forward = (res) => {
      window.postMessage(
        { type: 'HOU_CLI_FETCH_PDF_RESULT', requestId: rid, success: res.success, base64: res.base64, error: res.error },
        '*'
      )
    }
    const p = ensurePort()
    if (p) {
      const onResult = (msg) => {
        if (msg.type !== 'HOU_CLI_FETCH_PDF_RESULT' || msg.requestId !== rid) return
        try { p.onMessage.removeListener(onResult) } catch (_) {}
        forward(msg)
      }
      p.onMessage.addListener(onResult)
      try {
        p.postMessage({ type: 'HOU_CLI_FETCH_PDF', url, requestId: rid })
      } catch (e) {
        try { p.onMessage.removeListener(onResult) } catch (_) {}
        port = null
        forward({ success: false, error: humanizeExtensionError(e?.message || e), base64: undefined })
      }
    } else {
      try {
        chrome.runtime.sendMessage({ action: 'fetch_pdf', url }, (r) => {
          try {
            if (chrome.runtime?.lastError) {
              forward({
                success: false,
                error: humanizeExtensionError(chrome.runtime.lastError.message),
                base64: undefined,
              })
              return
            }
            forward(r || { success: false, error: '扩展无响应' })
          } catch (_) {
            forward({ success: false, error: humanizeExtensionError(''), base64: undefined })
          }
        })
      } catch (_) {
        forward({ success: false, error: humanizeExtensionError(''), base64: undefined })
      }
    }
    return
  }
  if (event.data?.type === 'HOU_CLI_REFETCH_IMAGES') {
    const { imageUrls, pageUrl } = event.data
    const requestId = event.data.requestId || 'refetch-' + Date.now()
    if (!Array.isArray(imageUrls) || !imageUrls.length || !(pageUrl || '').trim().startsWith('http')) return

    const forward = (msg) => {
      window.postMessage(
        {
          type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
          requestId: msg.requestId || requestId,
          success: msg.success,
          data: msg.data,
          error: msg.error,
        },
        '*'
      )
    }

    const p = ensurePort()
    if (p) {
      const onResult = (msg) => {
        if (msg.type !== 'HOU_CLI_REFETCH_IMAGES_RESULT' || msg.requestId !== requestId) return
        try {
          p.onMessage.removeListener(onResult)
          p.onDisconnect.removeListener(onDisconnect)
        } catch (_) {}
        forward(msg)
      }
      const onDisconnect = () => {
        port = null
        forward({ type: 'HOU_CLI_REFETCH_IMAGES_RESULT', requestId, success: false, error: '扩展连接已断开，请刷新页面后重试' })
      }
      p.onMessage.addListener(onResult)
      p.onDisconnect.addListener(onDisconnect)
      try {
        p.postMessage({ type: 'HOU_CLI_REFETCH_IMAGES', requestId, imageUrls, pageUrl: (pageUrl || '').trim() })
      } catch (e) {
        try {
          p.onMessage.removeListener(onResult)
          p.onDisconnect.removeListener(onDisconnect)
        } catch (_) {}
        port = null
        forward({
          type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
          requestId,
          success: false,
          error: humanizeExtensionError(e?.message || e),
        })
      }
    } else {
      try {
        chrome.runtime.sendMessage(
          {
            action: 'refetch_images',
            requestId,
            imageUrls,
            pageUrl: (pageUrl || '').trim(),
          },
          (response) => {
            try {
              if (chrome.runtime?.lastError) {
                forward({
                  type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
                  requestId,
                  success: false,
                  error: humanizeExtensionError(chrome.runtime.lastError.message),
                })
              } else {
                forward({
                  type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
                  requestId,
                  success: response?.success,
                  data: response?.data,
                  error: response?.error,
                })
              }
            } catch (_) {
              forward({
                type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
                requestId,
                success: false,
                error: humanizeExtensionError(''),
              })
            }
          }
        )
      } catch (_) {
        forward({
          type: 'HOU_CLI_REFETCH_IMAGES_RESULT',
          requestId,
          success: false,
          error: humanizeExtensionError(''),
        })
      }
    }
    return
  }
  if (event.data?.type !== 'HOU_CLI_FETCH' || !event.data?.url) return
  const { url, requestId, apiBase, inlineImages, wereadImagesOnly } = event.data

  const forward = (res) => {
    window.postMessage(
      { type: 'HOU_CLI_FETCH_RESULT', requestId, success: res.success, data: res.data, error: res.error },
      '*'
    )
  }

  const p = ensurePort()
  if (p) {
    const onResult = (msg) => {
      if (msg.type !== 'HOU_CLI_FETCH_RESULT' || msg.requestId !== requestId) return
      try {
        p.onMessage.removeListener(onResult)
        p.onDisconnect.removeListener(onDisconnect)
      } catch (_) {}
      forward(msg)
    }
    const onDisconnect = () => {
      // 扩展上下文失效时，任何对 p（Port）的访问都会抛错，故不调用 removeListener
      port = null
      forward({ success: false, error: '扩展连接已断开，请刷新页面后重试' })
    }
    p.onMessage.addListener(onResult)
    p.onDisconnect.addListener(onDisconnect)
    try {
      p.postMessage({
        type: 'HOU_CLI_FETCH',
        url,
        requestId,
        apiBase: apiBase || window.location.origin,
        inlineImages: !!inlineImages,
        wereadImagesOnly: !!wereadImagesOnly,
      })
    } catch (e) {
      try {
        p.onMessage.removeListener(onResult)
        p.onDisconnect.removeListener(onDisconnect)
      } catch (_) {}
      port = null
      forward({ success: false, error: humanizeExtensionError(e?.message || e) })
    }
  } else {
    // Port 失败时回退到 sendMessage：至少能触发跳转，长任务回调可能超时
    try {
      chrome.runtime.sendMessage(
        {
          action: 'fetch',
          url,
          requestId,
          apiBase: apiBase || window.location.origin,
          inlineImages: !!inlineImages,
          wereadImagesOnly: !!wereadImagesOnly,
        },
        (response) => {
          try {
            if (chrome.runtime?.lastError) {
              forward({
                success: false,
                error: humanizeExtensionError(chrome.runtime.lastError.message),
              })
              return
            }
            forward(response || { success: false, error: '扩展无响应' })
          } catch (e) {
            forward({ success: false, error: humanizeExtensionError(e?.message || e) })
          }
        }
      )
    } catch (e) {
      forward({ success: false, error: humanizeExtensionError(e?.message || e) })
    }
  }
})

/** www.jthou.com/mediawiki：浮动链接 hou-gvim:// → 本机协议处理 / GvimService（见 gvim-protocol-handler） */
;(function injectJthouMediaWikiGvimButton() {
  const ATTR = 'data-hou-cli-gvim-btn'
  function hostOk(hostname) {
    const h = (hostname || '').toLowerCase()
    return h === 'www.jthou.com' || h === 'jthou.com'
  }
  function houGvimMediawikiUrl(pageTitle) {
    return 'hou-gvim://mediawiki?title=' + encodeURIComponent(pageTitle)
  }
  function mediaWikiTitleFromLocation(href) {
    try {
      const u = new URL(href)
      if (!hostOk(u.hostname)) return null
      if (!/\/mediawiki(\/|$)/i.test(u.pathname)) return null
      const q = u.searchParams.get('title')
      if (q) return q.replace(/\+/g, ' ').trim() || null
      const lower = u.pathname
      const idx = lower.toLowerCase().indexOf('index.php/')
      if (idx !== -1) {
        const rest = u.pathname.slice(idx + 'index.php/'.length)
        if (rest) {
          try {
            return decodeURIComponent(rest.replace(/\+/g, '%20'))
          } catch (_) {
            return rest
          }
        }
      }
      const wm = u.pathname.match(/\/wiki\/(.+)$/i)
      if (wm) {
        try {
          return decodeURIComponent(wm[1]).replace(/_/g, ' ')
        } catch (_) {
          return wm[1].replace(/_/g, ' ')
        }
      }
      return null
    } catch (_) {
      return null
    }
  }
  function mount() {
    if (!document.body || document.documentElement.getAttribute(ATTR)) return
    const title = mediaWikiTitleFromLocation(window.location.href)
    if (!title) return
    document.documentElement.setAttribute(ATTR, '1')
    const a = document.createElement('a')
    a.href = houGvimMediawikiUrl(title)
    a.textContent = '用 gvim 打开'
    a.setAttribute(
      'title',
      '本机已注册 hou-gvim:// 协议时打开 gvim（仓库 gvim-protocol-handler；与 GvimService 同源）。词条：' + title
    )
    Object.assign(a.style, {
      position: 'fixed',
      right: '14px',
      bottom: '14px',
      zIndex: '2147483646',
      padding: '8px 14px',
      fontSize: '13px',
      fontFamily: 'system-ui, sans-serif',
      cursor: 'pointer',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,.2)',
      background: 'rgba(22,22,40,.94)',
      color: '#eee',
      boxShadow: '0 2px 12px rgba(0,0,0,.35)',
      textDecoration: 'none',
      display: 'inline-block',
    })
    document.body.appendChild(a)
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
  else mount()
})()
