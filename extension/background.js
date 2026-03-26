/**
 * Hou CLI 网页阅读助手 - Background Service Worker
 * 微信读书：截图 + Qwen-VL OCR
 * 飞书多维表格：DOM 提取，延长等待 + 专用选择器
 * 普通网页：DOM 提取
 */

const OVERALL_TIMEOUT_MS = 90000  // 90 秒，适配复杂页面（自动展开 + 慢速站点）

/** 页面内：等待 document.readyState === 'complete' 或 window.load，最多 20s */
function waitForPageLoad() {
  return new Promise((resolve) => {
    if (document.readyState === 'complete') {
      resolve()
      return
    }
    const onLoad = () => resolve()
    window.addEventListener('load', onLoad, { once: true })
    setTimeout(() => {
      window.removeEventListener('load', onLoad)
      resolve()
    }, 20000)
  })
}

/** 极简额外等待：SPA  hydration / 飞书等，load 后仍需短暂延迟 */
function waitForPage() {
  const href = window.location.href || ''
  const delay = /weread\.qq\.com/.test(href) ? 2500
    : /feishu\.cn|feishubase\.com/.test(href) ? 3000
    : /blogs\.nvidia\.com|medium\.com|substack\.com|wordpress\.com|blog\./.test(href) ? 2000
    : 800
  return new Promise((r) => setTimeout(r, delay))
}

/** 展开所有隐藏/折叠内容，返回本轮点击数量。在页面内执行（依赖先注入 amazon.js） */
function expandAllHiddenContent() {
  const href = window.location.href || ''
  const amazon = typeof window.__HOU_AMAZON !== 'undefined' ? window.__HOU_AMAZON : null
  let clicked = 0
  if (amazon?.isAmazonUrl?.(href)) {
    clicked += (amazon.loadProductDetailsSection?.() ?? 0)
    clicked += (amazon.expandProductDetails?.() ?? 0)
  }

  const patterns = [
    /see\s*more/i, /read\s*more/i, /show\s*more/i, /view\s*more/i, /load\s*more/i,
    /expand\s*(all)?/i, /see\s*full/i, /show\s*all/i,
    /product\s*details/i, /full\s*content/i,
    /展开/, /查看更多/, /展开更多/, /显示更多/, /加载更多/,
    /全文/, /更多内容/, /更多详情/, /更多信息/, /产品详情/,
  ]
  const isExpandLike = (text) => {
    const t = (text || '').trim()
    if (t.length < 2 || t.length > 80) return false
    return patterns.some((p) => p.test(t))
  }

  // 1. <details> 元素：直接展开
  document.querySelectorAll('details:not([open])').forEach((el) => {
    const summary = el.querySelector('summary')
    if (summary) {
      try {
        summary.click()
        clicked++
      } catch (_) {}
    } else {
      el.open = true
      clicked++
    }
  })

  // 2. 可点击元素：文本匹配「展开」类
  const clickables = document.querySelectorAll(
    'a, button, [role="button"], [onclick], [data-action], [class*="expand"], [class*="more"], [class*="toggle"]'
  )
  clickables.forEach((el) => {
    if (clicked >= 20) return
    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim()
    if (!isExpandLike(text)) return
    if (el.offsetParent === null && el.getBoundingClientRect().height === 0) return
    try {
      el.scrollIntoView({ block: 'center', behavior: 'auto' })
      el.click()
      clicked++
    } catch (_) {}
  })

  // 3. aria-expanded="false" 的折叠项
  document.querySelectorAll('[aria-expanded="false"]').forEach((el) => {
    if (clicked >= 20) return
    const text = (el.innerText || el.textContent || '').trim()
    if (text.length < 2) return
    try {
      el.scrollIntoView({ block: 'center', behavior: 'auto' })
      el.click()
      clicked++
    } catch (_) {}
  })

  // 4. 带 data-expanded / data-collapsed 的折叠触发器
  document.querySelectorAll('[data-expanded="false"], [data-collapsed="true"]').forEach((el) => {
    if (clicked >= 20) return
    try {
      el.scrollIntoView({ block: 'center', behavior: 'auto' })
      el.click()
      clicked++
    } catch (_) {}
  })

  return clicked
}

