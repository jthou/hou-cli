import { useEffect, useState } from 'react'

/**
 * 检测 Hou CLI 浏览器扩展是否已加载（通过 PING/PONG）
 * @param {Object} options
 * @param {number} [options.timeoutMs=15000] 超时毫秒数，超时后停止 ping
 * @param {boolean} [options.initialNull=false] 若 true，初始为 null，超时后为 false；若 false，初始为 false
 * @returns {boolean|null} true=已加载, false=未检测到, null=检测中（仅当 initialNull 时）
 */
export function useExtensionReady({ timeoutMs = 15000, initialNull = false } = {}) {
  const [ready, setReady] = useState(initialNull ? null : false)

  useEffect(() => {
    let resolved = false
    const setResolved = (v) => {
      if (!resolved) {
        resolved = true
        setReady(v)
      }
    }

    const check = () => {
      if (typeof window !== 'undefined' && window.__HOU_CLI_EXTENSION_LOADED) {
        setResolved(true)
        return true
      }
      return false
    }

    if (check()) return

    const handler = (e) => {
      if (e.data?.type === 'HOU_CLI_PONG') {
        setResolved(true)
        window.removeEventListener('message', handler)
      }
    }
    window.addEventListener('message', handler)

    const ping = () => {
      if (window.__HOU_CLI_EXTENSION_LOADED) return
      window.postMessage({ type: 'HOU_CLI_PING' }, '*')
    }
    ping()

    const id = setInterval(() => {
      if (check()) {
        clearInterval(id)
        return
      }
      ping()
    }, 600)

    const stop = setTimeout(() => {
      setResolved(false)
      clearInterval(id)
    }, timeoutMs)

    return () => {
      clearInterval(id)
      clearTimeout(stop)
      window.removeEventListener('message', handler)
    }
  }, [timeoutMs])

  return ready
}
