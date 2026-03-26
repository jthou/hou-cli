/**
 * 大图查看：Mac 触控板双指捏合（wheel+ctrlKey）缩放；放大后双指滑动平移；单指针拖拽平移。
 * 100% 时普通双指滑动不拦截，便于外层区域滚动（若父级可滚）。
 */
import { useState, useRef, useEffect, useLayoutEffect, useCallback } from 'react'

/**
 * @param {Object} props
 * @param {string} props.src
 * @param {string} [props.alt='']
 * @param {string} [props.className] - 视口外层（占满父级 flex 区域）
 * @param {string} [props.imgClassName] - 额外样式（圆角、描边等）；尺寸策略见 fitContainer
 * @param {boolean} [props.fitContainer=false] - true：object-contain 铺满视口（小图会被放大，可能发糊）；false：默认不超过原图像素，仅缩小时适配容器
 */
export default function ZoomPanFigure({
  src,
  alt = '',
  className = '',
  imgClassName = '',
  fitContainer = false,
}) {
  const [scale, setScale] = useState(1)
  const [tx, setTx] = useState(0)
  const [ty, setTy] = useState(0)
  const [dragging, setDragging] = useState(false)
  const viewportRef = useRef(null)
  const dragRef = useRef(null)
  const txRef = useRef(0)
  const tyRef = useRef(0)
  const scaleRef = useRef(1)
  useEffect(() => {
    txRef.current = tx
    tyRef.current = ty
  }, [tx, ty])
  scaleRef.current = scale

  useEffect(() => {
    setScale(1)
    setTx(0)
    setTy(0)
  }, [src])

  const resetView = useCallback(() => {
    setScale(1)
    setTx(0)
    setTy(0)
  }, [])

  // useLayoutEffect：首帧即可拿到 ref；截图弹层父级为 flex+justify-center，useEffect 偶发 ref 仍空导致从未绑定 wheel
  useLayoutEffect(() => {
    const el = viewportRef.current
    if (!el) return undefined

    const wheelDeltaToPixels = (e) => {
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

    const onWheel = (e) => {
      const pinchZoom = e.ctrlKey === true

      if (pinchZoom) {
        e.preventDefault()
        e.stopPropagation()
        const { dy } = wheelDeltaToPixels(e)
        const factor = Math.exp(-dy * 0.007)
        setScale((s) => {
          const next = Math.min(8, Math.max(1, s * factor))
          if (next <= 1) {
            setTx(0)
            setTy(0)
          }
          return next
        })
        return
      }

      if (scaleRef.current > 1) {
        e.preventDefault()
        e.stopPropagation()
        const { dx, dy } = wheelDeltaToPixels(e)
        setTx((t) => t - dx)
        setTy((t) => t - dy)
        return
      }

      // 全屏灯箱：普通滚轮缩放（鼠标 / 触控板竖滑）
      e.preventDefault()
      e.stopPropagation()
      const mul = e.deltaY > 0 ? 0.92 : 1.08
      setScale((s) => {
        const next = Math.min(8, Math.max(1, s * mul))
        if (next <= 1) {
          setTx(0)
          setTy(0)
        }
        return next
      })
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [src])

  const onPointerDown = useCallback((e) => {
    if (e.button !== 0) return
    if (scale <= 1) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    setDragging(true)
    dragRef.current = {
      sx: e.clientX,
      sy: e.clientY,
      tx0: txRef.current,
      ty0: tyRef.current,
    }
  }, [scale])

  const onPointerMove = useCallback((e) => {
    const d = dragRef.current
    if (!d) return
    if (scale <= 1) return
    setTx(d.tx0 + e.clientX - d.sx)
    setTy(d.ty0 + e.clientY - d.sy)
  }, [scale])

  const endDrag = useCallback(() => {
    dragRef.current = null
    setDragging(false)
  }, [])

  const onPointerUp = useCallback(
    (e) => {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId)
      } catch (_) {
        /* ignore */
      }
      endDrag()
    },
    [endDrag]
  )

  const onDoubleClick = useCallback((e) => {
    e.stopPropagation()
    resetView()
  }, [resetView])

  // 默认 1:1 且无平移时不用 transform：整图被提到 GPU 合成层 + 子像素 translate 时，Chrome 下截图/文字常比列表里更糊
  const plainCenter = scale === 1 && tx === 0 && ty === 0

  const imgSizeClass = fitContainer
    ? 'max-h-full max-w-full w-auto h-auto object-contain'
    : 'h-auto w-auto max-h-[min(100%,max-content)] max-w-[min(100%,max-content)]'

  return (
    <div
      ref={viewportRef}
      role="presentation"
      className={`relative min-h-0 w-full flex-1 overflow-hidden touch-none select-none ${className}`.trim()}
      style={{ cursor: scale > 1 ? (dragging ? 'grabbing' : 'grab') : 'zoom-in' }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onLostPointerCapture={endDrag}
      onDoubleClick={onDoubleClick}
    >
      {plainCenter ? (
        <div className="flex h-full w-full min-h-0 min-w-0 items-center justify-center">
          <img
            src={src}
            alt={alt}
            draggable={false}
            className={`pointer-events-none shadow-2xl ${imgSizeClass} ${imgClassName}`.trim()}
          />
        </div>
      ) : (
        <div
          className="absolute left-1/2 top-1/2 flex items-center justify-center"
          style={{
            transform: `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px)) scale(${scale})`,
            transformOrigin: 'center center',
          }}
        >
          <img
            src={src}
            alt={alt}
            draggable={false}
            className={`pointer-events-none shadow-2xl ${imgSizeClass} ${imgClassName}`.trim()}
          />
        </div>
      )}
    </div>
  )
}