function extractContent() {
  const href = window.location.href || ''
  const isWeixinMp = /mp\.weixin\.qq\.com/.test(href)
  const isFeishu = /feishu\.cn|feishubase\.com/.test(href)
  // 时间：2026-03-14；理由：executeScript 只注入本函数，外层 helper 不可用；方法：微信 svg 占位 src 从 data-src 写回真 URL
  const rewriteWeixinLazyImgSrc = (root) => {
    if (!root || !root.querySelectorAll) return
    root.querySelectorAll('img').forEach((img) => {
      const src = (img.getAttribute('src') || '').trim()
      if (!src.startsWith('data:image/')) return
      const raw =
        (img.getAttribute('data-src') || '').trim() ||
        (img.getAttribute('data-original') || '').trim() ||
        (img.getAttribute('data-lazy-src') || '').trim() ||
        (img.getAttribute('data-url') || '').trim()
      if (!raw || raw.startsWith('data:')) return
      try {
        const abs = raw.startsWith('//') ? window.location.protocol + raw : new URL(raw, location.href).href
        if (/^https?:\/\//i.test(abs)) img.setAttribute('src', abs)
      } catch (_) {}
    })
  }
  const amazon = typeof window.__HOU_AMAZON !== 'undefined' ? window.__HOU_AMAZON : null
  const isAmazon = amazon?.isAmazonProductPage?.(href) ?? /amazon\.(com|co\.\w{2}|cn|co\.jp)\/(dp|gp\/product)/.test(href)
  const isWikipedia = /\.wikipedia\.org\//.test(href) || /\.wikimedia\.org\//.test(href)
  const baseSelectors = [
    'article', 'main', '[role="main"]', '.post-content', '.article-body',
    '.content', '#content', '.entry-content', '.post-body', '.article-content',
    '[class*="blog-post"]', '[class*="post-content"]', '[class*="article-body"]',
    '[class*="entry-content"]', '[class*="prose"]',  // Tailwind prose, 常见博客
  ]
  // 维基百科：优先提取正文，避免导航/侧栏/语言切换等 UI 混入
  const wikipediaSelectors = ['#mw-content-text', '#bodyContent', '.mw-parser-output']
  const amazonSelectors = (amazon?.SELECTORS ?? []).length ? amazon.SELECTORS : [
    '#productDetails_feature_div', '#prodDetails', '#productDetails',
    '#detailBullets_feature_div', '#feature-bullets',
  ]
  const feishuSelectors = [
    '[data-type="bitable"]', '[class*="bitable"]', '[class*="base-table"]',
    '[class*="baseTable"]', '[class*="Bitable"]', 'main', '[role="main"]',
  ]
  const selectors = isWikipedia ? [...wikipediaSelectors, ...baseSelectors]
    : isAmazon ? [...amazonSelectors, ...baseSelectors]
    : isFeishu ? [...feishuSelectors, ...baseSelectors] : baseSelectors
  const minLen = isFeishu ? 30 : isAmazon ? 50 : 100
  let el = null
  if (isWikipedia || isAmazon || isFeishu) {
    for (const s of selectors) {
      try {
        const candidate = document.querySelector(s)
        if (candidate && (candidate.innerText || candidate.textContent || '').trim().length >= minLen) {
          el = candidate
          break
        }
      } catch (_) {}
    }
  } else {
    // 微信公众号：优先 #js_content，避免误取长侧栏容器导致 img 仍为 svg 占位
    if (isWeixinMp) {
      const js = document.querySelector('#js_content')
      if (js && (js.innerText || js.textContent || '').trim().length >= 50) el = js
    }
    if (!el) {
      // 博客/普通站：选正文最长的容器，避免误取「Related News」等侧栏
      let bestLen = minLen - 1
      const seen = new WeakSet()
      for (const s of selectors) {
        try {
          document.querySelectorAll(s).forEach((c) => {
            if (seen.has(c)) return
            const len = (c.innerText || c.textContent || '').trim().length
            if (len > bestLen) {
              bestLen = len
              el = c
            }
            seen.add(c)
          })
        } catch (_) {}
      }
    }
  }
  el = el || document.body
  let content = (el.innerText || el.textContent || '').trim()
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
  if (isWeixinMp) rewriteWeixinLazyImgSrc(temp)
  temp.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove())
  temp.querySelectorAll('[onclick], [onload], [onerror]').forEach((n) => {
    n.removeAttribute('onclick'); n.removeAttribute('onload'); n.removeAttribute('onerror')
  })
  let html = temp.innerHTML
  let fullPageHtml = ''
  try {
    const doc = document.documentElement.cloneNode(true)
    doc.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove())
    doc.querySelectorAll('[onclick], [onload], [onerror]').forEach((n) => {
      n.removeAttribute('onclick'); n.removeAttribute('onload'); n.removeAttribute('onerror')
    })
    if (isWeixinMp) {
      const jsRoot = doc.querySelector('#js_content')
      if (jsRoot) rewriteWeixinLazyImgSrc(jsRoot)
    }
    fullPageHtml = doc.outerHTML
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

/**
 * 页面内执行：收集正文区域 img 的绝对 URL（微信优先 #js_content）。
 * 时间：2026-03-14；理由：微信 CDN 跨域；方法：已懒加载时优先 src（含 tp=webp 等与 innerHTML 一致），否则 data-src
 */
function collectArticleImageUrlsForInlining() {
  const href = window.location.href || ''
  const roots = []
  if (/mp\.weixin\.qq\.com/.test(href)) {
    const js = document.querySelector('#js_content')
    if (js) roots.push(js)
  }
  if (!roots.length) {
    const el =
      document.querySelector('article') ||
      document.querySelector('main') ||
      document.querySelector('[role="main"]') ||
      document.querySelector('#content') ||
      document.body
    if (el) roots.push(el)
  }
  const seen = new Set()
  const urls = []
  for (const root of roots) {
    try {
      root.querySelectorAll('img').forEach((img) => {
        const srcAttr = (img.getAttribute('src') || '').trim()
        let raw = ''
        if (/^https?:\/\//i.test(srcAttr) && !srcAttr.toLowerCase().startsWith('data:')) {
          raw = srcAttr
        } else {
          raw =
            (img.getAttribute('data-src') || '').trim() ||
            (img.getAttribute('data-original') || '').trim() ||
            srcAttr ||
            ''
        }
        if (!raw || String(raw).startsWith('data:')) {
          const cs = img.currentSrc || ''
          if (cs && !String(cs).startsWith('data:') && /^https?:\/\//i.test(cs)) raw = cs
        }
        if (!raw || String(raw).startsWith('data:')) return
        try {
          const abs = new URL(raw, location.href).href
          if (seen.has(abs)) return
          seen.add(abs)
          if (/\.svg(\?|$)/i.test(abs)) return
          urls.push(abs)
        } catch (_) {}
      })
    } catch (_) {}
  }
  return urls
}

/** 与防盗链站点对话时 Referer 需为站点根；插图在 res.weread.qq.com 时仍用微信读书主站 Referer */
function refererForImageFetch(pageUrl, imageUrl) {
  const iu = (imageUrl || '').trim()
  if (/res\.weread\.qq\.com/i.test(iu)) return 'https://weread.qq.com/'
  if (/\.myqcloud\.com/i.test(iu) && /weread|qqread|wrepub/i.test(iu)) return 'https://weread.qq.com/'
  const u = pageUrl || ''
  if (/mp\.weixin\.qq\.com/i.test(u)) return 'https://mp.weixin.qq.com/'
  if (/weread\.qq\.com/i.test(u)) return 'https://weread.qq.com/'
  return u
}

function originBaseForCookieLookup(urlStr) {
  try {
    const u = new URL(String(urlStr || '').trim())
    return `${u.protocol}//${u.host}/`
  } catch (_) {
    return ''
  }
}

/**
 * 合并多来源 Cookie（微信读书插图常在 res.* / CDN，会话 Cookie 在 weread.qq.com，仅按图片域 getAll 会缺登录态）
 */
async function mergedCookieHeaderForFetch(imageUrl, pageUrl) {
  const bases = []
  const imgBase = originBaseForCookieLookup(imageUrl)
  if (imgBase) bases.push(imgBase)
  const pageBase = originBaseForCookieLookup(pageUrl || '')
  if (pageBase && pageBase !== imgBase) bases.push(pageBase)
  const iu = (imageUrl || '').trim()
  const pu = (pageUrl || '').trim()
  const wereadish =
    /weread\.qq\.com/i.test(iu) ||
    /weread\.qq\.com/i.test(pu) ||
    /res\.weread\.qq\.com/i.test(iu) ||
    (/\.myqcloud\.com/i.test(iu) && /weread|qqread|wrepub/i.test(iu))
  const wereadRoot = 'https://weread.qq.com/'
  if (wereadish && !bases.includes(wereadRoot)) bases.push(wereadRoot)

  const byName = new Map()
  for (const base of bases) {
    try {
      const list = await chrome.cookies.getAll({ url: base })
      for (const c of list) {
        byName.set(c.name, c.value)
      }
    } catch (_) {}
  }
  return [...byName.entries()].map(([n, v]) => `${n}=${v}`).join('; ')
}

function shortUrlForFetchError(absUrl) {
  try {
    const u = new URL(absUrl)
    const path = u.pathname + u.search
    const tail = path.length > 52 ? `${path.slice(0, 49)}…` : path
    return `${u.hostname}${tail}`
  } catch (_) {
    return String(absUrl || '').slice(0, 64)
  }
}

/**
 * Service Worker：用扩展权限拉取图片（带 Referer/Cookie），转 data URL。
 * @returns {{ map: Record<string,string>, errors: string[] }} errors 为简短诊断（最多十余条）
 */
async function fetchImagesViaExtension(absUrls, pageUrl) {
  const ua =
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
  const out = {}
  const errors = []
  const maxErr = 12
  /** 单图体积上限：防止异常响应用尽内存；正常书籍插图远低于此 */
  const maxBytesPerImage = 40 * 1024 * 1024
  for (const u of absUrls || []) {
    if (!u || u.startsWith('data:')) continue
    try {
      const cookieStr = await mergedCookieHeaderForFetch(u, pageUrl)
      const headers = {
        Referer: refererForImageFetch(pageUrl, u),
        'User-Agent': ua,
        Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
      }
      if (cookieStr) headers.Cookie = cookieStr
      const r = await fetch(u, { headers, redirect: 'follow' })
      if (!r.ok) {
        if (errors.length < maxErr) errors.push(`${shortUrlForFetchError(u)} → HTTP ${r.status}`)
        continue
      }
      const blob = await r.blob()
      if (!blob || blob.size > maxBytesPerImage) {
        if (errors.length < maxErr) errors.push(`${shortUrlForFetchError(u)} → 空响应或超过体积上限`)
        continue
      }
      const ct = blob.type && blob.type.startsWith('image/') ? blob.type : 'image/jpeg'
      const buf = await blob.arrayBuffer()
      const bytes = new Uint8Array(buf)
      let binary = ''
      const chunkSize = 8192
      for (let i = 0; i < bytes.length; i += chunkSize) {
        const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length))
        binary += String.fromCharCode.apply(null, chunk)
      }
      const b64 = btoa(binary)
      out[u] = `data:${ct};base64,${b64}`
    } catch (e) {
      if (errors.length < maxErr) errors.push(`${shortUrlForFetchError(u)} → ${e?.message || '请求失败'}`)
    }
  }
  return { map: out, errors }
}

