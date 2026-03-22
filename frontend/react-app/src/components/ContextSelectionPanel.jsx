/**
 * 展示本轮对话注入 LLM 的历史消息筛选结果（编排侧，非模型 CoT）。
 *
 * 时间：2026-03-13；理由：混合历史策略需可解释；方法与后端 __CTX_META__ / hybrid_history 对齐。
 */
import { useState } from 'react'

/** 时间：2026-03-13；理由：解析逻辑与 utils 共用；方法：从 streamContextMeta 再导出，兼容旧 import 路径 */
export { parseContextMetaChunk } from '../utils/streamContextMeta'

const sourceLabel = (s) => {
  if (s === 'recent_tail') return '最近保留'
  if (s === 'keyword_hit') return '关键词命中'
  // 时间：2026-03-13；理由：article_writing __CTX_META__ 素材轨；方法：与 backend article_writing_context_meta source 对齐
  if (s === 'injected_draft') return '草稿锚点'
  if (s === 'injected_reference') return '参考块'
  if (s === 'injected_profile') return '写作画像'
  if (s === 'injected_constraints') return '系统检出'
  if (s === 'user_turn') return '本轮指令'
  return s || '—'
}

/** @param {{ meta: object | null }} props */
export default function ContextSelectionPanel({ meta }) {
  const [open, setOpen] = useState(true)
  if (!meta || meta.type !== 'context_selection') return null

  const strat =
    meta.strategy === 'hybrid'
      ? '混合（最近 + 检索）'
      : meta.strategy === 'article_writing'
        ? '写作助手（会话聊天未注入）'
        : '全部历史'
  const items = Array.isArray(meta.items) ? meta.items : []

  // 时间：2026-03-22；理由：标题行原 text-cyan-200/90 在深色底上对比不足；方法：主文案用 text-fg、次要信息用 text-muted/95，展开/收起重在可读
  return (
    <div className="rounded-lg border border-border bg-surface/80 px-3 py-2 text-xs w-full max-w-[85%]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 text-left text-fg/95 hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent/60 rounded"
      >
        <span>
          <span className="font-semibold text-fg">本次上下文</span>
          <span className="text-muted ml-2 text-[11px] sm:text-xs">
            已选 {meta.used_count ?? items.length} / 会话共 {meta.total_in_session ?? '—'} 条 · {strat}
          </span>
        </span>
        <span className="shrink-0 text-[11px] font-medium text-fg/90 tabular-nums">{open ? '收起' : '展开'}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 border-t border-border pt-2">
          {meta.query_preview && (
            <p className="text-[11px] text-fg/85 leading-relaxed">
              <span className="font-medium text-fg/90">
                {meta.strategy === 'article_writing' ? '用户指令（摘要）：' : '检索依据（摘要）：'}
              </span>
              <span className="text-muted">{meta.query_preview}</span>
            </p>
          )}
          <ul className="max-h-40 overflow-y-auto space-y-1">
            {items.map((it, idx) => (
              <li
                key={`${it.message_id || idx}-${it.index}`}
                className="flex flex-wrap gap-x-2 gap-y-0.5 rounded bg-black/20 px-2 py-1"
              >
                <span className="shrink-0 font-medium text-fg/90">
                  {it.display_role || (it.role === 'user' ? '用户' : '助手')}
                </span>
                <span className="shrink-0 rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                  {sourceLabel(it.source)}
                </span>
                <span className="min-w-0 break-words text-fg/80">{it.preview || '（空）'}</span>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-muted leading-snug">
            {meta.strategy === 'article_writing' && meta.article_writing_note
              ? meta.article_writing_note
              : '说明：以上为系统选入模型上下文的聊天记录摘要，用于核对「带了哪些历史」；不是模型的推理过程。若需完整思维链，须模型与 API 支持且另行合规开启。'}
          </p>
        </div>
      )}
    </div>
  )
}
