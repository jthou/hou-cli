/**
 * Amazon 产品页 DOM 提取 - 注入到目标页面执行
 * 展开 #productDetails_feature_div 内折叠项，提供产品详情选择器
 */
(function () {
  const AMAZON_URL_RE = /amazon\.(com|co\.\w{2}|cn|co\.jp)\//
  const AMAZON_PRODUCT_RE = /amazon\.(com|co\.\w{2}|cn|co\.jp)\/(dp|gp\/product)/

  function isAmazonUrl(href) {
    return AMAZON_URL_RE.test(href || '')
  }

  function isAmazonProductPage(href) {
    return AMAZON_PRODUCT_RE.test(href || '')
  }

  /** 点击 "See more product details" 加载 #productDetails_feature_div（默认未加载，需点击才加载） */
  function loadProductDetailsSection() {
    const link = document.getElementById('seeMoreDetailsLink') || document.querySelector('a[href="#productDetails"]')
    if (!link || link.offsetParent === null) return 0
    const root = document.getElementById('productDetails_feature_div')
    if (root && (root.innerText || '').trim().length > 100) return 0
    try {
      link.scrollIntoView({ block: 'center', behavior: 'auto' })
      link.click()
      return 1
    } catch (_) {
      return 0
    }
  }

  function expandProductDetails() {
    const root = document.getElementById('productDetails_feature_div')
    if (!root) return 0
    let clicked = 0
    root.querySelectorAll('.a-expander-header[aria-expanded="false"], [data-action="a-expander-toggle"][aria-expanded="false"]').forEach((el) => {
      try {
        el.scrollIntoView({ block: 'center', behavior: 'auto' })
        el.click()
        clicked++
      } catch (_) {}
    })
    root.querySelectorAll('[data-expanded="false"].a-expander-content').forEach((el) => {
      const trigger = el.previousElementSibling?.querySelector?.('[data-action="a-expander-toggle"]') || el.closest('.a-expander-container')?.querySelector?.('.a-expander-header')
      if (trigger && trigger.getAttribute('aria-expanded') === 'false') {
        try {
          trigger.scrollIntoView({ block: 'center', behavior: 'auto' })
          trigger.click()
          clicked++
        } catch (_) {}
      }
    })
    return clicked
  }

  const SELECTORS = [
    '#productDetails_feature_div',
    '#prodDetails',
    '#productDetails',
    '#detailBullets_feature_div',
    '#feature-bullets',
  ]

  /** 指定位置截图目标：id、选择器、描述 */
  const SCREENSHOT_TARGETS = [
    { id: 'productImage', selector: '#imgTagWrapperId, #landingImage, .imgTagWrapper img, #main-image-container', desc: '主图' },
    { id: 'titlePrice', selector: '#titleSection, #corePrice_feature_div, #corePriceDisplay_desktop', desc: '标题与价格' },
    { id: 'featureBullets', selector: '#feature-bullets, #featurebullets_feature_div', desc: '产品要点' },
    { id: 'productDetails', selector: '#productDetails_feature_div', desc: '产品详情' },
  ]

  /** 获取可截图的元素列表（存在且可见），返回 { id, selector } */
  function getScreenshotTargets() {
    const out = []
    for (const t of SCREENSHOT_TARGETS) {
      const sel = t.selector.split(/,\s*/)[0]
      const el = document.querySelector(sel)
      if (el && el.offsetParent !== null && el.getBoundingClientRect().height > 0) {
        out.push({ id: t.id, selector: sel })
      }
    }
    return out
  }

  /** 滚动到指定元素并返回其视口内位置（CSS 像素）及 devicePixelRatio */
  function scrollElementIntoView(selector) {
    const el = document.querySelector(selector)
    if (!el) return null
    el.scrollIntoView({ block: 'center', behavior: 'auto' })
    const r = el.getBoundingClientRect()
    return { x: r.x, y: r.y, width: r.width, height: r.height, dpr: window.devicePixelRatio || 1 }
  }

  /** 将全屏截图裁剪为指定元素区域，dataUrl 为原图，rect 为 {x,y,width,height} CSS 像素，dpr 为设备像素比 */
  function cropImageToRect(dataUrl, rect, dpr) {
    if (!dataUrl || !rect || rect.width <= 0 || rect.height <= 0) return dataUrl
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        try {
          const scale = dpr || 1
          const x = Math.max(0, Math.min(rect.x * scale, img.width - 1))
          const y = Math.max(0, Math.min(rect.y * scale, img.height - 1))
          const w = Math.max(1, Math.min(rect.width * scale, img.width - x))
          const h = Math.max(1, Math.min(rect.height * scale, img.height - y))
          const canvas = document.createElement('canvas')
          canvas.width = w
          canvas.height = h
          const ctx = canvas.getContext('2d')
          if (!ctx) { resolve(dataUrl); return }
          ctx.drawImage(img, x, y, w, h, 0, 0, w, h)
          resolve(canvas.toDataURL('image/png'))
        } catch (_) {
          resolve(dataUrl)
        }
      }
      img.onerror = () => resolve(dataUrl)
      img.src = dataUrl
    })
  }

  window.__HOU_AMAZON = {
    isAmazonUrl,
    isAmazonProductPage,
    loadProductDetailsSection,
    expandProductDetails,
    SELECTORS,
    SCREENSHOT_TARGETS,
    getScreenshotTargets,
    scrollElementIntoView,
    cropImageToRect,
  }
})()
