/**
 * 公众号草稿编辑处展示本机出口 IP，便于复制到微信 API IP 白名单。
 * 调用 GET /api/wechat-mp/outbound-ip，展示「本机出口 IP（白名单备用）」。
 */
import { useState, useEffect } from 'react'

const labelCls = 'block text-sm text-[#94a3b8] mb-1'
const valueCls = 'text-[#e2e8f0] font-mono text-sm'

export default function WechatOutboundIpHint() {
  const [ip, setIp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetch('/api/wechat-mp/outbound-ip')
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (cancelled) return
        if (ok && data.success && data.ip) setIp(data.ip)
        else {
          const msg = data?.detail || data?.message || '获取失败'
          const friendly = /SSL|EOF|protocol|证书/i.test(msg)
            ? '无法获取出口 IP，请检查网络或代理后重试'
            : msg
          setError(friendly)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || '请求失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const handleCopy = () => {
    if (!ip) return
    navigator.clipboard.writeText(ip).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div className="mt-2">
        <span className={labelCls}>本机出口 IP（白名单备用）</span>
        <p className={`${valueCls} text-[#64748b]`}>获取中…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className="mt-2">
        <span className={labelCls}>本机出口 IP（白名单备用）</span>
        <p className="text-xs text-amber-400/90">{error}</p>
      </div>
    )
  }
  if (!ip) return null

  return (
    <div className="mt-2">
      <label className={labelCls}>本机出口 IP（白名单备用）</label>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={valueCls}>{ip}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="px-2 py-1 text-xs rounded bg-white/10 text-[#94a3b8] hover:text-white hover:bg-white/15"
        >
          {copied ? '已复制' : '复制'}
        </button>
      </div>
    </div>
  )
}