const SCROLL_PAUSE_MS = 600
/** 微信读书：沿章节滚动触发懒加载后再采 URL（步数不设上限，靠到底部/滚动停滞退出） */
const WEREAD_IMAGE_PRELOAD_PAUSE_MS = 360

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

/** 飞书多维表格：查找滚动容器（表格虚拟滚动区域） */
function findFeishuScrollContainer() {
  const candidates = [
    '[class*="bitable"]', '[class*="base-table"]', '[class*="BaseTable"]',
    '[class*="virtual"]', '[class*="Virtual"]', '[class*="scroll"]',
    '[class*="table-body"]', '[class*="tableBody"]', '[class*="grid"]',
    'main', '[role="main"]',
  ]
  let best = document.scrollingElement || document.documentElement
  let maxSh = best.scrollHeight || 0
  for (const sel of candidates) {
    try {
      document.querySelectorAll(sel).forEach((el) => {
        if (!el || !el.scrollHeight) return
        const s = window.getComputedStyle(el)
        const oy = s.overflowY || s.overflow
        if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay') && el.scrollHeight > el.clientHeight + 80 && el.scrollHeight > maxSh) {
          best = el
          maxSh = el.scrollHeight
        }
      })
    } catch (_) {}
  }
  return best
}

/** 飞书多维表格：滚动 + 分步提取，应对虚拟滚动 */
async function extractContentWithScrollFeishu() {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms))
  const scrollEl = findFeishuScrollContainer()
  const maxSteps = 25
  const stepPause = 500
  const seen = new Set()
  const lines = []

  for (let i = 0; i < maxSteps; i++) {
    scrollEl.scrollTop = Math.min(i * Math.floor((scrollEl.clientHeight || 400) * 0.8), scrollEl.scrollHeight)
    await wait(stepPause)

    const extractRoot = (scrollEl === document.documentElement || scrollEl === document.body) ? document.body : scrollEl
    const text = (extractRoot.innerText || extractRoot.textContent || '').trim()
    const newLines = text.split(/\r?\n/).filter((l) => l.trim())
    for (const line of newLines) {
      const key = line.slice(0, 200)
      if (!seen.has(key)) {
        seen.add(key)
        lines.push(line)
      }
    }

    const atBottom = scrollEl.scrollTop + (scrollEl.clientHeight || 0) >= (scrollEl.scrollHeight || 0) - 30
    if (atBottom) break
  }

  scrollEl.scrollTop = 0
  const content = lines.join('\n')
  const path = window.location.pathname || '/'
  const dir = path.endsWith('/') ? path : path.replace(/\/[^/]*$/, '/') || '/'
  const base = window.location.origin + dir
  return {
    title: document.title || '',
    content,
    html: content ? '<pre>' + content.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>' : '',
    fullPageHtml: '',
    baseUrl: base,
    stylesheets: [],
    inlineStyles: [],
    url: window.location.href,
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

/**
 * 微信读书页面内执行：阅读器容器内正文 HTML / 纯文本 + 插图 URL（扩展内 fetch 拉图，与公众号同源）
 * 时间：2026-03-24；理由：先图后文 + web/reader 图常在根外或 background-image；方法：全页 img 过滤、根内 bg 扫描、章节容器补集
 */
function extractWereadReaderBundle() {
  function isWereadBookImageUrl(abs) {
    const u = String(abs || '').toLowerCase()
    if (!/^https?:\/\//.test(u)) return false
    if (/\.svg(\?|$)/i.test(u)) return false
    if (/avatar|emoji|favicon|wx\.qlogo|qpic\.cn\/mmbiz|headimg|\/misc\//.test(u)) return false
    if (u.includes('wrepub')) return true
    if (u.includes('i.weread.qq.com')) return true
    if (u.includes('res.weread.qq.com')) return true
    try {
      const host = new URL(u).hostname
      if (host === 'weread.qq.com' || host.endsWith('.weread.qq.com')) return true
    } catch (_) {}
    if (/\.myqcloud\.com/i.test(u) && /weread|wrepub|qqread/i.test(u)) return true
    return false
  }
  function pushAbsoluteImageUrl(abs, seen, imageUrls) {
    if (!abs || seen.has(abs)) return
    if (!isWereadBookImageUrl(abs)) return
    seen.add(abs)
    imageUrls.push(abs)
  }
  function tryPushBgImageFromEl(el, seen, imageUrls) {
    let bg = ''
    try {
      bg = window.getComputedStyle(el).backgroundImage || ''
    } catch (_) {}
    if (!bg || bg === 'none') return
    const re = /url\(["']?([^)"']+)["']?\)/gi
    let m
    while ((m = re.exec(bg)) !== null) {
      const raw = (m[1] || '').trim()
      if (!raw || raw.startsWith('data:')) continue
      try {
        pushAbsoluteImageUrl(new URL(raw, location.href).href, seen, imageUrls)
      } catch (_) {}
    }
  }
  function findReaderRoot() {
    const bookImg = document.querySelector('img.wr_readerImage_opacity, img[class*="wr_readerImage"]')
    if (bookImg) {
      const byShell =
        bookImg.closest('[class*="readerChapter"], [class*="reader_chapter"], [class*="chapter_content"], [class*="wr_reader"]') ||
        bookImg.closest('[class*="wr_"]')
      if (byShell && (byShell.innerText || '').trim().length > 40) return byShell
      let p = bookImg.parentElement
      for (let d = 0; d < 24 && p; d++) {
        const t = (p.innerText || '').trim().length
        if (t > 180) return p
        p = p.parentElement
      }
      return bookImg.closest('main, [id*="app"], body') || document.body
    }
    let el = document.scrollingElement || document.documentElement
    try {
      const sel = '[class*="reader"], [class*="chapter"], [class*="content"], [class*="book"], [id*="reader"], main'
      const list = document.querySelectorAll(sel)
      let maxSh = el.scrollHeight || 0
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
    return el
  }
  function pushImgUrl(img, seen, imageUrls) {
    const srcAttr = (img.getAttribute('src') || '').trim()
    let raw = ''
    if (/^https?:\/\//i.test(srcAttr) && !srcAttr.toLowerCase().startsWith('data:')) {
      raw = srcAttr
    } else {
      raw =
        (img.getAttribute('data-src') || '').trim() ||
        (img.getAttribute('data-original') || '').trim() ||
        srcAttr ||
        ''
    }
    if (!raw || String(raw).startsWith('data:')) {
      const cs = img.currentSrc || ''
      if (cs && !String(cs).startsWith('data:') && /^https?:\/\//i.test(cs)) raw = cs
    }
    if (!raw || String(raw).startsWith('data:')) return
    try {
      const abs = new URL(raw, location.href).href
      if (seen.has(abs)) return
      seen.add(abs)
      if (/\.svg(\?|$)/i.test(abs)) return
      imageUrls.push(abs)
    } catch (_) {}
    const ss = (img.getAttribute('srcset') || '').trim()
    if (ss) {
      ss.split(',').forEach((part) => {
        const piece = (part || '').trim().split(/\s+/)[0]
        if (!piece || piece.startsWith('data:')) return
        try {
          const abs = new URL(piece, location.href).href
          if (seen.has(abs) || /\.svg(\?|$)/i.test(abs)) return
          seen.add(abs)
          imageUrls.push(abs)
        } catch (_) {}
      })
    }
  }
  const root = findReaderRoot()
  const title = (document.title || '').trim() || '微信读书'
  const content = (root.innerText || root.textContent || '').trim().slice(0, 500000)
  const temp = document.createElement('div')
  temp.innerHTML = root.innerHTML || ''
  temp.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove())
  temp.querySelectorAll('[onclick], [onload], [onerror]').forEach((n) => {
    n.removeAttribute('onclick'); n.removeAttribute('onload'); n.removeAttribute('onerror')
  })
  const html = temp.innerHTML.slice(0, 2000000)
  const seen = new Set()
  const imageUrls = []
  temp.querySelectorAll('img').forEach((img) => pushImgUrl(img, seen, imageUrls))
  try {
    document
      .querySelectorAll(
        'img.wr_readerImage_opacity, img[class*="wr_readerImage"], img[src*="res.weread.qq.com/wrepub/"], img[data-src*="res.weread.qq.com/wrepub/"]'
      )
      .forEach((img) => pushImgUrl(img, seen, imageUrls))
  } catch (_) {}
  try {
    document.querySelectorAll('img').forEach((img) => {
      const raw =
        (img.getAttribute('data-src') || '').trim() ||
        (img.getAttribute('src') || '').trim() ||
        (img.currentSrc || '').trim()
      if (!raw || String(raw).startsWith('data:')) return
      try {
        pushAbsoluteImageUrl(new URL(raw, location.href).href, seen, imageUrls)
      } catch (_) {}
    })
  } catch (_) {}
  try {
    const nodes = root && root.querySelectorAll ? root.querySelectorAll('*') : []
    for (let i = 0; i < nodes.length; i++) {
      tryPushBgImageFromEl(nodes[i], seen, imageUrls)
    }
  } catch (_) {}
  try {
    document.querySelectorAll('body *').forEach((el) => {
      tryPushBgImageFromEl(el, seen, imageUrls)
    })
  } catch (_) {}
  try {
    document
      .querySelectorAll(
        '[class*="readerChapter"], [class*="reader_chapter"], [class*="chapter_content"], [class*="wr_reader"]'
      )
      .forEach((container) => {
        container.querySelectorAll?.('img').forEach((img) => pushImgUrl(img, seen, imageUrls))
      })
  } catch (_) {}
  return { title, content, html, imageUrls }
}

/**
 * 仅收集当前 DOM 内插图 URL（与 extract 规则一致），供沿章节滚动时多次快照合并，避免懒加载只露出首屏。
 */
function snapshotWereadImageUrls() {
  function isWereadBookImageUrl(abs) {
    const u = String(abs || '').toLowerCase()
    if (!/^https?:\/\//.test(u)) return false
    if (/\.svg(\?|$)/i.test(u)) return false
    if (/avatar|emoji|favicon|wx\.qlogo|qpic\.cn\/mmbiz|headimg|\/misc\//.test(u)) return false
    if (u.includes('wrepub')) return true
    if (u.includes('i.weread.qq.com')) return true
    if (u.includes('res.weread.qq.com')) return true
    try {
      const host = new URL(u).hostname
      if (host === 'weread.qq.com' || host.endsWith('.weread.qq.com')) return true
    } catch (_) {}
    if (/\.myqcloud\.com/i.test(u) && /weread|wrepub|qqread/i.test(u)) return true
    return false
  }
  function pushAbsoluteImageUrl(abs, seen, imageUrls) {
    if (!abs || seen.has(abs)) return
    if (!isWereadBookImageUrl(abs)) return
    seen.add(abs)
    imageUrls.push(abs)
  }
  function tryPushBgImageFromEl(el, seen, imageUrls) {
    let bg = ''
    try {
      bg = window.getComputedStyle(el).backgroundImage || ''
    } catch (_) {}
    if (!bg || bg === 'none') return
    const re = /url\(["']?([^)"']+)["']?\)/gi
    let m
    while ((m = re.exec(bg)) !== null) {
      const raw = (m[1] || '').trim()
      if (!raw || raw.startsWith('data:')) continue
      try {
        pushAbsoluteImageUrl(new URL(raw, location.href).href, seen, imageUrls)
      } catch (_) {}
    }
  }
  function pushImgUrl(img, seen, imageUrls) {
    const srcAttr = (img.getAttribute('src') || '').trim()
    let raw = ''
    if (/^https?:\/\//i.test(srcAttr) && !srcAttr.toLowerCase().startsWith('data:')) {
      raw = srcAttr
    } else {
      raw =
        (img.getAttribute('data-src') || '').trim() ||
        (img.getAttribute('data-original') || '').trim() ||
        srcAttr ||
        ''
    }
    if (!raw || String(raw).startsWith('data:')) {
      const cs = img.currentSrc || ''
      if (cs && !String(cs).startsWith('data:') && /^https?:\/\//i.test(cs)) raw = cs
    }
    if (!raw || String(raw).startsWith('data:')) return
    try {
      const abs = new URL(raw, location.href).href
      if (seen.has(abs)) return
      seen.add(abs)
      if (/\.svg(\?|$)/i.test(abs)) return
      imageUrls.push(abs)
    } catch (_) {}
    const ss = (img.getAttribute('srcset') || '').trim()
    if (ss) {
      ss.split(',').forEach((part) => {
        const piece = (part || '').trim().split(/\s+/)[0]
        if (!piece || piece.startsWith('data:')) return
        try {
          const abs = new URL(piece, location.href).href
          if (seen.has(abs) || /\.svg(\?|$)/i.test(abs)) return
          seen.add(abs)
          imageUrls.push(abs)
        } catch (_) {}
      })
    }
  }
  const seen = new Set()
  const imageUrls = []
  try {
    document.querySelectorAll('img').forEach((img) => pushImgUrl(img, seen, imageUrls))
  } catch (_) {}
  try {
    document
      .querySelectorAll(
        'img.wr_readerImage_opacity, img[class*="wr_readerImage"], img[src*="res.weread.qq.com/wrepub/"], img[data-src*="res.weread.qq.com/wrepub/"]'
      )
      .forEach((img) => pushImgUrl(img, seen, imageUrls))
  } catch (_) {}
  try {
    document.querySelectorAll('img').forEach((img) => {
      const raw =
        (img.getAttribute('data-src') || '').trim() ||
        (img.getAttribute('src') || '').trim() ||
        (img.currentSrc || '').trim()
      if (!raw || String(raw).startsWith('data:')) return
      try {
        pushAbsoluteImageUrl(new URL(raw, location.href).href, seen, imageUrls)
      } catch (_) {}
    })
  } catch (_) {}
  try {
    document.querySelectorAll('body *').forEach((el) => {
      tryPushBgImageFromEl(el, seen, imageUrls)
    })
  } catch (_) {}
  try {
    document
      .querySelectorAll(
        '[class*="readerChapter"], [class*="reader_chapter"], [class*="chapter_content"], [class*="wr_reader"]'
      )
      .forEach((container) => {
        container.querySelectorAll?.('img').forEach((img) => pushImgUrl(img, seen, imageUrls))
      })
  } catch (_) {}
  return imageUrls
}

/**
 * 微信读书：滚动预载插图 URL → 回顶 extract → 扩展内 fetch 拉图（与截图无关的共用段）
 * @returns {{ bundle: object, inlineImageMap?: object }}
 */
async function fetchWereadReaderCore(tabId, url) {
  await chrome.tabs.update(tabId, { active: true })
  await chrome.scripting.executeScript({ target: { tabId }, func: waitForPageLoad }).catch(() => {})
  await new Promise((r) => setTimeout(r, 4000))

  const mergedImageUrls = new Set()
  let preOff = 0
  let prePrev = -1
  for (;;) {
    const [scrollRes] = await chrome.scripting
      .executeScript({ target: { tabId }, func: scrollToPositionWeread, args: [preOff] })
      .catch(() => [{}])
    const info = scrollRes?.result
    await new Promise((r) => setTimeout(r, WEREAD_IMAGE_PRELOAD_PAUSE_MS))
    try {
      const [snapRes] = await chrome.scripting.executeScript({ target: { tabId }, func: snapshotWereadImageUrls })
      const arr = snapRes?.result
      if (Array.isArray(arr)) {
        for (const u of arr) {
          if (u && typeof u === 'string') mergedImageUrls.add(u)
        }
      }
    } catch (_) {}
    if (!info || info.atBottom) break
    if (info.scrollTop === prePrev) break
    prePrev = info.scrollTop
    preOff = info.scrollTop + Math.floor(info.clientHeight * 0.82)
    if (preOff >= info.scrollHeight) break
  }
  try {
    await chrome.scripting.executeScript({ target: { tabId }, func: scrollToPositionWeread, args: [0] })
    await new Promise((r) => setTimeout(r, 500))
  } catch (_) {}

  let bundle = { title: '微信读书', content: '', html: '', imageUrls: [] }
  try {
    const [bundleRes] = await chrome.scripting.executeScript({ target: { tabId }, func: extractWereadReaderBundle })
    const r = bundleRes?.result
    if (r && typeof r === 'object') {
      bundle = {
        title: ((r.title || '') + '').trim() || '微信读书',
        content: r.content || '',
        html: r.html || '',
        imageUrls: Array.isArray(r.imageUrls) ? r.imageUrls : [],
      }
    }
  } catch (_) {}
  for (const u of bundle.imageUrls || []) {
    if (u && typeof u === 'string') mergedImageUrls.add(u)
  }
  bundle.imageUrls = [...mergedImageUrls]

  let inlineImageMap
  if (bundle.imageUrls.length) {
    try {
      const { map } = await fetchImagesViaExtension(bundle.imageUrls, url)
      if (map && Object.keys(map).length) inlineImageMap = map
    } catch (_) {}
  }

  await new Promise((r) => setTimeout(r, 800))
  return { bundle, inlineImageMap }
}

async function switchWereadTabBack(createdByUs, tabId) {
  const all = await chrome.tabs.query({ currentWindow: true })
  const wereadReader = all.find((t) => /\/weread-reader/.test(t.url || ''))
  const webReader = all.find((t) => /\/web-reader/.test(t.url || ''))
  const targetTab = wereadReader || webReader
  if (createdByUs && tabId) {
    if (targetTab?.id) await chrome.tabs.update(targetTab.id, { active: true }).catch(() => {})
    await chrome.tabs.remove(tabId).catch(() => {})
  } else if (tabId && targetTab?.id) {
    await chrome.tabs.update(targetTab.id, { active: true }).catch(() => {})
  }
}

/** 微信读书：仅 DOM + 拉图，不 captureVisibleTab、不依赖截图 */
async function fetchWereadImagesOnly(url, createdByUs, tabId) {
  const { bundle, inlineImageMap } = await fetchWereadReaderCore(tabId, url)
  await switchWereadTabBack(createdByUs, tabId)

  const hasDom =
    (bundle.content || '').trim().length > 0 || (bundle.html || '').trim().length > 0 || (bundle.imageUrls || []).length > 0
  const hasMap = inlineImageMap && Object.keys(inlineImageMap).length > 0
  if (!hasDom && !hasMap) {
    throw new Error('未能从页面读取正文或插图，请确认章节已打开且已登录')
  }

  const out = {
    title: bundle.title,
    content: bundle.content || '',
    html: bundle.html || '',
    fullPageHtml: '',
    baseUrl: new URL(url).origin + '/',
    stylesheets: [],
    inlineStyles: [],
    url,
    screenshots: [],
    imageUrls: Array.isArray(bundle.imageUrls) ? bundle.imageUrls : [],
    pendingOcr: false,
    wereadImagesOnly: true,
  }
  if (inlineImageMap && Object.keys(inlineImageMap).length) out.inlineImageMap = inlineImageMap
  return out
}

/**
 * 页内执行：全屏截图 → 裁视口水平居中条带（微信读书正文在中间，左右为大留白）。
 * 固定按视口宽约 43% 居中裁切，避免误判到「整页宽的滚动容器」导致不裁切。
 */
function cropWereadVisibleTabScreenshot(dataUrl) {
  if (!dataUrl || typeof dataUrl !== 'string') return Promise.resolve(dataUrl)
  const vw = window.innerWidth || document.documentElement.clientWidth
  const vh = window.innerHeight || document.documentElement.clientHeight
  const dpr = window.devicePixelRatio || 1
  const nw = Math.max(120, Math.floor(vw * 0.43))
  const x = Math.max(0, Math.floor((vw - nw) / 2))
  const y = 0
  const w = Math.min(nw, vw - x)
  const h = vh
  if (w < 100 || h < 100) return Promise.resolve(dataUrl)

  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      try {
        const scale = dpr
        const sx = Math.max(0, Math.min(x * scale, img.width - 1))
        const sy = Math.max(0, Math.min(y * scale, img.height - 1))
        const sw = Math.max(1, Math.min(w * scale, img.width - sx))
        const sh = Math.max(1, Math.min(h * scale, img.height - sy))
        const canvas = document.createElement('canvas')
        canvas.width = sw
        canvas.height = sh
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          resolve(dataUrl)
          return
        }
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
        resolve(canvas.toDataURL('image/png'))
      } catch (_) {
        resolve(dataUrl)
      }
    }
    img.onerror = () => resolve(dataUrl)
    img.src = dataUrl
  })
}

/** 微信读书：DOM 插图拉图 + 正文；长页分屏截图，DOM 字少则 OCR */
async function fetchWereadScreenshot(url, createdByUs, tabId) {
  const { bundle, inlineImageMap } = await fetchWereadReaderCore(tabId, url)

  const screenshots = []
  let offsetY = 0
  let prevScrollTop = -1

  for (;;) {
    const [scrollRes] = await chrome.scripting
      .executeScript({ target: { tabId }, func: scrollToPositionWeread, args: [offsetY] })
      .catch(() => [{}])
    const info = scrollRes?.result

    await new Promise((r) => setTimeout(r, SCROLL_PAUSE_MS))

    await chrome.tabs.update(tabId, { active: true }).catch(() => {})
    await new Promise((r) => setTimeout(r, 120))

    let dataUrl
    try {
      const tab = await chrome.tabs.get(tabId)
      const winId = tab?.windowId
      dataUrl = await chrome.tabs.captureVisibleTab(winId != null ? winId : null, { format: 'png' })
    } catch (e) {
      if (screenshots.length === 0) {
        throw new Error('截图失败：' + (e?.message || '请确保标签页已完全加载，且未切换窗口'))
      }
      break
    }

    try {
      const [cRes] = await chrome.scripting.executeScript({
        target: { tabId },
        func: cropWereadVisibleTabScreenshot,
        args: [dataUrl],
      })
      let cropped = cRes?.result
      if (cropped != null && typeof cropped.then === 'function') {
        cropped = await cropped
      }
      if (typeof cropped === 'string' && cropped.startsWith('data:image') && cropped.length > 500) {
        dataUrl = cropped
      }
    } catch (_) {}

    screenshots.push(dataUrl)

    if (!info || info.atBottom) break
    if (info.scrollTop === prevScrollTop) break
    prevScrollTop = info.scrollTop

    offsetY = info.scrollTop + Math.floor(info.clientHeight * 0.85)
    if (offsetY >= info.scrollHeight) break
  }

  await switchWereadTabBack(createdByUs, tabId)

  if (screenshots.length === 0) {
    const hasDom =
      (bundle.content || '').trim().length > 0 || (bundle.html || '').trim().length > 0 || (bundle.imageUrls || []).length > 0
    if (!hasDom) {
      throw new Error('未能截取到任何画面，且未能从页面读取正文')
    }
  }

  const domLen = (bundle.content || '').trim().length
  const domEnough = domLen >= 80

  const out = {
    title: bundle.title,
    content: bundle.content || '',
    html: bundle.html || '',
    fullPageHtml: '',
    baseUrl: new URL(url).origin + '/',
    stylesheets: [],
    inlineStyles: [],
    url,
    screenshots,
    /** 阅读器 DOM 内收集到的插图 URL（扩展已尽量拉图写入 inlineImageMap） */
    imageUrls: Array.isArray(bundle.imageUrls) ? bundle.imageUrls : [],
    pendingOcr: screenshots.length > 0 && !domEnough,
  }
  if (inlineImageMap && Object.keys(inlineImageMap).length) out.inlineImageMap = inlineImageMap
  return out
}

/** 等待标签页加载完成（status === 'complete'），超时 30s */
async function waitForTabComplete(tabId, timeoutMs = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const tab = await chrome.tabs.get(tabId)
      if (tab.status === 'complete') return
    } catch (_) {}
    await new Promise((r) => setTimeout(r, 200))
  }
}

/** 普通网页 / 飞书：DOM 提取。needLoad 时先等 tab 加载完成，再等页面 load，最后 SPA 额外延迟 */
async function runDomExtraction(tabId, url, createdByUs, needLoad, opts = {}) {
  await chrome.tabs.update(tabId, { active: true }).catch(() => {})
  if (needLoad) {
    await waitForTabComplete(tabId)
    await chrome.scripting.executeScript({ target: { tabId }, func: waitForPageLoad }).catch(() => {})
  }
  await chrome.scripting.executeScript({ target: { tabId }, func: waitForPage }).catch(() => {})

  // 注入 Amazon 专用逻辑（若为 Amazon 页则展开 productDetails）
  await chrome.scripting.executeScript({ target: { tabId }, files: ['amazon.js'] }).catch(() => {})

  // 自动展开所有隐藏/折叠内容（See more、展开更多等），多轮直到无新元素
  const isAmazon = /amazon\.(com|co\.\w{2}|cn|co\.jp)\/(dp|gp\/product)/.test(url || '')
  const maxExpandRounds = isAmazon ? 8 : 5
  const expandPauseMs = 800
  const amazonLoadWaitMs = 1500
  for (let r = 0; r < maxExpandRounds; r++) {
    const [res] = await chrome.scripting
      .executeScript({ target: { tabId }, func: expandAllHiddenContent })
      .catch(() => [{ result: 0 }])
    const count = res?.result ?? 0
    if (count === 0) break
    const waitMs = isAmazon && count === 1 ? amazonLoadWaitMs : expandPauseMs
    await new Promise((x) => setTimeout(x, waitMs))
  }
  await new Promise((x) => setTimeout(x, 300))

  let data
  if (opts.useScrollExtract) {
    const scrollRes = await chrome.scripting.executeScript({ target: { tabId }, func: extractContentWithScrollFeishu })
    data = scrollRes?.[0]?.result
    if (data && (data.content || '').trim().length < 50) {
      const fallback = await chrome.scripting.executeScript({ target: { tabId }, func: extractContent })
      data = fallback?.[0]?.result || data
    }
  } else {
    const results = await chrome.scripting.executeScript({ target: { tabId }, func: extractContent })
    data = results?.[0]?.result
  }

  // 时间：2026-03-14；理由：微信等站图片禁止外链；方法：关 tab 前在 SW 内 fetch + Cookie/Referer，返回 inlineImageMap
  if (opts.inlineImages && data && data.html) {
    try {
      const [imgRes] = await chrome.scripting.executeScript({
        target: { tabId },
        func: collectArticleImageUrlsForInlining,
      })
      const urls = imgRes?.result || []
      if (urls.length) {
        const { map } = await fetchImagesViaExtension(urls, url)
        if (map && Object.keys(map).length) data.inlineImageMap = map
      }
    } catch (_) {}
  }

  // Amazon：对指定位置截图（主图、价格、产品详情等）
  if (data && isAmazon) {
    const screenshots = await runAmazonScreenshots(tabId)
    if (screenshots.length) data.screenshots = screenshots
  }

  if (createdByUs) await chrome.tabs.remove(tabId).catch(() => {})
  return data
}

/** 在页面内裁剪截图到指定元素区域（依赖 amazon.js 的 cropImageToRect） */
function cropScreenshotToElement(dataUrl, rect, dpr) {
  const amazon = typeof window.__HOU_AMAZON !== 'undefined' ? window.__HOU_AMAZON : null
  if (!amazon?.cropImageToRect) return dataUrl
  return amazon.cropImageToRect(dataUrl, rect, dpr)
}

/** Amazon 指定位置截图：滚动到各目标元素，截取视口后裁剪为元素区域 */
async function runAmazonScreenshots(tabId) {
  await chrome.tabs.update(tabId, { active: true }).catch(() => {})
  const getTargets = () => {
    const amazon = typeof window.__HOU_AMAZON !== 'undefined' ? window.__HOU_AMAZON : null
    return amazon?.getScreenshotTargets?.() ?? []
  }
  const scrollTo = (selector) => {
    const amazon = typeof window.__HOU_AMAZON !== 'undefined' ? window.__HOU_AMAZON : null
    return amazon?.scrollElementIntoView?.(selector) ?? null
  }

  const [targetsRes] = await chrome.scripting
    .executeScript({ target: { tabId }, func: getTargets })
    .catch(() => [{}])
  const targets = targetsRes?.result ?? []
  if (!targets.length) return []

  const screenshots = []
  for (const t of targets) {
    try {
      const [scrollRes] = await chrome.scripting.executeScript({ target: { tabId }, func: scrollTo, args: [t.selector] }).catch(() => [{}])
      const rect = scrollRes?.result
      await new Promise((r) => setTimeout(r, 500))
      const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' })
      if (rect && rect.width > 0 && rect.height > 0) {
        const [cropRes] = await chrome.scripting
          .executeScript({ target: { tabId }, func: cropScreenshotToElement, args: [dataUrl, rect, rect.dpr || 1] })
          .catch(() => [{}])
        const cropped = cropRes?.result
        screenshots.push(typeof cropped === 'string' ? cropped : dataUrl)
      } else {
        screenshots.push(dataUrl)
      }
    } catch (_) {
      break
    }
  }
  return screenshots
}

/** 主流程：获取或创建 tab，执行提取 */
async function doFetch(url, opts) {
  const { postMessage, requestId, apiBase, inlineImages, wereadImagesOnly } = opts
  const isWeread = /weread\.qq\.com/.test(url)
  const isFeishu = /feishu\.cn|feishubase\.com/.test(url)
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
    } else if (isFeishu) {
      const [a, b, c] = await Promise.all([
        chrome.tabs.query({ url: '*://*.feishu.cn/*' }),
        chrome.tabs.query({ url: '*://feishu.cn/*' }),
        chrome.tabs.query({ url: '*://*.feishubase.com/*' }),
      ])
      const existing = [...a, ...b, ...c]
      const reqPath = url.split('?')[0]
      const match = existing.find((t) => (t.url || '').split('?')[0] === reqPath)
      if (match) {
        tabId = match.id
      } else if (existing.length > 0) {
        tabId = existing[0].id
        await chrome.tabs.update(tabId, { url, active: true })
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
      data = wereadImagesOnly
        ? await fetchWereadImagesOnly(url, createdByUs, tabId)
        : await fetchWereadScreenshot(url, createdByUs, tabId)
    } else {
      const domOpts = isFeishu ? { useScrollExtract: true, inlineImages } : { inlineImages }
      data = await runDomExtraction(tabId, url, createdByUs, needLoad, domOpts)
    }

    if (
      data &&
      (data.content ||
        data.title ||
        data.html ||
        data.screenshots?.length ||
        (data.inlineImageMap && Object.keys(data.inlineImageMap).length))
    ) {
      respond({ success: true, data })
    } else {
      respond({ success: false, error: '未能提取到内容' })
    }
  } catch (err) {
    if (tabId && createdByUs) chrome.tabs.remove(tabId).catch(() => {})
    respond({ success: false, error: err?.message || '提取失败' })
  }
}

