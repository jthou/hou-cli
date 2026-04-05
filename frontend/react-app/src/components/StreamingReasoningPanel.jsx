/**
 * 深度思考 / reasoning_content 流式展示（与后端 LLMService 下发的 __REASONING__: 前缀配套）。
 * 时间：2026-04-04；理由：用户要求思考过程可在前端实时看到；方法：SSE 侧写累积，不进入主 Markdown 正文。
 */
export default function StreamingReasoningPanel({ text, className = '' }) {
  if (!text || String(text).trim() === '') return null
  return (
    <details open className={`rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-2 ${className}`}>
      <summary className="cursor-pointer text-xs font-medium text-violet-100/95 select-none">
        思考过程（流式）
      </summary>
      <pre className="mt-2 max-h-64 overflow-auto text-[11px] leading-relaxed whitespace-pre-wrap break-words text-muted">
        {text}
      </pre>
    </details>
  )
}
