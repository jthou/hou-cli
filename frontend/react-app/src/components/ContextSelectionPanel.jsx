/**
 * 展示本轮对话注入 LLM 的历史消息筛选结果（编排侧，非模型 CoT）。
 *
 * 时间：2026-03-13；理由：混合历史策略需可解释；方法与后端 __CTX_META__ / hybrid_history 对齐。
 */
import { useState } from 'react'

const PREFIX = '__CTX_META__:'

/** @param {string} raw */
export function parseContextMetaChunk(raw) {
  if (raw == null || typeof raw !== 'string' || !raw.startsWith(PREFIX)) return null
  try {
    const data = JSON.parse(raw.slice(PREFIX.length).trim())
    return data?.type === 'context_selection' ? data : null
  } catch {
    return null
  }
}

const sourceLabel = (s) => {
  if (s === 'recent_tail') return '最近保留'
  if (s === 'keyword_hit') return '关键词命中'
  return s || '—'
}

/** @param {{ meta: object | null }} props */
export default function ContextSelectionPanel({ meta }) {
  const [open, setOpen] = useState(true)
  if (!meta || meta.type !== 'context_selection') return null

  const strat = meta.strategy === 'hybrid' ? '混合（最近 + 检索）' : '全部历史'
  const items = Array.isArray(meta.items) ? meta.items : []

  return (
    <div className="rounded-lg border border-cyan-500/25 bg-cyan-500/5 px-3 py-2 text-xs text-muted w-full max-w-[85%]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 text-left text-cyan-200/90 hover:text-cyan-100"
      >
        <span>
          <span className="font-medium">本次上下文</span>
          <span className="text-muted ml-2">
            已选 {meta.used_count ?? items.length} / 会话共 {meta.total_in_session ?? '—'} 条 · {strat}
          </span>
        </span>
        <span className="shrink-0 text-[10px] opacity-80">{open ? '收起' : '展开'}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 border-t border-cyan-500/20 pt-2">
          {meta.query_preview && (
            <p className="text-[11px] text-muted/90">
              <span className="text-muted">检索依据（摘要）：</span>
              {meta.query_preview}
            </p>
          )}
          <ul className="max-h-40 overflow-y-auto space-y-1">
            {items.map((it, idx) => (
              <li
                key={`${it.message_id || idx}-${it.index}`}
                className="flex flex-wrap gap-x-2 gap-y-0.5 rounded bg-black/20 px-2 py-1"
              >
                <span className="shrink-0 font-medium text-fg/90">
                  {it.role === 'user' ? '用户' : '助手'}
                </span>
                <span className="shrink-0 rounded bg-white/10 px-1 text-[10px] text-cyan-300/90">
                  {sourceLabel(it.source)}
                </span>
                <span className="min-w-0 break-words text-muted">{it.preview || '（空）'}</span>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-muted/70 leading-snug">
            说明：以上为系统选入模型上下文的聊天记录摘要，用于核对「带了哪些历史」；不是模型的推理过程。若需完整思维链，须模型与 API 支持且另行合规开启。
          </p>
        </div>
      )}
    </div>
  )
}
