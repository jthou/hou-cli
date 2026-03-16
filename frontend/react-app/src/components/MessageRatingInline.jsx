/**
 * 对单条助手回复打分+理由（时间：2025-03-15；理由：供系统提示词注入、调整后续回答）
 * 理由输入框：点击展开、失焦且为空时缩回（方案1）
 * 提交后：显示「继续提问」引导进入下一轮对话
 */
import { useState } from 'react'

export default function MessageRatingInline({ sessionId, messageId, onRated, onScrollToInput }) {
  const [score, setScore] = useState(null)
  const [reason, setReason] = useState('')
  const [reasonFocused, setReasonFocused] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const reasonExpanded = reasonFocused || (reason && reason.trim().length > 0)

  const handleSubmit = async () => {
    if (!sessionId || !messageId || score == null || submitting) return
    setSubmitting(true)
    try {
      const r = await fetch('/api/chat/rate-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          score,
          reason: reason.trim() || undefined,
        }),
      })
      const d = await r.json()
      if (d.success) {
        setSubmitted(true)
        onRated?.()
      }
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <span className="inline-flex items-center gap-2 text-xs">
        <span className="text-muted">
          已打分 {score}/5
          {reason.trim() && ` · ${reason.trim().slice(0, 30)}${reason.length > 30 ? '…' : ''}`}
        </span>
        {onScrollToInput && (
          <button
            type="button"
            onClick={onScrollToInput}
            className="text-accent hover:underline"
          >
            继续提问
          </button>
        )}
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 flex-wrap">
      <span className="text-xs text-muted">打分：</span>
      {[1, 2, 3, 4, 5].map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => setScore(s)}
          disabled={submitting}
          className={`w-6 h-6 text-xs rounded border ${
            score === s ? 'border-accent bg-accent/20 text-accent' : 'border-border text-muted hover:bg-white/5'
          }`}
        >
          {s}
        </button>
      ))}
      <input
        type="text"
        placeholder="理由（可选）"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        onFocus={() => setReasonFocused(true)}
        onBlur={() => setReasonFocused(false)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        className={`px-1.5 py-0.5 text-xs rounded border border-border bg-black/20 text-fg placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent transition-all duration-200 ${
          reasonExpanded ? 'w-48 min-w-[12rem]' : 'w-20 min-w-[4rem]'
        }`}
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={score == null || submitting}
        className="px-2 py-0.5 text-xs rounded border border-border text-muted hover:bg-white/5 disabled:opacity-50"
      >
        {submitting ? '…' : '提交'}
      </button>
    </span>
  )
}
