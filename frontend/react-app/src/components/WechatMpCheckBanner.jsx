/**
 * 公众号草稿对话框打开时立即检查 token + 白名单，有问题在顶部显示警告。
 * 时间：2025-03-19；理由：不要等到后续操作才发现有问题。
 */
import { useState, useEffect } from 'react'

export default function WechatMpCheckBanner() {
  const [status, setStatus] = useState('loading') // loading | ok | error
  const [error, setError] = useState(null)
  const [hint, setHint] = useState(null)

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    setError(null)
    setHint(null)
    fetch('/api/wechat-mp/check')
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        if (data.success) {
          setStatus('ok')
        } else {
          setStatus('error')
          setError(data.error || '未知错误')
          setHint(data.hint || null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setStatus('error')
          setError(err?.message || '请求失败')
          setHint(null)
        }
      })
    return () => { cancelled = true }
  }, [])

  if (status === 'loading') {
    return (
      <div className="mb-4 px-4 py-2 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-200 text-sm">
        正在检查公众号 API（token、白名单）…
      </div>
    )
  }
  if (status === 'ok') return null

  return (
    <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-200 text-sm space-y-1">
      <p className="font-medium">⚠ 公众号 API 不可用</p>
      <p className="text-xs text-red-200/90 break-words">{error}</p>
      {hint && <p className="text-xs text-amber-200/90 mt-1">{hint}</p>}
    </div>
  )
}
