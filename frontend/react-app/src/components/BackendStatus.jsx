import { useState, useEffect } from 'react'

export default function BackendStatus() {
  const [status, setStatus] = useState({ text: '连接中...', ok: false })

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/heartbeat/status')
        const data = await res.json()
        if (data.success && data.status) {
          const s = data.status
          setStatus({
            text: s.is_running ? '运行中' : '已停止',
            ok: s.is_running,
          })
        } else {
          setStatus({ text: '获取失败', ok: false })
        }
      } catch {
        setStatus({ text: '连接失败', ok: false })
      }
    }
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${
          status.ok ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500'
        }`}
      />
      <span>{status.text}</span>
    </div>
  )
}
