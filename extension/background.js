/**
 * Hou CLI 网页阅读助手 - Background Service Worker
 * 微信读书：截图 + Qwen-VL OCR；普通网页：DOM 提取
 */

const OVERALL_TIMEOUT_MS = 45000

/** 极简等待 */
function waitForPage() {
  const delay = /weread\.qq\.com/.test(window.location.href) ? 2500 : 1500
  return new Promise((r) => setTimeout(r, delay))
}

function extractContent() {
  const selectors = [
    'article', 'main', '[role="main"]', '.post-content', '.article-body',
    '.content', '#content', '.entry-content', '.post-body', '.article-content',
  ]
  let el = null
  for (const s of selectors) {
    try {
      const candidate = document.querySelector(s)
      if (candidate && (candidate.innerText || candidate.textContent || '').trim().length >= 100) {
        el = candidate
        break
      }
    } catch (_) {}
  }
  el = el || document.body
  let content = (el.innerText || el.textContent || '').trim().slice(0, 500000)
  const path = window.location.pathname || '/'
  const dir = path.endsWith('/') ? path : path.replace(/\/[^/]*$/, '/') || '/'
  const base = window.location.origin + dir
  const toAbsolute = (href) => {
    if (!href || href.startsWith('data:') || href.startsWith('#')) return href
    if (href.startsWith('http')) return href
    if (href.startsWith('//')) return window.location.protocol + href
    if (href.startsWith('/')) return window.location.origin + href
    return base.replace(/\/[^/]*$/, '/') + href
  }
  const stylesheets = []
  document.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
    const href = link.getAttribute('href')
    if (href) stylesheets.push(toAbsolute(href))
  })
  const inlineStyles = []
  document.querySelectorAll('style').forEach((s) => { if (s.textContent) inlineStyles.push(s.textContent) })
  const temp = document.createElement('div')
  temp.innerHTML = el.innerHTML
  temp.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove())
  temp.querySelectorAll('[onclick], [onload], [onerror]').forEach((n) => {
    n.removeAttribute('onclick'); n.removeAttribute('onload'); n.removeAttribute('onerror')
  })
  let html = temp.innerHTML.slice(0, 2000000)
  let fullPageHtml = ''
  try {
    const doc = document.documentElement.cloneNode(true)
    doc.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove())
    doc.querySelectorAll('[onclick], [onload], [onerror]').forEach((n) => {
      n.removeAttribute('onclick'); n.removeAttribute('onload'); n.removeAttribute('onerror')
    })
    fullPageHtml = doc.outerHTML.slice(0, 3000000)
  } catch (_) {}
  return {
    title: document.title || '',
    content,
    html: html || (content ? '<p>' + String(content).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>' : ''),
    fullPageHtml: fullPageHtml || html || '',
    baseUrl: base,
    stylesheets,
    inlineStyles,
    url: window.location.href,
  }
}

const MAX_SCREENSHOTS = 30
const SCROLL_PAUSE_MS = 600

/** 在页面内执行：滚动到指定位置，返回当前滚动信息 */
function scrollToPosition(offsetY) {
  const el = document.scrollingElement || document.documentElement
  el.scrollTop = Math.max(0, offsetY)
  return {
    scrollTop: el.scrollTop,
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
    atBottom: el.scrollTop + el.clientHeight >= el.scrollHeight - 20,
  }
}

/** 微信读书专用：尝试查找实际滚动容器（正文可能在 overflow 的 div 内），失败则用 document */
function scrollToPositionWeread(offsetY) {
  let el = document.scrollingElement || document.documentElement
  try {
    const sel = '[class*="reader"], [class*="chapter"], [class*="content"], [class*="book"], [id*="reader"], main'
    const list = document.querySelectorAll(sel)
    let maxSh = el.scrollHeight
    for (let i = 0; i < Math.min(list.length, 30); i++) {
      const c = list[i]
      if (!c || !c.scrollHeight) continue
      const s = window.getComputedStyle(c)
      const oy = s.overflowY || s.overflow
      if ((oy === 'auto' || oy === 'scroll') && c.scrollHeight > c.clientHeight + 100 && c.scrollHeight > maxSh) {
        el = c
        maxSh = c.scrollHeight
      }
    }
  } catch (_) {}
  el.scrollTop = Math.max(0, offsetY)
  return {
    scrollTop: el.scrollTop,
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
    atBottom: el.scrollTop + el.clientHeight >= el.scrollHeight - 20,
  }
}

