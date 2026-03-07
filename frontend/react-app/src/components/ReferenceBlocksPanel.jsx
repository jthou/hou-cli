/**
 * 参考块面板 UI：块列表、编辑/预览切换、新增
 * 供 ArticleWriting、WorkAssistant 复用
 */
import { useState, useEffect } from 'react'
import MarkdownPreview from './MarkdownPreview'

const BLOCK_CLS = 'rounded-lg border border-border bg-white/5 px-3 py-2 space-y-2'
const INPUT_CLS = 'flex-1 min-w-0 px-2 py-1 rounded bg-transparent border border-border/60 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-accent'
const TEXTAREA_CLS = 'w-full min-h-[120px] px-2 py-1.5 rounded bg-black/20 border border-border text-xs text-white placeholder-[#64748b] resize-y focus:outline-none focus:border-accent'

export default function ReferenceBlocksPanel({
  referenceBlocks,
  onAdd,
  onUpdate,
  onRemove,
}) {
  const [previewBlockId, setPreviewBlockId] = useState(null)
  useEffect(() => {
    if (previewBlockId && !referenceBlocks.some((b) => b.id === previewBlockId)) {
      setPreviewBlockId(null)
    }
  }, [referenceBlocks, previewBlockId])

  return (
    <div className="mt-2 space-y-2 max-h-[40vh] overflow-y-auto min-h-0">
      {referenceBlocks.length === 0 && (
        <p className="text-[11px] text-muted">
          可以在这里粘贴多段资料作为上下文，助手回答时会一并参考，但不会单独显示为消息。
        </p>
      )}
      {referenceBlocks.map((block, idx) => (
        <div key={block.id} className={BLOCK_CLS}>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-muted shrink-0">参考 {idx + 1}</span>
            <input
              type="text"
              value={block.title}
              onChange={(e) => onUpdate(block.id, 'title', e.target.value)}
              placeholder="可选：给这段资料起个标题"
              className={INPUT_CLS}
            />
            <button
              type="button"
              onClick={() => onRemove(block.id)}
              className="px-2 py-1 text-[11px] rounded border border-border text-muted hover:text-red-400 hover:border-red-400/60"
            >
              删除
            </button>
            <button
              type="button"
              onClick={() => setPreviewBlockId((prev) => (prev === block.id ? null : block.id))}
              className={`px-2 py-1 text-[11px] rounded border ${
                previewBlockId === block.id
                  ? 'border-accent/60 text-accent bg-accent/10'
                  : 'border-border text-muted hover:text-fg hover:bg-white/5'
              }`}
            >
              {previewBlockId === block.id ? '编辑' : '预览'}
            </button>
          </div>
          {previewBlockId === block.id ? (
            <div className="min-h-[120px] max-h-[280px] overflow-y-auto rounded bg-black/20 border border-border p-2">
              <MarkdownPreview
                markdown={block.content || ''}
                theme="dark"
                className="text-xs"
              />
            </div>
          ) : (
            <textarea
              rows={6}
              value={block.content}
              onChange={(e) => onUpdate(block.id, 'content', e.target.value)}
              placeholder="在这里粘贴这段参考资料文本（支持多段）。"
              className={TEXTAREA_CLS}
            />
          )}
        </div>
      ))}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onAdd}
          className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:text-fg hover:bg-white/5"
        >
          + 新增参考块
        </button>
        <p className="text-[11px] text-muted text-right">
          参考信息会自动加入每次请求的隐藏上下文，无需在输入框里重复粘贴。
        </p>
      </div>
    </div>
  )
}