/** 通过扩展获取 PDF（复用浏览器 cookies，统一方案） */
async function fetchPdfWithCookies(url) {
  const u = (url || '').trim()
  if (!u.startsWith('http://') && !u.startsWith('https://')) {
    return { success: false, error: '无效的 URL' }
  }
  try {
    const list = await chrome.cookies.getAll({ url: u })
    const cookieStr = list.map((c) => `${c.name}=${c.value}`).join('; ')
    const headers = {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'application/pdf,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    if (cookieStr) headers['Cookie'] = cookieStr

    const res = await fetch(u, { headers, credentials: 'omit' })
    if (!res.ok) return { success: false, error: `HTTP ${res.status}` }
    const ct = (res.headers.get('content-type') || '').toLowerCase()
    if (!ct.includes('pdf') && !ct.includes('octet-stream')) {
      return { success: false, error: '响应不是 PDF 格式' }
    }
    const buf = await res.arrayBuffer()
    const bytes = new Uint8Array(buf)
    let binary = ''
    const chunkSize = 8192
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length))
      binary += String.fromCharCode.apply(null, chunk)
    }
    const base64 = btoa(binary)
    return { success: true, base64, size: buf.byteLength }
  } catch (e) {
    return { success: false, error: e?.message || '下载失败' }
  }
}

