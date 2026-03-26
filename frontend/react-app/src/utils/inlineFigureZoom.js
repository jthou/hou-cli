/**
 * 在 .wechat-draft-preview 内为 Markdown 图片挂载「内联缩放 + 放大后平移」，不依赖弹层。
 * 与点击图片打开灯箱（onImgClick）共存：拖拽平移后短暂抑制一次 click，避免误开弹层。
 *
 * Mac 触控板：双指捏合在 Chrome/Safari 上表现为 wheel + ctrlKey → 缩放；
 * 双指滑动为普通 wheel → 未放大时**不拦截**，便于继续滚动预览正文；放大后转为平移图片。
 */

const VIEWPORT_CLS = 'wechat-inline-zoom-viewport'
const INNER_CLS = 'wechat-inline-zoom-inner'

/** wheel deltaY/deltaX 近似换算为像素（LINE/PAGE 模式） */
function wheelDeltaToPixels(e) {
  let dx = e.deltaX
  let dy = e.deltaY
  if (e.deltaMode === 1) {
    dx *= 16
    dy *= 16
  } else if (e.deltaMode === 2) {
    dx *= 800
    dy *= 800
  }
  return { dx, dy }
}

/**
 * 拆掉内联缩放包裹，还原为裸 img（供关闭 zoom 或重新挂载前使用）
 * @param {HTMLElement} root
 */
export function unmountInlineFigureZoom(root) {
  if (!root?.querySelectorAll) return
  const vps = [...root.querySelectorAll(`.${VIEWPORT_CLS}`)]
  for (const vp of vps) {
    const inner = vp.querySelector(`.${INNER_CLS}`)
    const im = inner?.querySelector('img')
    const parent = vp.parentNode
    if (im && parent) {
      parent.insertBefore(im, vp)
      parent.removeChild(vp)
    }
  }
}

/**
 * @param {HTMLElement} root - 预览根节点（含 .wechat-draft-preview）
 */
export function mountInlineFigureZoom(root) {
  if (!root?.querySelectorAll) return () => {}

  const imgs = [...root.querySelectorAll('img')].filter((img) => {
    if (!img.getAttribute('src')) return false
    if (img.closest(`.${VIEWPORT_CLS}`)) return false
    return true
  })

  const disposers = imgs.map((img) => mountOne(img))
  return () => disposers.forEach((fn) => fn())
}

function mountOne(img) {
  const viewport = document.createElement('div')
  viewport.className = VIEWPORT_CLS
  const inner = document.createElement('div')
  inner.className = INNER_CLS

  const parent = img.parentNode
  if (!parent) return () => {}
  parent.insertBefore(viewport, img)
  inner.appendChild(img)
  viewport.appendChild(inner)

  let scale = 1
  let tx = 0
  let ty = 0
  let drag = null
  const gesture = { moved: false, suppressClick: false }

  const applyTransform = () => {
    if (scale <= 1) {
      scale = 1
      tx = 0
      ty = 0
    }
    inner.style.transform = `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px)) scale(${scale})`
    inner.style.transformOrigin = 'center center'
  }

  const syncViewportMinHeight = () => {
    const prev = inner.style.transform
    inner.style.transform = 'translate(-50%, -50%) scale(1)'
    const h = Math.max(img.offsetHeight || img.naturalHeight || 1, 1)
    viewport.style.minHeight = `${h}px`
    inner.style.transform = prev
  }

  const onWheel = (e) => {
    const pinchZoom = e.ctrlKey === true

    if (pinchZoom) {
      e.preventDefault()
      e.stopPropagation()
      const { dy } = wheelDeltaToPixels(e)
      const factor = Math.exp(-dy * 0.007)
      scale = Math.min(8, Math.max(1, scale * factor))
      applyTransform()
      if (scale <= 1) syncViewportMinHeight()
      return
    }

    if (scale > 1) {
      e.preventDefault()
      e.stopPropagation()
      const { dx, dy } = wheelDeltaToPixels(e)
      tx -= dx
      ty -= dy
      applyTransform()
      return
    }

    // 100% 时：普通双指滑动交给外层 Markdown 预览滚动（不 preventDefault）
  }

  const onPointerDown = (e) => {
    if (e.button !== 0) return
    if (scale <= 1) return
    viewport.setPointerCapture(e.pointerId)
    drag = { sx: e.clientX, sy: e.clientY, tx0: tx, ty0: ty }
    gesture.moved = false
  }

  const onPointerMove = (e) => {
    if (!drag) return
    const dx = e.clientX - drag.sx
    const dy = e.clientY - drag.sy
    if (Math.hypot(dx, dy) > 6) gesture.moved = true
    tx = drag.tx0 + dx
    ty = drag.ty0 + dy
    applyTransform()
  }

  const onPointerUp = (e) => {
    if (drag && gesture.moved) {
      gesture.suppressClick = true
      window.setTimeout(() => {
        gesture.suppressClick = false
      }, 320)
    }
    drag = null
    try {
      viewport.releasePointerCapture(e.pointerId)
    } catch (_) {
      /* ignore */
    }
  }

  const onClickCapture = (e) => {
    if (gesture.suppressClick) {
      e.preventDefault()
      e.stopPropagation()
      gesture.suppressClick = false
    }
  }

  const onDblClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    scale = 1
    tx = 0
    ty = 0
    applyTransform()
    syncViewportMinHeight()
  }

  viewport.addEventListener('wheel', onWheel, { passive: false })
  viewport.addEventListener('pointerdown', onPointerDown)
  viewport.addEventListener('pointermove', onPointerMove)
  viewport.addEventListener('pointerup', onPointerUp)
  viewport.addEventListener('pointercancel', onPointerUp)
  viewport.addEventListener('click', onClickCapture, true)
  viewport.addEventListener('dblclick', onDblClick)

  const onImgLoad = () => syncViewportMinHeight()
  img.addEventListener('load', onImgLoad)
  requestAnimationFrame(() => syncViewportMinHeight())

  applyTransform()

  return () => {
    viewport.removeEventListener('wheel', onWheel)
    viewport.removeEventListener('pointerdown', onPointerDown)
    viewport.removeEventListener('pointermove', onPointerMove)
    viewport.removeEventListener('pointerup', onPointerUp)
    viewport.removeEventListener('pointercancel', onPointerUp)
    viewport.removeEventListener('click', onClickCapture, true)
    viewport.removeEventListener('dblclick', onDblClick)
    img.removeEventListener('load', onImgLoad)
    const p = viewport.parentNode
    if (p?.contains?.(viewport) && img.parentNode === inner) {
      try {
        p.insertBefore(img, viewport)
        p.removeChild(viewport)
      } catch (_) {
        /* 已由 React 替换 innerHTML 时父节点可能已变 */
      }
    }
  }
}