/** 微信读书：长页面分屏截图，OCR 由前端分批完成 */
async function fetchWereadScreenshot(url, createdByUs, tabId) {
  await chrome.tabs.update(tabId, { active: true })
  await new Promise((r) => setTimeout(r, 5000))

  const screenshots = []
  let offsetY = 0
  let prevScrollTop = -1

  for (let i = 0; i < MAX_SCREENSHOTS; i++) {
    const [scrollRes] = await chrome.scripting
      .executeScript({ target: { tabId }, func: scrollToPositionWeread, args: [offsetY] })
      .catch(() => [{}])
    const info = scrollRes?.result

    await new Promise((r) => setTimeout(r, SCROLL_PAUSE_MS))

    let dataUrl
    try {
      dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' })
    } catch (e) {
      if (screenshots.length === 0) {
        throw new Error('截图失败：' + (e?.message || '请确保标签页已完全加载，且未切换窗口'))
      }
      break
    }

    screenshots.push(dataUrl)

    if (!info || info.atBottom) break
    if (info.scrollTop === prevScrollTop) break
    prevScrollTop = info.scrollTop

    offsetY = info.scrollTop + Math.floor(info.clientHeight * 0.85)
    if (offsetY >= info.scrollHeight) break
  }

  const all = await chrome.tabs.query({ currentWindow: true })
  const webReader = all.find((t) => /\/web-reader/.test(t.url || ''))
  if (createdByUs && tabId) {
    if (webReader?.id) await chrome.tabs.update(webReader.id, { active: true }).catch(() => {})
    await chrome.tabs.remove(tabId).catch(() => {})
  } else if (tabId && webReader?.id) {
    await chrome.tabs.update(webReader.id, { active: true }).catch(() => {})
  }

  if (screenshots.length === 0) {
    throw new Error('未能截取到任何画面')
  }

  return {
    title: '微信读书',
    content: '',
    html: '',
    fullPageHtml: '',
    baseUrl: new URL(url).origin + '/',
    stylesheets: [],
    inlineStyles: [],
    url,
    screenshots,
    pendingOcr: true,
  }
}

/** 普通网页：DOM 提取 */
async function runDomExtraction(tabId, url, createdByUs, needLoad) {
  if (needLoad) await new Promise((r) => setTimeout(r, 2500))
  await chrome.scripting.executeScript({ target: { tabId }, func: waitForPage }).catch(() => {})
  const results = await chrome.scripting.executeScript({ target: { tabId }, func: extractContent })
  const data = results?.[0]?.result
  if (createdByUs) await chrome.tabs.remove(tabId).catch(() => {})
  return data
}

/** 主流程：获取或创建 tab，执行提取 */
async function doFetch(url, opts) {
  const { postMessage, requestId, apiBase } = opts
  const isWeread = /weread\.qq\.com/.test(url)
  let tabId = null
  let createdByUs = false

  const respond = (payload) => {
    try {
      postMessage({ type: 'HOU_CLI_FETCH_RESULT', requestId, ...payload })
    } catch (_) {}
  }

  try {
    let needLoad = false
    if (isWeread) {
      const existing = await chrome.tabs.query({ url: '*://weread.qq.com/*' })
      const reqPath = url.split('?')[0]
      const match = existing.find((t) => (t.url || '').split('?')[0] === reqPath)
      if (match) {
        tabId = match.id
      } else if (existing.length > 0) {
        tabId = existing[0].id
        await chrome.tabs.update(tabId, { url })
        needLoad = true
      }
    }

    if (!tabId) {
      const tab = await chrome.tabs.create({ url, active: true })
      tabId = tab.id
      createdByUs = true
      needLoad = true
    }

    let data
    if (isWeread) {
      const navigated = needLoad
      if (navigated) await new Promise((r) => setTimeout(r, 3000))
      data = await fetchWereadScreenshot(url, createdByUs, tabId)
    } else {
      data = await runDomExtraction(tabId, url, createdByUs, needLoad)
    }

    if (data && (data.content || data.title || data.html || data.screenshots?.length)) {
      respond({ success: true, data })
    } else {
      respond({ success: false, error: '未能提取到内容' })
    }
  } catch (err) {
    if (tabId && createdByUs) chrome.tabs.remove(tabId).catch(() => {})
    respond({ success: false, error: err?.message || '提取失败' })
  }
}

// Port 长连接：保持 SW 活跃，避免 sendResponse 因 SW 被 kill 而丢失
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'hou-cli-web-reader') return

  port.onMessage.addListener((msg) => {
    if (msg.type !== 'HOU_CLI_FETCH' || !msg.url) return

    const url = (msg.url || '').trim()
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      port.postMessage({
        type: 'HOU_CLI_FETCH_RESULT',
        requestId: msg.requestId,
        success: false,
        error: '无效的 URL',
      })
      return
    }

    const requestId = msg.requestId || 'req-' + Date.now()
    let resolved = false
    const postMessage = (payload) => {
      if (resolved) return
      resolved = true
      clearTimeout(timeout)
      port.postMessage(payload)
    }
    const timeout = setTimeout(() => {
      postMessage({ type: 'HOU_CLI_FETCH_RESULT', requestId, success: false, error: '提取超时，请重试' })
    }, OVERALL_TIMEOUT_MS)

    const apiBase = msg.apiBase || ''
    doFetch(url, { postMessage, requestId, apiBase }).catch(() => {
      postMessage({ type: 'HOU_CLI_FETCH_RESULT', requestId, success: false, error: '提取失败' })
    })
  })
})

// 兼容旧版 sendMessage
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action !== 'fetch' || !msg.url) {
    sendResponse?.({ success: false, error: 'Unknown action' })
    return false
  }

  const url = (msg.url || '').trim()
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    sendResponse({ success: false, error: '无效的 URL' })
    return false
  }

  const requestId = msg.requestId || 'req-' + Date.now()
  let resolved = false
  const postMessage = (payload) => {
    if (resolved) return
    resolved = true
    clearTimeout(timeout)
    sendResponse?.({ success: payload.success, data: payload.data, error: payload.error })
  }
  const timeout = setTimeout(() => {
    postMessage({ success: false, error: '提取超时，请重试' })
  }, OVERALL_TIMEOUT_MS)

  const apiBase = msg.apiBase || ''
  doFetch(url, { postMessage, requestId, apiBase }).catch(() => {
    postMessage({ success: false, error: '提取失败' })
  })

  return true
})