/** 导出指定域名的 cookies 为 Netscape 格式（供 yt-dlp 等使用） */
async function exportCookiesForDomain(domain) {
  const d = (domain || '').trim().toLowerCase().replace(/^\./, '')
  if (!d) return { success: false, error: '缺少域名' }
  const baseUrl = d.startsWith('http') ? d : `https://www.${d}`
  const list = await chrome.cookies.getAll({ url: baseUrl })
  if (!list || list.length === 0) return { success: false, error: `未找到 ${domain} 的 cookies，请先在浏览器中登录` }
  const lines = ['# Netscape HTTP Cookie File', '# https://youtube.com']
  for (const c of list) {
    const host = (c.domain || '').startsWith('.') ? c.domain.slice(1) : c.domain
    const flag = (c.hostOnly === false) ? 'TRUE' : 'FALSE'
    const path = c.path || '/'
    const secure = c.secure ? 'TRUE' : 'FALSE'
    const exp = (c.expirationDate && c.expirationDate > 0) ? Math.floor(c.expirationDate) : 0
    lines.push([host, flag, path, secure, exp, c.name || '', (c.value || '').replace(/\t/g, ' ')].join('\t'))
  }
  return { success: true, content: lines.join('\n') }
}

// Port 长连接：保持 SW 活跃，避免 sendResponse 因 SW 被 kill 而丢失
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'hou-cli-web-reader') return

  port.onMessage.addListener(async (msg) => {
    if (msg.type === 'HOU_CLI_EXPORT_COOKIES') {
      const requestId = msg.requestId || 'cookies-' + Date.now()
      try {
        const res = await exportCookiesForDomain(msg.domain || 'youtube.com')
        port.postMessage({ type: 'HOU_CLI_EXPORT_COOKIES_RESULT', requestId, ...res })
      } catch (e) {
        port.postMessage({ type: 'HOU_CLI_EXPORT_COOKIES_RESULT', requestId, success: false, error: e?.message || '导出失败' })
      }
      return
    }
    if (msg.type === 'HOU_CLI_FETCH_PDF' && msg.url) {
      const requestId = msg.requestId || 'pdf-' + Date.now()
      try {
        const res = await fetchPdfWithCookies(msg.url)
        port.postMessage({ type: 'HOU_CLI_FETCH_PDF_RESULT', requestId, ...res })
      } catch (e) {
        port.postMessage({ type: 'HOU_CLI_FETCH_PDF_RESULT', requestId, success: false, error: e?.message || '下载失败' })
      }
      return
    }
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
    const inlineImages = !!msg.inlineImages
    const wereadImagesOnly = !!msg.wereadImagesOnly
    doFetch(url, { postMessage, requestId, apiBase, inlineImages, wereadImagesOnly }).catch(() => {
      postMessage({ type: 'HOU_CLI_FETCH_RESULT', requestId, success: false, error: '提取失败' })
    })
  })
})

// 兼容旧版 sendMessage
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === 'export_cookies') {
    exportCookiesForDomain(msg.domain || 'youtube.com')
      .then((res) => sendResponse?.(res))
      .catch((e) => sendResponse?.({ success: false, error: e?.message || '导出失败' }))
    return true
  }
  if (msg.action === 'fetch_pdf' && msg.url) {
    fetchPdfWithCookies(msg.url)
      .then((res) => sendResponse?.(res))
      .catch((e) => sendResponse?.({ success: false, error: e?.message || '下载失败' }))
    return true
  }
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
  const inlineImages = !!msg.inlineImages
  const wereadImagesOnly = !!msg.wereadImagesOnly
  doFetch(url, { postMessage, requestId, apiBase, inlineImages, wereadImagesOnly }).catch(() => {
    postMessage({ success: false, error: '提取失败' })
  })

  return true
})
