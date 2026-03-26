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

function ensurePort() {
  if (port) return port
  for (let i = 0; i < 3; i++) {
    try {
      port = chrome.runtime.connect({ name: 'hou-cli-web-reader' })
      port.onDisconnect.addListener(() => {
        try { port = null } catch (_) {}
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
      p.postMessage({ type: 'HOU_CLI_EXPORT_COOKIES', domain: domain || 'youtube.com', requestId: rid })
    } else {
      try {
        chrome.runtime.sendMessage(
          { action: 'export_cookies', domain: domain || 'youtube.com', requestId: rid },
          (r) => {
            try {
              forward(r || { success: false, error: '扩展无响应' })
            } catch (_) {
              forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
            }
          }
        )
      } catch (_) {
        forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
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
      p.postMessage({ type: 'HOU_CLI_FETCH_PDF', url, requestId: rid })
    } else {
      try {
        chrome.runtime.sendMessage({ action: 'fetch_pdf', url }, (r) => {
          try {
            forward(r || { success: false, error: '扩展无响应' })
          } catch (_) {
            forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
          }
        })
      } catch (_) {
        forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
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
    p.postMessage({
      type: 'HOU_CLI_FETCH',
      url,
      requestId,
      apiBase: apiBase || window.location.origin,
      inlineImages: !!inlineImages,
      wereadImagesOnly: !!wereadImagesOnly,
    })
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
              forward({ success: false, error: '扩展无响应，请刷新页面后重试' })
            } else {
              forward(response || { success: false, error: '扩展无响应' })
            }
          } catch (e) {
            forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
          }
        }
      )
    } catch (e) {
      forward({ success: false, error: '扩展已重新加载，请刷新页面后重试' })
    }
  }
})
