/**
 * 在浏览器空闲时执行回调，避免阻塞主线程
 * @param {() => void} fn
 * @param {{ timeout?: number }} opts - timeout: 最多等待毫秒数，超时后强制执行
 */
export function runWhenIdle(fn, opts = {}) {
  const { timeout = 50 } = opts
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(fn, { timeout })
  } else {
    setTimeout(fn, 0)
  }
}
